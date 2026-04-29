import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import io
import os

st.set_page_config(page_title="Money Health", page_icon="💰", layout="wide")

# ══════════════════════════════════════════════════════════
#  CONSTANTS
# ══════════════════════════════════════════════════════════
FIXED_CATS    = {"Rent","Childcare","Insurance","Utilities","Phone","Internet","Car Expenses"}
BUDGET_GUIDE  = {"Rent":30,"Groceries":12,"Eating Out":5,"Transport":5,
                 "Subscriptions":3,"Shopping":5,"Health":5,"Utilities":6}
TREEMAP_SCALE = ["#fef0eb","#f5c4ab","#ec996b","#e06d35","#c8501a","#8c300a"]
DAY_ORDER     = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]

# ══════════════════════════════════════════════════════════
#  CSS  — Syne display font · DM Sans body · warm cream canvas
# ══════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;1,400&display=swap');

/* ── Reset ── */
html,body,[class*="css"]{font-family:'DM Sans',sans-serif;}

/* ── Canvas ── */
[data-testid="stAppViewContainer"]{background:#f0ebe4;}
.block-container{padding:1.4rem 2.6rem 4rem;max-width:1480px;}

/* ── Sidebar ── */
[data-testid="stSidebar"]{background:#16110d!important;border-right:none!important;}
[data-testid="stSidebar"] *{color:#e0d5ca!important;}
[data-testid="stSidebar"] label{
    color:#7a6e64!important;font-size:10px!important;
    font-family:'DM Sans',sans-serif!important;
    text-transform:uppercase;letter-spacing:.08em;}
[data-testid="stSidebar"] .stButton>button{
    background:#e06d35!important;border:none!important;color:#fff!important;
    border-radius:12px!important;font-weight:600!important;letter-spacing:.02em;}
[data-testid="stSidebar"] .stDownloadButton>button{
    background:#2a2018!important;border:1px solid #3a3025!important;
    color:#c8bcb0!important;border-radius:12px!important;}

/* ── Verdict banner ── */
.verdict{
    border-radius:28px;padding:38px 48px;
    margin-bottom:24px;position:relative;overflow:hidden;
    display:flex;align-items:center;gap:48px;
}
.verdict::before{
    content:'';position:absolute;right:-60px;top:-60px;
    width:300px;height:300px;border-radius:50%;
    background:rgba(255,255,255,.06);
}
.v-score{
    font-family:'Syne',sans-serif;
    font-size:108px;font-weight:800;line-height:.85;
    letter-spacing:-5px;flex-shrink:0;
}
.v-right{}
.v-label{font-size:12px;font-weight:600;letter-spacing:.12em;
          text-transform:uppercase;opacity:.7;margin-bottom:6px;}
.v-title{font-family:'Syne',sans-serif;font-size:26px;
          font-weight:800;line-height:1.25;color:#fff;margin-bottom:8px;}
.v-sub{font-size:14px;line-height:1.6;opacity:.75;color:#fff;max-width:480px;}

/* ── KPI strip ── */
.kpi{
    background:#fff;border-radius:22px;
    padding:22px 24px 18px;
    box-shadow:0 2px 0 rgba(0,0,0,.04),0 6px 20px rgba(42,28,14,.08);
    margin-bottom:16px;
}
.kpi-label{font-size:10px;font-weight:700;text-transform:uppercase;
           letter-spacing:.09em;color:#b8a898;margin-bottom:6px;font-family:'DM Sans',sans-serif;}
.kpi-value{font-family:'Syne',sans-serif;font-size:28px;font-weight:800;
           line-height:1.05;letter-spacing:-.5px;}
.kpi-delta{font-size:12px;margin-top:6px;font-weight:500;}
.up{color:#1a9e75;}.down{color:#d94838;}.neu{color:#c0b6ae;}

/* ── Section label ── */
.sec{
    font-family:'Syne',sans-serif;
    font-size:14px;font-weight:800;letter-spacing:.04em;
    text-transform:uppercase;color:#8c7c6c;
    margin:0 0 14px;display:flex;align-items:center;gap:8px;
}
.sec::after{content:'';flex:1;height:1px;background:#e0d8cf;}

/* ── Chart card ── */
.cc{
    background:#fff;border-radius:22px;
    padding:22px 22px 8px;
    box-shadow:0 2px 0 rgba(0,0,0,.04),0 6px 20px rgba(42,28,14,.08);
    margin-bottom:16px;
}

/* ── Insight / Action cards ── */
.ins{
    background:#faf6f1;border-left:3px solid #e06d35;
    border-radius:0 14px 14px 0;
    padding:13px 18px;margin-bottom:10px;
    font-size:14px;color:#2a1c10;line-height:1.65;
}
.act{
    background:#fff;border-radius:16px;padding:14px 18px;
    margin-bottom:10px;border:1px solid #e8e0d6;
    box-shadow:0 1px 4px rgba(42,28,14,.05);
    display:flex;gap:12px;align-items:flex-start;
}
.act-n{
    min-width:24px;height:24px;background:#fdeede;color:#c85a10;
    border-radius:50%;display:flex;align-items:center;justify-content:center;
    font-size:11px;font-weight:800;font-family:'Syne',sans-serif;flex-shrink:0;margin-top:2px;
}
.act-t{font-weight:700;font-size:13.5px;color:#1a1008;margin-bottom:3px;font-family:'Syne',sans-serif;}
.act-d{font-size:13px;color:#8c7c6c;line-height:1.55;}

/* ── Top-transaction callout ── */
.txn{
    background:#fff;border-radius:18px;padding:16px 20px;
    margin-bottom:10px;border:1px solid #e8e0d6;
    box-shadow:0 1px 4px rgba(42,28,14,.05);
}
.txn-amt{font-family:'Syne',sans-serif;font-size:24px;font-weight:800;
          color:#d94838;letter-spacing:-.5px;}
.txn-desc{font-size:13px;font-weight:600;color:#2a1c10;margin:3px 0 2px;}
.txn-meta{font-size:11px;color:#b8a898;}

/* ── Sub row ── */
.sub-row{
    display:flex;justify-content:space-between;align-items:center;
    padding:11px 0;border-bottom:1px solid #f0e8de;
}
.sub-row:last-child{border-bottom:none;}
.sub-name{font-size:13.5px;font-weight:600;color:#2a1c10;}
.sub-cat{font-size:11px;color:#b8a898;margin-top:1px;}
.sub-amt{font-family:'Syne',sans-serif;font-size:16px;font-weight:800;color:#d94838;}

/* ── Split stat ── */
.split-stat{
    background:#fff;border-radius:18px;padding:18px 22px;
    box-shadow:0 2px 0 rgba(0,0,0,.04),0 6px 20px rgba(42,28,14,.08);
    margin-bottom:10px;display:flex;gap:16px;align-items:center;
}
.split-icon{font-size:32px;}
.split-label{font-size:11px;font-weight:700;text-transform:uppercase;
              letter-spacing:.08em;color:#b8a898;margin-bottom:4px;}
.split-val{font-family:'Syne',sans-serif;font-size:22px;font-weight:800;color:#2a1c10;}
.split-sub{font-size:12px;color:#a09080;margin-top:2px;}

/* ── Privacy / footer ── */
.privacy{
    background:#e8e0d6;border-radius:14px;padding:11px 18px;
    margin-bottom:24px;font-size:12.5px;color:#7a6e64;line-height:1.55;
}
.disclaimer{
    background:#e4dcd2;border-radius:14px;padding:12px 20px;
    font-size:11px;color:#a09080;text-align:center;margin-top:28px;line-height:1.6;
}

/* ── Streamlit fixes ── */
[data-testid="stFileUploaderDropzone"]{
    background:#fff!important;border:2px dashed #d4cbbf!important;border-radius:16px!important;}
[data-testid="stTabs"] [data-baseweb="tab"]{
    font-family:'DM Sans',sans-serif!important;font-weight:600!important;}
div[data-testid="stHorizontalBlock"]{gap:16px;}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════
def money(v, signed=False):
    if signed:
        return f"+${v:,.0f}" if v >= 0 else f"-${abs(v):,.0f}"
    return f"${v:,.2f}"

def moneyf(v):   return f"${v:,.2f}"

def delta_html(curr, prev, invert=False):
    if prev == 0: return '<span class="neu">—</span>'
    d = (curr - prev) / abs(prev) * 100
    cls   = ("down" if d > 0 else "up") if invert else ("up" if d > 0 else "down")
    arrow = "▲" if d > 0 else "▼"
    return f'<span class="{cls}">{arrow} {abs(d):.1f}%</span>'

@st.cache_data
def load_rules():
    path  = os.path.join(os.path.dirname(__file__), "category_rules.csv")
    rules = pd.read_csv(path)
    rules["keyword"] = rules["keyword"].astype(str).str.lower().str.strip()
    return rules

def categorise(desc, amount, rules):
    d = str(desc).lower()
    for _, r in rules.iterrows():
        if r["keyword"] in d:
            return r["category"], r["type"]
    return ("Other Income","Income") if amount > 0 else ("Other Expense","Expense")

def score_color(s):
    if s >= 80: return "#2db88a"
    if s >= 65: return "#5b7cf0"
    if s >= 45: return "#e09a2e"
    return "#e05c4e"

def score_bg(s):
    if s >= 80: return "#082b1a"
    if s >= 65: return "#0a1830"
    if s >= 45: return "#28180a"
    return "#280a08"

def score_meta(s):
    if s >= 80: return "Excellent"
    if s >= 65: return "Healthy"
    if s >= 45: return "Needs Attention"
    return "At Risk"

def verdict_sentence(s, net, sr, top_cat):
    tc = top_cat or "spending"
    if s >= 80: return f"You're in great financial shape — saving {sr:.0f}% of your income and staying well within budget."
    if s >= 65: return f"Your finances are healthy. Keeping an eye on {tc} will help you improve further."
    if s >= 45: return f"A few things need attention. Focusing on {tc} will have the biggest impact."
    return "Your spending is outpacing your income right now. Let's look at where to start." if net < 0 \
        else "There are some areas under pressure — small changes can make a real difference."

def calc_score(income, expense, net, sr, sub_total):
    s = 0
    if income > 0:    s += 20
    if net > 0:       s += 25
    if sr >= 20:      s += 25
    elif sr >= 10:    s += 15
    elif sr > 0:      s += 8
    r = expense / income if income > 0 else 1
    if r <= 0.75:     s += 15
    elif r <= 0.90:   s += 8
    sr2 = sub_total / income if income > 0 else 0
    if sr2 <= 0.03:   s += 15
    elif sr2 <= 0.06: s += 8
    return min(s, 100)

def get_ai_insights(api_key, summary):
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key":api_key,"content-type":"application/json",
                     "anthropic-version":"2023-06-01"},
            json={"model":"claude-sonnet-4-20250514","max_tokens":600,
                  "messages":[{"role":"user","content":(
                      "You are a warm personal finance coach for everyday people.\n"
                      "Write exactly 4 short insights from the summary below.\n"
                      "Rules: start each with a relevant emoji · max 2 plain sentences · "
                      "mention actual numbers · be honest and encouraging · no intro/outro.\n\n"
                      f"Summary:\n{summary}")}]},
            timeout=15)
        if r.status_code == 200:
            return r.json()["content"][0]["text"]
    except Exception:
        pass
    return None

def base_layout(h=360, **kw):
    return dict(
        height=h,
        paper_bgcolor="#ffffff", plot_bgcolor="#ffffff",
        font={"family":"'DM Sans',sans-serif","color":"#5a4e42"},
        margin=dict(t=14,b=28,l=4,r=4),
        **kw)

def ax(grid=True):
    base = dict(title="", zeroline=False, linecolor="#ddd4c8")
    if grid: base.update(showgrid=True, gridcolor="#f4ede4", gridwidth=1)
    else:    base.update(showgrid=False)
    return base


# ══════════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### Filters")
    _month_ph = st.empty()
    _cat_ph   = st.empty()
    st.markdown("---")
    st.markdown("### AI Coach")
    api_key = st.text_input("Anthropic API Key", type="password",
                             placeholder="sk-ant-…",
                             help="Optional — get one at console.anthropic.com")
    run_ai  = st.button("✦ Generate Insights", use_container_width=True)
    st.markdown("---")
    st.markdown("### Export")
    _export_ph = st.empty()


# ══════════════════════════════════════════════════════════
#  UPLOAD
# ══════════════════════════════════════════════════════════
st.markdown("""
<div class="privacy">
  🔒 <b>Privacy:</b> Your file is processed only in this browser session — never stored or shared.
  For personal tracking only, not financial advice.
</div>
""", unsafe_allow_html=True)

up = st.file_uploader("Upload your bank statement CSV",type=["csv"],
                       help="Needs: Date · Description · Amount columns")

if up is None:
    c1,c2,c3 = st.columns(3)
    for col,(icon,title,desc) in zip([c1,c2,c3],[
        ("📂","Upload a CSV","Export from your bank's app — any CSV with Date, Description, and Amount columns."),
        ("⚡","Instant Categorisation","Every transaction auto-labelled: groceries, rent, subscriptions, transport, and more."),
        ("🎯","Personalised Actions","Plain-English summary and specific steps — no jargon, no complexity."),
    ]):
        with col:
            st.markdown(f"""
            <div style="background:#fff;border-radius:22px;padding:34px 26px;text-align:center;
                        border:1px solid #ddd4c8;box-shadow:0 6px 20px rgba(42,28,14,.07)">
              <div style="font-size:38px;margin-bottom:14px">{icon}</div>
              <div style="font-family:Syne,sans-serif;font-size:15px;font-weight:800;
                          color:#1a1008;margin-bottom:8px">{title}</div>
              <div style="font-size:13px;color:#9a8e82;line-height:1.6">{desc}</div>
            </div>""", unsafe_allow_html=True)
    st.stop()


# ══════════════════════════════════════════════════════════
#  LOAD & CLEAN
# ══════════════════════════════════════════════════════════
rules = load_rules()
try:
    df = pd.read_csv(io.BytesIO(up.read()), encoding="utf-8-sig")
except Exception:
    st.error("Could not read the file. Please upload a valid UTF-8 CSV.")
    st.stop()

df.columns = df.columns.str.strip()
col_map = {}
for col in df.columns:
    cl = col.lower().strip()
    if cl in ["date","transaction date","trans date","value date","posting date"]:
        col_map["Date"] = col
    elif cl in ["description","details","narration","narrative","memo","reference","particulars"]:
        col_map["Description"] = col
    elif cl in ["amount","debit/credit","value","net amount","transaction amount"]:
        col_map["Amount"] = col

if len(col_map) < 3:
    st.error(f"Need columns: Date, Description, Amount. Found: {df.columns.tolist()}")
    st.stop()

df = df.rename(columns={v:k for k,v in col_map.items()})
extra = [c for c in df.columns if c not in ["Date","Description","Amount"]]
df = df[["Date","Description","Amount"]+extra]
df["Date"]   = pd.to_datetime(df["Date"], errors="coerce", dayfirst=True)
df["Amount"] = (df["Amount"].astype(str)
                .str.replace(r"[\$,\s]","",regex=True)
                .str.replace(r"\((.+?)\)",r"-\1",regex=True)
                .pipe(pd.to_numeric, errors="coerce"))
df = df.dropna(subset=["Date","Amount"]).sort_values("Date")
df[["Category","Type"]] = df.apply(
    lambda r: pd.Series(categorise(r["Description"], r["Amount"], rules)), axis=1)
df["Month"] = df["Date"].dt.to_period("M").astype(str)
df["Day"]   = df["Date"].dt.date
df["DOW"]   = df["Date"].dt.strftime("%a")

# Fill sidebar filters now that df is loaded
sel_month = _month_ph.selectbox("Month", ["All"]+sorted(df["Month"].unique()))
sel_cat   = _cat_ph.selectbox("Category", ["All"]+sorted(df["Category"].unique()))
_export_ph.download_button("⬇ Download Categorised CSV",
    data=df.to_csv(index=False).encode("utf-8"),
    file_name="money_health_transactions.csv", mime="text/csv",
    use_container_width=True)


# ══════════════════════════════════════════════════════════
#  METRICS
# ══════════════════════════════════════════════════════════
fdf = df.copy()
if sel_month != "All": fdf = fdf[fdf["Month"] == sel_month]
if sel_cat   != "All": fdf = fdf[fdf["Category"] == sel_cat]

inc_df = fdf[fdf["Type"] == "Income"]
exp_df = fdf[fdf["Type"] == "Expense"]

total_income  = inc_df["Amount"].sum()
total_expense = abs(exp_df["Amount"].sum())
net           = total_income - total_expense
savings_rate  = (net / total_income * 100) if total_income > 0 else 0

exp_summary = (exp_df.groupby("Category")["Amount"].sum().abs()
               .reset_index().rename(columns={"Amount":"Total"})
               .sort_values("Total", ascending=False))

sub_total    = exp_df[exp_df["Category"].isin(["Subscription","Subscriptions"])]["Amount"].abs().sum()
fixed_total  = exp_df[exp_df["Category"].isin(FIXED_CATS)]["Amount"].abs().sum()
flex_total   = total_expense - fixed_total
health_score = calc_score(total_income, total_expense, net, savings_rate, sub_total)
s_label      = score_meta(health_score)
top_cat      = exp_summary.iloc[0]["Category"] if not exp_summary.empty else None

# Previous period
all_months = sorted(df["Month"].unique())
if sel_month != "All" and sel_month in all_months:
    idx  = all_months.index(sel_month)
    prev = df[df["Month"] == all_months[idx-1]] if idx > 0 else pd.DataFrame()
else:
    prev = pd.DataFrame()

prev_inc = prev[prev["Type"]=="Income"]["Amount"].sum() if not prev.empty else 0
prev_exp = abs(prev[prev["Type"]=="Expense"]["Amount"].sum()) if not prev.empty else 0
prev_net = prev_inc - prev_exp


# ══════════════════════════════════════════════════════════
#  §0  VERDICT BANNER
# ══════════════════════════════════════════════════════════
sc = score_color(health_score)
bg = score_bg(health_score)
vtext = verdict_sentence(health_score, net, savings_rate, top_cat)

st.markdown(f"""
<div class="verdict" style="background:{bg}">
  <div class="v-score" style="color:{sc}">{health_score}</div>
  <div class="v-right">
    <div class="v-label">Money Health Score &nbsp;·&nbsp; {s_label}</div>
    <div class="v-title">{vtext}</div>
    <div class="v-sub">
      Income <b>{moneyf(total_income)}</b> &nbsp;·&nbsp;
      Expenses <b>{moneyf(total_expense)}</b> &nbsp;·&nbsp;
      Saved <b>{money(net, signed=True)}</b>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════
#  §1  KPI STRIP
# ══════════════════════════════════════════════════════════
k1,k2,k3,k4 = st.columns(4)

fixed_pct = (fixed_total / total_expense * 100) if total_expense > 0 else 0
flex_pct  = 100 - fixed_pct
avg_daily = total_expense / max(len(exp_df["Day"].unique()), 1)
txn_count = len(fdf)

with k1:
    nc = "#1a9e75" if net >= 0 else "#d94838"
    st.markdown(f"""
    <div class="kpi">
      <div class="kpi-label">Money Left Over</div>
      <div class="kpi-value" style="color:{nc}">{money(net,signed=True)}</div>
      <div class="kpi-delta">{delta_html(net,prev_net)} vs last period</div>
    </div>""", unsafe_allow_html=True)

with k2:
    src = "#1a9e75" if savings_rate>=20 else "#e09a2e" if savings_rate>=10 else "#d94838"
    st.markdown(f"""
    <div class="kpi">
      <div class="kpi-label">Savings Rate</div>
      <div class="kpi-value" style="color:{src}">{savings_rate:.1f}%</div>
      <div class="kpi-delta"><span class="neu">Goal: 20% · You're at {savings_rate:.0f}%</span></div>
    </div>""", unsafe_allow_html=True)

with k3:
    st.markdown(f"""
    <div class="kpi">
      <div class="kpi-label">Avg Daily Spend</div>
      <div class="kpi-value" style="color:#2a1c10">{moneyf(avg_daily)}</div>
      <div class="kpi-delta"><span class="neu">Across {len(exp_df["Day"].unique())} spending days</span></div>
    </div>""", unsafe_allow_html=True)

with k4:
    fc = "#d94838" if flex_pct > 50 else "#e09a2e" if flex_pct > 35 else "#1a9e75"
    st.markdown(f"""
    <div class="kpi">
      <div class="kpi-label">Flexible Spending</div>
      <div class="kpi-value" style="color:{fc}">{flex_pct:.0f}%</div>
      <div class="kpi-delta"><span class="neu">{moneyf(flex_total)} of {moneyf(total_expense)} is cuttable</span></div>
    </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════
#  §2  CASHFLOW WATERFALL  +  FIXED vs FLEXIBLE
# ══════════════════════════════════════════════════════════
st.markdown('<p class="sec">💧 Where Did the Money Go?</p>', unsafe_allow_html=True)
w1, w2 = st.columns([1.6, 1])

with w1:
    # Waterfall: income → each category → net
    cats   = exp_summary["Category"].head(9).tolist()
    vals   = (-exp_summary["Total"].head(9)).tolist()
    others = -(total_expense - exp_summary["Total"].head(9).sum())
    if abs(others) > 1:
        cats.append("Other"); vals.append(others)
    x_all = ["Income"] + cats + ["Net"]
    y_all = [total_income] + vals + [0]
    m_all = ["absolute"] + ["relative"]*len(cats) + ["total"]
    labels = [moneyf(total_income)] + [f"-{moneyf(abs(v))}" for v in vals] + [money(net,signed=True)]

    wf = go.Figure(go.Waterfall(
        orientation="v", measure=m_all,
        x=x_all, y=y_all,
        text=labels, textposition="outside",
        textfont={"size":10,"family":"'DM Sans',sans-serif"},
        connector={"line":{"color":"#e8ddd2","width":1}},
        increasing={"marker":{"color":"#2db88a","line":{"width":0}}},
        decreasing={"marker":{"color":"#e86858","line":{"width":0}}},
        totals={"marker":{"color":"#5b7cf0","line":{"width":0}}},
    ))
    wf.update_layout(
        **base_layout(h=400),
        showlegend=False,
        xaxis={**ax(False),"tickfont":{"size":11}},
        yaxis={**ax(),"tickprefix":"$"},
    )
    st.markdown('<div class="cc">', unsafe_allow_html=True)
    st.plotly_chart(wf, use_container_width=True, config={"displayModeBar":False})
    st.markdown('</div>', unsafe_allow_html=True)

with w2:
    # Fixed vs Flexible donut — tells a different story than "donut by category"
    if total_expense > 0:
        fvf_df = pd.DataFrame({
            "Type":   ["Fixed Bills","Flexible Spending"],
            "Amount": [fixed_total, flex_total],
        })
        fvf = px.pie(fvf_df, names="Type", values="Amount", hole=.58,
                     color_discrete_sequence=["#5b7cf0","#e86858"])
        fvf.update_traces(textposition="inside", textinfo="percent+label",
                          textfont_size=12, pull=[0,.03])
        fvf.update_layout(
            **base_layout(h=260), showlegend=False,
            margin=dict(t=14,b=10,l=0,r=0),
            annotations=[dict(text=f"<b>{moneyf(total_expense)}</b><br><span style='font-size:10px'>total spend</span>",
                              x=.5,y=.5,font_size=13,showarrow=False,
                              font={"family":"'DM Sans',sans-serif","color":"#2a1c10"})]
        )
        st.markdown('<div class="cc"><div style="font-family:Syne,sans-serif;font-size:13px;'
                    'font-weight:800;color:#2a1c10;margin-bottom:6px">Fixed vs Flexible</div>',
                    unsafe_allow_html=True)
        st.plotly_chart(fvf, use_container_width=True, config={"displayModeBar":False})
        st.markdown('</div>', unsafe_allow_html=True)

    # Budget health — compact, in same column
    st.markdown('<div class="cc">', unsafe_allow_html=True)
    st.markdown('<div style="font-family:Syne,sans-serif;font-size:13px;font-weight:800;'
                'color:#2a1c10;margin-bottom:14px">Budget Check</div>', unsafe_allow_html=True)
    for cat,rec in list(BUDGET_GUIDE.items())[:5]:
        act   = float(exp_summary[exp_summary["Category"]==cat]["Total"].sum())
        ap    = (act/total_income*100) if total_income>0 else 0
        bw    = min(ap/rec*100,100) if rec>0 else 0
        fill  = "#e86858" if ap>rec else "#f0b85b" if ap>rec*.8 else "#2db88a"
        badge = (f'<span style="color:#c03020;font-size:10px;font-weight:700">↑ {ap:.0f}%/{rec}%</span>'
                 if ap>rec else
                 f'<span style="color:#8a6000;font-size:10px;font-weight:700">↗ {ap:.0f}%/{rec}%</span>'
                 if ap>rec*.8 else
                 f'<span style="color:#1a7a50;font-size:10px;font-weight:700">✓ {ap:.0f}%/{rec}%</span>')
        st.markdown(f"""
        <div style="margin-bottom:12px">
          <div style="display:flex;justify-content:space-between;font-size:12.5px;
                      color:#3a2c20;margin-bottom:4px;font-weight:600">
            <span>{cat}</span>{badge}
          </div>
          <div style="background:#ede4d8;border-radius:99px;height:5px;overflow:hidden">
            <div style="width:{bw:.0f}%;height:100%;background:{fill};border-radius:99px"></div>
          </div>
        </div>""", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════
#  §3  SPENDING TREEMAP  +  TOP TRANSACTIONS & SUBS
# ══════════════════════════════════════════════════════════
st.markdown('<p class="sec">🗂 Spending Breakdown</p>', unsafe_allow_html=True)
t1, t2 = st.columns([1.5, 1])

with t1:
    if not exp_summary.empty:
        tree = px.treemap(
            exp_summary, path=["Category"], values="Total",
            color="Total",
            color_continuous_scale=TREEMAP_SCALE,
            custom_data=["Total"],
        )
        tree.update_traces(
            texttemplate="<b>%{label}</b><br>$%{value:,.0f}",
            textfont={"size":13,"family":"'DM Sans',sans-serif"},
            hovertemplate="<b>%{label}</b><br>$%{value:,.2f}<extra></extra>",
        )
        tree.update_layout(
            **base_layout(h=400),
            coloraxis_showscale=False,
            margin=dict(t=14,b=8,l=4,r=4),
        )
        st.markdown('<div class="cc">', unsafe_allow_html=True)
        st.plotly_chart(tree, use_container_width=True, config={"displayModeBar":False})
        st.markdown('</div>', unsafe_allow_html=True)

with t2:
    # Top 3 individual transactions
    st.markdown('<div style="font-family:Syne,sans-serif;font-size:13px;font-weight:800;'
                'color:#2a1c10;margin-bottom:10px">Biggest Single Spends</div>',
                unsafe_allow_html=True)
    top3 = exp_df.nsmallest(3,"Amount")[["Date","Description","Amount","Category"]].reset_index(drop=True)
    for _, row in top3.iterrows():
        st.markdown(f"""
        <div class="txn">
          <div class="txn-amt">{moneyf(abs(row.Amount))}</div>
          <div class="txn-desc">{row.Description}</div>
          <div class="txn-meta">{row.Date.strftime("%d %b %Y")} &nbsp;·&nbsp; {row.Category}</div>
        </div>""", unsafe_allow_html=True)

    # Subscriptions list
    subs_df = (exp_df[exp_df["Category"].isin(["Subscription","Subscriptions"])]
               .groupby("Description")["Amount"].sum().abs()
               .reset_index().sort_values("Amount",ascending=False))
    if not subs_df.empty:
        st.markdown('<div style="font-family:Syne,sans-serif;font-size:13px;font-weight:800;'
                    'color:#2a1c10;margin:16px 0 10px">Subscriptions</div>',
                    unsafe_allow_html=True)
        rows_html = "".join(
            f'<div class="sub-row"><div><div class="sub-name">{r.Description}</div></div>'
            f'<div class="sub-amt">{moneyf(r.Amount)}</div></div>'
            for _, r in subs_df.iterrows()
        )
        total_html = (f'<div style="display:flex;justify-content:space-between;padding:10px 0 2px;'
                      f'font-weight:700;font-size:13px;color:#8c7c6c">'
                      f'<span>Total</span>'
                      f'<span style="font-family:Syne,sans-serif;color:#d94838">{moneyf(sub_total)}</span></div>')
        st.markdown(
            f'<div style="background:#fff;border-radius:18px;padding:16px 20px;'
            f'border:1px solid #e8e0d6;box-shadow:0 1px 4px rgba(42,28,14,.05)">'
            f'{rows_html}{total_html}</div>',
            unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════
#  §4  SPENDING PATTERNS — Day of Week  +  Monthly Trend
# ══════════════════════════════════════════════════════════
st.markdown('<p class="sec">📅 Spending Patterns</p>', unsafe_allow_html=True)
p1, p2 = st.columns(2)

with p1:
    # Day of week bar
    dow = (exp_df.groupby("DOW")["Amount"].sum().abs()
           .reindex(DAY_ORDER, fill_value=0).reset_index())
    peak_day = dow.loc[dow["Amount"].idxmax(),"DOW"]
    colors   = ["#e06d35" if d==peak_day else "#d4c4b4" for d in dow["DOW"]]

    fig_dow = go.Figure(go.Bar(
        x=dow["DOW"], y=dow["Amount"],
        marker_color=colors, marker_line_width=0,
        text=[f"${v:,.0f}" for v in dow["Amount"]],
        textposition="outside", textfont={"size":10},
    ))
    fig_dow.update_layout(
        **base_layout(h=320),
        xaxis={**ax(False),"tickfont":{"size":12}},
        yaxis={**ax(),"tickprefix":"$"},
        annotations=[dict(
            text=f"Most spending on <b>{peak_day}s</b>",
            x=0.01,y=1.06,xref="paper",yref="paper",
            showarrow=False,font={"size":12,"color":"#8c7c6c","family":"'DM Sans',sans-serif"}
        )],
    )
    st.markdown('<div class="cc">'
                '<div style="font-family:Syne,sans-serif;font-size:13px;font-weight:800;'
                'color:#2a1c10;margin-bottom:6px">When Do You Spend?</div>',
                unsafe_allow_html=True)
    st.plotly_chart(fig_dow, use_container_width=True, config={"displayModeBar":False})
    st.markdown('</div>', unsafe_allow_html=True)

with p2:
    # Monthly savings rate trend
    def month_sr(g):
        inc = g[g["Type"]=="Income"]["Amount"].sum()
        exp = g[g["Type"]=="Expense"]["Amount"].abs().sum()
        return (inc-exp)/inc*100 if inc > 0 else 0

    msr = df.groupby("Month").apply(month_sr).reset_index()
    msr.columns = ["Month","SavingsRate"]
    msr["Color"] = msr["SavingsRate"].apply(
        lambda v: "#1a9e75" if v>=20 else "#e09a2e" if v>=10 else "#d94838")

    fig_sr = go.Figure()
    fig_sr.add_hline(y=20, line_dash="dot", line_color="#c0d8c0", line_width=1.5,
                     annotation_text="20% goal", annotation_position="right",
                     annotation_font={"size":10,"color":"#8ca88c"})
    fig_sr.add_trace(go.Scatter(
        x=msr["Month"], y=msr["SavingsRate"],
        mode="lines+markers+text",
        line=dict(color="#5b7cf0", width=2.5),
        marker=dict(size=10, color=msr["Color"], line=dict(color="#fff",width=2)),
        text=[f"{v:.0f}%" for v in msr["SavingsRate"]],
        textposition="top center",
        textfont={"size":10,"family":"'DM Sans',sans-serif"},
        fill="tozeroy", fillcolor="rgba(91,124,240,.07)",
    ))
    fig_sr.update_layout(
        **base_layout(h=320),
        xaxis={**ax(False),"tickfont":{"size":11}},
        yaxis={**ax(),"ticksuffix":"%"},
    )
    st.markdown('<div class="cc">'
                '<div style="font-family:Syne,sans-serif;font-size:13px;font-weight:800;'
                'color:#2a1c10;margin-bottom:6px">Savings Rate Over Time</div>',
                unsafe_allow_html=True)
    st.plotly_chart(fig_sr, use_container_width=True, config={"displayModeBar":False})
    st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════
#  §5  INSIGHTS & ACTIONS  (tabbed — no repetition)
# ══════════════════════════════════════════════════════════
st.markdown('<p class="sec">💡 Insights & Actions</p>', unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["📖  What happened", "🚀  What to do", "✦  AI Coach"])

# ── Tab 1: Story ──────────────────────────────────────────
with tab1:
    story = [
        f"You earned <b>{moneyf(total_income)}</b> and spent <b>{moneyf(total_expense)}</b>. "
        + (f"You came out <b>{moneyf(net)} ahead</b>." if net>=0 else f"You overspent by <b>{moneyf(abs(net))}</b>."),
    ]
    if not exp_summary.empty:
        t = exp_summary.iloc[0]
        pct = t["Total"]/total_expense*100 if total_expense>0 else 0
        story.append(f"<b>{t['Category']}</b> was your biggest cost at {moneyf(t['Total'])} "
                     f"— {pct:.0f}% of all spending.")
    story.append(f"<b>{fixed_pct:.0f}%</b> of your expenses are fixed bills you can't easily change. "
                 f"The remaining <b>{flex_pct:.0f}%</b> ({moneyf(flex_total)}) is flexible and cuttable.")
    if sub_total > 0:
        story.append(f"Subscriptions are costing <b>{moneyf(sub_total)}</b> this period.")
    if savings_rate >= 20:
        story.append(f"Your savings rate of <b>{savings_rate:.1f}%</b> is excellent. You're building a cushion.")
    elif savings_rate < 10 and total_income > 0:
        story.append(f"A savings rate of <b>{savings_rate:.1f}%</b> is below the 10–20% range. "
                     "Small regular transfers help build the habit.")

    c_s1, c_s2 = st.columns(2)
    for i, item in enumerate(story):
        (c_s1 if i%2==0 else c_s2).markdown(
            f'<div class="ins">{item}</div>', unsafe_allow_html=True)

# ── Tab 2: Actions ────────────────────────────────────────
with tab2:
    actions = []
    if net < 0:
        actions.append(("🔴","Spending exceeds income",
            f"You're over by {moneyf(abs(net))}. Eating out and shopping tend to be the fastest wins."))
    elif savings_rate < 10:
        actions.append(("🟡","Boost your savings rate",
            f"At {savings_rate:.1f}% you're below the 10% floor. Automate a transfer on payday — even $50 builds the habit."))
    else:
        actions.append(("🟢","Keep going — and invest the surplus",
            f"You're saving {savings_rate:.1f}%. A high-interest account or index fund puts that to work."))

    if flex_pct > 40 and flex_total > 200:
        actions.append(("✂️","Cut flexible spending",
            f"{moneyf(flex_total)} of your spending is discretionary. Identify two categories to reduce this month."))

    if not exp_summary.empty:
        t = exp_summary.iloc[0]
        actions.append(("📌",f"Dig into {t['Category']}",
            f"At {moneyf(t['Total'])} this is your biggest category. One targeted review here has the most leverage."))

    if sub_total > 80:
        actions.append(("📺","Review subscriptions",
            f"You're paying {moneyf(sub_total)}. Cancel anything you haven't actively used this month."))

    actions.append(("📅","Upload next month",
        "Month-over-month tracking is the single most effective habit for improving financial health."))

    c_a1, c_a2 = st.columns(2)
    for i,(emoji,title,desc) in enumerate(actions[:4]):
        col = c_a1 if i%2==0 else c_a2
        with col:
            st.markdown(f"""
            <div class="act">
              <div class="act-n">{i+1}</div>
              <div>
                <div class="act-t">{emoji} {title}</div>
                <div class="act-d">{desc}</div>
              </div>
            </div>""", unsafe_allow_html=True)

# ── Tab 3: AI Coach ───────────────────────────────────────
with tab3:
    ai_text = None
    if run_ai:
        k = api_key.strip() or os.environ.get("ANTHROPIC_API_KEY","")
        if k:
            tc = exp_summary.iloc[0]["Category"] if not exp_summary.empty else "N/A"
            ta = moneyf(exp_summary.iloc[0]["Total"]) if not exp_summary.empty else "N/A"
            with st.spinner("Thinking…"):
                ai_text = get_ai_insights(k, (
                    f"Income: {moneyf(total_income)}\nExpenses: {moneyf(total_expense)}\n"
                    f"Net Cashflow: {money(net,True)}\nSavings Rate: {savings_rate:.1f}%\n"
                    f"Health Score: {health_score}/100 ({s_label})\n"
                    f"Biggest expense: {tc} ({ta})\nFixed bills: {moneyf(fixed_total)}\n"
                    f"Flexible spend: {moneyf(flex_total)}\nSubscriptions: {moneyf(sub_total)}\n"
                    f"Avg daily spend: {moneyf(avg_daily)}"
                ))
            if not ai_text:
                st.warning("Couldn't reach the AI. Check your API key and connection.")
        else:
            st.info("Add your Anthropic API key in the sidebar to unlock AI coaching.")

    if ai_text:
        st.markdown(
            f'<div style="background:linear-gradient(140deg,#f5f2ff,#f0f8ff);'
            f'border:1px solid #d8d0f4;border-radius:18px;padding:22px 24px">'
            f'<div style="background:#ece6fd;color:#5738c8;font-size:10px;font-weight:800;'
            f'text-transform:uppercase;letter-spacing:.1em;padding:3px 10px;border-radius:99px;'
            f'margin-bottom:12px;display:inline-block;font-family:DM Sans,sans-serif">✦ Claude AI</div>'
            f'<div style="font-size:14px;color:#1a1008;line-height:1.8;white-space:pre-line">{ai_text}</div>'
            f'</div>',
            unsafe_allow_html=True)
    else:
        st.markdown(
            '<div style="padding:24px;text-align:center;color:#b8a898;font-size:14px">'
            'Enter your Anthropic API key in the sidebar and click <b>Generate Insights</b> '
            'for personalised AI coaching.</div>',
            unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════
#  §6  TRANSACTION TABLE
# ══════════════════════════════════════════════════════════
st.markdown('<p class="sec">🔎 Transaction Explorer</p>', unsafe_allow_html=True)

disp = fdf[["Date","Description","Amount","Category","Type","Month"]].copy()
disp["Date"] = disp["Date"].dt.strftime("%d %b %Y")
disp = disp.sort_values("Date", ascending=False)
st.dataframe(disp, use_container_width=True, height=400,
             column_config={
                 "Amount":   st.column_config.NumberColumn("Amount ($)", format="$%.2f"),
                 "Category": st.column_config.TextColumn("Category"),
             })

st.markdown("""
<div class="disclaimer">
  Money Health Agent is for personal education and spending awareness only.
  It does not constitute financial, tax, investment, or credit advice.
  Consult a licensed financial adviser for professional guidance.
</div>
""", unsafe_allow_html=True)
