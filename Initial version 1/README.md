# 💰 Money Health Agent

A customer-ready personal finance dashboard that turns a plain bank statement CSV into a clear, visual, and actionable financial story — built for people with no finance background.

---

## ✨ Features

| Feature | Description |
|---|---|
| **Smart Categorisation** | Auto-labels every transaction (groceries, rent, subscriptions, etc.) using keyword rules |
| **Money Health Score** | Gauge chart scoring 0–100 based on saving behaviour, expense ratio, and cashflow |
| **Month-over-Month Deltas** | KPI cards show ▲/▼ change vs the previous period |
| **Budget Health Check** | Visual progress bars vs recommended % benchmarks per category |
| **Daily Spending Trend** | Area chart showing day-by-day expense patterns |
| **Recurring Bills View** | Isolated bar chart for rent, subscriptions, utilities, insurance, etc. |
| **AI Insights (optional)** | Claude-powered personalised insights via Anthropic API |
| **Plain-English Insights** | Rule-based fallback insights when no API key is provided |
| **Next Best Actions** | Prioritised action steps tailored to your financial situation |
| **Transaction Explorer** | Searchable, filterable full transaction table |
| **CSV Export** | Download the categorised transactions for further analysis |
| **Flexible CSV Parsing** | Handles BOM characters, different column names, $ signs, and parenthetical negatives |

---

## 🚀 Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Place your files in the same directory

```
your-project/
├── app.py
├── category_rules.csv
├── requirements.txt
└── sample_bank_statement.csv   # optional — for testing
```

### 3. Run the app

```bash
streamlit run app.py
```

---

## 📄 CSV Format

Your bank statement CSV must contain these three columns (exact names, or common variants):

| Column | Accepted Variants |
|---|---|
| `Date` | `transaction date`, `trans date`, `value date`, `posting date` |
| `Description` | `details`, `narration`, `narrative`, `memo`, `reference`, `particulars` |
| `Amount` | `debit/credit`, `value`, `net amount`, `transaction amount` |

- Positive amounts = income
- Negative amounts = expenses
- Supports `$` signs, commas, and parenthetical negatives like `(150.00)`

---

## 🤖 AI Insights (Optional)

1. Get a free API key at [console.anthropic.com](https://console.anthropic.com)
2. Paste it into the **Anthropic API Key** field in the sidebar
3. Click **Generate AI Insights**

Alternatively, set an environment variable before running:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
streamlit run app.py
```

Your API key is never stored or logged.

---

## ⚙️ Customising Categories

Edit `category_rules.csv` to add or change how transactions are categorised.

```
keyword,category,type
woolworths,Groceries,Expense
netflix,Subscriptions,Expense
salary,Salary,Income
```

Rules are matched on **keyword contains** (case-insensitive).

---

## 🏗️ Tech Stack

- **Python 3.10+**
- **Streamlit** — UI and web app framework
- **Pandas** — data processing
- **Plotly** — interactive charts
- **Requests** — Claude API integration

---

## ⚠️ Disclaimer

Money Health Agent is for personal education and spending awareness only.  
It does not provide financial, tax, investment, or credit advice.  
Always consult a licensed financial adviser for professional guidance.
