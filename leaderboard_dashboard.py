import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from zoneinfo import ZoneInfo

# ------------------------------
# PAGE CONFIG
# ------------------------------
st.set_page_config(page_title="Leaderboard Dashboard", layout="wide")

# ------------------------------
# HEADER
# ------------------------------
st.title("🏏 IPL Prediction Leaderboard")
st.caption("Live leaderboard from Google Sheets")

# ------------------------------
# GOOGLE SHEETS CONNECTION
# ------------------------------
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

SHEET_KEY = "1_a84iRq_2ia-MZYpMLdpLA6kzQADuPDa8mKEUIkF4Kk"

@st.cache_data(ttl=120)
def load_data():
    creds = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]),
        scopes=SCOPES
    )
    client = gspread.authorize(creds)

    sheet = client.open_by_key(SHEET_KEY)
    worksheet = sheet.get_worksheet(0)

    data = worksheet.get_all_values()
    df = pd.DataFrame(data[1:], columns=data[0])

    df.rename(columns={df.columns[0]: "Match"}, inplace=True)

    df["COMPLETED"] = df["COMPLETED"].astype(str).str.upper().str.strip()
    df = df[df["COMPLETED"] == "YES"].copy()

    player_cols = [col for col in df.columns if col not in ["Match", "COMPLETED"]]

    for col in player_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df

# ------------------------------
# LOAD DATA
# ------------------------------
df = load_data()

# ✅ IST TIME FIX
last_updated = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%d-%b-%Y %I:%M:%S %p IST")

if df.empty:
    st.warning("No completed matches yet.")
    st.stop()

match_order = df["Match"].tolist()
completed_matches_count = df.shape[0]

# ------------------------------
# TRANSFORM
# ------------------------------
long_df = df.melt(id_vars=["Match"], var_name="Player", value_name="Points")
long_df["Points"] = pd.to_numeric(long_df["Points"], errors="coerce").fillna(0)

# ------------------------------
# LEADERBOARD
# ------------------------------
leaderboard = long_df.groupby("Player").agg(
    Total_Points=("Points", "sum"),
    Best_Score=("Points", "max")
).reset_index()

leaderboard["Avg_Points"] = (
    leaderboard["Total_Points"] / completed_matches_count
).round(2)

leaderboard = leaderboard.sort_values(
    ["Total_Points", "Best_Score", "Player"],
    ascending=[False, False, True]
).reset_index(drop=True)

leaderboard["Rank"] = range(1, len(leaderboard) + 1)

player_list = leaderboard["Player"].tolist()

# ------------------------------
# TOP BAR
# ------------------------------
col1, col2 = st.columns([3, 1])

with col1:
    st.caption(f"Last refreshed: {last_updated}")

with col2:
    if st.button("🔄 Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ------------------------------
# METRICS
# ------------------------------
m1, m2, m3, m4 = st.columns(4)
m1.metric("Players", len(leaderboard))
m2.metric("Leader", leaderboard.iloc[0]["Player"])
m3.metric("Top Points", int(leaderboard.iloc[0]["Total_Points"]))
m4.metric("Matches", int(completed_matches_count))

st.divider()

# ------------------------------
# TOP 3
# ------------------------------
st.subheader("🥇 Top 3 Players")

top3 = leaderboard.head(3)
c1, c2, c3 = st.columns(3)

def card(col, row, medal):
    with col:
        st.markdown(f"""
        <div style="padding:20px; border-radius:12px; border:1px solid #eee; text-align:center;">
            <h2>{medal}</h2>
            <h3>{row['Player']}</h3>
            <p><b>{int(row['Total_Points'])} pts</b></p>
            <p>Avg: {row['Avg_Points']} | Best: {int(row['Best_Score'])}</p>
        </div>
        """, unsafe_allow_html=True)

if len(top3) > 0: card(c1, top3.iloc[0], "🥇")
if len(top3) > 1: card(c2, top3.iloc[1], "🥈")
if len(top3) > 2: card(c3, top3.iloc[2], "🥉")

st.divider()

# ------------------------------
# LEADERBOARD TABLE
# ------------------------------
st.subheader("🏆 Leaderboard")

display = leaderboard[["Rank", "Player", "Total_Points", "Avg_Points", "Best_Score"]]
display.columns = ["Rank", "Player", "Total Points", "Avg Points", "Best Score"]

st.dataframe(display, use_container_width=True, hide_index=True)

st.divider()

# ------------------------------
# TOP 10 CHART
# ------------------------------
st.subheader("📊 Top 10")

top10 = leaderboard.head(10).sort_values("Total_Points")

fig = px.bar(top10, x="Total_Points", y="Player", orientation="h", text="Total_Points")
fig.update_layout(height=400)
fig.update_xaxes(rangemode="tozero")

st.plotly_chart(fig, use_container_width=True)

st.divider()

# ------------------------------
# PLAYER VS PLAYER
# ------------------------------
st.subheader("⚔️ Player vs Player")

p1, p2 = st.columns(2)
player1 = p1.selectbox("Player 1", player_list)
player2 = p2.selectbox("Player 2", player_list, index=1 if len(player_list) > 1 else 0)

if player1 != player2:

    df1 = long_df[long_df["Player"] == player1][["Match", "Points"]]
    df2 = long_df[long_df["Player"] == player2][["Match", "Points"]]

    df1.rename(columns={"Points": player1}, inplace=True)
    df2.rename(columns={"Points": player2}, inplace=True)

    comp = df1.merge(df2, on="Match", how="outer").fillna(0)

    comp["Match"] = pd.Categorical(comp["Match"], categories=match_order, ordered=True)
    comp = comp.sort_values("Match")

    comp[player1] = comp[player1].cumsum()
    comp[player2] = comp[player2].cumsum()

    fig2 = px.line(comp, x="Match", y=[player1, player2], markers=True)

    fig2.update_layout(
        legend_title_text="Player",
        height=400
    )

    fig2.update_yaxes(rangemode="tozero")

    st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ------------------------------
# PLAYER TREND
# ------------------------------
st.subheader("📈 Player Trend")

player = st.selectbox("Select Player", player_list)

trend = long_df[long_df["Player"] == player]
trend["Match"] = pd.Categorical(trend["Match"], categories=match_order, ordered=True)
trend = trend.sort_values("Match")

fig3 = px.line(trend, x="Match", y="Points", markers=True)
fig3.update_yaxes(rangemode="tozero")

st.plotly_chart(fig3, use_container_width=True)
