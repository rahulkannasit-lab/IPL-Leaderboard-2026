import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ------------------------------
# PAGE CONFIG
# ------------------------------
st.set_page_config(page_title="Leaderboard Dashboard", layout="wide")

# ------------------------------
# CUSTOM STYLING
# ------------------------------
st.markdown("""
<style>
.block-container {
    padding-top: 1.2rem;
    padding-bottom: 1.5rem;
}
h1, h2, h3 {
    letter-spacing: -0.3px;
}
.metric-card {
    border: 1px solid #e6e6e6;
    border-radius: 14px;
    padding: 14px 16px;
    background: #fafafa;
}
.section-card {
    border: 1px solid #ececec;
    border-radius: 16px;
    padding: 14px 16px;
    background: white;
}
</style>
""", unsafe_allow_html=True)

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

    # Rename first column to Match
    df.rename(columns={df.columns[0]: "Match"}, inplace=True)

    # Validate COMPLETED column
    if "COMPLETED" not in df.columns:
        raise ValueError("Column 'COMPLETED' not found in Sheet 1.")

    # Normalize completed flag
    df["COMPLETED"] = df["COMPLETED"].astype(str).str.strip().str.upper()

    # Keep only completed matches
    df = df[df["COMPLETED"] == "YES"].copy()

    # Convert player columns to numeric
    player_cols = [col for col in df.columns if col not in ["Match", "COMPLETED"]]
    for col in player_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df

# ------------------------------
# LOAD DATA
# ------------------------------
df = load_data()
last_updated = datetime.now().strftime("%d-%b-%Y %I:%M:%S %p")

if df.empty:
    st.warning("No completed matches found yet. Mark matches as YES in the COMPLETED column.")
    st.stop()

match_order = df["Match"].tolist()
completed_matches_count = df.shape[0]

# ------------------------------
# TRANSFORM DATA
# ------------------------------
long_df = df.melt(
    id_vars=["Match"],
    var_name="Player",
    value_name="Points"
)
long_df["Points"] = pd.to_numeric(long_df["Points"], errors="coerce").fillna(0)

# ------------------------------
# LEADERBOARD CALCULATIONS
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
top_left, top_right = st.columns([3, 1])

with top_left:
   st.caption(f"Last refreshed: {last_updated}")

with top_right:
    if st.button("🔄 Refresh", width="stretch"):
        st.cache_data.clear()
        st.rerun()

# ------------------------------
# SUMMARY METRICS
# ------------------------------
m1, m2, m3, m4 = st.columns(4)
m1.metric("Players", len(leaderboard))
m2.metric("Leader", leaderboard.iloc[0]["Player"])
m3.metric("Top Points", int(leaderboard.iloc[0]["Total_Points"]))
m4.metric("Completed Matches", int(completed_matches_count))

st.divider()

# ------------------------------
# TOP 3 PODIUM
# ------------------------------
st.subheader("🥇 Top 3 Players")

top3 = leaderboard.head(3).copy()
p1, p2, p3 = st.columns(3)

def podium_card(container, title, row, medal, highlight=False):
    border = "#d9d9d9" if not highlight else "#c9a227"
    background = "#fafafa" if not highlight else "#fffaf0"
    with container:
        st.markdown(
            f"""
            <div style="
                border: 1px solid {border};
                border-radius: 16px;
                padding: 18px;
                text-align: center;
                background: {background};
                min-height: 170px;
            ">
                <div style="font-size: 28px;">{medal}</div>
                <div style="font-size: 13px; color: #666;">{title}</div>
                <div style="font-size: 25px; font-weight: 700; margin-top: 8px;">{row['Player']}</div>
                <div style="font-size: 18px; margin-top: 8px;">{int(row['Total_Points'])} pts</div>
                <div style="font-size: 12px; color: #666; margin-top: 6px;">
                    Avg: {row['Avg_Points']} | Best: {int(row['Best_Score'])}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

if len(top3) >= 1:
    podium_card(p1, "Rank 1", top3.iloc[0], "🥇", highlight=True)
if len(top3) >= 2:
    podium_card(p2, "Rank 2", top3.iloc[1], "🥈")
if len(top3) >= 3:
    podium_card(p3, "Rank 3", top3.iloc[2], "🥉")

st.divider()

# ------------------------------
# LEADERBOARD TABLE
# ------------------------------
st.subheader("🏆 Leaderboard")

leaderboard_display = leaderboard[[
    "Rank",
    "Player",
    "Total_Points",
    "Avg_Points",
    "Best_Score"
]].copy()

leaderboard_display.columns = [
    "Rank",
    "Player",
    "Total Points",
    "Avg Points",
    "Best Score"
]

st.dataframe(
    leaderboard_display.reset_index(drop=True),
    width="stretch",
    hide_index=True
)

st.divider()

# ------------------------------
# TOP PLAYERS CHART
# ------------------------------
st.subheader("📊 Top 10 Players")

if leaderboard["Total_Points"].sum() > 0:
    top10 = leaderboard.head(10).copy().sort_values("Total_Points", ascending=True)

    fig_top10 = px.bar(
        top10,
        x="Total_Points",
        y="Player",
        orientation="h",
        text="Total_Points",
        title="Top 10 by Total Points"
    )
    fig_top10.update_traces(textposition="outside")
    fig_top10.update_layout(
        height=420,
        yaxis_title="",
        xaxis_title="Points",
        margin=dict(l=10, r=30, t=50, b=20)
    )
    fig_top10.update_xaxes(rangemode="tozero")
    st.plotly_chart(fig_top10, width="stretch")
else:
    st.info("No points recorded yet. The top players chart will appear once scores are added.")

st.divider()

# ------------------------------
# PLAYER VS PLAYER
# ------------------------------
st.subheader("⚔️ Player vs Player")

v1, v2 = st.columns(2)
player1 = v1.selectbox("Player 1", player_list, index=0)
player2_default = 1 if len(player_list) > 1 else 0
player2 = v2.selectbox("Player 2", player_list, index=player2_default)

if player1 == player2:
    st.warning("Select two different players.")
else:
    p1_row = leaderboard[leaderboard["Player"] == player1].iloc[0]
    p2_row = leaderboard[leaderboard["Player"] == player2].iloc[0]

    st.markdown("#### Quick Comparison")
    c1, c2 = st.columns(2)

    with c1:
        st.markdown(f"**{player1}**")
        a1, a2, a3 = st.columns(3)
        a1.metric("Total", int(p1_row["Total_Points"]))
        a2.metric("Avg", float(p1_row["Avg_Points"]))
        a3.metric("Best", int(p1_row["Best_Score"]))

    with c2:
        st.markdown(f"**{player2}**")
        b1, b2, b3 = st.columns(3)
        b1.metric("Total", int(p2_row["Total_Points"]))
        b2.metric("Avg", float(p2_row["Avg_Points"]))
        b3.metric("Best", int(p2_row["Best_Score"]))

    p1_df = long_df[long_df["Player"] == player1][["Match", "Points"]].rename(
        columns={"Points": player1}
    )
    p2_df = long_df[long_df["Player"] == player2][["Match", "Points"]].rename(
        columns={"Points": player2}
    )

    compare_df = p1_df.merge(p2_df, on="Match", how="outer").fillna(0)
    compare_df["Match"] = pd.Categorical(
        compare_df["Match"],
        categories=match_order,
        ordered=True
    )
    compare_df = compare_df.sort_values("Match")

    compare_df[player1] = compare_df[player1].cumsum()
    compare_df[player2] = compare_df[player2].cumsum()

    st.markdown("#### Cumulative Points Comparison")
    fig_cum = px.line(
        compare_df,
        x="Match",
        y=[player1, player2],
        markers=True
    )
    fig_cum.update_layout(
legend_title_text="Player",        
height=390,
        yaxis_title="Points",
        xaxis_title="Match",
        margin=dict(l=10, r=10, t=20, b=20)
    )
    fig_cum.update_yaxes(rangemode="tozero")
    st.plotly_chart(fig_cum, width="stretch")

st.divider()

# ------------------------------
# PLAYER TREND
# ------------------------------
st.subheader("📈 Player Trend")

selected_player = st.selectbox("Select Player", player_list)

player_trend = long_df[long_df["Player"] == selected_player].copy()
player_trend["Match"] = pd.Categorical(
    player_trend["Match"],
    categories=match_order,
    ordered=True
)
player_trend = player_trend.sort_values("Match")

if player_trend["Points"].sum() > 0:
    fig_trend = px.line(
        player_trend,
        x="Match",
        y="Points",
        markers=True,
        title=f"{selected_player} - Match by Match Points"
    )
    fig_trend.update_layout(
        height=390,
        yaxis_title="Points",
        xaxis_title="Match",
        margin=dict(l=10, r=10, t=45, b=20)
    )
    fig_trend.update_yaxes(rangemode="tozero")
    st.plotly_chart(fig_trend, width="stretch")
else:
    st.info(f"{selected_player} does not have any points recorded yet.")

# ------------------------------
# RAW DATA
# ------------------------------
with st.expander("Show Raw Completed Match Data"):
    st.dataframe(df, width="stretch", hide_index=True)
