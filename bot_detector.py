#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np
import time
import logging
from tqdm import tqdm
from sklearn.ensemble import IsolationForest
from scipy.stats import kstest
from collections import Counter
import matplotlib.pyplot as plt

# ---------------------- НАСТРОЙКА ЛОГИРОВАНИЯ ----------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ---------------------- КОНФИГУРАЦИЯ (всё в одном файле) ----------------------
CONFIG = {
    'contamination': 0.05,           # доля аномалий для Isolation Forest
    'n_estimators': 200,             # деревьев в лесу
    'max_interval_sec': 3600,        # максимальная пауза (1 час), чтобы отсечь ночные перерывы
    'entropy_noise_level': 0.1,      # уровень шума для стохастического резонанса
    'ratio_clip': 100.0,             # обрезаем стохастический коэффициент сверху
    'random_state': 42,              # для воспроизводимости
    'weights': {                     # веса в гибридном скоре (ваш стиль)
        'entropy': 0.7,
        'ml': 0.3
    },
    'thresholds': {                  # пороги для вердиктов (как в старой версии)
        'critical': 0.8,
        'suspicious': 0.65,
        'speed_warning': 1.2         # порог скорости (сек)
    }
}


# ---------------------- ФУНКЦИИ ПРЕДОБРАБОТКИ ----------------------

def clean_paths_fast(df):
    """
    Очистка путей: маскировка UUID и цифровых ID, удаление общих префиксов.
    Если колонки нет, возвращаем df без изменений (защита).
    """
    if 'RequestPath' not in df.columns:
        logger.warning("Колонка 'RequestPath' отсутствует – пропускаем очистку путей.")
        df['path_clean'] = ''
        return df

    df['path_clean'] = df['RequestPath'].str.split('?').str[0]
    uuid_regex = r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}'
    df['path_clean'] = df['path_clean'].str.replace(uuid_regex, '{uuid}', regex=True)
    df['path_clean'] = df['path_clean'].str.replace(r'/\d+', '/{id}', regex=True)
    prefixes = ['/api/v1', '/v1', '/reservations-api/v1', '/reservations-api']
    pattern = '|'.join([re.escape(p) for p in prefixes])
    df['path_clean'] = df['path_clean'].str.replace(pattern, '', regex=True, case=False)
    df['path_clean'] = '/' + df['path_clean'].str.lstrip('/')
    return df


def entropy_with_noise_fast(intervals, noise_level=0.1, random_state=None):
    """
    Стохастический резонанс с адаптивным шумом.
    Возвращает (исходная_энтропия, отношение_шум/оригинал).
    """
    n = len(intervals)
    if n < 2:
        return 0.0, 1.0

    m_int = np.mean(intervals)
    if m_int <= 0:
        return 0.0, 1.0

    # Количество бинов по правилу квадратного корня
    bins = int(np.sqrt(n)) + 2
    # Гистограмма без density, чтобы самим нормировать вероятности
    hist, _ = np.histogram(intervals, bins=bins, density=False)
    p = hist / (hist.sum() + 1e-12)
    h_orig = -np.sum(p[p > 0] * np.log2(p[p > 0]))

    # Адаптивный шум
    std_int = np.std(intervals)
    adaptive_noise = noise_level * (m_int + std_int + 1e-6)
    rng = np.random.default_rng(random_state)
    noise = rng.normal(0, adaptive_noise, size=n)
    noisy = np.clip(intervals + noise, 1e-6, None)

    hist_n, _ = np.histogram(noisy, bins=bins, density=False)
    p_n = hist_n / (hist_n.sum() + 1e-12)
    h_noisy = -np.sum(p_n[p_n > 0] * np.log2(p_n[p_n > 0]))

    # Отношение с клиппингом
    ratio = h_noisy / (h_orig + 1e-12)
    ratio = np.clip(ratio, 0, CONFIG.get('ratio_clip', 100))
    return h_orig, ratio


def compute_user_features(group, config):
    """
    Вычисляет все признаки для одного пользователя.
    Возвращает словарь с признаками или None, если данных недостаточно.
    """
    intervals = group['interval'].dropna().values
    intervals = intervals[intervals <= config['max_interval_sec']]
    if len(intervals) < 4:
        return None

    # Основные статистики
    mean_int = np.mean(intervals)
    cv_int = np.std(intervals) / (mean_int + 1e-6)

    # Энтропия и стохастический тест
    h_orig, h_ratio = entropy_with_noise_fast(
        intervals,
        noise_level=config['entropy_noise_level'],
        random_state=config['random_state']
    )

    # Разнообразие эндпоинтов
    diversity = len(group['endpoint'].unique()) / len(group) if len(group) > 0 else 0

    # Дополнительные признаки ритмичности
    unique_ratio = len(np.unique(intervals)) / len(intervals)
    if len(intervals) > 1:
        autocorr = np.corrcoef(intervals[:-1], intervals[1:])[0, 1]
        autocorr = 0 if np.isnan(autocorr) else autocorr
    else:
        autocorr = 0

    # Тест на экспоненциальность (p-value)
    try:
        _, p_exp = kstest(intervals, 'expon', args=(0, mean_int))
    except:
        p_exp = 1.0

    # Доля трёх самых частых интервалов
    if len(intervals) >= 3:
        counts = Counter(intervals)
        top3_freq = sum([c for _, c in counts.most_common(3)]) / len(intervals)
    else:
        top3_freq = 1.0

    return {
        'userId': group['userId'].iloc[0],
        'mean_int': mean_int,
        'cv_int': cv_int,
        'entropy_orig': h_orig,
        'stochastic_ratio': h_ratio,
        'diversity': diversity,
        'unique_interval_ratio': unique_ratio,
        'autocorr_lag1': autocorr,
        'p_value_exponential': p_exp,
        'top3_freq': top3_freq,
        'num_ops': len(group)
    }


# ---------------------- ОСНОВНАЯ ФУНКЦИЯ ----------------------

def main(input_file, config=None):
    if config is None:
        config = CONFIG

    start_time = time.time()
    logger.info(f"🚀 Запуск анализа логов: {input_file}")

    # 1. Загрузка данных
    try:
        df = pd.read_csv(input_file, parse_dates=['timestamp'])
    except Exception as e:
        logger.error(f"Не удалось загрузить файл: {e}")
        return

    required_cols = ['userId', 'RequestId', 'timestamp']
    for col in required_cols:
        if col not in df.columns:
            logger.error(f"В файле отсутствует обязательная колонка: {col}")
            return

    logger.info(f"Загружено записей: {len(df)}")

    # 2. Очистка путей (защита от отсутствия RequestPath внутри функции)
    df = clean_paths_fast(df)

    # 3. Группировка по операциям
    logger.info("Группировка операций (RequestId)...")
    ops = df.groupby(['userId', 'RequestId'], observed=True).agg(
        op_start=('timestamp', 'min'),
        endpoint=('path_clean', 'first')
    ).reset_index().sort_values(['userId', 'op_start'])

    # 4. Интервалы между операциями
    ops['interval'] = ops.groupby('userId', observed=True)['op_start'].diff().dt.total_seconds()

    # 5. Расчёт признаков
    logger.info("Расчёт признаков для пользователей...")
    features = []
    user_groups = ops.groupby('userId', observed=True)

    for user_id, group in tqdm(user_groups, desc="Пользователи", unit="пользователь"):
        feat = compute_user_features(group, config)
        if feat is not None:
            features.append(feat)

    if not features:
        logger.error("Недостаточно данных ни для одного пользователя.")
        return

    features_df = pd.DataFrame(features)
    logger.info(f"Проанализировано пользователей: {len(features_df)}")

    # 6. Isolation Forest
    logger.info("Обучение модели Isolation Forest...")
    ml_cols = ['mean_int', 'cv_int', 'entropy_orig', 'stochastic_ratio', 'diversity',
               'unique_interval_ratio', 'autocorr_lag1', 'p_value_exponential', 'top3_freq']
    ml_cols = [c for c in ml_cols if c in features_df.columns]

    iso = IsolationForest(
        n_estimators=config['n_estimators'],
        contamination=config['contamination'],
        n_jobs=-1,
        random_state=config['random_state']
    )
    iso.fit(features_df[ml_cols])

    # Нормализация скора аномалии в [0,1] (1 = бот)
    raw_scores = iso.decision_function(features_df[ml_cols])
    min_score, max_score = raw_scores.min(), raw_scores.max()
    if max_score - min_score < 1e-12:
        features_df['ml_score'] = 0.0
    else:
        features_df['ml_score'] = 1 - (raw_scores - min_score) / (max_score - min_score + 1e-12)

    # 7. Гибридный скор (ваши веса 0.7/0.3)
    # Логарифмируем стохастическое отношение
    log_ratio = np.log1p(features_df['stochastic_ratio'].clip(lower=0, upper=config['ratio_clip']))
    s_ratio_norm = (log_ratio - log_ratio.min()) / (log_ratio.max() - log_ratio.min() + 1e-12)

    w_ent = config['weights']['entropy']
    w_ml = config['weights']['ml']
    features_df['FINAL_PROBABILITY'] = w_ent * s_ratio_norm + w_ml * features_df['ml_score']

    # 8. Вердикты (ваши старые пороги + проверка скорости)
    def get_verdict(row):
        prob = row['FINAL_PROBABILITY']
        if prob > config['thresholds']['critical']:
            return "🔴 КРИТИЧНО: Явный бот (Таймер)"
        if prob > config['thresholds']['suspicious']:
            return "🟠 ПОДОЗРИТЕЛЬНО: Агрессивный скрипт"
        if row['mean_int'] < config['thresholds']['speed_warning']:
            return "🟡 ВНИМАНИЕ: Сверхчеловеческая скорость"
        return "🟢 НОРМА: Похож на человека"

    features_df['Verdict'] = features_df.apply(get_verdict, axis=1)

    # 9. Отчёт
    report = features_df.rename(columns={
        'userId': 'ID_Пользователя',
        'mean_int': 'Средняя_пауза_сек',
        'entropy_orig': 'Хаотичность_кликов',
        'stochastic_ratio': 'Тест_на_робота',
        'FINAL_PROBABILITY': 'Вероятность_Бота',
        'Verdict': 'Вердикт'
    })
    report = report.sort_values('Вероятность_Бота', ascending=False)

    out_file = 'GIS_EPD_Final_Report.csv'
    report.to_csv(out_file, index=False, encoding='utf-8-sig')
    logger.info(f"✅ Отчёт сохранён в {out_file}")

    # 10. Визуализация
    try:
        plt.figure(figsize=(10, 6))
        scatter = plt.scatter(
            features_df['entropy_orig'],
            features_df['stochastic_ratio'],
            c=features_df['FINAL_PROBABILITY'],
            cmap='coolwarm',
            alpha=0.6
        )
        plt.colorbar(scatter, label='Вероятность бота')
        plt.xlabel('Хаотичность (исходная энтропия)')
        plt.ylabel('Тест на робота (стохастическое отношение)')
        plt.title('Cyber-Geometric Distribution: Humans vs. Snowflakes')
        plt.grid(True, linestyle='--', alpha=0.5)
        plt.savefig('snowflakes_plot.png', dpi=150)
        plt.close()
        logger.info("📊 График сохранён как snowflakes_plot.png")
    except Exception as e:
        logger.warning(f"Не удалось сохранить график: {e}")

    elapsed = time.time() - start_time
    logger.info(f"⏱️ Время выполнения: {elapsed:.2f} сек.")


if __name__ == "__main__":
    main('raw_request.csv')