# chess_commands.py - Chess tournament management commands for Discord bot
import discord
from discord import app_commands
import datetime
import json
import os
import random
import asyncio
from typing import Optional, List, Dict, Tuple
import math

# Constants for chess ratings
RATING_TIERS = {
    "Grandmaster": 2500,
    "Master": 2200,
    "Expert": 2000,
    "Class A": 1800,
    "Class B": 1600,
    "Class C": 1400,
    "Class D": 1200,
    "Beginner": 0
}

# File paths for data storage
TOURNAMENTS_FILE = 'data/tournaments.json'
PLAYERS_FILE = 'data/players.json'
MATCHES_FILE = 'data/matches.json'

# Ensure data directory exists
os.makedirs('data', exist_ok=True)

# Helper functions for data management
def load_data(file_path, default=None):
    """Load data from a JSON file"""
    if default is None:
        default = {}
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        save_data(file_path, default)
        return default

def save_data(file_path, data):
    """Save data to a JSON file"""
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)

# Load data
tournaments = load_data(TOURNAMENTS_FILE, {"tournaments": {}})
players = load_data(PLAYERS_FILE, {"players": {}})
matches = load_data(MATCHES_FILE, {"matches": {}})

# Helper function to get player rating tier
def get_rating_tier(rating):
    """Get the rating tier for a given rating"""
    for tier, min_rating in sorted(RATING_TIERS.items(), key=lambda x: x[1], reverse=True):
        if rating >= min_rating:
            return tier
    return "Beginner"

# Helper function to generate a unique ID
def generate_id(prefix):
    """Generate a unique ID with the given prefix"""
    return f"{prefix}-{random.randint(1000, 9999)}"

# Tournament creation view
class TournamentCreationView(discord.ui.View):
    def __init__(self, interaction: discord.Interaction):
        super().__init__(timeout=300)  # 5 minute timeout
        self.interaction = interaction
        self.tournament_name = None
        self.tournament_type = "Swiss"
        self.rounds = 5
        self.time_control = "10+5"
        self.description = "Chess Tournament"
        self.registration_deadline = None
        self.start_date = None
        
    @discord.ui.button(label="Swiss System", style=discord.ButtonStyle.primary)
    async def swiss_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.tournament_type = "Swiss"
        await interaction.response.send_message("Tournament type set to Swiss System", ephemeral=True)
        
    @discord.ui.button(label="Round Robin", style=discord.ButtonStyle.primary)
    async def round_robin_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.tournament_type = "Round Robin"
        await interaction.response.send_message("Tournament type set to Round Robin", ephemeral=True)
        
    @discord.ui.button(label="Single Elimination", style=discord.ButtonStyle.primary)
    async def single_elim_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.tournament_type = "Single Elimination"
        await interaction.response.send_message("Tournament type set to Single Elimination", ephemeral=True)
    
    @discord.ui.button(label="Set Details", style=discord.ButtonStyle.success)
    async def details_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Create a modal for tournament details
        modal = TournamentDetailsModal(self)
        await interaction.response.send_modal(modal)

# Tournament details modal
class TournamentDetailsModal(discord.ui.Modal, title="Tournament Details"):
    name = discord.ui.TextInput(
        label="Tournament Name",
        placeholder="Enter tournament name",
        required=True
    )
    
    rounds = discord.ui.TextInput(
        label="Number of Rounds",
        placeholder="Enter number of rounds",
        required=True,
        default="5"
    )
    
    time_control = discord.ui.TextInput(
        label="Time Control",
        placeholder="e.g., 10+5 (minutes + increment)",
        required=True,
        default="10+5"
    )
    
    description = discord.ui.TextInput(
        label="Description",
        placeholder="Enter tournament description",
        required=False,
        style=discord.TextStyle.paragraph
    )
    
    start_date = discord.ui.TextInput(
        label="Start Date (YYYY-MM-DD)",
        placeholder="e.g., 2023-12-31",
        required=True
    )
    
    def __init__(self, view: TournamentCreationView):
        super().__init__()
        self.view = view
    
    async def on_submit(self, interaction: discord.Interaction):
        # Update the view with the form data
        self.view.tournament_name = self.name.value
        
        try:
            self.view.rounds = int(self.rounds.value)
        except ValueError:
            await interaction.response.send_message("Invalid number of rounds. Please enter a number.", ephemeral=True)
            return
            
        self.view.time_control = self.time_control.value
        self.view.description = self.description.value or "Chess Tournament"
        
        try:
            self.view.start_date = datetime.datetime.strptime(self.start_date.value, "%Y-%m-%d")
            # Set registration deadline to 1 day before start
            self.view.registration_deadline = self.view.start_date - datetime.timedelta(days=1)
        except ValueError:
            await interaction.response.send_message("Invalid date format. Please use YYYY-MM-DD.", ephemeral=True)
            return
        
        # Create the tournament
        tournament_id = generate_id("T")
        
        # Store tournament data
        tournaments["tournaments"][tournament_id] = {
            "id": tournament_id,
            "name": self.view.tournament_name,
            "type": self.view.tournament_type,
            "rounds": self.view.rounds,
            "time_control": self.view.time_control,
            "description": self.view.description,
            "start_date": self.view.start_date.strftime("%Y-%m-%d"),
            "registration_deadline": self.view.registration_deadline.strftime("%Y-%m-%d"),
            "status": "Registration Open",
            "creator_id": str(interaction.user.id),
            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "participants": [],
            "current_round": 0,
            "completed_rounds": 0,
            "matches": []
        }
        
        save_data(TOURNAMENTS_FILE, tournaments)
        
        # Create embed with tournament details
        embed = discord.Embed(
            title=f"Tournament Created: {self.view.tournament_name}",
            description=self.view.description,
            color=discord.Color.green()
        )
        
        embed.add_field(name="Tournament Type", value=self.view.tournament_type, inline=True)
        embed.add_field(name="Rounds", value=str(self.view.rounds), inline=True)
        embed.add_field(name="Time Control", value=self.view.time_control, inline=True)
        embed.add_field(name="Start Date", value=self.view.start_date.strftime("%Y-%m-%d"), inline=True)
        embed.add_field(name="Registration Deadline", value=self.view.registration_deadline.strftime("%Y-%m-%d"), inline=True)
        embed.add_field(name="Tournament ID", value=tournament_id, inline=True)
        
        embed.set_footer(text=f"Created by {interaction.user.name} | Use /chess register {tournament_id} to register")
        
        # Disable all buttons in the view
        for item in self.view.children:
            item.disabled = True
        
        await interaction.response.edit_message(content="Tournament created successfully!", embed=embed, view=self.view)

# Tournament registration view
class TournamentRegistrationView(discord.ui.View):
    def __init__(self, tournament_id, timeout=None):
        super().__init__(timeout=timeout)
        self.tournament_id = tournament_id
        
    @discord.ui.button(label="Register", style=discord.ButtonStyle.success)
    async def register_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if tournament exists
        if self.tournament_id not in tournaments["tournaments"]:
            await interaction.response.send_message("Tournament not found.", ephemeral=True)
            return
            
        tournament = tournaments["tournaments"][self.tournament_id]
        
        # Check if registration is still open
        if tournament["status"] != "Registration Open":
            await interaction.response.send_message("Registration is closed for this tournament.", ephemeral=True)
            return
            
        # Check if user is already registered
        user_id = str(interaction.user.id)
        if user_id in tournament["participants"]:
            await interaction.response.send_message("You are already registered for this tournament.", ephemeral=True)
            return
            
        # Register the user
        tournament["participants"].append(user_id)
        
        # If user is not in players database, add them
        if user_id not in players["players"]:
            players["players"][user_id] = {
                "id": user_id,
                "username": interaction.user.name,
                "rating": 1200,  # Default rating
                "tournaments": [],
                "matches": [],
                "wins": 0,
                "losses": 0,
                "draws": 0
            }
            
        # Add tournament to player's tournament list
        if self.tournament_id not in players["players"][user_id]["tournaments"]:
            players["players"][user_id]["tournaments"].append(self.tournament_id)
            
        # Save data
        save_data(TOURNAMENTS_FILE, tournaments)
        save_data(PLAYERS_FILE, players)
        
        await interaction.response.send_message(f"You have successfully registered for {tournament['name']}!", ephemeral=True)

# Match reporting view
class MatchReportView(discord.ui.View):
    def __init__(self, match_id, timeout=None):
        super().__init__(timeout=timeout)
        self.match_id = match_id
        
    @discord.ui.button(label="Player 1 Won", style=discord.ButtonStyle.primary)
    async def player1_won_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.report_result(interaction, "player1")
        
    @discord.ui.button(label="Draw", style=discord.ButtonStyle.secondary)
    async def draw_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.report_result(interaction, "draw")
        
    @discord.ui.button(label="Player 2 Won", style=discord.ButtonStyle.primary)
    async def player2_won_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.report_result(interaction, "player2")
    
    async def report_result(self, interaction: discord.Interaction, result):
        # Check if match exists
        if self.match_id not in matches["matches"]:
            await interaction.response.send_message("Match not found.", ephemeral=True)
            return
            
        match = matches["matches"][self.match_id]
        
        # Check if user is one of the players or a tournament director/arbiter
        user_id = str(interaction.user.id)
        is_player = user_id == match["player1_id"] or user_id == match["player2_id"]
        
        # Check for admin roles (Tournament Director or Arbiter)
        is_admin = False
        for role in interaction.user.roles:
            if role.name in ["Tournament Director", "Arbiter", "Moderator"]:
                is_admin = True
                break
                
        if not (is_player or is_admin):
            await interaction.response.send_message("You don't have permission to report this match result.", ephemeral=True)
            return
            
        # Check if match is already completed
        if match["status"] == "Completed":
            await interaction.response.send_message("This match has already been completed.", ephemeral=True)
            return
            
        # Update match result
        match["result"] = result
        match["status"] = "Completed"
        match["reported_by"] = user_id
        match["completed_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Update player stats
        player1_id = match["player1_id"]
        player2_id = match["player2_id"]
        
        if player1_id in players["players"] and player2_id in players["players"]:
            # Add match to players' match lists
            if self.match_id not in players["players"][player1_id]["matches"]:
                players["players"][player1_id]["matches"].append(self.match_id)
            if self.match_id not in players["players"][player2_id]["matches"]:
                players["players"][player2_id]["matches"].append(self.match_id)
                
            # Update win/loss/draw counts
            if result == "player1":
                players["players"][player1_id]["wins"] += 1
                players["players"][player2_id]["losses"] += 1
            elif result == "player2":
                players["players"][player1_id]["losses"] += 1
                players["players"][player2_id]["wins"] += 1
            else:  # draw
                players["players"][player1_id]["draws"] += 1
                players["players"][player2_id]["draws"] += 1
                
            # Update ratings using a simple Elo system
            await self.update_ratings(player1_id, player2_id, result)
        
        # Update tournament if this is a tournament match
        if "tournament_id" in match and match["tournament_id"] in tournaments["tournaments"]:
            tournament = tournaments["tournaments"][match["tournament_id"]]
            
            # Mark match as completed in tournament
            for i, match_id in enumerate(tournament["matches"]):
                if match_id == self.match_id:
                    # This match is completed
                    break
                    
            # Check if all matches in the current round are completed
            current_round = tournament["current_round"]
            all_completed = True
            
            for match_id in tournament["matches"]:
                if matches["matches"][match_id]["round"] == current_round and matches["matches"][match_id]["status"] != "Completed":
                    all_completed = False
                    break
                    
            if all_completed and current_round < tournament["rounds"]:
                # All matches in current round completed, advance to next round
                tournament["completed_rounds"] = current_round
                tournament["current_round"] = current_round + 1
                
                # Generate pairings for next round if not the final round
                if current_round + 1 <= tournament["rounds"]:
                    await self.generate_next_round_pairings(interaction, tournament)
                else:
                    # Tournament is complete
                    tournament["status"] = "Completed"
                    await interaction.response.send_message(f"Tournament {tournament['name']} has been completed!", ephemeral=True)
        
        # Save all data
        save_data(MATCHES_FILE, matches)
        save_data(PLAYERS_FILE, players)
        save_data(TOURNAMENTS_FILE, tournaments)
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
            
        # Create result embed
        embed = discord.Embed(
            title=f"Match Result: {self.match_id}",
            color=discord.Color.green()
        )
        
        player1_name = players["players"][player1_id]["username"] if player1_id in players["players"] else "Player 1"
        player2_name = players["players"][player2_id]["username"] if player2_id in players["players"] else "Player 2"
        
        if result == "player1":
            result_text = f"**{player1_name}** defeated {player2_name}"
        elif result == "player2":
            result_text = f"{player1_name} was defeated by **{player2_name}**"
        else:
            result_text = f"{player1_name} drew with {player2_name}"
            
        embed.add_field(name="Result", value=result_text, inline=False)
        embed.add_field(name="Reported by", value=interaction.user.mention, inline=True)
        embed.add_field(name="Time", value=match["completed_at"], inline=True)
        
        if "tournament_id" in match:
            tournament_name = tournaments["tournaments"][match["tournament_id"]]["name"]
            embed.add_field(name="Tournament", value=tournament_name, inline=True)
            embed.add_field(name="Round", value=str(match["round"]), inline=True)
            
        await interaction.response.edit_message(content="Match result recorded!", embed=embed, view=self)
    
    async def update_ratings(self, player1_id, player2_id, result):
        """Update player ratings using Elo system"""
        # Get current ratings
        player1_rating = players["players"][player1_id]["rating"]
        player2_rating = players["players"][player2_id]["rating"]
        
        # Calculate expected scores
        expected_score1 = 1 / (1 + 10 ** ((player2_rating - player1_rating) / 400))
        expected_score2 = 1 / (1 + 10 ** ((player1_rating - player2_rating) / 400))
        
        # Calculate actual scores
        if result == "player1":
            actual_score1 = 1
            actual_score2 = 0
        elif result == "player2":
            actual_score1 = 0
            actual_score2 = 1
        else:  # draw
            actual_score1 = 0.5
            actual_score2 = 0.5
            
        # K-factor (determines how much ratings change)
        k_factor = 32
        
        # Calculate new ratings
        new_rating1 = player1_rating + k_factor * (actual_score1 - expected_score1)
        new_rating2 = player2_rating + k_factor * (actual_score2 - expected_score2)
        
        # Update player ratings
        players["players"][player1_id]["rating"] = round(new_rating1)
        players["players"][player2_id]["rating"] = round(new_rating2)
        
        # Update player tiers based on new ratings
        players["players"][player1_id]["tier"] = get_rating_tier(round(new_rating1))
        players["players"][player2_id]["tier"] = get_rating_tier(round(new_rating2))
    
    async def generate_next_round_pairings(self, interaction, tournament):
        """Generate pairings for the next round of the tournament"""
        tournament_id = tournament["id"]
        current_round = tournament["current_round"] + 1  # Next round
        participants = tournament["participants"]
        
        # Get player standings
        standings = []
        for player_id in participants:
            if player_id in players["players"]:
                player = players["players"][player_id]
                
                # Calculate points from tournament matches
                points = 0
                for match_id in tournament["matches"]:
                    match = matches["matches"][match_id]
                    if match["status"] == "Completed":
                        if match["player1_id"] == player_id:
                            if match["result"] == "player1":
                                points += 1
                            elif match["result"] == "draw":
                                points += 0.5
                        elif match["player2_id"] == player_id:
                            if match["result"] == "player2":
                                points += 1
                            elif match["result"] == "draw":
                                points += 0.5
                
                standings.append({
                    "player_id": player_id,
                    "username": player["username"],
                    "rating": player["rating"],
                    "points": points
                })
        
        # Sort standings by points (descending) and then by rating (descending)
        standings.sort(key=lambda x: (x["points"], x["rating"]), reverse=True)
        
        # Generate pairings based on tournament type
        new_matches = []
        
        if tournament["type"] == "Swiss":
            # Swiss system pairing
            # Players with same points play each other, avoiding rematches
            paired_players = set()
            
            for i in range(len(standings)):
                player1 = standings[i]
                if player1["player_id"] in paired_players:
                    continue
                    
                # Find opponent with closest points who hasn't played this player yet
                for j in range(i + 1, len(standings)):
                    player2 = standings[j]
                    if player2["player_id"] in paired_players:
                        continue
                        
                    # Check if these players have already played each other
                    already_played = False
                    for match_id in tournament["matches"]:
                        match = matches["matches"][match_id]
                        if ((match["player1_id"] == player1["player_id"] and match["player2_id"] == player2["player_id"]) or
                            (match["player1_id"] == player2["player_id"] and match["player2_id"] == player1["player_id"])):
                            already_played = True
                            break
                            
                    if not already_played:
                        # Create a new match
                        match_id = generate_id("M")
                        
                        matches["matches"][match_id] = {
                            "id": match_id,
                            "tournament_id": tournament_id,
                            "round": current_round,
                            "player1_id": player1["player_id"],
                            "player2_id": player2["player_id"],
                            "player1_name": player1["username"],
                            "player2_name": player2["username"],
                            "status": "Scheduled",
                            "result": None,
                            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "scheduled_for": None,
                            "completed_at": None,
                            "reported_by": None
                        }
                        
                        new_matches.append(match_id)
                        paired_players.add(player1["player_id"])
                        paired_players.add(player2["player_id"])
                        break
                        
                # If no opponent found, give a bye (counts as a win)
                if player1["player_id"] not in paired_players:
                    match_id = generate_id("M")
                    
                    matches["matches"][match_id] = {
                        "id": match_id,
                        "tournament_id": tournament_id,
                        "round": current_round,
                        "player1_id": player1["player_id"],
                        "player2_id": "BYE",
                        "player1_name": player1["username"],
                        "player2_name": "BYE",
                        "status": "Completed",  # Auto-complete bye matches
                        "result": "player1",    # Player gets a win
                        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "scheduled_for": None,
                        "completed_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "reported_by": "SYSTEM"
                    }
                    
                    new_matches.append(match_id)
                    paired_players.add(player1["player_id"])
                    
                    # Update player stats for the bye
                    if player1["player_id"] in players["players"]:
                        players["players"][player1["player_id"]]["wins"] += 1
                        if match_id not in players["players"][player1["player_id"]]["matches"]:
                            players["players"][player1["player_id"]]["matches"].append(match_id)
        
        elif tournament["type"] == "Round Robin":
            # For Round Robin, each player plays every other player once
            # In each round, pair players who haven't played yet
            paired_players = set()
            
            for i in range(len(participants)):
                player1_id = participants[i]
                if player1_id in paired_players:
                    continue
                    
                for j in range(i + 1, len(participants)):
                    player2_id = participants[j]
                    if player2_id in paired_players:
                        continue
                        
                    # Check if these players should play in this round
                    # Using a formula to determine round pairings
                    should_play_this_round = ((i + j) % (len(participants) - 1) + 1) == current_round
                    
                    if should_play_this_round:
                        # Create a new match
                        match_id = generate_id("M")
                        
                        player1_name = players["players"][player1_id]["username"] if player1_id in players["players"] else "Player 1"
                        player2_name = players["players"][player2_id]["username"] if player2_id in players["players"] else "Player 2"
                        
                        matches["matches"][match_id] = {
                            "id": match_id,
                            "tournament_id": tournament_id,
                            "round": current_round,
                            "player1_id": player1_id,
                            "player2_id": player2_id,
                            "player1_name": player1_name,
                            "player2_name": player2_name,
                            "status": "Scheduled",
                            "result": None,
                            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "scheduled_for": None,
                            "completed_at": None,
                            "reported_by": None
                        }
                        
                        new_matches.append(match_id)
                        paired_players.add(player1_id)
                        paired_players.add(player2_id)
                        break
        
        elif tournament["type"] == "Single Elimination":
            # For Single Elimination, winners advance to next round
            # First round is seeded by rating
            if current_round == 1:
                # Sort participants by rating for seeding
                seeded_players = []
                for player_id in participants:
                    if player_id in players["players"]:
                        seeded_players.append({
                            "player_id": player_id,
                            "rating": players["players"][player_id]["rating"],
                            "username": players["players"][player_id]["username"]
                        })
                
                seeded_players.sort(key=lambda x: x["rating"], reverse=True)
                
                # Create first round matches with proper seeding
                # 1 vs 8, 4 vs 5, 2 vs 7, 3 vs 6, etc.
                num_players = len(seeded_players)
                num_matches = num_players // 2
                
                for i in range(num_matches):
                    player1 = seeded_players[i]
                    player2 = seeded_players[num_players - 1 - i]
                    
                    match_id = generate_id("M")
                    
                    matches["matches"][match_id] = {
                        "id": match_id,
                        "tournament_id": tournament_id,
                        "round": current_round,
                        "player1_id": player1["player_id"],
                        "player2_id": player2["player_id"],
                        "player1_name": player1["username"],
                        "player2_name": player2["username"],
                        "status": "Scheduled",
                        "result": None,
                        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "scheduled_for": None,
                        "completed_at": None,
                        "reported_by": None
                    }
                    
                    new_matches.append(match_id)
                
                # If odd number of players, give top seed a bye
                if num_players % 2 == 1:
                    player1 = seeded_players[0]
                    
                    match_id = generate_id("M")
                    
                    matches["matches"][match_id] = {
                        "id": match_id,
                        "tournament_id": tournament_id,
                        "round": current_round,
                        "player1_id": player1["player_id"],
                        "player2_id": "BYE",
                        "player1_name": player1["username"],
                        "player2_name": "BYE",
                        "status": "Completed",
                        "result": "player1",
                        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "scheduled_for": None,
                        "completed_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "reported_by": "SYSTEM"
                    }
                    
                    new_matches.append(match_id)
                    
                    # Update player stats for the bye
                    if player1["player_id"] in players["players"]:
                        players["players"][player1["player_id"]]["wins"] += 1
                        if match_id not in players["players"][player1["player_id"]]["matches"]:
                            players["players"][player1["player_id"]]["matches"].append(match_id)
            else:
                # For subsequent rounds, pair winners from previous round
                previous_round = current_round - 1
                winners = []
                
                for match_id in tournament["matches"]:
                    match = matches["matches"][match_id]
                    if match["round"] == previous_round and match["status"] == "Completed":
                        if match["result"] == "player1":
                            winners.append({
                                "player_id": match["player1_id"],
                                "username": match["player1_name"],
                                "match_id": match_id
                            })
                        elif match["result"] == "player2":
                            winners.append({
                                "player_id": match["player2_id"],
                                "username": match["player2_name"],
                                "match_id": match_id
                            })
                
                # Pair winners for next round
                for i in range(0, len(winners), 2):
                    if i + 1 < len(winners):
                        player1 = winners[i]
                        player2 = winners[i + 1]
                        
                        match_id = generate_id("M")
                        
                        matches["matches"][match_id] = {
                            "id": match_id,
                            "tournament_id": tournament_id,
                            "round": current_round,
                            "player1_id": player1["player_id"],
                            "player2_id": player2["player_id"],
                            "player1_name": player1["username"],
                            "player2_name": player2["username"],
                            "status": "Scheduled",
                            "result": None,
                            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "scheduled_for": None,
                            "completed_at": None,
                            "reported_by": None,
                            "previous_matches": [player1["match_id"], player2["match_id"]]
                        }
                        
                        new_matches.append(match_id)
                    else:
                        # Odd number of winners, give a bye
                        player1 = winners[i]
                        
                        match_id = generate_id("M")
                        
                        matches["matches"][match_id] = {
                            "id": match_id,
                            "tournament_id": tournament_id,
                            "round": current_round,
                            "player1_id": player1["player_id"],
                            "player2_id": "BYE",
                            "player1_name": player1["username"],
                            "player2_name": "BYE",
                            "status": "Completed",
                            "result": "player1",
                            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "scheduled_for": None,
                            "completed_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "reported_by": "SYSTEM",
                            "previous_matches": [player1["match_id"]]
                        }
                        
                        new_matches.append(match_id)
                        
                        # Update player stats for the bye
                        if player1["player_id"] in players["players"]:
                            players["players"][player1["player_id"]]["wins"] += 1
                            if match_id not in players["players"][player1["player_id"]]["matches"]:
                                players["players"][player1["player_id"]]["matches"].append(match_id)
        
        # Add new matches to tournament
        tournament["matches"].extend(new_matches)
        
        # Save data
        save_data(MATCHES_FILE, matches)
        save_data(TOURNAMENTS_FILE, tournaments)
        
        # Announce new pairings
        pairings_message = f"**Round {current_round} Pairings for {tournament['name']}**\n\n"
        
        for match_id in new_matches:
            match = matches["matches"][match_id]
            if match["player2_id"] == "BYE":
                pairings_message += f"• {match['player1_name']} receives a bye\n"
            else:
                pairings_message += f"• {match['player1_name']} vs {match['player2_name']}\n"
        
        # Try to find the appropriate channel to send pairings
        pairings_channel = None
        for channel in interaction.guild.text_channels:
            if "pairings" in channel.name.lower():
                pairings_channel = channel
                break
        
        if pairings_channel:
            await pairings_channel.send(pairings_message)
        else:
            # If no pairings channel found, send to the current channel
            await interaction.channel.send(pairings_message)

# Chess commands implementation
async def create_tournament_command(interaction: discord.Interaction):
    """Create a new chess tournament"""
    # Check if user has permission (Tournament Director or Moderator)
    has_permission = False
    for role in interaction.user.roles:
        if role.name in ["Tournament Director", "Moderator"]:
            has_permission = True
            break
    
    if not has_permission:
        await interaction.response.send_message("You don't have permission to create tournaments. You need the Tournament Director or Moderator role.", ephemeral=True)
        return
    
    # Create tournament creation view
    view = TournamentCreationView(interaction)
    
    embed = discord.Embed(
        title="Create a Chess Tournament",
        description="Select a tournament type and then click 'Set Details' to configure the tournament.",
        color=discord.Color.blue()
    )
    
    embed.add_field(name="Swiss System", value="Players play a fixed number of rounds, paired against others with similar scores.", inline=False)
    embed.add_field(name="Round Robin", value="Each player plays against every other player once.", inline=False)
    embed.add_field(name="Single Elimination", value="Players are eliminated after one loss, with winners advancing to the next round.", inline=False)
    
    await interaction.response.send_message(embed=embed, view=view)

async def list_tournaments_command(interaction: discord.Interaction, status: Optional[str] = None):
    """List all tournaments or filter by status"""
    await interaction.response.defer()
    
    if not tournaments["tournaments"]:
        await interaction.followup.send("No tournaments found.")
        return
    
    # Filter tournaments by status if provided
    filtered_tournaments = []
    for tournament_id, tournament in tournaments["tournaments"].items():
        if status is None or tournament["status"].lower() == status.lower():
            filtered_tournaments.append(tournament)
    
    if not filtered_tournaments:
        await interaction.followup.send(f"No tournaments found with status: {status}")
        return
    
    # Sort tournaments by start date (most recent first)
    filtered_tournaments.sort(key=lambda t: t["start_date"], reverse=True)
    
    # Create embed
    embed = discord.Embed(
        title="Chess Tournaments",
        description=f"Found {len(filtered_tournaments)} tournament(s)" + (f" with status: {status}" if status else ""),
        color=discord.Color.blue()
    )
    
    # Add each tournament to the embed
    for tournament in filtered_tournaments[:10]:  # Limit to 10 tournaments
        tournament_name = tournament["name"]
        tournament_id = tournament["id"]
        tournament_type = tournament["type"]
        tournament_status = tournament["status"]
        start_date = tournament["start_date"]
        participant_count = len(tournament["participants"])
        
        value = (
            f"**Type:** {tournament_type}\n"
            f"**Status:** {tournament_status}\n"
            f"**Start Date:** {start_date}\n"
            f"**Participants:** {participant_count}\n"
            f"**ID:** {tournament_id}"
        )
        
        embed.add_field(name=tournament_name, value=value, inline=False)
    
    if len(filtered_tournaments) > 10:
        embed.set_footer(text=f"Showing 10 of {len(filtered_tournaments)} tournaments. Use /chess tournament info [id] for details.")
    
    await interaction.followup.send(embed=embed)

async def tournament_info_command(interaction: discord.Interaction, tournament_id: str):
    """Show detailed information about a tournament"""
    await interaction.response.defer()
    
    if tournament_id not in tournaments["tournaments"]:
        await interaction.followup.send(f"Tournament with ID {tournament_id} not found.")
        return
    
    tournament = tournaments["tournaments"][tournament_id]
    
    # Create embed
    embed = discord.Embed(
        title=f"Tournament: {tournament['name']}",
        description=tournament["description"],
        color=discord.Color.blue()
    )
    
    # Basic info
    embed.add_field(name="Type", value=tournament["type"], inline=True)
    embed.add_field(name="Status", value=tournament["status"], inline=True)
    embed.add_field(name="Rounds", value=f"{tournament['completed_rounds']}/{tournament['rounds']}", inline=True)
    embed.add_field(name="Start Date", value=tournament["start_date"], inline=True)
    embed.add_field(name="Registration Deadline", value=tournament["registration_deadline"], inline=True)
    embed.add_field(name="Time Control", value=tournament["time_control"], inline=True)
    
    # Participants
    participant_count = len(tournament["participants"])
    embed.add_field(name=f"Participants ({participant_count})", value=f"Use `/chess tournament players {tournament_id}` to view", inline=False)
    
    # Current standings if tournament has started
    if tournament["current_round"] > 0:
        embed.add_field(name="Current Round", value=str(tournament["current_round"]), inline=True)
        embed.add_field(name="Standings", value=f"Use `/chess tournament standings {tournament_id}` to view", inline=False)
    
    # Registration button if tournament is open for registration
    view = None
    if tournament["status"] == "Registration Open":
        view = TournamentRegistrationView(tournament_id)
        embed.add_field(name="Registration", value="Click the Register button below to join this tournament", inline=False)
    
    await interaction.followup.send(embed=embed, view=view)

async def tournament_players_command(interaction: discord.Interaction, tournament_id: str):
    """Show players registered for a tournament"""
    await interaction.response.defer()
    
    if tournament_id not in tournaments["tournaments"]:
        await interaction.followup.send(f"Tournament with ID {tournament_id} not found.")
        return
    
    tournament = tournaments["tournaments"][tournament_id]
    participant_ids = tournament["participants"]
    
    if not participant_ids:
        await interaction.followup.send(f"No players registered for tournament: {tournament['name']}")
        return
    
    # Get player details
    participants = []
    for player_id in participant_ids:
        if player_id in players["players"]:
            player = players["players"][player_id]
            participants.append({
                "id": player_id,
                "username": player["username"],
                "rating": player["rating"],
                "tier": player.get("tier", get_rating_tier(player["rating"]))
            })
        else:
            # Player ID exists in tournament but not in players database
            participants.append({
                "id": player_id,
                "username": f"Unknown Player ({player_id})",
                "rating": 1200,
                "tier": "Beginner"
            })
    
    # Sort by rating
    participants.sort(key=lambda p: p["rating"], reverse=True)
    
    # Create embed
    embed = discord.Embed(
        title=f"Players in {tournament['name']}",
        description=f"Total Participants: {len(participants)}",
        color=discord.Color.blue()
    )
    
    # Add players to embed
    player_list = ""
    for i, player in enumerate(participants, 1):
        player_list += f"{i}. **{player['username']}** - {player['rating']} ({player['tier']})\n"
        
        # Split into multiple fields if too many players
        if i % 15 == 0 or i == len(participants):
            embed.add_field(name=f"Players {i-14 if i > 15 else 1}-{i}", value=player_list, inline=False)
            player_list = ""
    
    await interaction.followup.send(embed=embed)

async def tournament_standings_command(interaction: discord.Interaction, tournament_id: str):
    """Show current standings for a tournament"""
    await interaction.response.defer()
    
    if tournament_id not in tournaments["tournaments"]:
        await interaction.followup.send(f"Tournament with ID {tournament_id} not found.")
        return
    
    tournament = tournaments["tournaments"][tournament_id]
    
    if tournament["current_round"] == 0:
        await interaction.followup.send(f"Tournament {tournament['name']} has not started yet.")
        return
    
    # Calculate standings
    standings = []
    for player_id in tournament["participants"]:
        if player_id in players["players"]:
            player = players["players"][player_id]
            
            # Calculate tournament stats
            wins = 0
            losses = 0
            draws = 0
            
            for match_id in tournament["matches"]:
                match = matches["matches"][match_id]
                if match["status"] == "Completed":
                    if match["player1_id"] == player_id:
                        if match["result"] == "player1":
                            wins += 1
                        elif match["result"] == "player2":
                            losses += 1
                        elif match["result"] == "draw":
                            draws += 1
                    elif match["player2_id"] == player_id:
                        if match["result"] == "player2":
                            wins += 1
                        elif match["result"] == "player1":
                            losses += 1
                        elif match["result"] == "draw":
                            draws += 1
            
            # Calculate points (1 for win, 0.5 for draw)
            points = wins + (draws * 0.5)
            
            standings.append({
                "player_id": player_id,
                "username": player["username"],
                "rating": player["rating"],
                "points": points,
                "wins": wins,
                "losses": losses,
                "draws": draws,
                "matches_played": wins + losses + draws
            })
    
    # Sort by points (descending) and then by rating (descending)
    standings.sort(key=lambda x: (x["points"], x["rating"]), reverse=True)
    
    # Create embed
    embed = discord.Embed(
        title=f"Standings: {tournament['name']}",
        description=f"Current Round: {tournament['current_round']}/{tournament['rounds']}",
        color=discord.Color.gold()
    )
    
    # Add standings to embed
    standings_text = ""
    for i, player in enumerate(standings, 1):
        standings_text += f"{i}. **{player['username']}** - {player['points']} pts ({player['wins']}-{player['losses']}-{player['draws']})\n"
        
        # Split into multiple fields if too many players
        if i % 15 == 0 or i == len(standings):
            embed.add_field(name=f"Standings", value=standings_text, inline=False)
            standings_text = ""
    
    await interaction.followup.send(embed=embed)

async def tournament_matches_command(interaction: discord.Interaction, tournament_id: str, round_num: Optional[int] = None):
    """Show matches for a tournament, optionally filtered by round"""
    await interaction.response.defer()
    
    if tournament_id not in tournaments["tournaments"]:
        await interaction.followup.send(f"Tournament with ID {tournament_id} not found.")
        return
    
    tournament = tournaments["tournaments"][tournament_id]
    
    if not tournament["matches"]:
        await interaction.followup.send(f"No matches found for tournament: {tournament['name']}")
        return
    
    # Filter matches by round if specified
    filtered_matches = []
    for match_id in tournament["matches"]:
        if match_id in matches["matches"]:
            match = matches["matches"][match_id]
            if round_num is None or match["round"] == round_num:
                filtered_matches.append(match)
    
    if not filtered_matches:
        round_text = f" for round {round_num}" if round_num else ""
        await interaction.followup.send(f"No matches found{round_text} in tournament: {tournament['name']}")
        return
    
    # Sort matches by round and then by status (completed last)
    filtered_matches.sort(key=lambda m: (m["round"], 0 if m["status"] == "Scheduled" else 1))
    
    # Create embed
    embed = discord.Embed(
        title=f"Matches: {tournament['name']}",
        description=f"{'Round ' + str(round_num) if round_num else 'All Rounds'} • {len(filtered_matches)} matches",
        color=discord.Color.blue()
    )
    
    # Group matches by round
    matches_by_round = {}
    for match in filtered_matches:
        round_num = match["round"]
        if round_num not in matches_by_round:
            matches_by_round[round_num] = []
        matches_by_round[round_num].append(match)
    
    # Add matches to embed, grouped by round
    for round_num in sorted(matches_by_round.keys()):
        round_matches = matches_by_round[round_num]
        
        matches_text = ""
        for match in round_matches:
            status_emoji = "🏁" if match["status"] == "Completed" else "⏳"
            
            if match["player2_id"] == "BYE":
                matches_text += f"{status_emoji} **{match['player1_name']}** receives a bye\n"
            else:
                if match["status"] == "Completed":
                    if match["result"] == "player1":
                        matches_text += f"{status_emoji} **{match['player1_name']}** defeated {match['player2_name']}\n"
                    elif match["result"] == "player2":
                        matches_text += f"{status_emoji} {match['player1_name']} defeated by **{match['player2_name']}**\n"
                    else:  # draw
                        matches_text += f"{status_emoji} {match['player1_name']} drew with {match['player2_name']}\n"
                else:
                    matches_text += f"{status_emoji} {match['player1_name']} vs {match['player2_name']} (ID: {match['id']})\n"
        
        embed.add_field(name=f"Round {round_num}", value=matches_text, inline=False)
    
    await interaction.followup.send(embed=embed)

async def register_player_command(interaction: discord.Interaction, tournament_id: str):
    """Register a player for a tournament"""
    if tournament_id not in tournaments["tournaments"]:
        await interaction.response.send_message(f"Tournament with ID {tournament_id} not found.", ephemeral=True)
        return
    
    tournament = tournaments["tournaments"][tournament_id]
    
    # Check if registration is still open
    if tournament["status"] != "Registration Open":
        await interaction.response.send_message("Registration is closed for this tournament.", ephemeral=True)
        return
    
    # Check if user is already registered
    user_id = str(interaction.user.id)
    if user_id in tournament["participants"]:
        await interaction.response.send_message("You are already registered for this tournament.", ephemeral=True)
        return
    
    # Register the user
    tournament["participants"].append(user_id)
    
    # If user is not in players database, add them
    if user_id not in players["players"]:
        players["players"][user_id] = {
            "id": user_id,
            "username": interaction.user.name,
            "rating": 1200,  # Default rating
            "tier": "Beginner",
            "tournaments": [],
            "matches": [],
            "wins": 0,
            "losses": 0,
            "draws": 0
        }
    
    # Add tournament to player's tournament list
    if tournament_id not in players["players"][user_id]["tournaments"]:
        players["players"][user_id]["tournaments"].append(tournament_id)
    
    # Save data
    save_data(TOURNAMENTS_FILE, tournaments)
    save_data(PLAYERS_FILE, players)
    
    await interaction.response.send_message(f"You have successfully registered for {tournament['name']}!", ephemeral=True)

async def unregister_player_command(interaction: discord.Interaction, tournament_id: str):
    """Unregister a player from a tournament"""
    if tournament_id not in tournaments["tournaments"]:
        await interaction.response.send_message(f"Tournament with ID {tournament_id} not found.", ephemeral=True)
        return
    
    tournament = tournaments["tournaments"][tournament_id]
    
    # Check if registration is still open
    if tournament["status"] != "Registration Open":
        await interaction.response.send_message("Registration is closed for this tournament.", ephemeral=True)
        return
    
    # Check if user is registered
    user_id = str(interaction.user.id)
    if user_id not in tournament["participants"]:
        await interaction.response.send_message("You are not registered for this tournament.", ephemeral=True)
        return
    
    # Unregister the user
    tournament["participants"].remove(user_id)
    
    # Remove tournament from player's tournament list
    if user_id in players["players"] and tournament_id in players["players"][user_id]["tournaments"]:
        players["players"][user_id]["tournaments"].remove(tournament_id)
    
    # Save data
    save_data(TOURNAMENTS_FILE, tournaments)
    save_data(PLAYERS_FILE, players)
    
    await interaction.response.send_message(f"You have been unregistered from {tournament['name']}.", ephemeral=True)

async def start_tournament_command(interaction: discord.Interaction, tournament_id: str):
    """Start a tournament (admin only)"""
    # Check if user has permission (Tournament Director or Moderator)
    has_permission = False
    for role in interaction.user.roles:
        if role.name in ["Tournament Director", "Moderator"]:
            has_permission = True
            break
    
    if not has_permission:
        await interaction.response.send_message("You don't have permission to start tournaments. You need the Tournament Director or Moderator role.", ephemeral=True)
        return
    
    if tournament_id not in tournaments["tournaments"]:
        await interaction.response.send_message(f"Tournament with ID {tournament_id} not found.", ephemeral=True)
        return
    
    tournament = tournaments["tournaments"][tournament_id]
    
    # Check if tournament can be started
    if tournament["status"] != "Registration Open":
        await interaction.response.send_message(f"Tournament {tournament['name']} cannot be started. Current status: {tournament['status']}", ephemeral=True)
        return
    
    # Check if there are enough participants
    if len(tournament["participants"]) < 2:
        await interaction.response.send_message(f"Tournament {tournament['name']} needs at least 2 participants to start.", ephemeral=True)
        return
    
    # Update tournament status
    tournament["status"] = "In Progress"
    tournament["current_round"] = 1
    tournament["started_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Create a match report view for the first round
    view = MatchReportView(tournament_id)
    
    # Generate first round pairings
    await view.generate_next_round_pairings(interaction, tournament)
    
    # Save data
    save_data(TOURNAMENTS_FILE, tournaments)
    
    await interaction.response.send_message(f"Tournament {tournament['name']} has been started! First round pairings have been generated.", ephemeral=True)

async def report_match_command(interaction: discord.Interaction, match_id: str):
    """Report the result of a match"""
    if match_id not in matches["matches"]:
        await interaction.response.send_message(f"Match with ID {match_id} not found.", ephemeral=True)
        return
    
    match = matches["matches"][match_id]
    
    # Check if match is already completed
    if match["status"] == "Completed":
        await interaction.response.send_message("This match has already been completed.", ephemeral=True)
        return
    
    # Check if user is one of the players or a tournament director/arbiter
    user_id = str(interaction.user.id)
    is_player = user_id == match["player1_id"] or user_id == match["player2_id"]
    
    # Check for admin roles (Tournament Director or Arbiter)
    is_admin = False
    for role in interaction.user.roles:
        if role.name in ["Tournament Director", "Arbiter", "Moderator"]:
            is_admin = True
            break
    
    if not (is_player or is_admin):
        await interaction.response.send_message("You don't have permission to report this match result.", ephemeral=True)
        return
    
    # Create match report view
    view = MatchReportView(match_id)
    
    # Create embed with match details
    embed = discord.Embed(
        title=f"Report Match Result: {match_id}",
        description="Select the result of the match below.",
        color=discord.Color.blue()
    )
    
    player1_name = match["player1_name"]
    player2_name = match["player2_name"]
    
    embed.add_field(name="Players", value=f"{player1_name} vs {player2_name}", inline=False)
    
    if "tournament_id" in match and match["tournament_id"] in tournaments["tournaments"]:
        tournament_name = tournaments["tournaments"][match["tournament_id"]]["name"]
        embed.add_field(name="Tournament", value=tournament_name, inline=True)
        embed.add_field(name="Round", value=str(match["round"]), inline=True)
    
    await interaction.response.send_message(embed=embed, view=view)

async def player_profile_command(interaction: discord.Interaction, user: Optional[discord.Member] = None):
    """Show a player's chess profile"""
    # If no user specified, use the command author
    if user is None:
        user = interaction.user
    
    user_id = str(user.id)
    
    # Check if player exists in database
    if user_id not in players["players"]:
        # Create a new player profile
        players["players"][user_id] = {
            "id": user_id,
            "username": user.name,
            "rating": 1200,  # Default rating
            "tier": "Beginner",
            "tournaments": [],
            "matches": [],
            "wins": 0,
            "losses": 0,
            "draws": 0
        }
        save_data(PLAYERS_FILE, players)
    
    player = players["players"][user_id]
    
    # Create embed
    embed = discord.Embed(
        title=f"Chess Profile: {player['username']}",
        color=discord.Color.blue()
    )
    
    # Set user avatar as thumbnail
    embed.set_thumbnail(url=user.display_avatar.url)
    
    # Basic stats
    embed.add_field(name="Rating", value=str(player["rating"]), inline=True)
    embed.add_field(name="Tier", value=player.get("tier", get_rating_tier(player["rating"])), inline=True)
    
    # Record
    wins = player["wins"]
    losses = player["losses"]
    draws = player["draws"]
    total_games = wins + losses + draws
    win_rate = (wins / total_games * 100) if total_games > 0 else 0
    
    embed.add_field(name="Record", value=f"{wins}-{losses}-{draws} ({win_rate:.1f}% win rate)", inline=True)
    
    # Tournament participation
    tournament_count = len(player["tournaments"])
    embed.add_field(name="Tournaments", value=str(tournament_count), inline=True)
    
    # Recent matches
    recent_matches = []
    for match_id in player["matches"][-5:]:  # Get last 5 matches
        if match_id in matches["matches"]:
            match = matches["matches"][match_id]
            
            # Determine result from player's perspective
            result = ""
            if match["player1_id"] == user_id:
                if match["result"] == "player1":
                    result = "Win"
                elif match["result"] == "player2":
                    result = "Loss"
                else:
                    result = "Draw"
                opponent = match["player2_name"]
            else:
                if match["result"] == "player2":
                    result = "Win"
                elif match["result"] == "player1":
                    result = "Loss"
                else:
                    result = "Draw"
                opponent = match["player1_name"]
            
            recent_matches.append(f"{result} vs {opponent}")
    
    if recent_matches:
        embed.add_field(name="Recent Matches", value="\n".join(recent_matches), inline=False)
    else:
        embed.add_field(name="Recent Matches", value="No matches played yet", inline=False)
    
    await interaction.response.send_message(embed=embed)

async def leaderboard_command(interaction: discord.Interaction):
    """Show the chess rating leaderboard"""
    await interaction.response.defer()
    
    if not players["players"]:
        await interaction.followup.send("No players found in the database.")
        return
    
    # Get all players with at least one match
    active_players = []
    for player_id, player in players["players"].items():
        if player["matches"]:  # Only include players who have played matches
            active_players.append({
                "id": player_id,
                "username": player["username"],
                "rating": player["rating"],
                "tier": player.get("tier", get_rating_tier(player["rating"])),
                "wins": player["wins"],
                "losses": player["losses"],
                "draws": player["draws"]
            })
    
    if not active_players:
        await interaction.followup.send("No active players found with completed matches.")
        return
    
    # Sort by rating (descending)
    active_players.sort(key=lambda p: p["rating"], reverse=True)
    
    # Create embed
    embed = discord.Embed(
        title="Chess Rating Leaderboard",
        description="Players ranked by rating",
        color=discord.Color.gold()
    )
    
    # Add players to leaderboard
    leaderboard_text = ""
    for i, player in enumerate(active_players[:20], 1):  # Show top 20 players
        total_games = player["wins"] + player["losses"] + player["draws"]
        leaderboard_text += f"{i}. **{player['username']}** - {player['rating']} ({player['tier']}) - {player['wins']}-{player['losses']}-{player['draws']}\n"
        
        # Split into multiple fields if too many players
        if i % 10 == 0 or i == min(len(active_players), 20):
            embed.add_field(name=f"Rank {i-9}-{i}", value=leaderboard_text, inline=False)
            leaderboard_text = ""
    
    await interaction.followup.send(embed=embed)

async def set_rating_command(interaction: discord.Interaction, user: discord.Member, rating: int):
    """Set a player's rating (admin only)"""
    # Check if user has permission (Tournament Director or Moderator)
    has_permission = False
    for role in interaction.user.roles:
        if role.name in ["Tournament Director", "Moderator"]:
            has_permission = True
            break
    
    if not has_permission:
        await interaction.response.send_message("You don't have permission to set ratings. You need the Tournament Director or Moderator role.", ephemeral=True)
        return
    
    # Validate rating
    if rating < 100 or rating > 3000:
        await interaction.response.send_message("Rating must be between 100 and 3000.", ephemeral=True)
        return
    
    user_id = str(user.id)
    
    # Check if player exists in database
    if user_id not in players["players"]:
        # Create a new player profile
        players["players"][user_id] = {
            "id": user_id,
            "username": user.name,
            "rating": rating,
            "tier": get_rating_tier(rating),
            "tournaments": [],
            "matches": [],
            "wins": 0,
            "losses": 0,
            "draws": 0
        }
    else:
        # Update existing player
        players["players"][user_id]["rating"] = rating
        players["players"][user_id]["tier"] = get_rating_tier(rating)
    
    # Save data
    save_data(PLAYERS_FILE, players)
    
    await interaction.response.send_message(f"Rating for {user.mention} has been set to {rating} ({get_rating_tier(rating)}).", ephemeral=True)

async def chess_help_command(interaction: discord.Interaction):
    """Show help for chess commands"""
    embed = discord.Embed(
        title="Chess Tournament Commands",
        description="Here are all the available chess commands:",
        color=discord.Color.blue()
    )
    
    # Tournament management commands
    embed.add_field(
        name="Tournament Management",
        value=(
            "`/chess create` - Create a new tournament\n"
            "`/chess list [status]` - List all tournaments\n"
            "`/chess tournament info [id]` - Show tournament details\n"
            "`/chess tournament players [id]` - Show registered players\n"
            "`/chess tournament standings [id]` - Show tournament standings\n"
            "`/chess tournament matches [id] [round]` - Show tournament matches\n"
            "`/chess start [id]` - Start a tournament (admin only)"
        ),
        inline=False
    )
    
    # Player commands
    embed.add_field(
        name="Player Commands",
        value=(
            "`/chess register [id]` - Register for a tournament\n"
            "`/chess unregister [id]` - Unregister from a tournament\n"
            "`/chess profile [user]` - View player profile\n"
            "`/chess leaderboard` - View rating leaderboard\n"
            "`/chess report [match_id]` - Report match result"
        ),
        inline=False
    )
    
    # Admin commands
    embed.add_field(
        name="Admin Commands",
        value=(
            "`/chess setrating [user] [rating]` - Set a player's rating\n"
            "`/chess delete [id]` - Delete a tournament (admin only)"
        ),
        inline=False
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

async def delete_tournament_command(interaction: discord.Interaction, tournament_id: str):
    """Delete a tournament (admin only)"""
    # Check if user has permission (Tournament Director or Moderator)
    has_permission = False
    for role in interaction.user.roles:
        if role.name in ["Tournament Director", "Moderator"]:
            has_permission = True
            break
    
    if not has_permission:
        await interaction.response.send_message("You don't have permission to delete tournaments. You need the Tournament Director or Moderator role.", ephemeral=True)
        return
    
    if tournament_id not in tournaments["tournaments"]:
        await interaction.response.send_message(f"Tournament with ID {tournament_id} not found.", ephemeral=True)
        return
    
    tournament = tournaments["tournaments"][tournament_id]
    
    # Create confirmation view
    class ConfirmationView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=60)
            self.confirmed = False
        
        @discord.ui.button(label="Confirm Delete", style=discord.ButtonStyle.danger)
        async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.confirmed = True
            
            # Delete tournament
            tournament_name = tournament["name"]
            del tournaments["tournaments"][tournament_id]
            
            # Remove tournament from players' tournament lists
            for player_id in tournament["participants"]:
                if player_id in players["players"] and tournament_id in players["players"][player_id]["tournaments"]:
                    players["players"][player_id]["tournaments"].remove(tournament_id)
            
            # Delete tournament matches
            for match_id in tournament["matches"]:
                if match_id in matches["matches"]:
                    del matches["matches"][match_id]
            
            # Save data
            save_data(TOURNAMENTS_FILE, tournaments)
            save_data(PLAYERS_FILE, players)
            save_data(MATCHES_FILE, matches)
            
            await interaction.response.edit_message(content=f"Tournament '{tournament_name}' has been deleted.", view=None)
        
        @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
        async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.edit_message(content="Tournament deletion cancelled.", view=None)
    
    view = ConfirmationView()
    
    await interaction.response.send_message(f"Are you sure you want to delete tournament '{tournament['name']}'? This cannot be undone.", view=view, ephemeral=True)

# Function to register all chess commands
def setup(bot):
    # Create a command group for chess commands
    chess_group = app_commands.Group(name="chess", description="Chess tournament commands")
    
    # Add commands to the group
    chess_group.add_command(app_commands.Command(
        name="create",
        description="Create a new chess tournament",
        callback=create_tournament_command
    ))
    
    chess_group.add_command(app_commands.Command(
        name="list",
        description="List all chess tournaments",
        callback=list_tournaments_command
    ))
    
    # Tournament subgroup
    tournament_group = app_commands.Group(name="tournament", description="Tournament management commands")
    
    tournament_group.add_command(app_commands.Command(
        name="info",
        description="Show detailed information about a tournament",
        callback=tournament_info_command
    ))
    
    tournament_group.add_command(app_commands.Command(
        name="players",
        description="Show players registered for a tournament",
        callback=tournament_players_command
    ))
    
    tournament_group.add_command(app_commands.Command(
        name="standings",
        description="Show current standings for a tournament",
        callback=tournament_standings_command
    ))
    
    tournament_group.add_command(app_commands.Command(
        name="matches",
        description="Show matches for a tournament",
        callback=tournament_matches_command
    ))
    
    chess_group.add_command(tournament_group)
    
    # Player commands
    chess_group.add_command(app_commands.Command(
        name="register",
        description="Register for a chess tournament",
        callback=register_player_command
    ))
    
    chess_group.add_command(app_commands.Command(
        name="unregister",
        description="Unregister from a chess tournament",
        callback=unregister_player_command
    ))
    
    chess_group.add_command(app_commands.Command(
        name="profile",
        description="View a player's chess profile",
        callback=player_profile_command
    ))
    
    chess_group.add_command(app_commands.Command(
        name="leaderboard",
        description="View the chess rating leaderboard",
        callback=leaderboard_command
    ))
    
    # Admin commands
    chess_group.add_command(app_commands.Command(
        name="start",
        description="Start a chess tournament",
        callback=start_tournament_command
    ))
    
    chess_group.add_command(app_commands.Command(
        name="report",
        description="Report the result of a chess match",
        callback=report_match_command
    ))
    
    chess_group.add_command(app_commands.Command(
        name="setrating",
        description="Set a player's chess rating",
        callback=set_rating_command
    ))
    
    chess_group.add_command(app_commands.Command(
        name="delete",
        description="Delete a chess tournament",
        callback=delete_tournament_command
    ))
    
    chess_group.add_command(app_commands.Command(
        name="help",
        description="Show help for chess commands",
        callback=chess_help_command
    ))
    
    # Add the group to the command tree
    bot.tree.add_command(chess_group)
    
    # Log setup
    print("Chess tournament commands registered as group")



