# Web Traffic & Bot Detection Analyzer (Shannon Entropy Engine)
**Author:** Eugene Arkhipov  
**Project Status:** Functional MVP 

## 📌 Project Overview
A lightweight Python analytical utility designed to parse, sanitize, and analyze web server access logs to detect automated bot activity. 

Instead of simple signature matching, this script evaluates user behavior by computing **Shannon Entropy** to measure the structural diversity of visited URLs alongside request intensity metrics (Requests Per Minute - RPM).

## 🔥 Key Features
* **Vectorized Log Sanitization:** Highly optimized string manipulation using Pandas and Regular Expressions to clean dynamic path parameters (UUIDs, dynamic IDs, query strings) into unified endpoints (e.g., changing `/api/v1/user/123-abc` to `/{id}`).
* **Shannon Entropy Computation:** Calculates data entropy metrics for each user to analyze behavioral randomness. Low entropy signifies repetitive, non-human, structured routing paths (typical cyclic bots).
* **Behavioral Heuristics Classification:** Automatically categories traffic patterns into three operational states:
  * `definite_bots` — High speed (RPM > 100) or extremely low navigation diversity (< 10%).
  * `possible_bots` — Users sitting inside suspicious behavioral thresholds (Diversity < 30%).
  * `humans` — Standard organic navigation footprints.
* **Dual-Layer Analytics Reports:** Computes statistical metrics across the full log structure, isolating high-frequency actors to minimize false positives.

## 🛠️ Requirements & Tech Stack
* **Language:** Python 3.8+
* **Libraries:** `pandas`, `numpy`

To install dependencies:
```bash
pip install pandas numpy
```

## 🚀 How It Works & Usage
1. Place your log CSV file into your working environment (Required columns: `timestamp`, `RequestPath`, `userId`, `ipAddress`).
2. Run the main analytical engine:
   ```bash
   python main.py
   ```
3. Check execution logs in your terminal and find your processed output inside the `/analysis_results` folder.
