    def calculate_entropy(x):
        if len(x) <= 1: return pd.Series([0.0, 0.0])
        probs = x.value_counts(normalize=True)
        h = -(probs * np.log2(probs)).sum()
        h_max = np.log2(len(probs)) if len(probs) > 1 else 0
        h_norm = (h / h_max * 100) if h_max > 0 else 0
        return pd.Series([h, h_norm])

    entropy_results = grouped['path_clean'].apply(calculate_entropy).unstack()
    entropy_results.columns = ['Entropy_bits', 'Diversity_%']

    final_df = pd.merge(agg_df, entropy_results, on='userId')

    # 5. Классификация (Золотая логика)
    def classify(row):
        # Порог отсечки 5 запросов
        if row['Total_Req'] <= 5:
            return 'definite_bots' if row['RPM'] > 100 else 'humans'

        # Основные признаки ботов
        if row['RPM'] > 100: return 'definite_bots'  # Скоростной бот
        if row['Diversity_%'] < 10: return 'definite_bots'  # Цикличный бот
        if row['Diversity_%'] < 30: return 'possible_bots'  # Подозрительный (серая зона)

        return 'humans'

    final_df['category'] = final_df.apply(classify, axis=1)

    # --- ВЫВОД ОТЧЕТОВ ---
    def print_stat(title, data):
        total = len(data)
        stats = data['category'].value_counts()
        print(f"\n{title}")
        print("-" * 50)
        for cat in ['definite_bots', 'possible_bots', 'humans']:
            count = stats.get(cat, 0)
            print(f"STAT;{cat};{count};{(count / total * 100) if total > 0 else 0:.2f}%")

        all_bots = stats.get('definite_bots', 0) + stats.get('possible_bots', 0)
        print(f"STAT;bots_all;{all_bots};{(all_bots / total * 100) if total > 0 else 0:.2f}%")
        print("=" * 50)

    print("\n" + "=" * 50)
    print_stat(f"ОБЩАЯ СТАТИСТИКА (Всего ID: {len(final_df)})", final_df)

    active_df = final_df[final_df['Total_Req'] > 5]
    print_stat(f"АНАЛИЗ АКТИВНЫХ ПОЛЬЗОВАТЕЛЕЙ (Запросов > 5)", active_df)

    # Сохранение результатов
    os.makedirs(output_dir, exist_ok=True)
    report_path = os.path.join(output_dir, "golden_entropy_report_2026.csv")
    final_df.to_csv(report_path, index=False)

    print(f"✅ Анализ завершен за {round(time.time() - start_time, 2)} сек.")
    print(f"📁 Отчет сохранен: {report_path}")


if __name__ == "__main__":
    # Укажи путь к своему CSV
    csv_file = 'C:/Users/MyNew/PycharmProjects/pythonProjectSentinel/raw_request.csv'
    run_golden_standard_analyzer(csv_file)
