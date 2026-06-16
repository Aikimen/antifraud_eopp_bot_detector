Behaviour-based Bot Detection Engine
Author: Eugene Arkhipov + AI help
Project Status: Functional prototype (actively maintained)

📌 Project Overview
A lightweight Python analytics utility designed to identify automated traffic (bots, scripts, timed attacks) in web service logs. Unlike traditional signature-based methods, this engine analyses temporal interaction patterns between the user and the API, applying information theory and unsupervised machine learning.

Core idea: a human clicks with chaotic, naturally varying pauses; a script operates rhythmically like a metronome or produces statistically degenerate sequences. The detector catches these differences via stochastic resonance, interval entropy analysis, and an Isolation Forest model.

🔥 Key Features
Temporal Interval Analysis – computation of pauses between consecutive operations for each user, filtering out "overnight" gaps.

Stochastic Resonance – adding adaptive noise to the interval distribution and measuring the entropy change: regular (bot) patterns cause a sharp entropy increase, while chaotic human patterns remain almost unchanged.

Extended Rhythm Metrics – autocorrelation, unique interval ratio, exponential distribution test, frequency of the three most common pauses.

Unsupervised Machine Learning (Isolation Forest) – automatic detection of anomalous users in the feature space, no labeled data required.

Hybrid Scoring – combination of the stochastic test and the ML score into a single "bot probability" with configurable weights.

Interpretable Verdicts – four-tier classification: normal, suspicious (speed bot), aggressive script, critical timer-based bot.

Visualisation – scatter plot "Chaos vs Robot Test" with colour mapping for bot probability.

Resilience to incomplete data – gracefully handles missing columns (e.g., request URL) without breaking.

🛠️ Requirements & Tech Stack
Language: Python 3.8+

Libraries: pandas, numpy, scipy, scikit-learn, matplotlib, tqdm

Install dependencies:

bash
pip install pandas numpy scipy scikit-learn matplotlib tqdm
🚀 How It Works & Usage
Data Preparation: Place your log CSV in the project root. Required columns: userId, RequestId, timestamp. If RequestPath is present, endpoint diversity analysis is activated.

Execution: Run the script:

bash
python bot_detector.py
The input filename can be changed in the if __name__ == "__main__": block (default is raw_request.csv).

Outputs: The script generates:

GIS_EPD_Final_Report.csv – table with per-user scores: average pause, click chaos, robot test, final probability, and verdict.

snowflakes_plot.png – visualisation of the bot detection landscape.

📁 Directory Structure
text
/behaviour-bot-detector
│
├── bot_detector.py          # Main analytical pipeline
├── raw_request.csv          # Input data (not included in repo)
├── GIS_EPD_Final_Report.csv # Output report
├── snowflakes_plot.png      # Visualisation
└── README.md                # This documentation
⚙️ Configuration (inside the script)
All key parameters are stored in the CONFIG dictionary at the top of the file, making them easy to adjust:

Verdict thresholds (critical, suspicious, speed_warning)

Isolation Forest parameters (contamination, n_estimators)

Hybrid score weights (entropy / ml)

Noise level for stochastic resonance, and more.

💡 Why This Matters (Business & Security Impact)
Traditional WAFs and signature-based filters miss "silent" bots that disguise themselves as legitimate traffic. Temporal behavioural analysis:

Detects timer-based attacks (credential stuffing, automated enumeration) before damage is done.

Does not require bot examples (unsupervised), thus effective against novel, unseen scripts.

Reduces SOC analyst workload by providing a pre-ranked list of suspicious users.

Easily integrates into offline log audit pipelines, serving as an additional intelligence source for blocking rules.

Ideal for API-driven systems where each user operation is logged with a request ID and timestamp.
