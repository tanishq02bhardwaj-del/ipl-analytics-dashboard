import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="IPL Analytics Dashboard",
    page_icon="🏏",
    layout="wide",
)

st.markdown("""
<style>
[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(circle at 15% 0%, rgba(255, 214, 102, 0.28) 0%, transparent 35%),
        radial-gradient(circle at 85% 0%, rgba(90, 170, 255, 0.30) 0%, transparent 38%),
        radial-gradient(ellipse at 50% 110%, rgba(20, 170, 95, 0.40) 0%, transparent 55%),
        radial-gradient(rgba(255, 255, 255, 0.06) 1px, transparent 1px),
        linear-gradient(160deg, #050b18 0%, #0a1a3a 55%, #07142b 100%);
    background-size: auto, auto, auto, 26px 26px, auto;
    background-attachment: fixed;
}
[data-testid="stHeader"] {
    background: transparent;
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0b1730 0%, #151a45 100%);
    border-right: 1px solid rgba(255, 180, 0, 0.3);
}
[data-testid="stMetric"] {
    background: rgba(255, 255, 255, 0.07);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-top: 3px solid #ffb400;
    border-radius: 14px;
    padding: 14px 18px;
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.35);
}
[data-testid="stPlotlyChart"] {
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 14px;
    padding: 8px;
}
h1 {
    background: linear-gradient(90deg, #ffb400, #ff6a00);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 800;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: #ffb400;
}
</style>
""", unsafe_allow_html=True)

DATA_FOLDER = Path(__file__).parent / "data"
NOT_BOWLER_WICKETS = {"run out", "retired hurt", "retired out", "obstructing the field"}

TEAM_NAMES = {
    "Delhi Daredevils": "Delhi Capitals",
    "Kings XI Punjab": "Punjab Kings",
    "Royal Challengers Bangalore": "Royal Challengers Bengaluru",
    "Rising Pune Supergiant": "Rising Pune Supergiants",
}


def clean(name):
    return TEAM_NAMES.get(name, name)


@st.cache_data(show_spinner="Loading IPL data...")
def load_data():
    matches, balls, outs = [], [], []
    files = sorted(DATA_FOLDER.rglob("*.json"))

    for match_id, path in enumerate(files):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        info = data.get("info", {})
        season = str(info.get("season", "Unknown"))
        teams = [clean(t) for t in info.get("teams", [])]
        toss = info.get("toss", {})
        dates = info.get("dates", [])

        matches.append({
            "match_id": match_id,
            "season": season,
            "date": str(dates[0]) if dates else None,
            "team1": teams[0] if len(teams) > 0 else None,
            "team2": teams[1] if len(teams) > 1 else None,
            "winner": clean(info.get("outcome", {}).get("winner")),
            "toss_winner": clean(toss.get("winner")),
            "toss_decision": toss.get("decision"),
            "venue": info.get("venue"),
        })

        for innings_no, inning in enumerate(data.get("innings", [])):
            if inning.get("super_over"):
                continue
            batting = clean(inning.get("team"))
            bowling = next((t for t in teams if t != batting), None)

            for over in inning.get("overs", []):
                for d in over.get("deliveries", []):
                    runs = d.get("runs", {})
                    extras = d.get("extras", {})
                    batter_runs = runs.get("batter", 0)
                    is_wide = "wides" in extras
                    is_noball = "noballs" in extras
                    is_boundary = not runs.get("non_boundary", False)
                    wicket_list = d.get("wickets", [])

                    wickets = sum(
                        1 for w in wicket_list
                        if w.get("kind") not in NOT_BOWLER_WICKETS
                    )
                    for w in wicket_list:
                        outs.append({"season": season, "player_out": w.get("player_out")})

                    balls.append({
                        "match_id": match_id,
                        "season": season,
                        "innings": innings_no,
                        "batting_team": batting,
                        "bowling_team": bowling,
                        "batter": d.get("batter"),
                        "bowler": d.get("bowler"),
                        "batter_runs": batter_runs,
                        "total_runs": runs.get("total", 0),
                        "wickets": wickets,
                        "faced": 0 if is_wide else 1,
                        "legal": 0 if (is_wide or is_noball) else 1,
                        "four": 1 if (batter_runs == 4 and is_boundary) else 0,
                        "six": 1 if (batter_runs == 6 and is_boundary) else 0,
                        "conceded": runs.get("total", 0) - extras.get("byes", 0) - extras.get("legbyes", 0),
                    })

    return pd.DataFrame(matches), pd.DataFrame(balls), pd.DataFrame(outs)


def bar_chart(series, title, x_label, y_label):
    df = series.reset_index()
    df.columns = [y_label, x_label]
    fig = px.bar(df, x=x_label, y=y_label, orientation="h", title=title, text=x_label)
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    return fig


def season_bar(df, value_col, title, label):
    fig = px.bar(
        df, x="season", y=value_col, title=title, text=value_col,
        labels={value_col: label},
    )
    fig.update_xaxes(type="category")
    return fig


all_matches, all_balls, all_outs = load_data()

st.title("🏏 IPL Cricket Analytics")
st.subheader("Indian Premier League Performance Dashboard")

if all_matches.empty:
    st.error("No match files found. Check that your 'data' folder has the IPL JSON files.")
    st.stop()

# ---- Sidebar filters ----
seasons = sorted(all_matches["season"].unique())
selected = st.sidebar.multiselect("Select seasons", seasons, default=seasons)

all_teams = sorted(set(all_matches["team1"].dropna()) | set(all_matches["team2"].dropna()))
team = st.sidebar.selectbox("Select team", ["All Teams"] + all_teams)

season_matches = all_matches[all_matches["season"].isin(selected)]
season_balls = all_balls[all_balls["season"].isin(selected)]
season_outs = all_outs[all_outs["season"].isin(selected)]

if season_matches.empty:
    st.warning("Pick at least one season in the sidebar.")
    st.stop()

if team == "All Teams":
    matches = season_matches
    bat_balls = season_balls
    bowl_balls = season_balls
else:
    matches = season_matches[
        (season_matches["team1"] == team) | (season_matches["team2"] == team)
    ]
    bat_balls = season_balls[season_balls["batting_team"] == team]
    bowl_balls = season_balls[season_balls["bowling_team"] == team]

if matches.empty:
    st.warning("No matches for this team in the selected seasons.")
    st.stop()

# ---- Top metrics ----
c1, c2, c3, c4 = st.columns(4)
c1.metric("Matches", f"{len(matches):,}")
c2.metric("Seasons", matches["season"].nunique())
if team == "All Teams":
    c3.metric("Teams", pd.concat([matches["team1"], matches["team2"]]).nunique())
else:
    c3.metric("Wins", int((matches["winner"] == team).sum()))
c4.metric("Total Runs", f"{int(bat_balls['total_runs'].sum()):,}")

st.divider()

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    ["Overview", "Teams", "Players", "Toss", "Player Search", "Head to Head"]
)

# ---- Overview ----
with tab1:
    left, right = st.columns(2)

    with left:
        per_season = matches.groupby("season").size().reset_index(name="Matches")
        st.plotly_chart(season_bar(per_season, "Matches", "Matches per Season", "Matches"))

    with right:
        scores = (
            bat_balls.groupby(["match_id", "innings", "batting_team", "bowling_team", "season"])["total_runs"]
            .sum()
            .reset_index()
            .nlargest(10, "total_runs")
            .rename(columns={"total_runs": "Runs"})
        )
        scores["Match"] = (
            scores["batting_team"] + " vs " + scores["bowling_team"] + " (" + scores["season"] + ")"
        )
        fig = px.bar(scores, x="Runs", y="Match", orientation="h", title="Highest Team Scores", text="Runs")
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig)

# ---- Teams ----
with tab2:
    if team != "All Teams":
        st.caption("These charts compare all teams for the selected seasons.")

    wins = season_matches["winner"].dropna().value_counts()
    played = pd.concat([season_matches["team1"], season_matches["team2"]]).value_counts()
    win_pct = (wins.reindex(played.index).fillna(0) / played * 100).round(1)
    win_pct = win_pct.sort_values(ascending=False)

    left, right = st.columns(2)
    with left:
        st.plotly_chart(bar_chart(wins, "Total Wins by Team", "Wins", "Team"))
    with right:
        st.plotly_chart(bar_chart(win_pct, "Win Percentage by Team", "Win %", "Team"))

# ---- Players ----
with tab3:
    left, right = st.columns(2)
    with left:
        top_runs = bat_balls.groupby("batter")["batter_runs"].sum().nlargest(10)
        st.plotly_chart(bar_chart(top_runs, "Top 10 Run Scorers", "Runs", "Batter"))
    with right:
        top_wkts = bowl_balls.groupby("bowler")["wickets"].sum().nlargest(10)
        st.plotly_chart(bar_chart(top_wkts, "Top 10 Wicket Takers", "Wickets", "Bowler"))

# ---- Toss ----
with tab4:
    if team == "All Teams":
        toss_matches = matches
    else:
        toss_matches = matches[matches["toss_winner"] == team]
        st.caption(f"Showing matches where {team} won the toss.")

    decided = toss_matches.dropna(subset=["winner", "toss_winner"])

    if toss_matches.empty:
        st.info("No toss data for this selection.")
    else:
        left, right = st.columns(2)

        with left:
            decisions = toss_matches["toss_decision"].dropna().value_counts().reset_index()
            decisions.columns = ["Decision", "Matches"]
            st.plotly_chart(px.pie(decisions, names="Decision", values="Matches", title="Toss Decisions"))

        with right:
            won = int((decided["winner"] == decided["toss_winner"]).sum())
            lost = len(decided) - won
            result = pd.DataFrame({
                "Result": ["Won the match", "Lost the match"],
                "Matches": [won, lost],
            })
            st.plotly_chart(px.pie(result, names="Result", values="Matches", title="Match Result After Winning Toss"))

# ---- Player Search ----
with tab5:
    st.caption("Uses the season filter in the sidebar. The team filter doesn't apply here.")

    players = sorted(set(season_balls["batter"].dropna()) | set(season_balls["bowler"].dropna()))
    player = st.selectbox(
        "Search a player (type a name)", players, index=None, placeholder="e.g. V Kohli"
    )

    if player is None:
        st.info("Pick a player above to see their batting and bowling stats.")
    else:
        bat = season_balls[season_balls["batter"] == player]
        bowl = season_balls[season_balls["bowler"] == player]
        dismissals = int((season_outs["player_out"] == player).sum())

        st.subheader(f"Batting: {player}")
        if bat.empty:
            st.info("No batting data for this player in the selected seasons.")
        else:
            per_inn = bat.groupby(["match_id", "innings"])["batter_runs"].sum()
            runs = int(bat["batter_runs"].sum())
            faced = int(bat["faced"].sum())

            a1, a2, a3, a4 = st.columns(4)
            a1.metric("Innings", len(per_inn))
            a2.metric("Runs", f"{runs:,}")
            a3.metric("Highest Score", int(per_inn.max()))
            a4.metric("Average", f"{runs / dismissals:.2f}" if dismissals else "-")

            b1, b2, b3, b4 = st.columns(4)
            b1.metric("Strike Rate", f"{runs / faced * 100:.1f}" if faced else "-")
            b2.metric("Fours", int(bat["four"].sum()))
            b3.metric("Sixes", int(bat["six"].sum()))
            b4.metric(
                "50s / 100s",
                f"{int(((per_inn >= 50) & (per_inn < 100)).sum())} / {int((per_inn >= 100).sum())}",
            )

            runs_by_season = bat.groupby("season")["batter_runs"].sum().reset_index()
            st.plotly_chart(season_bar(runs_by_season, "batter_runs", "Runs per Season", "Runs"))

        st.subheader(f"Bowling: {player}")
        if bowl.empty:
            st.info("No bowling data for this player in the selected seasons.")
        else:
            legal = int(bowl["legal"].sum())
            conceded = int(bowl["conceded"].sum())

            d1, d2, d3, d4 = st.columns(4)
            d1.metric("Matches", bowl["match_id"].nunique())
            d2.metric("Wickets", int(bowl["wickets"].sum()))
            d3.metric("Overs", f"{legal // 6}.{legal % 6}")
            d4.metric("Economy", f"{conceded / (legal / 6):.2f}" if legal else "-")

            wkts_by_season = bowl.groupby("season")["wickets"].sum().reset_index()
            st.plotly_chart(season_bar(wkts_by_season, "wickets", "Wickets per Season", "Wickets"))

# ---- Head to Head ----
with tab6:
    st.caption("Uses the season filter in the sidebar. The team filter doesn't apply here.")

    default_a = all_teams.index("Mumbai Indians") if "Mumbai Indians" in all_teams else 0
    default_b = all_teams.index("Chennai Super Kings") if "Chennai Super Kings" in all_teams else 1

    col_a, col_b = st.columns(2)
    team_a = col_a.selectbox("Team A", all_teams, index=default_a, key="h2h_a")
    team_b = col_b.selectbox("Team B", all_teams, index=default_b, key="h2h_b")

    if team_a == team_b:
        st.warning("Please pick two different teams.")
    else:
        h2h = season_matches[
            ((season_matches["team1"] == team_a) & (season_matches["team2"] == team_b))
            | ((season_matches["team1"] == team_b) & (season_matches["team2"] == team_a))
        ]

        if h2h.empty:
            st.info("These two teams did not play each other in the selected seasons.")
        else:
            wins_a = int((h2h["winner"] == team_a).sum())
            wins_b = int((h2h["winner"] == team_b).sum())
            no_result = len(h2h) - wins_a - wins_b

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Matches Played", len(h2h))
            m2.metric(f"{team_a} Wins", wins_a)
            m3.metric(f"{team_b} Wins", wins_b)
            m4.metric("No Result / Tie", no_result)

            h2h_balls = season_balls[season_balls["match_id"].isin(h2h["match_id"])]

            left, right = st.columns(2)
            with left:
                pie = pd.DataFrame({
                    "Result": [f"{team_a} wins", f"{team_b} wins", "No result / tie"],
                    "Matches": [wins_a, wins_b, no_result],
                })
                st.plotly_chart(px.pie(pie, names="Result", values="Matches", title="Head to Head Record"))

            with right:
                innings_scores = (
                    h2h_balls.groupby(["match_id", "innings", "batting_team"])["total_runs"]
                    .sum()
                    .reset_index()
                )
                high = (
                    innings_scores.groupby("batting_team")["total_runs"]
                    .max()
                    .reindex([team_a, team_b])
                    .fillna(0)
                    .astype(int)
                    .reset_index()
                )
                high.columns = ["Team", "Highest Score"]
                fig = px.bar(high, x="Team", y="Highest Score", text="Highest Score",
                             title="Highest Score in This Rivalry")
                st.plotly_chart(fig)

            st.subheader("Top batters in this rivalry")
            left, right = st.columns(2)
            with left:
                top_a = h2h_balls[h2h_balls["batting_team"] == team_a].groupby("batter")["batter_runs"].sum().nlargest(5)
                st.plotly_chart(bar_chart(top_a, f"{team_a} - Top 5 Batters", "Runs", "Batter"))
            with right:
                top_b = h2h_balls[h2h_balls["batting_team"] == team_b].groupby("batter")["batter_runs"].sum().nlargest(5)
                st.plotly_chart(bar_chart(top_b, f"{team_b} - Top 5 Batters", "Runs", "Batter"))

            st.subheader("Top bowlers in this rivalry")
            left, right = st.columns(2)
            with left:
                wk_a = h2h_balls[h2h_balls["bowling_team"] == team_a].groupby("bowler")["wickets"].sum().nlargest(5)
                st.plotly_chart(bar_chart(wk_a, f"{team_a} - Top 5 Bowlers", "Wickets", "Bowler"))
            with right:
                wk_b = h2h_balls[h2h_balls["bowling_team"] == team_b].groupby("bowler")["wickets"].sum().nlargest(5)
                st.plotly_chart(bar_chart(wk_b, f"{team_b} - Top 5 Bowlers", "Wickets", "Bowler"))

            st.subheader("Last 5 meetings")
            recent = h2h.sort_values("date", ascending=False).head(5)[["date", "season", "venue", "winner"]]
            recent.columns = ["Date", "Season", "Venue", "Winner"]
            recent["Winner"] = recent["Winner"].fillna("No result")
            st.dataframe(recent, hide_index=True)