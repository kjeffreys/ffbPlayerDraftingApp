# Fantasy Football Draft Assistant

A web-based draft assistant built with React and Vite, designed to help fantasy football players optimize their picks using sortable Value Over Replacement (VOR), Average Draft Position (ADP), and Bye Week tracking.

## ✨ Features

- View and filter all available players by position
- Sort by VOR or ADP
- Visual indicators for positional scarcity
- Draft tracking and reset functionality
- Bye week clustering analysis for drafted team
- JSON-based player data (fully editable)
- Customizable weighting for rookies and projections

## 🚀 Getting Started

### Prerequisites

- [Node.js](https://nodejs.org/en/) 18+ (recommend using `nvm`)

### Install & Run

```bash
npm install
npm run 
```
Then visit: http://localhost:5173

📁 File Structure
index.html – Entrypoint for Vite app

index.tsx – Main React code and component logic

players.json – Source of all player data (ADP, VOR, etc.)

vite.config.ts – Vite bundler configuration

🧠 Data Logic & Scoring
VOR (Value Over Replacement) is calculated based on:

80% weight from expert 2025 PPG projections

20% weight from 2024 PPG stats

Optional rookie bonus adjustment (default +10%)

All scores are standardized so rookies and veterans are comparable

Settings like rookie bonus or PPG weights can be toggled per draft strategy

🛠 To Do
🔄 Fetch and preprocess updated 2025 player pool

📊 Automate VOR calculation from live projections

🧩 Allow users to adjust scoring weights and rookie bias interactively

📤 Add export feature for drafted team

⚖ License
MIT License

yaml
Copy
Edit

---

## ✅ 2. How to Update `players.json` for 2025 (with Rookies)

You’ll need three steps:

### **Step 1: Get 2025 Player Pool**
Sources:
- [FantasyPros API (or CSV exports)](https://www.fantasypros.com/nfl/projections/qb.php)
- [Sleeper API (via community wrappers)](https://api.sleeper.app/v1/)
- [ESPN/FantasyData/Sportradar (paid/licensed)]
- GitHub repos like [`nflfastR`](https://github.com/mrcaseb/nflfastR)

We can write a script (Python or Node) to fetch or parse their data if you choose a source.

---

### **Step 2: Normalize Data Structure**

Each player needs:
```json
{
  "id": 999,
  "name": "Player Name",
  "team": "ABC",
  "position": "WR",
  "adp": 28.3,
  "vor": 56.7,
  "bye": 7
}
You can use:

Expert projected PPG (weighted 80%)

2024 actual PPG (weighted 20%)

Add +10% if rookie and use config.rookie_bonus = 1.1

Step 3: Automate Scoring and VOR Calculation
We can build a script to:

Assign VOR = player_score - replacement_score

Determine replacement values dynamically (e.g., RB#20 in 12-team league = baseline RB)

Use a config file like:

json
Copy
Edit
{
  "rookie_bonus": 0.10,
  "projection_weight": 0.80,
  "last_year_weight": 0.20,
  "league": {
    "teams": 12,
    "positions": {
      "QB": 1,
      "RB": 2,
      "WR": 2,
      "TE": 1,
      "FLEX": 1,
      "K": 1,
      "DEF": 1
    }
  }
}