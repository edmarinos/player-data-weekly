import streamlit as st
import pandas as pd
import altair as alt
import os

st.set_page_config(page_title="Player Stats Explorer", layout="wide")

# ============================================================
# LOAD DATA
# ============================================================

st.title("🏈 Player Stats Explorer")
st.caption("Explore volume, red zone usage, and share metrics by player.")

DEFAULT_FILE = "player_df.csv"

@st.cache_data
def load_data(file):
    return pd.read_csv(file)

uploaded_file = st.sidebar.file_uploader(
    "Upload a different CSV (optional)", type=["csv"]
)

if uploaded_file is not None:
    df = load_data(uploaded_file)
    st.sidebar.success("Using uploaded file")
elif os.path.exists(DEFAULT_FILE):
    df = load_data(DEFAULT_FILE)
    st.sidebar.info(f"Loaded {DEFAULT_FILE} automatically")
else:
    st.warning(
        f"Couldn't find `{DEFAULT_FILE}` in this folder. "
        "Either place it alongside app.py, or upload a CSV using the sidebar."
    )
    st.stop()

# ============================================================
# SIDEBAR FILTERS
# ============================================================

st.sidebar.header("Filters")

teams = sorted(df["Team_name"].dropna().unique())
positions = sorted(df["position"].dropna().unique())

team_options = ["All Teams"] + teams
selected_team = st.sidebar.selectbox("Team", team_options, index=0)

selected_positions = st.sidebar.multiselect("Position", positions, default=positions)

search_name = st.sidebar.text_input("Search player name")

min_targets = st.sidebar.slider(
    "Minimum targets", 0, int(df["targets"].max()), 0
)
min_rush_att = st.sidebar.slider(
    "Minimum rush attempts", 0, int(df["rush_attempts"].max()), 0
)

# ============================================================
# APPLY FILTERS
# ============================================================

if selected_team == "All Teams":
    team_mask = pd.Series(True, index=df.index)
else:
    team_mask = df["Team_name"] == selected_team

filtered = df[
    team_mask
    & df["position"].isin(selected_positions)
    & (df["targets"] >= min_targets)
    & (df["rush_attempts"] >= min_rush_att)
]

if search_name:
    filtered = filtered[filtered["player_name"].str.contains(search_name, case=False, na=False)]

st.subheader(f"Showing {len(filtered)} players")

# ============================================================
# SORT CONTROL
# ============================================================

numeric_cols = [c for c in filtered.columns if pd.api.types.is_numeric_dtype(filtered[c])]
sort_col = st.selectbox("Sort by", numeric_cols, index=numeric_cols.index("targets") if "targets" in numeric_cols else 0)
sort_desc = st.checkbox("Descending", value=True)

filtered_sorted = filtered.sort_values(sort_col, ascending=not sort_desc)

# ============================================================
# MAIN TABLE
# ============================================================

st.dataframe(filtered_sorted, use_container_width=True, height=500)

# ============================================================
# QUICK VISUALS
# ============================================================

col1, col2 = st.columns(2)

with col1:
    st.markdown("### Target Share by Position")
    if not filtered.empty:
        chart_data = filtered.groupby("position", as_index=False)["target_share"].mean()
        chart = (
            alt.Chart(chart_data)
            .mark_bar()
            .encode(x="position", y="target_share", tooltip=["position", "target_share"])
        )
        st.altair_chart(chart, use_container_width=True)

with col2:
    st.markdown("### Red Zone Touches vs Total Touches")
    if not filtered.empty:
        plot_df = filtered.copy()
        plot_df["total_touches"] = plot_df["targets"] + plot_df["rush_attempts"]
        plot_df["rz_touches"] = plot_df["rz_targets"] + plot_df["rz_rush_attempts"]
        scatter = (
            alt.Chart(plot_df)
            .mark_circle(size=80, opacity=0.7)
            .encode(
                x="total_touches",
                y="rz_touches",
                color="position",
                tooltip=["player_name", "Team_name", "position", "total_touches", "rz_touches"],
            )
            .interactive()
        )
        st.altair_chart(scatter, use_container_width=True)

# ============================================================
# TOP PERFORMERS QUICK VIEW
# ============================================================

st.markdown("### Top 10 by Selected Metric")
top10 = filtered_sorted.head(10)[["player_name", "Team_name", "position", sort_col]]
st.table(top10)

# ============================================================
# DOWNLOAD FILTERED DATA
# ============================================================

st.download_button(
    "Download filtered data as CSV",
    data=filtered_sorted.to_csv(index=False),
    file_name="filtered_player_df.csv",
    mime="text/csv",
)