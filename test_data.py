
import json
from pathlib import Path

# Location of our IPL match files
data_folder = Path("data/ipl_male_json")

# Find all JSON match files
match_files = list(data_folder.glob("*.json"))

print("🏏 IPL DATASET CHECK")
print("----------------------")
print("Total matches found:", len(match_files))

if match_files:
    # Read the first match
    with open(match_files[0], "r", encoding="utf-8") as file:
        match = json.load(file)

    info = match["info"]

    print("\nSample Match Details")
    print("----------------------")
    print("Season:", info.get("season", "Not available"))
    print("Teams:", info.get("teams", []))
    print("Venue:", info.get("venue", "Not available"))

    players = info.get("players", {})
    all_players = set()

    for team_players in players.values():
        all_players.update(team_players)

    print("\nPlayers in sample match:", len(all_players))
    print("Player names:", sorted(all_players))
else:
    print("No JSON files found. Please check the data folder.")
