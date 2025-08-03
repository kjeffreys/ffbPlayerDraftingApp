import json

import requests

# Fetch player data from Sleeper API
URL = "https://api.sleeper.app/v1/players/nfl"
response = requests.get(URL)
players_data = response.json()

# Filter for fantasy-eligible positions
fantasy_positions = ["QB", "RB", "WR", "TE", "K", "DEF"]
filtered_players = []

for player_id, player in players_data.items():
    if player["position"] in fantasy_positions:
        name = player.get(
            "full_name", player["team"]
        )  # Use full_name, fallback to team
        team = player["team"]
        position = player["position"]
        filtered_players.append(
            {"player_id": player_id, "name": name, "team": team, "position": position}
        )

# Sort players alphabetically by name
filtered_players.sort(key=lambda x: x["name"])

# Write to JSON file
with open("players.json", "w") as f:
    json.dump(filtered_players, f, indent=4)

print("JSON file 'players.json' created successfully!")
