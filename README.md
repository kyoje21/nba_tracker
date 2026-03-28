## NBA Salt Meter – Live Game Thread Salt Tracker 🧂

Every NBA game thread on Reddit tells a story — not just of the game itself, but of the fans living and dying with every play. The **NBA Salt Meter** captures that emotional rollercoaster by analyzing fan sentiment from Reddit game threads and visualizing it as an interactive "Salt Meter" dashboard.

Built with **Streamlit**, this app scrapes Reddit game thread comments, runs them through **VADER sentiment analysis** enhanced with a custom NBA slang lexicon (covering terms like "fraud," "cooked," "goat," and "clutch"), and produces a tug-of-war style visualization showing which fanbase is saltier at any given moment.

### Features

- **Live Game Discovery** — Automatically detects today's NBA games via the `nba_api` scoreboard endpoint and displays live scores and game status.
- **Reddit Scraping** — Searches team subreddits for game threads and scrapes comments in real time using Reddit's JSON API.
- **Custom NBA Lexicon** — VADER sentiment analyzer boosted with NBA-specific slang and emoji (🤡, 🧂, 🧱, 🐐, 🔥, etc.).
- **Salt Meter Visualization** — Animated tug-of-war bar with a tilting salt shaker and falling salt particles indicating which fanbase is more toxic.
- **Live Comment Feed** — Side-by-side scrolling panels showing the latest comments from each team's game thread.
- **Salt Status Levels** — From "Plain Jane" to "SALT MINE EXPLODED! WORLD STAR SALT ALERT!" based on sentiment difference.
- **Test Data Mode** — Replay a pre-scraped Miami Heat vs. Washington Wizards game thread to demo the app without any live data.
- **3-Column Layout** — Team logos flank a centered vertical stack containing the salt meter, controls, score, salt status, and live comments.

### Project Structure

```
nba_tracker/
├── app.py                  # Main Streamlit application
├── requirements.txt        # Python dependencies
├── .gitignore
├── .streamlit/
│   └── config.toml         # Streamlit theme configuration
├── assets/
│   ├── saltshaker.png      # Salt shaker image for the meter
│   └── logos/              # PNG logos for all 30 NBA teams
└── data/
    ├── miami_heat_thread.csv   # Test data (columns: Author, Score, CommentText)
    └── wizards_thread.csv      # Test data (columns: Author, Score, CommentText)
```

### Setup & Run Locally

**1. Clone the repository**

```bash
git clone https://github.com/kyoje21/nba_tracker.git
cd nba_tracker
```

**2. Create a virtual environment (recommended)**

```bash
python3 -m venv venv
source venv/bin/activate
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

**4. Run the app**

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`.

### How It Works

1. **Game Selection** — On launch, the app fetches today's NBA games from the live scoreboard API. You can pick any game from the dropdown, or choose the built-in test data (Miami Heat @ Washington Wizards).

2. **Comment Scraping** — When a live game is selected, the app searches both teams' subreddits for the active game thread and pulls comments via Reddit's public JSON API (no API key required).

3. **Sentiment Analysis** — Each comment is scored using NLTK's VADER analyzer, augmented with a custom lexicon of NBA slang, memes, and emoji. An exponential moving average (α = 0.8) tracks each fanbase's overall vibe.

4. **Salt Meter** — The sentiment difference drives the tug-of-war meter: the salt shaker slides toward the saltier fanbase, tilts, and spills animated salt particles when toxicity is high.

5. **Playback** — Press **▶ START** to begin processing comments. In test mode, comments replay one at a time (0.5s interval). In live mode, the app re-scrapes threads every 10 seconds for new comments using hash-based deduplication.

### Dependencies

| Package | Purpose |
|---------|---------|
| `streamlit` | Web dashboard framework |
| `pandas` | CSV data loading |
| `nltk` | VADER sentiment analysis |
| `nba_api` | Live NBA scoreboard data |
| `requests` | Reddit API scraping |
| `python-dotenv` | Environment variable loading |

### Live Deployment

The app is deployed on Streamlit Community Cloud:

👉 [https://kyoje21-nba-tracker.streamlit.app](https://kyoje21-nba-tracker.streamlit.app)

### Author

**kyoje21**

