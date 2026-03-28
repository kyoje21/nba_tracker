"""
================================================================================
NBA REDDIT GAME THREAD SALT TRACKER
Live game discovery + scraping + VADER sentiment analysis
Real-time tug-of-war salt meter visualization

Author: kyoje21
================================================================================
"""

import os
import time
import warnings
import re
from typing import Dict, Tuple, List, Optional
from collections import deque

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
import requests
from nltk.sentiment import SentimentIntensityAnalyzer

try:
    from nba_api.live.nba.endpoints import scoreboard
    NBA_API_AVAILABLE = True
except ImportError:
    NBA_API_AVAILABLE = False

try:
    sia = SentimentIntensityAnalyzer()
    VADER_AVAILABLE = True
except ImportError:
    sia = None
    VADER_AVAILABLE = False

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

load_dotenv()

# ============================================================================
# NBA LEXICON FOR VADER
# ============================================================================

NBA_LEXICON = {
    # Negative terms
    'merchant': -0.9, 'unethical': -0.9, 'cooked': -0.85, 'washed': -0.9,
    'fraud': -0.95, 'rigged': -0.95, 'terrorism': -1.0, 'statpad': -0.85,
    'mickey': -0.8, 'brick': -0.75, 'choke': -0.85, 'scrub': -0.8,
    'bum': -0.85, 'poverty': -0.9, 'masterclass': -0.7,
    '🤡': -0.95, '🧂': -0.9, '🧱': -0.85, '🗑️': -0.9,

    # Positive terms
    'goat': 0.95, 'clutch': 0.9, 'him': 0.85, 'aura': 0.8,
    'cinema': 0.85, 'cooking': 0.9, '🐐': 0.95, '🔥': 0.9,
}

if VADER_AVAILABLE and sia:
    sia.lexicon.update(NBA_LEXICON)

# ============================================================================
# TEAM MAPPING FOR SCRAPER
# ============================================================================

TEAM_REDDIT_MAP = {
    'Hawks': 'hawks', 'Celtics': 'bostonceltics', 'Nets': 'netsworld', 'Hornets': 'hornets',
    'Bulls': 'chicagobulls', 'Cavaliers': 'clevelandcavaliers', 'Mavericks': 'Mavericks',
    'Nuggets': 'denvernuggets', 'Pistons': 'DetroitPistons', 'Warriors': 'warriors',
    'Rockets': 'rockets', 'Grizzlies': 'memphisgrizzlies', 'Lakers': 'lakers', 'Heat': 'heat',
    'Bucks': 'MilwaukeeBucks', 'Timberwolves': 'timberwolves', 'Pelicans': 'NOLAPelicans',
    'Knicks': 'NYKnicks', '76ers': 'sixers', 'Suns': 'suns', 'Trail Blazers': 'ripcity',
    'Kings': 'kings', 'Spurs': 'NBASpurs', 'Raptors': 'torontoraptors', 'Jazz': 'UtahJazz',
    'Wizards': 'washingtonwizards', 'Pacers': 'pacers', 'Clippers': 'laclippers',
    'Thunder': 'oklahomacitythunder', 'Magic': 'OrlandoMagic',
}

TEAM_ABBR_MAP = {
    'ATL': 'Hawks', 'BOS': 'Celtics', 'BKN': 'Nets', 'CHA': 'Hornets', 'CHI': 'Bulls',
    'CLE': 'Cavaliers', 'DAL': 'Mavericks', 'DEN': 'Nuggets', 'DET': 'Pistons', 'GSW': 'Warriors',
    'HOU': 'Rockets', 'MEM': 'Grizzlies', 'LAL': 'Lakers', 'MIA': 'Heat', 'MIL': 'Bucks',
    'MIN': 'Timberwolves', 'NOP': 'Pelicans', 'NYK': 'Knicks', 'PHI': '76ers', 'PHX': 'Suns',
    'POR': 'Trail Blazers', 'SAC': 'Kings', 'SAS': 'Spurs', 'TOR': 'Raptors', 'UTA': 'Jazz',
    'WAS': 'Wizards', 'IND': 'Pacers', 'LAC': 'Clippers', 'OKC': 'Thunder', 'ORL': 'Magic',
}

# ============================================================================
# NBA API: LIVE GAME DISCOVERY
# ============================================================================

@st.cache_data(ttl=300)
def get_live_games() -> List[str]:
    """Get active NBA games from NBA API."""
    if not NBA_API_AVAILABLE:
        return []

    try:
        board = scoreboard.ScoreBoard()
        games = board.get_dict()

        matchups = []
        if 'scoreboard' in games and 'games' in games['scoreboard']:
            for game in games['scoreboard']['games']:
                away_abbr = game.get('awayTeam', {}).get('teamTricode', '')
                home_abbr = game.get('homeTeam', {}).get('teamTricode', '')

                away_name = TEAM_ABBR_MAP.get(away_abbr, away_abbr)
                home_name = TEAM_ABBR_MAP.get(home_abbr, home_abbr)

                matchup = f"{away_name} @ {home_name}"
                if matchup and matchup not in matchups:
                    matchups.append(matchup)

        return matchups

    except Exception as e:
        st.warning(f"⚠️ NBA API error: {str(e)[:60]}")
        return []

# ============================================================================
# REDDIT SCRAPER BRIDGE
# ============================================================================

def get_game_thread_url(team1: str, team2: str) -> Optional[str]:
    """
    Find Game Thread URL from Reddit for two teams.
    Checks both subreddits and returns first Game Thread found.
    """
    teams = [team1, team2]

    for team in teams:
        subreddit = TEAM_REDDIT_MAP.get(team)
        if not subreddit:
            continue

        try:
            url = f"https://www.reddit.com/r/{subreddit}/search.json"
            params = {'q': 'Game Thread', 'restrict_sr': True, 'sort': 'new', 'limit': 5}
            headers = {'User-Agent': 'NBA-Salt-Tracker'}

            response = requests.get(url, params=params, headers=headers, timeout=10)
            data = response.json()

            if 'data' in data and 'children' in data['data']:
                for post in data['data']['children']:
                    post_data = post['data']
                    if 'game thread' in post_data['title'].lower():
                        return f"https://www.reddit.com{post_data['permalink']}"

        except Exception:
            continue

    return None

def scrape_reddit_comments(url: str, max_comments: int = 500) -> List[str]:
    """
    Scrape comments from Reddit thread via .json endpoint.
    Returns list of comment strings.
    """
    try:
        json_url = url.rstrip('/') + '.json'
        headers = {'User-Agent': 'NBA-Salt-Tracker'}

        response = requests.get(json_url, headers=headers, timeout=15)
        data = response.json()

        comments = []

        def extract_comments(node, depth=0):
            if depth > 10:
                return

            if isinstance(node, list):
                for item in node:
                    extract_comments(item, depth)
            elif isinstance(node, dict):
                if node.get('kind') == 't1':
                    comment_text = node.get('data', {}).get('body', '')
                    if comment_text and comment_text != '[deleted]' and len(comment_text) > 10:
                        comments.append(comment_text)

                if 'children' in node.get('data', {}):
                    extract_comments(node['data']['children'], depth + 1)

        extract_comments(data)
        return comments[:max_comments]

    except Exception as e:
        st.error(f"❌ Scraper error: {str(e)[:60]}")
        return []

# ============================================================================
# SENTIMENT ANALYSIS
# ============================================================================

def analyze_sentiment(comment: str) -> float:
    """Analyze sentiment using VADER with NBA lexicon."""
    if not VADER_AVAILABLE or sia is None:
        return 0.0

    try:
        scores = sia.polarity_scores(comment)
        return float(scores['compound'])
    except Exception:
        return 0.0

def analyze_batch_sentiment(comments: List[str]) -> List[float]:
    """Analyze sentiment for batch of comments using VADER."""
    return [analyze_sentiment(c) for c in comments]

# ============================================================================
# SALT COMPUTATION (AMPLIFIED)
# ============================================================================

def compute_salt_metrics(team1_vibe: float, team2_vibe: float) -> Dict:
    team1_salt = -1.0 * team1_vibe
    team2_salt = -1.0 * team2_vibe

    salt_diff = team2_salt - team1_salt
    amplified_diff = salt_diff * 2.0

    tug_position = 50.0 + (amplified_diff * 12.5)
    tug_position = max(0.0, min(100.0, tug_position))

    if abs(amplified_diff) < 0.1:
        status_text = "🤝 Even"
    elif abs(amplified_diff) < 0.5:
        status_text = f"😤 {'Team 1' if amplified_diff < 0 else 'Team 2'} slightly saltier ({abs(amplified_diff):.2f})"
    elif abs(amplified_diff) < 1.2:
        status_text = f"🔥 {'Team 1' if amplified_diff < 0 else 'Team 2'} SALTY! ({abs(amplified_diff):.2f})"
    else:
        status_text = f"🌶️ {'Team 1' if amplified_diff < 0 else 'Team 2'} FURIOUS! ({abs(amplified_diff):.2f})"

    return {
        'team1_salt': team1_salt,
        'team2_salt': team2_salt,
        'salt_diff': amplified_diff,
        'tug_position': tug_position,
        'status_text': status_text,
    }

# ============================================================================
# VISUALIZATION
# ============================================================================

def render_tug_of_war(
    team1_name: str,
    team2_name: str,
    team1_vibe: float,
    team2_vibe: float,
    team1_colors: Optional[Tuple[str, str]] = None,
    team2_colors: Optional[Tuple[str, str]] = None
):
    if team1_colors is None:
        team1_colors = ("#98002E", "#F9A01B")
    if team2_colors is None:
        team2_colors = ("#002B5C", "#E31837")

    metrics = compute_salt_metrics(team1_vibe, team2_vibe)
    tug_pct = metrics['tug_position']
    status = metrics['status_text']
    salt_diff = metrics['salt_diff']

    st.markdown(
        f"""
        <div style="background: linear-gradient(145deg, rgba(255,255,255,0.04), rgba(0,0,0,0.6)); border-radius: 16px; padding: 2rem 1.5rem; margin-bottom: 2rem; border: 1px solid rgba(255,255,255,0.08);">
          <div style="text-align: center; margin-bottom: 1.5rem;">
            <div style="font-size: 0.9rem; opacity: 0.6; text-transform: uppercase;">🧂 Salt Meter – Tug of War 🧂</div>
            <div style="font-size: 1.3rem; font-weight: 700;">{status}</div>
            <div style="font-size: 0.85rem; opacity: 0.5;">Differential: {salt_diff:.3f}</div>
          </div>
          <div style="display: flex; justify-content: space-between; margin-bottom: 0.75rem; font-weight: 600;">
            <div style="color: {team1_colors[0]};">{team1_name}</div>
            <div style="color: #999; font-size: 0.75rem;">SALT DIFF</div>
            <div style="color: {team2_colors[0]};">{team2_name}</div>
          </div>
          <div style="position: relative; width: 100%; height: 60px; background: linear-gradient(90deg, rgba({int(team1_colors[0][1:3], 16)}, {int(team1_colors[0][3:5], 16)}, {int(team1_colors[0][5:7], 16)}, 0.2) 0%, rgba(0,0,0,0.3) 50%, rgba({int(team2_colors[0][1:3], 16)}, {int(team2_colors[0][3:5], 16)}, {int(team2_colors[0][5:7], 16)}, 0.2) 100%); border-radius: 999px; border: 2px solid rgba(255,255,255,0.1); overflow: hidden;">
            <div style="position: absolute; top: 50%; left: {tug_pct}%; transform: translate(-50%, -50%); width: 48px; height: 48px; background: radial-gradient(circle at 35% 35%, #FFD700, #FF8C00); border-radius: 50%; box-shadow: 0 0 20px rgba(255,140,0,0.8); display: flex; align-items: center; justify-content: center; font-size: 1.5rem; transition: all 400ms;">🧂</div>
          </div>
          <div style="display: flex; justify-content: space-between; font-size: 0.9rem; margin-top: 0.75rem;">
            <div>Vibe: <strong style="color: {team1_colors[0]};">{team1_vibe:+.2f}</strong></div>
            <div>Position: <strong>{tug_pct:.0f}%</strong></div>
            <div>Vibe: <strong style="color: {team2_colors[0]};">{team2_vibe:+.2f}</strong></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )

def render_live_feed(title: str, comments: List[str], primary_color: str):
    comments_html = "".join(
        f'<div style="font-size: 0.85rem; padding: 0.6rem; margin-bottom: 0.5rem; border-radius: 8px; background: rgba(0,0,0,0.3); border-left: 3px solid {primary_color}; color: #ddd;">{c[:120]}{"..." if len(c) > 120 else ""}</div>'
        for c in reversed(comments)
    )
    st.markdown(
        f'<div style="border-radius: 12px; background: linear-gradient(145deg, rgba(255,255,255,0.04), rgba(0,0,0,0.6)); padding: 1rem; height: 280px; overflow-y: auto; border: 1px solid rgba(255,255,255,0.08);"><div style="font-size: 0.95rem; font-weight: 700; color: {primary_color}; margin-bottom: 0.75rem;">{title}</div>{comments_html}</div>',
        unsafe_allow_html=True
    )

# ============================================================================
# DATA LOADING
# ============================================================================

@st.cache_data(show_spinner=False)
def load_csv_data() -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "data")

    miami_path = os.path.join(data_dir, "miami_heat_thread.csv")
    wizards_path = os.path.join(data_dir, "wizards_thread.csv")

    try:
        miami_df = pd.read_csv(miami_path).iloc[::-1].reset_index(drop=True)
        wizards_df = pd.read_csv(wizards_path).iloc[::-1].reset_index(drop=True)
        return miami_df, wizards_df
    except Exception:
        return None, None

def clean_comment(text: str) -> str:
    text = re.sub(r'\[.*?\]\(.*?\)', '', text)
    text = re.sub(r'http\S+', '', text)
    text = ' '.join(text.split())
    return text[:150] + "..." if len(text) > 150 else text

def init_session_state(max_len: int):
    if "current_index" not in st.session_state:
        st.session_state.current_index = 0
    if "team1_vibe" not in st.session_state:
        st.session_state.team1_vibe = 0.0
    if "team2_vibe" not in st.session_state:
        st.session_state.team2_vibe = 0.0
    if "team1_comments" not in st.session_state:
        st.session_state.team1_comments = deque(maxlen=5)
    if "team2_comments" not in st.session_state:
        st.session_state.team2_comments = deque(maxlen=5)
    if "is_replaying" not in st.session_state:
        st.session_state.is_replaying = False
    if "max_len" not in st.session_state:
        st.session_state.max_len = max_len
    if "last_scrape_count" not in st.session_state:
        st.session_state.last_scrape_count = 0
    if "team1_comments_live" not in st.session_state:
        st.session_state.team1_comments_live = []
    if "team2_comments_live" not in st.session_state:
        st.session_state.team2_comments_live = []

    st.session_state.max_len = max_len

def reset_replay_state(max_len: int):
    st.session_state.current_index = 0
    st.session_state.team1_vibe = 0.0
    st.session_state.team2_vibe = 0.0
    st.session_state.team1_comments = deque(maxlen=5)
    st.session_state.team2_comments = deque(maxlen=5)
    st.session_state.is_replaying = False
    st.session_state.max_len = max_len
    st.session_state.last_scrape_count = 0

def process_test_step(team1_comments_raw: List[str], team2_comments_raw: List[str], batch_size: int = 1):
    """
    Process one autoplay step for CSV test mode.
    This is the fix: update state now, render happens later, rerun happens at the bottom.
    """
    idx = st.session_state.current_index
    if idx >= st.session_state.max_len:
        st.session_state.is_replaying = False
        return

    process_count = min(
        batch_size,
        len(team1_comments_raw) - idx,
        len(team2_comments_raw) - idx,
        st.session_state.max_len - idx,
    )

    if process_count <= 0:
        st.session_state.is_replaying = False
        return

    batch_t1 = team1_comments_raw[idx:idx + process_count]
    batch_t2 = team2_comments_raw[idx:idx + process_count]

    vibes_t1 = analyze_batch_sentiment(batch_t1)
    vibes_t2 = analyze_batch_sentiment(batch_t2)

    for i in range(process_count):
        alpha = 0.8
        st.session_state.team1_vibe = (1 - alpha) * st.session_state.team1_vibe + alpha * vibes_t1[i]
        st.session_state.team2_vibe = (1 - alpha) * st.session_state.team2_vibe + alpha * vibes_t2[i]
        st.session_state.team1_comments.append(clean_comment(batch_t1[i]))
        st.session_state.team2_comments.append(clean_comment(batch_t2[i]))

    st.session_state.current_index += process_count

    if st.session_state.current_index >= st.session_state.max_len:
        st.session_state.is_replaying = False

def process_live_batch(url1: str, url2: str, batch_size: int = 50):
    """
    Simple live updater:
    rescrapes the threads, only processes newly seen comments based on prior count.
    """
    all_t1 = scrape_reddit_comments(url1) if url1 else []
    all_t2 = scrape_reddit_comments(url2) if url2 else []

    old_count = st.session_state.get("last_scrape_count", 0)
    new_count = min(len(all_t1), len(all_t2))

    if new_count <= old_count:
        return

    batch_t1 = all_t1[old_count:new_count][:batch_size]
    batch_t2 = all_t2[old_count:new_count][:batch_size]

    if not batch_t1 or not batch_t2:
        return

    vibes_t1 = analyze_batch_sentiment(batch_t1)
    vibes_t2 = analyze_batch_sentiment(batch_t2)

    for i in range(min(len(vibes_t1), len(vibes_t2))):
        alpha = 0.8
        st.session_state.team1_vibe = (1 - alpha) * st.session_state.team1_vibe + alpha * vibes_t1[i]
        st.session_state.team2_vibe = (1 - alpha) * st.session_state.team2_vibe + alpha * vibes_t2[i]
        st.session_state.team1_comments.append(clean_comment(batch_t1[i]))
        st.session_state.team2_comments.append(clean_comment(batch_t2[i]))

    st.session_state.last_scrape_count = old_count + min(len(batch_t1), len(batch_t2))

# ============================================================================
# MAIN APP
# ============================================================================

def main():
    st.set_page_config(page_title="NBA Salt Meter", layout="wide", page_icon="🧂")

    st.markdown(
        """
        <style>
            [data-testid="stAppViewContainer"] {
                background: radial-gradient(circle at top left, #192642 0, #050814 45%, #020308 100%);
                color: #f5f5f5;
            }
            [data-testid="stSidebar"] {
                background: linear-gradient(180deg, rgba(5,8,20,0.98), rgba(2,3,8,0.98));
            }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        '<div style="margin-bottom: 1.5rem;"><div style="font-size: 0.85rem; opacity: 0.7;">🏀 NBA REDDIT GAME THREAD TRACKER</div><div style="font-size: 2rem; font-weight: 700;">Salt Meter – Tug of War</div></div>',
        unsafe_allow_html=True
    )

    # Sidebar
    with st.sidebar:
        st.markdown("### ⚙️ Configuration")
        mode = st.radio("Replay Mode", ["Test (CSVs)", "Live (Scraper)"], index=0)

    url1 = None
    url2 = None

    # Mode selection
    if mode == "Test (CSVs)":
        miami_df, wizards_df = load_csv_data()
        if miami_df is None or wizards_df is None:
            st.error("❌ Failed to load CSV files")
            return

        init_session_state(min(len(miami_df), len(wizards_df)))

        team1_name, team2_name = "Miami Heat", "Washington Wizards"
        team1_colors, team2_colors = ("#98002E", "#F9A01B"), ("#002B5C", "#E31837")

        team1_comments_raw = [str(miami_df.iloc[i]["CommentText"]) for i in range(len(miami_df))]
        team2_comments_raw = [str(wizards_df.iloc[i]["CommentText"]) for i in range(len(wizards_df))]

        st.sidebar.success(f"✅ Test Mode\n{len(miami_df)} Heat comments\n{len(wizards_df)} Wiz comments")

    else:
        st.sidebar.markdown("### 🔴 Live Games")
        live_games = get_live_games()

        if not live_games:
            st.warning("⚠️ No games live right now. Try Test Mode or check back later!")
            return

        selected_game = st.sidebar.selectbox("Select Game", live_games)

        if selected_game:
            teams = selected_game.split(' @ ')
            team1_name, team2_name = teams[0].strip(), teams[1].strip()
            team1_colors, team2_colors = ("#98002E", "#F9A01B"), ("#002B5C", "#E31837")

            init_session_state(10_000)

            url1 = get_game_thread_url(team1_name, team2_name)
            url2 = get_game_thread_url(team2_name, team1_name)

            if st.sidebar.button("🔗 Fetch Comments", use_container_width=True):
                reset_replay_state(10_000)

                with st.spinner(f"Scraping {team1_name} vs {team2_name}..."):
                    if url1:
                        comments1 = scrape_reddit_comments(url1)
                        st.session_state.team1_comments_live = comments1
                        st.sidebar.success(f"✅ Found thread for {team1_name}")
                    else:
                        st.session_state.team1_comments_live = []
                        st.sidebar.error(f"❌ No thread found for {team1_name}")

                    if url2:
                        comments2 = scrape_reddit_comments(url2)
                        st.session_state.team2_comments_live = comments2
                        st.sidebar.success(f"✅ Found thread for {team2_name}")
                    else:
                        st.session_state.team2_comments_live = []
                        st.sidebar.error(f"❌ No thread found for {team2_name}")

                    st.session_state.last_scrape_count = 0

            team1_comments_raw = st.session_state.get("team1_comments_live", [])
            team2_comments_raw = st.session_state.get("team2_comments_live", [])

            if not team1_comments_raw and not team2_comments_raw:
                st.info("👈 Click 'Fetch Comments' to start!")
                return

    # Controls
    col_speed, col_buttons, col_status = st.columns([2, 2, 1])

    with col_speed:
        replay_speed = st.slider("Speed", 0.1, 3.0, 0.5)

    with col_buttons:
        col_r, col_t, col_s = st.columns(3)

        with col_r:
            if st.button("⏮ Reset", use_container_width=True):
                if mode == "Test (CSVs)":
                    reset_replay_state(min(len(team1_comments_raw), len(team2_comments_raw)))
                else:
                    reset_replay_state(10_000)
                st.rerun()

        with col_t:
            if st.button("▶ Start" if not st.session_state.is_replaying else "⏸ Pause", use_container_width=True, type="primary"):
                st.session_state.is_replaying = not st.session_state.is_replaying
                st.rerun()

        with col_s:
            if st.button("⏭ Step (50)", use_container_width=True):
                if mode == "Test (CSVs)":
                    process_test_step(team1_comments_raw, team2_comments_raw, batch_size=50)
                else:
                    if url1 or url2:
                        process_live_batch(url1, url2, batch_size=50)
                st.rerun()

    with col_status:
        pct = 0.0
        if st.session_state.max_len > 0:
            pct = (st.session_state.current_index / st.session_state.max_len) * 100
        st.metric("Progress", f"{pct:.1f}%")

    # FIXED AUTOPLAY:
    # Update the state here, but DO NOT rerun yet.
    # Render happens first, then rerun at the very bottom.
    if mode == "Test (CSVs)" and st.session_state.is_replaying:
        process_test_step(team1_comments_raw, team2_comments_raw, batch_size=1)

    if mode == "Live (Scraper)" and st.session_state.is_replaying:
        if url1 or url2:
            process_live_batch(url1, url2, batch_size=50)

    # Render visuals
    render_tug_of_war(
        team1_name,
        team2_name,
        st.session_state.team1_vibe,
        st.session_state.team2_vibe,
        team1_colors,
        team2_colors
    )

    st.markdown("### Live Comment Feeds")
    left_col, right_col = st.columns(2)

    with left_col:
        render_live_feed(f"🔥 {team1_name}", list(st.session_state.team1_comments), team1_colors[0])

    with right_col:
        render_live_feed(f"🔥 {team2_name}", list(st.session_state.team2_comments), team2_colors[0])

    # Helpful debug/status text
    st.caption(
        f"Visible: {compute_salt_metrics(st.session_state.team1_vibe, st.session_state.team2_vibe)['tug_position']:.0f}% | "
        f"Processed: {st.session_state.current_index}"
    )

    # IMPORTANT:
    # Sleep and rerun only AFTER rendering,
    # so the salt meter visibly updates while playing.
    if mode == "Test (CSVs)" and st.session_state.is_replaying:
        time.sleep(replay_speed)
        st.rerun()

    if mode == "Live (Scraper)" and st.session_state.is_replaying:
        time.sleep(5)
        st.rerun()

if __name__ == "__main__":
    main()