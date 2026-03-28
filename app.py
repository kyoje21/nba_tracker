"""
================================================================================
NBA REDDIT GAME THREAD SALT TRACKER
Live game discovery + scraping + VADER sentiment analysis
Real-time tug-of-war salt meter visualization with team logos & animated salt shaker

DESIGN: Clean Minimalist Wireframe
Author: kyoje21
================================================================================
"""

import os
import time
import math
import warnings
import re
import base64
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Tuple, List, Optional
from collections import deque

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv
import requests
import nltk
nltk.download('vader_lexicon', quiet=True)
from nltk.sentiment import SentimentIntensityAnalyzer

# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("SaltTracker")

try:
    from zoneinfo import ZoneInfo
    ZONEINFO_AVAILABLE = True
except ImportError:
    ZONEINFO_AVAILABLE = False

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
    'merchant': -0.9, 'unethical': -0.9, 'cooked': -0.85, 'washed': -0.9,
    'fraud': -0.95, 'rigged': -0.95, 'terrorism': -1.0, 'statpad': -0.85,
    'mickey': -0.8, 'brick': -0.75, 'choke': -0.85, 'scrub': -0.8,
    'bum': -0.85, 'poverty': -0.9, 'masterclass': -0.7,
    '🤡': -0.95, '🧂': -0.9, '🧱': -0.85, '🗑️': -0.9,
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
# TEAM LOGO MAPPING
# ============================================================================

TEAM_LOGO_MAP = {
    'Hawks': 'assets/logos/hawks.png',
    'Celtics': 'assets/logos/celtics.png',
    'Nets': 'assets/logos/nets.png',
    'Hornets': 'assets/logos/hornets.png',
    'Bulls': 'assets/logos/bulls.png',
    'Cavaliers': 'assets/logos/cavaliers.png',
    'Mavericks': 'assets/logos/mavericks.png',
    'Nuggets': 'assets/logos/nuggets.png',
    'Pistons': 'assets/logos/pistons.png',
    'Warriors': 'assets/logos/warriors.png',
    'Rockets': 'assets/logos/rockets.png',
    'Grizzlies': 'assets/logos/grizzlies.png',
    'Lakers': 'assets/logos/lakers.png',
    'Heat': 'assets/logos/heat.png',
    'Bucks': 'assets/logos/bucks.png',
    'Timberwolves': 'assets/logos/timberwolves.png',
    'Pelicans': 'assets/logos/pelicans.png',
    'Knicks': 'assets/logos/knicks.png',
    '76ers': 'assets/logos/76ers.png',
    'Suns': 'assets/logos/suns.png',
    'Trail Blazers': 'assets/logos/trail_blazers.png',
    'Kings': 'assets/logos/kings.png',
    'Spurs': 'assets/logos/spurs.png',
    'Raptors': 'assets/logos/raptors.png',
    'Jazz': 'assets/logos/jazz.png',
    'Wizards': 'assets/logos/wizards.png',
    'Pacers': 'assets/logos/pacers.png',
    'Clippers': 'assets/logos/clippers.png',
    'Thunder': 'assets/logos/thunder.png',
    'Magic': 'assets/logos/magic.png',
}

# ============================================================================
# PATH / IMAGE HELPERS
# ============================================================================

def get_asset_path(*parts) -> str:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, *parts)


def get_team_logo(team_name: str) -> Optional[str]:
    relative_path = TEAM_LOGO_MAP.get(team_name)
    if not relative_path:
        for key in TEAM_LOGO_MAP:
            if key.lower() in team_name.lower():
                relative_path = TEAM_LOGO_MAP[key]
                break
    if not relative_path:
        return None
    full_path = get_asset_path(relative_path)
    if os.path.exists(full_path):
        return full_path
    return None


def encode_image_b64(path: str) -> Optional[str]:
    if path and os.path.exists(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None


# ============================================================================
# REDDIT RATE LIMIT CHECK
# ============================================================================

def check_reddit_rate_limit(response: requests.Response, context: str = "") -> bool:
    remaining = response.headers.get('x-ratelimit-remaining', '?')
    reset = response.headers.get('x-ratelimit-reset', '?')
    used = response.headers.get('x-ratelimit-used', '?')

    if response.status_code == 429:
        retry_after = response.headers.get('Retry-After', '???')
        logger.warning(
            f"🚫 REDDIT RATE LIMITED [{context}] — "
            f"Status: 429 | Retry-After: {retry_after}s | "
            f"Used: {used} | Remaining: {remaining} | Reset: {reset}s"
        )
        return False
    elif response.status_code == 403:
        logger.warning(
            f"🚫 REDDIT FORBIDDEN [{context}] — "
            f"Status: 403 | Likely IP blocked or user-agent rejected"
        )
        return False
    elif response.status_code != 200:
        logger.warning(
            f"⚠️ REDDIT ERROR [{context}] — "
            f"Status: {response.status_code} | "
            f"Used: {used} | Remaining: {remaining} | Reset: {reset}s"
        )
        return False
    else:
        logger.info(
            f"✅ REDDIT OK [{context}] — "
            f"Status: 200 | Used: {used} | Remaining: {remaining} | Reset: {reset}s"
        )
        return True


# ============================================================================
# SHAKER ROTATION & SPILL COMPUTATION
# ============================================================================

def compute_shaker_rotation(salt_diff: float) -> float:
    abs_diff = abs(salt_diff)
    if abs_diff < 0.1:
        return 0
    elif abs_diff < 0.5:
        magnitude = 15
    elif abs_diff < 1.2:
        magnitude = 25
    else:
        magnitude = 35
    return magnitude * (-1 if salt_diff > 0 else 1)


def compute_spill_strength(salt_diff: float) -> float:
    abs_diff = abs(salt_diff)
    if abs_diff < 0.1:
        return 0.0
    elif abs_diff < 0.5:
        return 0.3 + (abs_diff - 0.1) * 0.4
    elif abs_diff < 1.2:
        return 0.5 + (abs_diff - 0.5) * 0.3
    else:
        return 0.8 + min((abs_diff - 1.2) * 0.2, 0.2)


def compute_spill_direction(salt_diff: float) -> str:
    return 'left' if salt_diff > 0 else 'right'


# ============================================================================
# NBA API: LIVE GAME DISCOVERY
# ============================================================================

def parse_game_time_et(game_time_utc: str) -> str:
    if not game_time_utc:
        return "Time TBD"
    try:
        dt = datetime.fromisoformat(game_time_utc.replace('Z', '+00:00'))
        if ZONEINFO_AVAILABLE:
            dt_et = dt.astimezone(ZoneInfo("America/New_York"))
        else:
            offset = 4 if 3 <= dt.month <= 10 else 5
            dt_et = dt - timedelta(hours=offset)
        return dt_et.strftime("%-I:%M %p ET")
    except Exception:
        return "Time TBD"


@st.cache_data(ttl=60)
def get_live_games_detailed() -> List[Dict]:
    if not NBA_API_AVAILABLE:
        logger.warning("nba_api not available — no live games")
        return []
    try:
        logger.info("Fetching NBA scoreboard...")
        board = scoreboard.ScoreBoard()
        games = board.get_dict()
        results = []
        if 'scoreboard' not in games or 'games' not in games['scoreboard']:
            logger.warning("No games found in NBA scoreboard response")
            return []
        for game in games['scoreboard']['games']:
            away_abbr = game.get('awayTeam', {}).get('teamTricode', '')
            home_abbr = game.get('homeTeam', {}).get('teamTricode', '')
            away_name = TEAM_ABBR_MAP.get(away_abbr, away_abbr)
            home_name = TEAM_ABBR_MAP.get(home_abbr, home_abbr)
            away_score = game.get('awayTeam', {}).get('score', 0)
            home_score = game.get('homeTeam', {}).get('score', 0)
            game_status = game.get('gameStatus', 1)
            game_status_text = game.get('gameStatusText', '').strip()
            game_time_utc = game.get('gameTimeUTC', '') or game.get('gameEt', '')
            time_display = parse_game_time_et(game_time_utc)
            if game_status == 1:
                status_text = time_display
            elif game_status == 2:
                status_text = game_status_text if game_status_text else "Live"
            elif game_status == 3:
                status_text = "Final"
            else:
                status_text = game_status_text if game_status_text else "—"
            if game_status == 1:
                label = f"{away_name} @ {home_name} — {time_display}"
            elif game_status == 2:
                label = f"{away_name} @ {home_name} — {game_status_text} (Live)"
            elif game_status == 3:
                label = f"{away_name} @ {home_name} — Final"
            else:
                label = f"{away_name} @ {home_name}"
            results.append({
                'away_name': away_name,
                'home_name': home_name,
                'away_score': away_score,
                'home_score': home_score,
                'game_status': game_status,
                'status_text': status_text,
                'label': label,
            })
        logger.info(f"Found {len(results)} NBA games")
        return results
    except Exception as e:
        logger.error(f"NBA API error: {e}")
        return []


# ============================================================================
# REDDIT SCRAPER BRIDGE
# ============================================================================

def get_game_thread_url(team1: str, team2: str) -> Optional[str]:
    teams = [team1, team2]
    for team in teams:
        subreddit = TEAM_REDDIT_MAP.get(team)
        if not subreddit:
            for key, val in TEAM_REDDIT_MAP.items():
                if key.lower() in team.lower():
                    subreddit = val
                    break
        if not subreddit:
            continue
        try:
            url = f"https://www.reddit.com/r/{subreddit}/search.json"
            params = {'q': 'Game Thread', 'restrict_sr': True, 'sort': 'new', 'limit': 5}
            headers = {'User-Agent': 'NBA-Salt-Tracker'}
            logger.info(f"Searching r/{subreddit} for game thread...")
            response = requests.get(url, params=params, headers=headers, timeout=10)
            if not check_reddit_rate_limit(response, context=f"search r/{subreddit}"):
                return None
            data = response.json()
            if 'data' in data and 'children' in data['data']:
                for post in data['data']['children']:
                    post_data = post['data']
                    if 'game thread' in post_data['title'].lower():
                        thread_url = f"https://www.reddit.com{post_data['permalink']}"
                        logger.info(f"Found game thread: {post_data['title'][:60]}...")
                        return thread_url
            logger.info(f"No game thread found in r/{subreddit}")
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout searching r/{subreddit}")
            continue
        except Exception as e:
            logger.error(f"Error searching r/{subreddit}: {e}")
            continue
    return None


def scrape_reddit_comments(url: str, max_comments: int = 500) -> List[str]:
    try:
        json_url = url.rstrip('/') + '.json'
        headers = {'User-Agent': 'NBA-Salt-Tracker'}
        params = {
            'sort': 'new',
            'limit': 500,
            't': int(time.time()),
        }
        logger.info(f"Scraping comments from: {url[:80]}...")
        response = requests.get(json_url, headers=headers, params=params, timeout=15)
        if not check_reddit_rate_limit(response, context="scrape comments"):
            return []
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
        logger.info(f"Scraped {len(comments)} comments (returning max {max_comments})")
        return comments[:max_comments]
    except requests.exceptions.Timeout:
        logger.warning("Timeout scraping comments")
        return []
    except Exception as e:
        logger.error(f"Error scraping comments: {e}")
        return []


# ============================================================================
# SENTIMENT ANALYSIS
# ============================================================================

def analyze_sentiment(comment: str) -> float:
    if not VADER_AVAILABLE or sia is None:
        return 0.0
    try:
        scores = sia.polarity_scores(comment)
        return float(scores['compound'])
    except Exception:
        return 0.0


def analyze_batch_sentiment(comments: List[str]) -> List[float]:
    return [analyze_sentiment(c) for c in comments]


# ============================================================================
# SALT COMPUTATION
# ============================================================================

def compute_salt_metrics(team1_name: str, team2_name: str, team1_vibe: float, team2_vibe: float) -> Dict:
    team1_salt = -1.0 * team1_vibe
    team2_salt = -1.0 * team2_vibe
    salt_diff = team2_salt - team1_salt
    amplified_diff = salt_diff * 2.0
    tug_position = 50.0 + (amplified_diff * 12.5)
    tug_position = max(8.0, min(92.0, tug_position))

    if abs(amplified_diff) < 0.1:
        status_text = "Plain Jane"
    elif abs(amplified_diff) < 0.5:
        salty_team = team1_name if amplified_diff < 0 else team2_name
        status_text = f"{salty_team} Little Salty from their Tears"
    elif abs(amplified_diff) < 1.2:
        salty_team = team1_name if amplified_diff < 0 else team2_name
        status_text = f"{salty_team} So Salty! Send'em Back to the Kitchen!"
    else:
        salty_team = team1_name if amplified_diff < 0 else team2_name
        status_text = f"{salty_team}'S SALT MINE EXPLODED! WORLD STAR SALT ALERT!"

    return {
        'team1_salt': team1_salt,
        'team2_salt': team2_salt,
        'salt_diff': amplified_diff,
        'tug_position': tug_position,
        'status_text': status_text,
    }


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
        logger.info(f"Loaded CSVs: Miami={len(miami_df)} rows, Wizards={len(wizards_df)} rows")
        return miami_df, wizards_df
    except Exception as e:
        logger.error(f"Failed to load CSV data: {e}")
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
    if "url1" not in st.session_state:
        st.session_state.url1 = None
    if "url2" not in st.session_state:
        st.session_state.url2 = None
    if "last_selected_game" not in st.session_state:
        st.session_state.last_selected_game = None
    if "_prev_t1_hashes" not in st.session_state:
        st.session_state._prev_t1_hashes = []
    if "_prev_t2_hashes" not in st.session_state:
        st.session_state._prev_t2_hashes = []
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
    st.session_state._prev_t1_hashes = []
    st.session_state._prev_t2_hashes = []


def process_test_step(team1_comments_raw: List[str], team2_comments_raw: List[str], batch_size: int = 1):
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
    Re-scrape the full thread each cycle to get fresh comments.
    Uses comment hashing to detect truly new comments.
    """
    all_t1 = scrape_reddit_comments(url1) if url1 else []
    all_t2 = scrape_reddit_comments(url2) if url2 else []

    if not all_t1 and not all_t2:
        logger.info("No comments returned from either thread")
        return

    # Compare against what we had before
    old_t1 = set(st.session_state.get("_prev_t1_hashes", []))
    old_t2 = set(st.session_state.get("_prev_t2_hashes", []))

    new_t1 = [c for c in all_t1 if hash(c) not in old_t1]
    new_t2 = [c for c in all_t2 if hash(c) not in old_t2]

    # Store current hashes for next cycle
    st.session_state._prev_t1_hashes = [hash(c) for c in all_t1]
    st.session_state._prev_t2_hashes = [hash(c) for c in all_t2]

    if not new_t1 and not new_t2:
        logger.info(f"No NEW comments (t1={len(all_t1)} total, t2={len(all_t2)} total, all seen before)")
        return

    batch_t1 = new_t1[:batch_size]
    batch_t2 = new_t2[:batch_size]

    logger.info(f"Found {len(new_t1)} new t1 comments, {len(new_t2)} new t2 comments")

    if batch_t1:
        vibes_t1 = analyze_batch_sentiment(batch_t1)
        for i in range(len(vibes_t1)):
            alpha = 0.8
            st.session_state.team1_vibe = (1 - alpha) * st.session_state.team1_vibe + alpha * vibes_t1[i]
            st.session_state.team1_comments.append(clean_comment(batch_t1[i]))

    if batch_t2:
        vibes_t2 = analyze_batch_sentiment(batch_t2)
        for i in range(len(vibes_t2)):
            alpha = 0.8
            st.session_state.team2_vibe = (1 - alpha) * st.session_state.team2_vibe + alpha * vibes_t2[i]
            st.session_state.team2_comments.append(clean_comment(batch_t2[i]))

    logger.info(
        f"Processed t1={len(batch_t1)}, t2={len(batch_t2)} new comments | "
        f"Vibes: t1={st.session_state.team1_vibe:.3f}, t2={st.session_state.team2_vibe:.3f}"
    )


def auto_fetch_live_comments(team1_name: str, team2_name: str):
    game_key = f"{team1_name}_vs_{team2_name}"
    if st.session_state.get("last_selected_game") == game_key:
        return
    st.session_state.last_selected_game = game_key
    reset_replay_state(10_000)
    logger.info(f"Auto-fetching comments for {team1_name} vs {team2_name}")
    with st.spinner(f"Fetching comments for {team1_name} vs {team2_name}..."):
        url1 = get_game_thread_url(team1_name, team2_name)
        url2 = get_game_thread_url(team2_name, team1_name)
        if url1:
            st.session_state.team1_comments_live = scrape_reddit_comments(url1)
            st.session_state.url1 = url1
        else:
            st.session_state.team1_comments_live = []
            st.session_state.url1 = None
        if url2:
            st.session_state.team2_comments_live = scrape_reddit_comments(url2)
            st.session_state.url2 = url2
        else:
            st.session_state.team2_comments_live = []
            st.session_state.url2 = None
        st.session_state.last_scrape_count = 0
        # Seed the hash tracking with initial comments
        st.session_state._prev_t1_hashes = [hash(c) for c in st.session_state.team1_comments_live]
        st.session_state._prev_t2_hashes = [hash(c) for c in st.session_state.team2_comments_live]
        logger.info(
            f"Fetch complete — Team1: {len(st.session_state.team1_comments_live)} comments, "
            f"Team2: {len(st.session_state.team2_comments_live)} comments"
        )


# ============================================================================
# THEME / CSS INJECTION
# ============================================================================

def inject_minimalist_theme():
    st.markdown("""
    <style>
        * { box-sizing: border-box; }
        html, body {
            background: #f5f5f5;
            color: #000;
            font-family: 'Courier New', monospace;
        }
        [data-testid="stAppViewContainer"] {
            background: #f5f5f5;
            color: #000;
        }
        /* [CHANGED] Reduce Streamlit default gaps for single-screen layout */
        [data-testid="stVerticalBlock"] > div { gap: 0.15rem !important; }
        .element-container { margin-bottom: 0 !important; }
        [data-testid="stSidebar"] { display: none !important; }
        /* [CHANGED] Push content below Streamlit toolbar */
        .block-container {
            padding-top: 3rem !important;
            padding-bottom: 0.3rem !important;
        }
        /* [CHANGED] Reduced title size/margins for compact layout */
        .page-title {
            text-align: center;
            font-size: 1.6rem;
            font-weight: normal;
            margin-bottom: 0.2rem;
            margin-top: 0.1rem;
            letter-spacing: 1px;
            font-family: 'Courier New', monospace;
        }
        .score-section {
            text-align: center;
            margin: 0.5rem 0 0.5rem 0;
            font-family: 'Courier New', monospace;
        }
        .score-label {
            font-size: 1rem;
            letter-spacing: 2px;
            opacity: 0.6;
            text-transform: uppercase;
            margin-bottom: 0.25rem;
        }
        .score-value {
            font-size: 2.2rem;
            font-weight: normal;
            letter-spacing: 4px;
        }
        .score-status {
            font-size: 0.85rem;
            opacity: 0.5;
            margin-top: 0.25rem;
        }
        .salt-status-text {
            font-size: 0.9rem;
            letter-spacing: 1px;
            font-family: 'Courier New', monospace;
            opacity: 0.7;
            margin-top: 0.4rem;
        }
        /* [CHANGED] Compact live comments heading */
        .live-comments-title {
            text-align: center;
            font-size: 1rem;
            margin-top: 0.15rem;
            margin-bottom: 0.15rem;
            font-weight: normal;
            letter-spacing: 1px;
            font-family: 'Courier New', monospace;
        }
        .comment-panel-title {
            font-size: 1rem;
            font-weight: normal;
            margin-bottom: 1rem;
            text-align: center;
            letter-spacing: 1px;
            font-family: 'Courier New', monospace;
        }
        /* [CHANGED] Reduced panel height for single-screen layout */
        .comment-panel {
            border: 2px solid #000;
            padding: 0.75rem;
            min-height: 120px;
            max-height: 230px;
            background: #fff;
            overflow-y: auto;
        }
        .comment-card {
            font-size: 0.95rem;
            line-height: 1.6;
            margin-bottom: 1rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid #ddd;
            white-space: normal;
            word-break: break-word;
            font-family: 'Courier New', monospace;
        }
        .comment-card:last-child {
            border-bottom: none;
            margin-bottom: 0;
            padding-bottom: 0;
        }
        [data-testid="stButton"] > button {
            background: #fff !important;
            border: 2px solid #000 !important;
            color: #000 !important;
            font-weight: normal !important;
            font-size: 0.95rem !important;
            padding: 0.6rem 1.2rem !important;
            border-radius: 0 !important;
            text-transform: uppercase !important;
            letter-spacing: 1px !important;
            box-shadow: none !important;
            transition: all 0.2s ease !important;
            font-family: 'Courier New', monospace !important;
            min-height: 48px !important;
        }
        [data-testid="stButton"] > button:hover {
            background: #000 !important;
            color: #fff !important;
        }
        [data-testid="stSelectbox"] > div {
            background: #f9f9f9 !important;
            border: 2px solid #000 !important;
            border-radius: 0 !important;
            box-shadow: none !important;
            margin-top: 15px !important;
        }
        [data-testid="stSelectbox"] > div > div {
            color: #000 !important;
            font-family: 'Courier New', monospace !important;
            font-size: 1.15rem !important;
        }
        [data-testid="stSelectbox"] [data-baseweb="select"] > div {
            background: #f9f9f9 !important;
            border: none !important;
            border-radius: 0 !important;
            box-shadow: none !important;
            font-family: 'Courier New', monospace !important;
            color: #000 !important;
            min-height: 48px !important;
            font-size: 1.15rem !important;
        }
        [data-testid="stSelectbox"] svg {
            fill: #000 !important;
        }
        [data-baseweb="popover"] {
            border: 2px solid #000 !important;
            border-radius: 0 !important;
            box-shadow: none !important;
        }
        [data-baseweb="popover"] ul {
            background: #f9f9f9 !important;
            border-radius: 0 !important;
            padding: 0 !important;
        }
        [data-baseweb="popover"] li {
            background: #f9f9f9 !important;
            color: #000 !important;
            font-family: 'Courier New', monospace !important;
            font-size: 0.95rem !important;
            border-bottom: 1px solid #e0e0e0 !important;
            padding: 0.6rem 1rem !important;
            border-radius: 0 !important;
        }
        [data-baseweb="popover"] li:last-child {
            border-bottom: none !important;
        }
        [data-baseweb="popover"] li:hover,
        [data-baseweb="popover"] li[aria-selected="true"] {
            background: #e8e8e8 !important;
            color: #000 !important;
        }
        [data-baseweb="select"] *:focus {
            outline: none !important;
            box-shadow: none !important;
        }
        div[data-testid="stMarkdownContainer"] p { margin-bottom: 0; }
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: #f5f5f5; }
        ::-webkit-scrollbar-thumb { background: #000; }
        @media (max-width: 768px) {
            .page-title { font-size: 1.5rem; }
            .score-value { font-size: 1.5rem; }
        }
    </style>
    """, unsafe_allow_html=True)


# ============================================================================
# RENDER FUNCTIONS
# ============================================================================

def render_title():
    st.markdown(
        '<div class="page-title">REDDIT NBA LIVE GAME THREAD SALT TRACKER</div>',
        unsafe_allow_html=True
    )


def render_game_selector(options: List[str]) -> Optional[str]:
    if not options:
        return None

    if "selected_game_index" not in st.session_state:
        st.session_state.selected_game_index = 0

    if st.session_state.selected_game_index >= len(options):
        st.session_state.selected_game_index = 0

    left, center, right = st.columns([1, 2, 1])
    with center:
        selected = st.selectbox(
            "SELECT GAME",
            options,
            index=st.session_state.selected_game_index,
            key="game_selector",
            label_visibility="collapsed"
        )

    if selected in options:
        new_index = options.index(selected)
        if new_index != st.session_state.selected_game_index:
            st.session_state.selected_game_index = new_index
            logger.info(f"Game selection changed to: {selected}")

    return selected


def render_salt_meter(team1_name: str, team2_name: str, team1_vibe: float, team2_vibe: float):
    metrics = compute_salt_metrics(team1_name, team2_name, team1_vibe, team2_vibe)
    tug_pct = metrics["tug_position"]
    salt_diff = metrics["salt_diff"]
    rotation = compute_shaker_rotation(salt_diff)
    spill = compute_spill_strength(salt_diff)

    shaker_path = get_asset_path("assets", "saltshaker.png")
    shaker_b64 = encode_image_b64(shaker_path)
    if shaker_b64:
        shaker_el = f'<img src="data:image/png;base64,{shaker_b64}" width="100" />'  # [CHANGED] larger shaker
    else:
        shaker_el = '<span style="font-size:5.5rem;">🧂</span>'  # [CHANGED] larger fallback

    spill_particles = ""
    FIXED_IFRAME_HEIGHT = 280
    if spill > 0.1:
        num_particles = int(spill * 18)
        rot_rad = math.radians(rotation)
        # Shaker center is at 50% of iframe; particles fall from just below it
        shaker_center_y = FIXED_IFRAME_HEIGHT * 0.5
        for i in range(num_particles):
            pour_offset_x = -math.sin(rot_rad) * 35
            fan_spread = (i - num_particles // 2) * 5
            fan_x = fan_spread * math.cos(rot_rad) + pour_offset_x
            # Particles fall downward from below the shaker
            fall_distance = 30 + (i % 6) * 8 + (i * 5 % 15)
            px = fan_x
            py = shaker_center_y + fall_distance
            size = 4 + (i % 3)
            opacity = 0.4 + spill * 0.35 - (i * 0.015)
            opacity = max(0.15, min(0.85, opacity))
            spill_particles += (
                f'<div style="position:absolute; top:{py:.0f}px; '
                f'left:calc({tug_pct}% + {px:.0f}px); '
                f'width:{size}px; height:{size}px; background:#333; '
                f'border-radius:50%; opacity:{opacity:.2f};"></div>'
            )

    meter_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                background: #f5f5f5;
                font-family: 'Courier New', monospace;
                color: #000;
                display: flex;
                flex-direction: column;
                align-items: center;
                padding: 0;
                height: {FIXED_IFRAME_HEIGHT}px;
                overflow: visible;
            }}
            .meter-wrapper {{
                width: 100%;
                height: 100%;
                position: relative;
            }}
            /* [CHANGED] Removed .team-names — team identity via logos only */
            .meter-area {{
                position: relative;
                width: 100%;
                height: 100%;
                overflow: visible;
            }}
            /* [CHANGED] Thin bar: 40px bordered → 4px solid line */
            .meter-track {{
                position: absolute;
                top: 50%;
                left: 0;
                right: 0;
                height: 4px;
                background: #000;
                transform: translateY(-50%);
            }}
            /* [CHANGED] Shaker centered on thin bar */
            .shaker {{
                position: absolute;
                top: 50%;
                left: {tug_pct}%;
                transform: translate(-50%, -50%) rotate({rotation}deg);
                transition: left 0.5s ease, transform 0.5s ease;
                z-index: 10;
            }}
        </style>
    </head>
    <body>
        <div class="meter-wrapper">
            <!-- [CHANGED] Removed team name labels -->
            <div class="meter-area">
                <div class="meter-track"></div>
                <div class="shaker">{shaker_el}</div>
                {spill_particles}
            </div>
        </div>
    </body>
    </html>
    """

    components.html(meter_html, height=FIXED_IFRAME_HEIGHT, scrolling=False)


def render_score_section(team1_name: str, team2_name: str,
                         team1_score="--", team2_score="--",
                         status_text="—"):
    """Score row: numbers and game status (logos rendered separately)."""
    team1_color = "#000"
    team2_color = "#000"
    team1_weight = "normal"
    team2_weight = "normal"

    try:
        if team1_score != "--" and team2_score != "--":
            t1 = int(team1_score)
            t2 = int(team2_score)
            if t1 > t2:
                team1_color = "#22c55e"
                team1_weight = "bold"
            elif t2 > t1:
                team2_color = "#22c55e"
                team2_weight = "bold"
    except Exception:
        pass

    score_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                background: #f5f5f5;
                font-family: 'Courier New', monospace;
                color: #000;
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 0;
            }}
            .score-center {{ text-align: center; }}
            .score-value {{
                font-size: 2.4rem;
                font-weight: normal;
                letter-spacing: 6px;
            }}
            .score-status {{
                font-size: 0.85rem;
                opacity: 0.5;
                margin-top: 4px;
            }}
        </style>
    </head>
    <body>
        <div class="score-center">
            <div class="score-value">
                <span style="color:{team1_color}; font-weight:{team1_weight};">{team1_score}</span>
                —
                <span style="color:{team2_color}; font-weight:{team2_weight};">{team2_score}</span>
            </div>
            <div class="score-status">{status_text}</div>
        </div>
    </body>
    </html>
    """

    components.html(score_html, height=80, scrolling=False)


def render_live_comments_heading():
    st.markdown(
        '<div class="live-comments-title">LIVE COMMENTS</div>',
        unsafe_allow_html=True
    )


def render_comment_panels(team1_name: str, team2_name: str, team1_comments: List[str], team2_comments: List[str]):
    col1, col2 = st.columns(2)

    team1_html = "".join(
        f'<div class="comment-card">{c}</div>' for c in reversed(team1_comments)
    ) or '<div class="comment-card">No comments yet.</div>'

    team2_html = "".join(
        f'<div class="comment-card">{c}</div>' for c in reversed(team2_comments)
    ) or '<div class="comment-card">No comments yet.</div>'

    with col1:
        # [CHANGED] Removed team name title — identified by logos in score section
        st.markdown(f'<div class="comment-panel">{team1_html}</div>', unsafe_allow_html=True)

    with col2:
        # [CHANGED] Removed team name title — identified by logos in score section
        st.markdown(f'<div class="comment-panel">{team2_html}</div>', unsafe_allow_html=True)


# ============================================================================
# MAIN APP
# ============================================================================

def main():
    st.set_page_config(page_title="NBA Salt Meter", layout="wide", page_icon="🧂")

    inject_minimalist_theme()
    st.markdown(
        '<style>[data-testid="collapsedControl"] { display: none; }</style>',
        unsafe_allow_html=True
    )

    render_title()
    init_session_state(100)

    # ------------------------------------------------------------------
    # MODE + GAME SELECTION
    # ------------------------------------------------------------------
    TEST_LABEL = "🧪 Test Data — Miami Heat @ Washington Wizards"

    live_games_data = get_live_games_detailed()
    live_labels = [g['label'] for g in live_games_data]

    all_options = [TEST_LABEL] + live_labels

    selected = render_game_selector(all_options)

    if not selected:
        return

    is_test_mode = (selected == TEST_LABEL)

    # ------------------------------------------------------------------
    # SETUP BASED ON SELECTION
    # ------------------------------------------------------------------
    url1 = None
    url2 = None
    team1_comments_raw = []
    team2_comments_raw = []
    team1_score = "--"
    team2_score = "--"
    game_status_display = "—"

    if is_test_mode:
        st.session_state.last_selected_game = None

        miami_df, wizards_df = load_csv_data()
        if miami_df is None or wizards_df is None:
            st.error("❌ Failed to load CSV test files from data/ folder.")
            return

        init_session_state(min(len(miami_df), len(wizards_df)))
        team1_name, team2_name = "Miami Heat", "Washington Wizards"
        team1_comments_raw = [str(miami_df.iloc[i]["CommentText"]) for i in range(len(miami_df))]
        team2_comments_raw = [str(wizards_df.iloc[i]["CommentText"]) for i in range(len(wizards_df))]

        team1_score = "--"
        team2_score = "--"
        game_status_display = "Test Data"

    else:
        game_data = None
        for g in live_games_data:
            if g['label'] == selected:
                game_data = g
                break

        if not game_data:
            st.warning("⚠️ Could not find game data for selection.")
            return

        team1_name = game_data['away_name']
        team2_name = game_data['home_name']
        team1_score = game_data['away_score']
        team2_score = game_data['home_score']
        game_status_display = game_data['status_text']

        init_session_state(10_000)

        auto_fetch_live_comments(team1_name, team2_name)

        team1_comments_raw = st.session_state.get("team1_comments_live", [])
        team2_comments_raw = st.session_state.get("team2_comments_live", [])

        url1 = st.session_state.get("url1")
        url2 = st.session_state.get("url2")

        if not team1_comments_raw and not team2_comments_raw:
            st.info("No game thread comments found for this matchup yet.")

    # ------------------------------------------------------------------
    # PROCESS STATE UPDATE (before layout so comments are current)
    # ------------------------------------------------------------------
    salt_metrics = compute_salt_metrics(
        team1_name, team2_name,
        st.session_state.team1_vibe, st.session_state.team2_vibe
    )

    if is_test_mode and st.session_state.is_replaying:
        process_test_step(team1_comments_raw, team2_comments_raw, batch_size=1)

    if not is_test_mode and st.session_state.is_replaying:
        if url1 or url2:
            process_live_batch(url1, url2, batch_size=50)

    # ------------------------------------------------------------------
    # 3-COLUMN LAYOUT: logos flanking center content
    # ------------------------------------------------------------------
    logo_left, center_area, logo_right = st.columns([1, 3, 1])

    with logo_left:
        st.markdown("<div style='height:100px;'></div>", unsafe_allow_html=True)
        logo_path = get_team_logo(team1_name)
        if logo_path:
            st.image(logo_path, use_container_width=True)

    with center_area:
        # 1. Salt meter (shaker on bar)
        render_salt_meter(
            team1_name,
            team2_name,
            st.session_state.team1_vibe,
            st.session_state.team2_vibe
        )

        # 2. Playback controls
        _, btn_col, _ = st.columns([2, 1, 2])
        with btn_col:
            is_playing = st.session_state.get('is_replaying', False)
            if st.button("▶ START" if not is_playing else "⏸ PAUSE", use_container_width=True):
                st.session_state.is_replaying = not st.session_state.is_replaying
                st.rerun()

        # 3. Score row
        render_score_section(
            team1_name,
            team2_name,
            team1_score=team1_score,
            team2_score=team2_score,
            status_text=game_status_display,
        )

        # 4-5. Salt status
        st.markdown(
            f'<div class="salt-status-text" style="text-align:center;font-size:1rem;'
            f'letter-spacing:1px;font-family:Courier New,monospace;font-weight:bold;'
            f'text-transform:uppercase;margin:0.3rem 0;">{salt_metrics["status_text"]}</div>',
            unsafe_allow_html=True
        )

        # 6-7. Live comments
        render_live_comments_heading()
        render_comment_panels(
            team1_name,
            team2_name,
            list(st.session_state.team1_comments),
            list(st.session_state.team2_comments)
        )

    with logo_right:
        st.markdown("<div style='height:100px;'></div>", unsafe_allow_html=True)
        logo_path = get_team_logo(team2_name)
        if logo_path:
            st.image(logo_path, use_container_width=True)

    # ------------------------------------------------------------------
    # AUTOPLAY RERUN
    # ------------------------------------------------------------------
    if st.session_state.is_replaying:
        if is_test_mode:
            time.sleep(0.5)
        else:
            time.sleep(10)
        st.rerun()


if __name__ == "__main__":
    main()