## NBA Salt Meter – Game Replay Dashboard

Every NBA game thread on Reddit tells a story — not just of the game itself, but of the fans living and dying with every play. The **NBA Salt Meter** captures that emotional rollercoaster by analyzing real-time fan sentiment from Reddit game threads and visualizing it as an interactive "Salt Meter" dashboard.

Built with Streamlit, this app scrapes Reddit game thread comments, runs them through VADER sentiment analysis enhanced with a custom NBA slang lexicon (covering terms like "fraud," "cooked," "goat," and "clutch"), and produces a tug-of-war style visualization showing which fanbase is saltier at any given moment during the game. The dashboard features team logos, animated salt shaker alerts for peak toxicity moments, and a replay mode that lets you watch fan sentiment evolve play-by-play.

The included sample data covers a **Miami Heat vs. Washington Wizards** matchup, but the app supports all 30 NBA teams and can discover live games via the NBA API to scrape fresh threads in real time.

### Setup

- **1. Install dependencies**

```bash
pip install -r requirements.txt
```

- **2. Environment**

Create a `.env` file in the project root with:

```bash
GOOGLE_API_KEY=YOUR_GOOGLE_API_KEY
```

- **3. Data**

Place your CSVs in a `data/` folder:

- `data/miami_heat_thread.csv`
- `data/wizards_thread.csv`

Each CSV should have at least a `comment` column containing fan comments.

### Run the app

From the project root:

```bash
streamlit run app.py
```

Use the **"Replay speed"** slider and **"Start Replay"** button to watch the sentiment evolve over the course of the game, including high-tension "High Salt Alert" moments.

