import asyncio
import discord
from discord import app_commands
from discord.ext import commands
import datetime
import json
import os
import random
import string
from typing import Optional, List, Dict, Any

# File paths for data storage
DATA_DIR = "data"
TOURNAMENTS_FILE = os.path.join(DATA_DIR, "tournaments.json")
PLAYERS_FILE = os.path.join(DATA_DIR, "players.json")
MATCHES_FILE = os.path.join(DATA_DIR, "matches.json")
TICKETS_FILE = os.path.join(DATA_DIR, "match_tickets.json")

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# Initialize data structures
tournaments = {"tournaments": {}}
players = {"players": {}}
matches = {"matches": {}}
tickets = {"tickets": {}}

# Load data from files
def load_data():
    """Load data from JSON files"""
    global tournaments, matches, players, tickets
    
    # Load tournaments
    try:
        with open(TOURNAMENTS_FILE, 'r') as f:
            tournaments = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        tournaments = {"tournaments": {}}
        save_data(TOURNAMENTS_FILE, tournaments)
    
    # Load matches
    try:
        with open(MATCHES_FILE, 'r') as f:
            matches = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        matches = {"matches": {}}
        save_data(MATCHES_FILE, matches)
    
    # Load players
    try:
        with open(PLAYERS_FILE, 'r') as f:
            players = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        players = {"players": {}}
        save_data(PLAYERS_FILE, players)
    
    # Load tickets
    try:
        with open(TICKETS_FILE, 'r') as f:
            tickets = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        tickets = {"tickets": {}}
        save_data(TICKETS_FILE, tickets)

# Save data to files
def save_data(file_path, data):
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)

# Load all data
tournaments = load_data(TOURNAMENTS_FILE, tournaments)
players = load_data(PLAYERS_FILE, players)
matches = load_data(MATCHES_FILE, matches)
tickets = load_data(TICKETS_FILE, tickets)

# Generate a unique ID
def generate_id(prefix):
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"{prefix}{timestamp}{random_str}"

# Get rating tier based on rating
def get_rating_tier(rating):
    if rating >= 2500:
        return "Grandmaster"
    elif rating >= 2200:
        return "Master"
    elif rating >= 2000:
        return "Expert"
    elif rating >= 1800:
        return "Class A"
    elif rating >= 1600:
        return "Class B"
    elif rating >= 1400:
        return "Class C"
    elif rating >= 1200:
        return "Class D"
    else:
        return "Beginner"

# Match ticket system
class MatchTicketSystem:
    @staticmethod
    async def create_match_ticket(guild, match_id):
        """Create a private channel for a match"""
        if not guild or match_id not in matches["matches"]:
            return None
            
        match = matches["matches"][match_id]
        
        # Get player objects
        player1_id = match["player1_id"]
        player2_id = match["player2_id"]
        
        # Skip if it's a bye match
        if player2_id == "BYE":
            return None
            
        # Try to get member objects
        try:
            player1_member = await guild.fetch_member(int(player1_id))
            player2_member = await guild.fetch_member(int(player2_id))
        except (discord.NotFound, discord.HTTPException):
            # One or both players not found in the server
            return None
            
        # Create ticket ID
        ticket_id = f"match-{match_id}"
        
        # Create channel permissions
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
            player1_member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            player2_member: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        # Add permissions for tournament officials
        for role in guild.roles:
            if role.name in ["Tournament Director", "Arbiter", "Moderator"]:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        
        # Create the channel
        try:
            # Find or create a category for match tickets
            category = None
            for cat in guild.categories:
                if cat.name.lower() in ["match rooms", "chess matches", "tournament matches"]:
                    category = cat
                    break
                    
            if not category:
                # Create a new category
                category = await guild.create_category("Match Rooms", overwrites={
                    guild.default_role: discord.PermissionOverwrite(read_messages=False)
                })
            
            # Create the channel in the category
            channel_name = f"match-{match['player1_name'].lower()}-vs-{match['player2_name'].lower()}"
            channel_name = channel_name.replace(" ", "-")[:32]  # Discord channel name limits
            
            channel = await guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites,
                topic=f"Match {match_id}: {match['player1_name']} vs {match['player2_name']}"
            )
            
            # Store ticket info
            tickets["tickets"][ticket_id] = {
                "id": ticket_id,
                "match_id": match_id,
                "channel_id": str(channel.id),
                "player1_id": player1_id,
                "player2_id": player2_id,
                "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status": "Open"
            }
            
            save_data(TICKETS_FILE, tickets)
            
            # Send welcome message
            tournament_name = "Unknown Tournament"
            if "tournament_id" in match and match["tournament_id"] in tournaments["tournaments"]:
                tournament_name = tournaments["tournaments"][match["tournament_id"]]["name"]
                
            embed = discord.Embed(
                title=f"Match: {match['player1_name']} vs {match['player2_name']}",
                description=f"Welcome to your match channel! This is a private channel for your tournament game.",
                color=discord.Color.blue()
            )
            
            embed.add_field(name="Tournament", value=tournament_name, inline=True)
            embed.add_field(name="Round", value=str(match["round"]), inline=True)
            embed.add_field(name="Match ID", value=match_id, inline=True)
            
            # Add instructions
            instructions = (
                "**Instructions:**\n"
                "1. Use this channel to coordinate your match\n"
                "2. Agree on a time to play\n"
                "3. You can play directly in this channel using the chess board below\n"
                "4. When the match is complete, use the buttons to report the result\n\n"
                "If you need assistance, mention a Tournament Director or Arbiter."
            )
            
            embed.add_field(name="How to Play", value=instructions, inline=False)
            
            # Create a chess board message
            await channel.send(embed=embed)
            await channel.send(f"{player1_member.mention} and {player2_member.mention}, your match channel is ready!")
            
            # Create a chess board
            await MatchTicketSystem.create_chess_board(channel, match_id)
            
            return channel
            
        except discord.HTTPException as e:
            print(f"Error creating match channel: {e}")
            return None
    
    @staticmethod
    async def create_chess_board(channel, match_id):
        """Create an interactive chess board in the channel"""
        # Initial chess board state (FEN: starting position)
        initial_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        
        # Create the board message
        board_embed = discord.Embed(
            title="Chess Board",
            description="Use the buttons below to make moves",
            color=discord.Color.green()
        )
        
        # Add the chess board image (using an external API)
        board_embed.set_image(url=f"https://chessboardimage.com/{initial_fen}.png")
        
        # Create the chess board view
        view = ChessBoardView(match_id, initial_fen)
        
        # Send the board
        board_message = await channel.send(embed=board_embed, view=view)
        
        # Store the message ID for future updates
        if match_id in matches["matches"]:
            matches["matches"][match_id]["board_message_id"] = str(board_message.id)
            matches["matches"][match_id]["current_fen"] = initial_fen
            matches["matches"][match_id]["moves"] = []
            save_data(MATCHES_FILE, matches)
    
    @staticmethod
    async def close_match_ticket(guild, match_id):
        """Close a match ticket when the match is completed"""
        # Find the ticket for this match
        ticket_id = None
        for tid, ticket in tickets["tickets"].items():
            if ticket["match_id"] == match_id:
                ticket_id = tid
                break
                
        if not ticket_id:
            return
            
        ticket = tickets["tickets"][ticket_id]
        
        # Get the channel
        try:
            channel = guild.get_channel(int(ticket["channel_id"]))
            if not channel:
                return
                
            # Update ticket status
            ticket["status"] = "Closed"
            save_data(TICKETS_FILE, tickets)
            
            # Send closing message
            match = matches["matches"][match_id]
            
            result_text = "The match has been completed."
            if match["result"] == "player1":
                result_text = f"**{match['player1_name']}** won the match!"
            elif match["result"] == "player2":
                result_text = f"**{match['player2_name']}** won the match!"
            else:
                result_text = "The match ended in a draw."
                
            embed = discord.Embed(
                title="Match Completed",
                description=result_text,
                color=discord.Color.gold()
            )
            
            embed.add_field(name="Reported By", value=f"<@{match['reported_by']}>", inline=True)
            embed.add_field(name="Completed At", value=match["completed_at"], inline=True)
            
            if "moves" in match and match["moves"]:
                pgn = " ".join(match["moves"])
                embed.add_field(name="Game Moves (PGN)", value=f"```{pgn}```", inline=False)
            
            await channel.send(embed=embed)
            
            # Archive the channel
            try:
                # Rename the channel to indicate it's closed
                await channel.edit(name=f"✓-{channel.name}")
                
                # Lock the channel
                for target, overwrite in channel.overwrites.items():
                    if isinstance(target, discord.Member) and target != guild.me:
                        overwrite.send_messages = False
                        await channel.set_permissions(target, overwrite=overwrite)
                
                # Send final message
                await channel.send("This match channel has been archived. It will be automatically deleted in 24 hours.")
                
                # Schedule channel for deletion (in a real bot, you'd use a task for this)
                # For now, we'll just mark it for deletion
                ticket["scheduled_for_deletion"] = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
                save_data(TICKETS_FILE, tickets)
                
            except discord.HTTPException as e:
                print(f"Error archiving channel: {e}")
            
        except Exception as e:
            print(f"Error closing match ticket: {e}")

# Chess Board View for interactive play
class ChessBoardView(discord.ui.View):
    def __init__(self, match_id, fen):
        super().__init__(timeout=None)  # No timeout for the chess board
        self.match_id = match_id
        self.current_fen = fen
        self.move_input = ""
        self.white_to_move = "w" in fen
        self.last_move = None
    
    @discord.ui.button(label="Make Move", style=discord.ButtonStyle.primary)
    async def make_move_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open a modal to input a chess move"""
        # Create a modal for move input
        class MoveInputModal(discord.ui.Modal, title="Enter Chess Move"):
            move = discord.ui.TextInput(
                label="Move (e.g., e2e4, Nf3, O-O)",
                placeholder="Enter your move in algebraic notation",
                required=True,
                min_length=2,
                max_length=10
            )
            
            async def on_submit(self, interaction: discord.Interaction):
                # Process the move
                move_text = self.move.value.strip()
                
                # Get the match
                match = matches["matches"][self.match_id]
                
                # Determine whose turn it is
                player1_id = match["player1_id"]
                player2_id = match["player2_id"]
                current_player_id = player1_id if self.white_to_move else player2_id
                
                # Check if it's the player's turn
                if str(interaction.user.id) != current_player_id:
                    await interaction.response.send_message("It's not your turn to move.", ephemeral=True)
                    return
                
                # In a real implementation, you would validate the move against chess rules
                # For now, we'll just accept any move and update the board
                
                # Add the move to the match history
                if "moves" not in match:
                    match["moves"] = []
                
                move_number = len(match["moves"]) // 2 + 1
                if self.white_to_move:
                    formatted_move = f"{move_number}. {move_text}"
                else:
                    formatted_move = move_text
                
                match["moves"].append(formatted_move)
                
                # Toggle whose turn it is
                self.white_to_move = not self.white_to_move
                
                # Update the last move
                self.last_move = move_text
                
                # In a real implementation, you would update the FEN based on the move
                # For now, we'll just use a placeholder update
                
                # Save the match data
                save_data(MATCHES_FILE, matches)
                
                # Update the chess board
                await self.update_chess_board(interaction)
            
            async def update_chess_board(self, interaction):
                """Update the chess board after a move"""
                # In a real implementation, you would calculate the new FEN based on the move
                # For now, we'll use an external API to get a new board image
                
                # Get the match
                match = matches["matches"][self.match_id]
                
                # Create a PGN string from the moves
                pgn = " ".join(match["moves"])
                
                # Update the board embed
                board_embed = discord.Embed(
                    title="Chess Board",
                    description=f"Last move: {self.last_move}" if self.last_move else "Game in progress",
                    color=discord.Color.green()
                )
                
                # For a real implementation, you would update the FEN based on the move
                # and generate a new board image. For now, we'll use a placeholder.
                
                # We'll use lichess.org's API to generate a board image from the PGN
                # This is a simplified approach - in a real implementation you'd track the FEN properly
                board_embed.set_image(url=f"https://lichess1.org/game/export/gif/placeholder?theme=brown&piece=cburnett")
                
                # Add turn indicator
                turn_text = f"**White** ({match['player1_name']})" if self.white_to_move else f"**Black** ({match['player2_name']})"
                board_embed.add_field(name="Current Turn", value=turn_text, inline=False)
                
                # Add move history
                if match["moves"]:
                    # Format the moves nicely
                    move_history = " ".join(match["moves"])
                    if len(move_history) > 1024:  # Discord field value limit
                        move_history = move_history[-1020:] + "..."
                    board_embed.add_field(name="Move History", value=f"```{move_history}```", inline=False)
                
                # Update the message
                try:
                    message = await interaction.channel.fetch_message(int(match["board_message_id"]))
                    await message.edit(embed=board_embed, view=self)
                    await interaction.response.send_message(f"Move {self.last_move} played. It's now {turn_text}'s turn.", ephemeral=True)
                except discord.NotFound:
                    await interaction.response.send_message("Could not update the chess board. The message may have been deleted.", ephemeral=True)
        
        # Create the modal with the match_id and white_to_move attributes
        modal = MoveInputModal(title="Enter Chess Move")
        modal.match_id = self.match_id
        modal.white_to_move = self.white_to_move
        
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="View PGN", style=discord.ButtonStyle.secondary)
    async def view_pgn_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """View the PGN notation of the game"""
        # Get the match
        match = matches["matches"][self.match_id]
        
        if "moves" not in match or not match["moves"]:
            await interaction.response.send_message("No moves have been played yet.", ephemeral=True)
            return
        
        # Format the PGN
        pgn = " ".join(match["moves"])
        
        # Create an embed with the PGN
        embed = discord.Embed(
            title="Game PGN",
            description=f"```{pgn}```",
            color=discord.Color.blue()
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="Claim Victory", style=discord.ButtonStyle.success)
    async def claim_victory_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Claim victory in the game"""
        # Get the match
        match = matches["matches"][self.match_id]
        
        # Check if the user is one of the players
        user_id = str(interaction.user.id)
        if user_id != match["player1_id"] and user_id != match["player2_id"]:
            await interaction.response.send_message("Only players in this match can claim victory.", ephemeral=True)
            return
        
        # Create a confirmation view
        class ConfirmationView(discord.ui.View):
            def __init__(self, match_id, claimer_id):
                super().__init__(timeout=60)
                self.match_id = match_id
                self.claimer_id = claimer_id
            
            @discord.ui.button(label="Confirm Victory Claim", style=discord.ButtonStyle.success)
            async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                # Get the match
                match = matches["matches"][self.match_id]
                
                # Determine the result
                if self.claimer_id == match["player1_id"]:
                    match["result"] = "player1"
                else:
                    match["result"] = "player2"
                
                # Update match status
                match["status"] = "Completed"
                match["completed_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                match["reported_by"] = self.claimer_id
                
                # Save the match data
                save_data(MATCHES_FILE, matches)
                
                # Update player stats
                winner_id = self.claimer_id
                loser_id = match["player2_id"] if winner_id == match["player1_id"] else match["player1_id"]
                
                if winner_id in players["players"]:
                    players["players"][winner_id]["wins"] += 1
                    if self.match_id not in players["players"][winner_id]["matches"]:
                        players["players"][winner_id]["matches"].append(self.match_id)
                
                if loser_id in players["players"]:
                    players["players"][loser_id]["losses"] += 1
                    if self.match_id not in players["players"][loser_id]["matches"]:
                        players["players"][loser_id]["matches"].append(self.match_id)
                
                # Save player data
                save_data(PLAYERS_FILE, players)
                
                # Close the match ticket
                await MatchTicketSystem.close_match_ticket(interaction.guild, self.match_id)
                
                # Notify the channel
                winner_name = match["player1_name"] if winner_id == match["player1_id"] else match["player2_name"]
                await interaction.response.edit_message(content=f"Victory has been claimed by {winner_name}. The match has been recorded as completed.", view=None)
                
                # Send a notification in the channel
                await interaction.channel.send(f"🏆 **{winner_name}** has claimed victory in this match! The match is now complete.")
            
            @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
            async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                await interaction.response.edit_message(content="Victory claim cancelled.", view=None)
        
        view = ConfirmationView(self.match_id, user_id)
        
        # Determine the opponent
        opponent_id = match["player2_id"] if user_id == match["player1_id"] else match["player1_id"]
        opponent_name = match["player2_name"] if user_id == match["player1_id"] else match["player1_name"]
        
        await interaction.response.send_message(
            f"You are claiming victory against {opponent_name}. Your opponent will be notified. "
            f"If they dispute this claim, they should contact a Tournament Director or Arbiter.\n\n"
            f"Are you sure you want to claim victory?",
            view=view,
            ephemeral=True
        )
    
    @discord.ui.button(label="Offer Draw", style=discord.ButtonStyle.secondary)
    async def offer_draw_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Offer a draw to the opponent"""
        # Get the match
        match = matches["matches"][self.match_id]
        
        # Check if the user is one of the players
        user_id = str(interaction.user.id)
        if user_id != match["player1_id"] and user_id != match["player2_id"]:
            await interaction.response.send_message("Only players in this match can offer a draw.", ephemeral=True)
            return
        
        # Determine the opponent
        opponent_id = match["player2_id"] if user_id == match["player1_id"] else match["player1_id"]
        opponent_name = match["player2_name"] if user_id == match["player1_id"] else match["player1_name"]
        
        # Create a draw offer view
        class DrawOfferView(discord.ui.View):
            def __init__(self, match_id, offerer_id):
                super().__init__(timeout=300)  # 5 minute timeout
                self.match_id = match_id
                self.offerer_id = offerer_id
            
            @discord.ui.button(label="Accept Draw", style=discord.ButtonStyle.primary)
            async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                # Check if the user is the opponent
                if str(interaction.user.id) != opponent_id:
                    await interaction.response.send_message("Only the opponent can accept this draw offer.", ephemeral=True)
                    return
                
                # Get the match
                match = matches["matches"][self.match_id]
                
                # Update match status
                match["result"] = "draw"
                match["status"] = "Completed"
                match["completed_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                match["reported_by"] = str(interaction.user.id)
                
                # Save the match data
                save_data(MATCHES_FILE, matches)
                
                # Update player stats
                player1_id = match["player1_id"]
                player2_id = match["player2_id"]
                
                for player_id in [player1_id, player2_id]:
                    if player_id in players["players"]:
                        players["players"][player_id]["draws"] += 1
                        if self.match_id not in players["players"][player_id]["matches"]:
                            players["players"][player_id]["matches"].append(self.match_id)
                
                # Save player data
                save_data(PLAYERS_FILE, players)
                
                # Close the match ticket
                await MatchTicketSystem.close_match_ticket(interaction.guild, self.match_id)
                
                # Notify the channel
                await interaction.response.edit_message(content="Draw offer accepted. The match has been recorded as a draw.", view=None)
                
                # Send a notification in the channel
                await interaction.channel.send("🤝 **Draw agreed!** The match has ended in a draw.")
            
            @discord.ui.button(label="Decline Draw", style=discord.ButtonStyle.secondary)
            async def decline_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                # Check if the user is the opponent
                if str(interaction.user.id) != opponent_id:
                    await interaction.response.send_message("Only the opponent can decline this draw offer.", ephemeral=True)
                    return
                
                await interaction.response.edit_message(content="Draw offer declined. The game continues.", view=None)
                
                # Send a notification in the channel
                await interaction.channel.send(f"Draw offer from <@{self.offerer_id}> has been declined. The game continues.")
        
        view = DrawOfferView(self.match_id, user_id)
        
        # Send the draw offer to the channel (visible to everyone)
        offerer_name = match["player1_name"] if user_id == match["player1_id"] else match["player2_name"]
        
        await interaction.response.send_message(
            f"✋ **Draw Offer**: {offerer_name} has offered a draw to {opponent_name}.\n"
            f"<@{opponent_id}>, please use the buttons below to accept or decline.",
            view=view
        )
    
    @discord.ui.button(label="Resign", style=discord.ButtonStyle.danger)
    async def resign_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Resign from the game"""
        # Get the match
        match = matches["matches"][self.match_id]
        
        # Check if the user is one of the players
        user_id = str(interaction.user.id)
        if user_id != match["player1_id"] and user_id != match["player2_id"]:
            await interaction.response.send_message("Only players in this match can resign.", ephemeral=True)
            return
        
        # Create a confirmation view
        class ConfirmationView(discord.ui.View):
            def __init__(self, match_id, resigner_id):
                super().__init__(timeout=60)
                self.match_id = match_id
                self.resigner_id = resigner_id
            
            @discord.ui.button(label="Confirm Resignation", style=discord.ButtonStyle.danger)
            async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                # Get the match
                match = matches["matches"][self.match_id]
                
                # Determine the result
                if self.resigner_id == match["player1_id"]:
                    match["result"] = "player2"  # Player 1 resigned, so Player 2 wins
                else:
                    match["result"] = "player1"  # Player 2 resigned, so Player 1 wins
                
                # Update match status
                match["status"] = "Completed"
                match["completed_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                match["reported_by"] = self.resigner_id
                
                # Save the match data
                save_data(MATCHES_FILE, matches)
                
                # Update player stats
                loser_id = self.resigner_id
                winner_id = match["player2_id"] if loser_id == match["player1_id"] else match["player1_id"]
                
                if winner_id in players["players"]:
                    players["players"][winner_id]["wins"] += 1
                    if self.match_id not in players["players"][winner_id]["matches"]:
                        players["players"][winner_id]["matches"].append(self.match_id)
                
                if loser_id in players["players"]:
                    players["players"][loser_id]["losses"] += 1
                    if self.match_id not in players["players"][loser_id]["matches"]:
                        players["players"][loser_id]["matches"].append(self.match_id)
                
                # Save player data
                save_data(PLAYERS_FILE, players)
                
                # Close the match ticket
                await MatchTicketSystem.close_match_ticket(interaction.guild, self.match_id)
                
                # Notify the channel
                resigner_name = match["player1_name"] if self.resigner_id == match["player1_id"] else match["player2_name"]
                winner_name = match["player2_name"] if self.resigner_id == match["player1_id"] else match["player1_name"]
                
                await interaction.response.edit_message(content=f"You have resigned. {winner_name} wins the match.", view=None)
                
                # Send a notification in the channel
                await interaction.channel.send(f"⚠️ **{resigner_name}** has resigned. **{winner_name}** wins the match!")
            
            @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
            async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                await interaction.response.edit_message(content="Resignation cancelled.", view=None)
        
        view = ConfirmationView(self.match_id, user_id)
        
        await interaction.response.send_message(
            "Are you sure you want to resign this match? This action cannot be undone.",
            view=view,
            ephemeral=True
        )

    @discord.ui.button(label="Call Arbiter", style=discord.ButtonStyle.danger)
    async def call_arbiter_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Call an arbiter for assistance"""
        # Get the match
        match = matches["matches"][self.match_id]
        
        # Check if the user is one of the players
        user_id = str(interaction.user.id)
        if user_id != match["player1_id"] and user_id != match["player2_id"]:
            await interaction.response.send_message("Only players in this match can call an arbiter.", ephemeral=True)
            return
        
        # Create a modal for the issue description
        class IssueReportModal(discord.ui.Modal, title="Call Arbiter"):
            issue = discord.ui.TextInput(
                label="Describe the issue",
                placeholder="Please describe the issue you're experiencing...",
                style=discord.TextStyle.paragraph,
                required=True,
                max_length=1000
            )
            
            async def on_submit(self, interaction: discord.Interaction):
                # Get the match
                match = matches["matches"][self.match_id]
                
                # Find arbiter role
                arbiter_role = None
                for role in interaction.guild.roles:
                    if role.name in ["Tournament Director", "Arbiter"]:
                        arbiter_role = role
                        break
                
                # Create the issue report
                reporter_name = match["player1_name"] if user_id == match["player1_id"] else match["player2_name"]
                
                embed = discord.Embed(
                    title="⚠️ Arbiter Assistance Requested",
                    description=f"**{reporter_name}** has requested arbiter assistance for this match.",
                    color=discord.Color.red()
                )
                
                embed.add_field(name="Issue Description", value=self.issue.value, inline=False)
                embed.add_field(name="Match", value=f"{match['player1_name']} vs {match['player2_name']}", inline=True)
                
                if "tournament_id" in match and match["tournament_id"] in tournaments["tournaments"]:
                    tournament_name = tournaments["tournaments"][match["tournament_id"]]["name"]
                    embed.add_field(name="Tournament", value=tournament_name, inline=True)
                
                embed.add_field(name="Round", value=str(match["round"]), inline=True)
                
                # Mention arbiters if role exists
                mention_text = f"{arbiter_role.mention} " if arbiter_role else ""
                
                await interaction.channel.send(
                    f"{mention_text}An arbiter has been called to this match. Please wait for assistance.",
                    embed=embed
                )
                
                await interaction.response.send_message("Your request for arbiter assistance has been submitted. An arbiter will join the channel soon.", ephemeral=True)
        
        # Show the modal
        await interaction.response.send_modal(IssueReportModal())

# Create Tournament Command
async def create_tournament_command(interaction: discord.Interaction, name: str, format: str = "Swiss", rounds: int = 3, description: str = ""):
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
    
    # Validate format
    valid_formats = ["Swiss", "Round Robin", "Single Elimination"]
    if format not in valid_formats:
        await interaction.response.send_message(f"Invalid tournament format. Please choose from: {', '.join(valid_formats)}", ephemeral=True)
        return
    
    # Validate rounds
    if rounds < 1 or rounds > 10:
        await interaction.response.send_message("Number of rounds must be between 1 and 10.", ephemeral=True)
        return
    
    # Generate tournament ID
    tournament_id = generate_id("T")
    
    # Create tournament
    tournaments["tournaments"][tournament_id] = {
        "id": tournament_id,
        "name": name,
        "format": format,
        "rounds": rounds,
        "description": description,
        "created_by": str(interaction.user.id),
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "Registration Open",
        "participants": [],
        "matches": [],
        "current_round": 0
    }
    
    # Save data
    save_data(TOURNAMENTS_FILE, tournaments)
    
    # Create embed
    embed = discord.Embed(
        title=f"Tournament Created: {name}",
        description=description if description else "No description provided.",
        color=discord.Color.green()
    )
    
    embed.add_field(name="Format", value=format, inline=True)
    embed.add_field(name="Rounds", value=str(rounds), inline=True)
    embed.add_field(name="Status", value="Registration Open", inline=True)
    embed.add_field(name="Tournament ID", value=tournament_id, inline=True)
    
    # Add registration instructions
    embed.add_field(
        name="How to Register",
        value=f"Use `/chess register {tournament_id}` to join this tournament.",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

# List Tournaments Command
async def list_tournaments_command(interaction: discord.Interaction, status: str = "All"):
    """List all chess tournaments"""
    await interaction.response.defer()
    
    if not tournaments["tournaments"]:
        await interaction.followup.send("No tournaments found.")
        return
    
    # Filter tournaments by status if specified
    filtered_tournaments = {}
    for tid, tournament in tournaments["tournaments"].items():
        if status == "All" or tournament["status"] == status:
            filtered_tournaments[tid] = tournament
    
    if not filtered_tournaments:
        await interaction.followup.send(f"No tournaments found with status: {status}")
        return
    
    # Sort tournaments by creation date (newest first)
    sorted_tournaments = sorted(
        filtered_tournaments.values(),
        key=lambda t: t["created_at"],
        reverse=True
    )
    
    # Create embed
    embed = discord.Embed(
        title="Chess Tournaments",
        description=f"Showing {len(filtered_tournaments)} tournament(s) with status: {status}",
        color=discord.Color.blue()
    )
    
    # Add each tournament
    for tournament in sorted_tournaments:
        # Format participant count
        participant_count = len(tournament["participants"])
        
        # Format status with emoji
        status_emoji = "🔄"  # Default
        if tournament["status"] == "Registration Open":
            status_emoji = "✅"
        elif tournament["status"] == "In Progress":
            status_emoji = "⏳"
        elif tournament["status"] == "Completed":
            status_emoji = "🏁"
        
        # Format value
        value = (
            f"**Format:** {tournament['format']} ({tournament['rounds']} rounds)\n"
            f"**Status:** {status_emoji} {tournament['status']}\n"
            f"**Participants:** {participant_count}\n"
            f"**ID:** {tournament['id']}"
        )
        
        embed.add_field(name=tournament["name"], value=value, inline=False)
    
    await interaction.followup.send(embed=embed)

# Tournament Info Command
async def tournament_info_command(interaction: discord.Interaction, tournament_id: str):
    """Show detailed information about a tournament"""
    if tournament_id not in tournaments["tournaments"]:
        await interaction.response.send_message(f"Tournament with ID {tournament_id} not found.", ephemeral=True)
        return
    
    tournament = tournaments["tournaments"][tournament_id]
    
    # Create embed
    embed = discord.Embed(
        title=f"Tournament: {tournament['name']}",
        description=tournament["description"] if tournament["description"] else "No description provided.",
        color=discord.Color.blue()
    )
    
    # Basic info
    embed.add_field(name="Format", value=tournament["format"], inline=True)
    embed.add_field(name="Rounds", value=str(tournament["rounds"]), inline=True)
    embed.add_field(name="Status", value=tournament["status"], inline=True)
    
    # Participants
    participant_count = len(tournament["participants"])
    embed.add_field(name="Participants", value=str(participant_count), inline=True)
    
    # Current round
    if tournament["status"] == "In Progress":
        embed.add_field(name="Current Round", value=str(tournament["current_round"]), inline=True)
    
    # Created info
    created_by = f"<@{tournament['created_by']}>"
    created_at = tournament["created_at"]
    embed.add_field(name="Created By", value=created_by, inline=True)
    embed.add_field(name="Created At", value=created_at, inline=True)
    
    # Tournament ID
    embed.add_field(name="Tournament ID", value=tournament_id, inline=True)
    
    # Add registration/match buttons
    class TournamentInfoView(discord.ui.View):
        def __init__(self, tournament_id):
            super().__init__(timeout=180)
            self.tournament_id = tournament_id
        
        @discord.ui.button(label="View Participants", style=discord.ButtonStyle.primary)
        async def view_participants_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            await tournament_players_command(interaction, self.tournament_id)
        
        @discord.ui.button(label="View Matches", style=discord.ButtonStyle.primary)
        async def view_matches_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            await tournament_matches_command(interaction, self.tournament_id)
        
        @discord.ui.button(label="Register", style=discord.ButtonStyle.success)
        async def register_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            await register_player_command(interaction, self.tournament_id)
    
    view = TournamentInfoView(tournament_id)
    
    await interaction.response.send_message(embed=embed, view=view)

# Tournament Players Command
async def tournament_players_command(interaction: discord.Interaction, tournament_id: str):
    """Show players registered for a tournament"""
    await interaction.response.defer()
    
    if tournament_id not in tournaments["tournaments"]:
        await interaction.followup.send(f"Tournament with ID {tournament_id} not found.")
        return
    
    tournament = tournaments["tournaments"][tournament_id]
    
    if not tournament["participants"]:
        await interaction.followup.send(f"No players registered for tournament: {tournament['name']}")
        return
    
    # Get player details
    player_details = []
    for player_id in tournament["participants"]:
        if player_id in players["players"]:
            player = players["players"][player_id]
            player_details.append({
                "id": player_id,
                "name": player["username"],
                "rating": player["rating"],
                "tier": player.get("tier", get_rating_tier(player["rating"]))
            })
        else:
            # Player not found in database, try to get from Discord
            try:
                member = await interaction.guild.fetch_member(int(player_id))
                player_details.append({
                    "id": player_id,
                    "name": member.display_name,
                    "rating": 1200,  # Default rating
                    "tier": "Beginner"
                })
            except:
                # Fallback if member not found
                player_details.append({
                    "id": player_id,
                    "name": f"Unknown Player ({player_id})",
                    "rating": 1200,
                    "tier": "Beginner"
                })
    
    # Sort by rating (descending)
    player_details.sort(key=lambda p: p["rating"], reverse=True)
    
    # Create embed
    embed = discord.Embed(
        title=f"Players: {tournament['name']}",
        description=f"{len(player_details)} registered participants",
        color=discord.Color.blue()
    )
    
    # Add players to embed
    players_text = ""
    for i, player in enumerate(player_details, 1):
        players_text += f"{i}. **{player['name']}** - {player['rating']} ({player['tier']})\n"
        
        # Split into multiple fields if too many players
        if i % 15 == 0 or i == len(player_details):
            embed.add_field(name=f"Players {i-14 if i > 15 else 1}-{i}", value=players_text, inline=False)
            players_text = ""
    
    await interaction.followup.send(embed=embed)

# Tournament Standings Command
async def tournament_standings_command(interaction: discord.Interaction, tournament_id: str):
    """Show current standings for a tournament"""
    await interaction.response.defer()
    
    if tournament_id not in tournaments["tournaments"]:
        await interaction.followup.send(f"Tournament with ID {tournament_id} not found.")
        return
    
    tournament = tournaments["tournaments"][tournament_id]
    
    if tournament["status"] == "Registration Open":
        await interaction.followup.send(f"Tournament {tournament['name']} has not started yet. No standings available.")
        return
    
    # Calculate standings
    standings = {}
    
    # Initialize standings for all participants
    for player_id in tournament["participants"]:
        player_name = "Unknown Player"
        if player_id in players["players"]:
            player_name = players["players"][player_id]["username"]
        
        standings[player_id] = {
            "id": player_id,
            "name": player_name,
            "matches_played": 0,
            "wins": 0,
            "losses": 0,
            "draws": 0,
            "points": 0,
            "opponents": []  # For tiebreaks
        }
    
    # Process all matches
    for match_id in tournament["matches"]:
        if match_id in matches["matches"]:
            match = matches["matches"][match_id]
            
            # Skip matches that aren't completed
            if match["status"] != "Completed":
                continue
            
            player1_id = match["player1_id"]
            player2_id = match["player2_id"]
            
            # Skip byes
            if player2_id == "BYE":
                if player1_id in standings:
                    standings[player1_id]["wins"] += 1
                    standings[player1_id]["matches_played"] += 1
                    standings[player1_id]["points"] += 1
                continue
            
            # Update standings based on result
            if match["result"] == "player1":
                # Player 1 won
                if player1_id in standings:
                    standings[player1_id]["wins"] += 1
                    standings[player1_id]["matches_played"] += 1
                    standings[player1_id]["points"] += 1
                    standings[player1_id]["opponents"].append(player2_id)
                
                if player2_id in standings:
                    standings[player2_id]["losses"] += 1
                    standings[player2_id]["matches_played"] += 1
                    standings[player2_id]["opponents"].append(player1_id)
                
            elif match["result"] == "player2":
                # Player 2 won
                if player2_id in standings:
                    standings[player2_id]["wins"] += 1
                    standings[player2_id]["matches_played"] += 1
                    standings[player2_id]["points"] += 1
                    standings[player2_id]["opponents"].append(player1_id)
                
                if player1_id in standings:
                    standings[player1_id]["losses"] += 1
                    standings[player1_id]["matches_played"] += 1
                    standings[player1_id]["opponents"].append(player2_id)
                
            elif match["result"] == "draw":
                # Draw
                if player1_id in standings:
                    standings[player1_id]["draws"] += 1
                    standings[player1_id]["matches_played"] += 1
                    standings[player1_id]["points"] += 0.5
                    standings[player1_id]["opponents"].append(player2_id)
                
                if player2_id in standings:
                    standings[player2_id]["draws"] += 1
                    standings[player2_id]["matches_played"] += 1
                    standings[player2_id]["points"] += 0.5
                    standings[player2_id]["opponents"].append(player1_id)
    
    # Calculate tiebreaks (Buchholz score - sum of opponents' scores)
    for player_id, player_data in standings.items():
        buchholz = 0
        for opponent_id in player_data["opponents"]:
            if opponent_id in standings:
                buchholz += standings[opponent_id]["points"]
        
        player_data["tiebreak"] = buchholz
    
    # Sort standings by points (descending), then tiebreak
    sorted_standings = sorted(
        standings.values(),
        key=lambda p: (p["points"], p["tiebreak"]),
        reverse=True
    )
    
    # Create embed
    embed = discord.Embed(
        title=f"Standings: {tournament['name']}",
        description=f"Current standings after round {tournament['current_round']}",
        color=discord.Color.gold()
    )
    
    # Add standings to embed
    standings_text = ""
    for i, player in enumerate(sorted_standings, 1):
        standings_text += f"{i}. **{player['name']}** - {player['points']} pts ({player['wins']}-{player['losses']}-{player['draws']})\n"
        
        # Split into multiple fields if too many players
        if i % 15 == 0 or i == len(sorted_standings):
            embed.add_field(name=f"Standings {i-14 if i > 15 else 1}-{i}", value=standings_text, inline=False)
            standings_text = ""
    
    await interaction.followup.send(embed=embed)

# Tournament Matches Command
async def tournament_matches_command(interaction: discord.Interaction, tournament_id: str, round: int = None):
    """Show matches for a tournament"""
    await interaction.response.defer()
    
    if tournament_id not in tournaments["tournaments"]:
        await interaction.followup.send(f"Tournament with ID {tournament_id} not found.")
        return
    
    tournament = tournaments["tournaments"][tournament_id]
    
    if tournament["status"] == "Registration Open":
        await interaction.followup.send(f"Tournament {tournament['name']} has not started yet. No matches available.")
        return
    
    # Determine which round to show
    current_round = tournament["current_round"]
    if round is None:
        round = current_round
    elif round < 1 or round > current_round:
        await interaction.followup.send(f"Invalid round number. Please choose a round between 1 and {current_round}.")
        return
    
    # Get matches for the specified round
    round_matches = []
    for match_id in tournament["matches"]:
        if match_id in matches["matches"]:
            match = matches["matches"][match_id]
            if match["round"] == round:
                round_matches.append(match)
    
    if not round_matches:
        await interaction.followup.send(f"No matches found for round {round}.")
        return
    
    # Create embed
    embed = discord.Embed(
        title=f"Matches: {tournament['name']} - Round {round}",
        description=f"{len(round_matches)} matches in this round",
        color=discord.Color.blue()
    )
    
    # Add matches to embed
    for i, match in enumerate(round_matches, 1):
        # Format result
        result_text = "⏳ In Progress"
        if match["status"] == "Completed":
            if match["result"] == "player1":
                result_text = f"✅ **{match['player1_name']}** won"
            elif match["result"] == "player2":
                result_text = f"✅ **{match['player2_name']}** won"
            elif match["result"] == "draw":
                result_text = "🤝 Draw"
        
        # Handle bye matches
        if match["player2_id"] == "BYE":
            match_text = f"**{match['player1_name']}** - BYE\n{result_text}"
        else:
            match_text = f"**{match['player1_name']}** vs **{match['player2_name']}**\n{result_text}"
        
        # Add match ID
        match_text += f"\nMatch ID: {match['id']}"
        
        embed.add_field(name=f"Match {i}", value=match_text, inline=True)
    
    # Add navigation buttons
    class MatchesView(discord.ui.View):
        def __init__(self, tournament_id, current_round, max_round):
            super().__init__(timeout=180)
            self.tournament_id = tournament_id
            self.current_round = current_round
            self.max_round = max_round
            
            # Disable buttons if at first/last round
            if current_round <= 1:
                self.previous_round_button.disabled = True
            if current_round >= max_round:
                self.next_round_button.disabled = True
        
        @discord.ui.button(label="Previous Round", style=discord.ButtonStyle.secondary)
        async def previous_round_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            await tournament_matches_command(interaction, self.tournament_id, self.current_round - 1)
        
        @discord.ui.button(label="Create Match Tickets", style=discord.ButtonStyle.primary)
        async def create_tickets_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            # Check if user has permission
            has_permission = False
            for role in interaction.user.roles:
                if role.name in ["Tournament Director", "Moderator", "Arbiter"]:
                    has_permission = True
                    break
            
            if not has_permission:
                await interaction.response.send_message("You don't have permission to create match tickets.", ephemeral=True)
                return
            
            await interaction.response.defer(ephemeral=True)
            
            # Get matches for the current round
            round_matches = []
            for match_id in tournaments["tournaments"][self.tournament_id]["matches"]:
                if match_id in matches["matches"]:
                    match = matches["matches"][match_id]
                    if match["round"] == self.current_round and match["player2_id"] != "BYE":
                        round_matches.append(match)
            
            if not round_matches:
                await interaction.followup.send("No valid matches found for this round.", ephemeral=True)
                return
            
            # Create tickets for each match
            created_count = 0
            for match in round_matches:
                # Skip if ticket already exists
                ticket_exists = False
                for ticket_id, ticket in tickets["tickets"].items():
                    if ticket["match_id"] == match["id"]:
                        ticket_exists = True
                        break
                
                if not ticket_exists:
                    channel = await MatchTicketSystem.create_match_ticket(interaction.guild, match["id"])
                    if channel:
                        created_count += 1
            
            await interaction.followup.send(f"Created {created_count} match tickets for round {self.current_round}.", ephemeral=True)
        
        @discord.ui.button(label="Next Round", style=discord.ButtonStyle.secondary)
        async def next_round_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            await tournament_matches_command(interaction, self.tournament_id, self.current_round + 1)
    
    view = MatchesView(tournament_id, round, current_round)
    
    await interaction.followup.send(embed=embed, view=view)

# Register Player Command
async def register_player_command(interaction: discord.Interaction, tournament_id: str):
    """Register for a chess tournament"""
    if tournament_id not in tournaments["tournaments"]:
        await interaction.response.send_message(f"Tournament with ID {tournament_id} not found.", ephemeral=True)
        return
    
    tournament = tournaments["tournaments"][tournament_id]
    
    # Check if tournament is open for registration
    if tournament["status"] != "Registration Open":
        await interaction.response.send_message(f"Registration for tournament '{tournament['name']}' is closed.", ephemeral=True)
        return
    
    user_id = str(interaction.user.id)
    
    # Check if already registered
    if user_id in tournament["participants"]:
        await interaction.response.send_message(f"You are already registered for tournament '{tournament['name']}'.", ephemeral=True)
        return
    
    # Register the player
    tournament["participants"].append(user_id)
    
    # Create or update player profile
    if user_id not in players["players"]:
        # Create new player profile
        players["players"][user_id] = {
            "id": user_id,
            "username": interaction.user.display_name,
            "rating": 1200,  # Default rating
            "tier": "Beginner",
            "tournaments": [tournament_id],
            "matches": [],
            "wins": 0,
            "losses": 0,
            "draws": 0
        }
    else:
        # Update existing player
        if tournament_id not in players["players"][user_id]["tournaments"]:
            players["players"][user_id]["tournaments"].append(tournament_id)
        
        # Update username if changed
        players["players"][user_id]["username"] = interaction.user.display_name
    
    # Save data
    save_data(TOURNAMENTS_FILE, tournaments)
    save_data(PLAYERS_FILE, players)
    
    # Create embed
    embed = discord.Embed(
        title=f"Registration Successful",
        description=f"You have been registered for tournament '{tournament['name']}'.",
        color=discord.Color.green()
    )
    
    embed.add_field(name="Tournament", value=tournament["name"], inline=True)
    embed.add_field(name="Format", value=tournament["format"], inline=True)
    embed.add_field(name="Participants", value=str(len(tournament["participants"])), inline=True)
    
    # Add player info
    player = players["players"][user_id]
    embed.add_field(name="Your Rating", value=f"{player['rating']} ({player['tier']})", inline=True)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Unregister Player Command
async def unregister_player_command(interaction: discord.Interaction, tournament_id: str):
    """Unregister from a chess tournament"""
    if tournament_id not in tournaments["tournaments"]:
        await interaction.response.send_message(f"Tournament with ID {tournament_id} not found.", ephemeral=True)
        return
    
    tournament = tournaments["tournaments"][tournament_id]
    
    # Check if tournament is open for registration
    if tournament["status"] != "Registration Open":
        await interaction.response.send_message(f"Registration for tournament '{tournament['name']}' is closed. You cannot unregister at this time.", ephemeral=True)
        return
    
    user_id = str(interaction.user.id)
    
    # Check if registered
    if user_id not in tournament["participants"]:
        await interaction.response.send_message(f"You are not registered for tournament '{tournament['name']}'.", ephemeral=True)
        return
    
    # Unregister the player
    tournament["participants"].remove(user_id)
    
    # Update player profile
    if user_id in players["players"] and tournament_id in players["players"][user_id]["tournaments"]:
        players["players"][user_id]["tournaments"].remove(tournament_id)
    
    # Save data
    save_data(TOURNAMENTS_FILE, tournaments)
    save_data(PLAYERS_FILE, players)
    
    await interaction.response.send_message(f"You have been unregistered from tournament '{tournament['name']}'.", ephemeral=True)

# Player Profile Command
async def player_profile_command(interaction: discord.Interaction, user: discord.Member = None):
    """View a player's chess profile"""
    await interaction.response.defer()
    
    # If no user specified, use the command author
    if user is None:
        user = interaction.user
    
    user_id = str(user.id)
    
    # Check if player exists in database
    if user_id not in players["players"]:
        await interaction.followup.send(f"{user.display_name} does not have a chess profile yet.")
        return
    
    player = players["players"][user_id]
    
    # Create embed
    embed = discord.Embed(
        title=f"Chess Profile: {player['username']}",
        description=f"Rating: **{player['rating']}** ({player['tier']})",
        color=discord.Color.blue()
    )
    
    # Set user avatar as thumbnail
    embed.set_thumbnail(url=user.display_avatar.url)
    
    # Add stats
    total_games = player["wins"] + player["losses"] + player["draws"]
    win_rate = (player["wins"] / total_games * 100) if total_games > 0 else 0
    
    embed.add_field(name="Record", value=f"{player['wins']}W - {player['losses']}L - {player['draws']}D", inline=True)
    embed.add_field(name="Win Rate", value=f"{win_rate:.1f}%", inline=True)
    embed.add_field(name="Total Games", value=str(total_games), inline=True)
    
    # Add tournament history
    tournament_count = len(player["tournaments"])
    if tournament_count > 0:
        tournament_names = []
        for tid in player["tournaments"]:
            if tid in tournaments["tournaments"]:
                tournament_names.append(tournaments["tournaments"][tid]["name"])
        
        if tournament_names:
            embed.add_field(name="Tournaments", value=", ".join(tournament_names[:5]) + (f" and {len(tournament_names) - 5} more" if len(tournament_names) > 5 else ""), inline=False)
        else:
            embed.add_field(name="Tournaments", value=f"{tournament_count} tournaments", inline=False)
    
    # Add recent matches
    if player["matches"]:
        recent_matches = []
        for mid in player["matches"][-5:]:  # Get last 5 matches
            if mid in matches["matches"]:
                match = matches["matches"][mid]
                
                # Determine if this player won or lost
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
                
                # Skip byes
                if opponent == "BYE":
                    continue
                
                recent_matches.append(f"{result} vs {opponent}")
        
        if recent_matches:
            embed.add_field(name="Recent Matches", value="\n".join(recent_matches), inline=False)
    
    await interaction.followup.send(embed=embed)

# Start Tournament Command
async def start_tournament_command(interaction: discord.Interaction, tournament_id: str):
    """Start a chess tournament"""
    # Check if user has permission
    has_permission = False
    for role in interaction.user.roles:
        if role.name in ["Tournament Director", "Moderator"]:
            has_permission = True
            break
    
    if not has_permission:
        await interaction.response.send_message("You don't have permission to start tournaments. You need the Tournament Director or Moderator role.", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    if tournament_id not in tournaments["tournaments"]:
        await interaction.followup.send(f"Tournament with ID {tournament_id} not found.")
        return
    
    tournament = tournaments["tournaments"][tournament_id]
    
    # Check if tournament can be started
    if tournament["status"] != "Registration Open":
        await interaction.followup.send(f"Tournament '{tournament['name']}' cannot be started. Current status: {tournament['status']}")
        return
    
    # Check if there are enough participants
    if len(tournament["participants"]) < 2:
        await interaction.followup.send(f"Cannot start tournament '{tournament['name']}' with fewer than 2 participants.")
        return
    
    # Update tournament status
    tournament["status"] = "In Progress"
    tournament["current_round"] = 1
    tournament["started_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Generate first round pairings
    await generate_pairings(tournament_id, 1)
    
    # Save data
    save_data(TOURNAMENTS_FILE, tournaments)
    
    # Create embed
    embed = discord.Embed(
        title=f"Tournament Started: {tournament['name']}",
        description=f"Round 1 pairings have been generated.",
        color=discord.Color.green()
    )
    
    embed.add_field(name="Participants", value=str(len(tournament["participants"])), inline=True)
    embed.add_field(name="Format", value=tournament["format"], inline=True)
    embed.add_field(name="Total Rounds", value=str(tournament["rounds"]), inline=True)
    
    # Add instructions
    embed.add_field(
        name="Next Steps",
        value="Use `/chess tournament matches " + tournament_id + "` to view the pairings for Round 1.",
        inline=False
    )
    
    await interaction.followup.send(embed=embed)

# Generate pairings for a tournament round
async def generate_pairings(tournament_id, round_number):
    """Generate pairings for a tournament round"""
    if tournament_id not in tournaments["tournaments"]:
        return False
    
    tournament = tournaments["tournaments"][tournament_id]
    
    # Get participants
    participants = tournament["participants"]
    
    if not participants:
        return False
    
    # Calculate standings for pairing purposes
    standings = {}
    
    # Initialize standings for all participants
    for player_id in participants:
        player_name = "Unknown Player"
        if player_id in players["players"]:
            player_name = players["players"][player_id]["username"]
            player_rating = players["players"][player_id]["rating"]
        else:
            player_rating = 1200  # Default rating
        
        standings[player_id] = {
            "id": player_id,
            "name": player_name,
            "rating": player_rating,
            "matches_played": 0,
            "points": 0,
            "opponents": []  # Keep track of previous opponents
        }
    
    # Process previous matches to calculate standings
    for match_id in tournament["matches"]:
        if match_id in matches["matches"]:
            match = matches["matches"][match_id]
            
            # Skip matches from future rounds
            if match["round"] >= round_number:
                continue
            
            player1_id = match["player1_id"]
            player2_id = match["player2_id"]
            
            # Skip byes
            if player2_id == "BYE":
                if player1_id in standings:
                    standings[player1_id]["matches_played"] += 1
                    standings[player1_id]["points"] += 1
                continue
            
            # Record that these players have played each other
            if player1_id in standings and player2_id in standings:
                standings[player1_id]["opponents"].append(player2_id)
                standings[player2_id]["opponents"].append(player1_id)
            
            # Update standings based on result
            if match["status"] == "Completed":
                if match["result"] == "player1":
                    # Player 1 won
                    if player1_id in standings:
                        standings[player1_id]["matches_played"] += 1
                        standings[player1_id]["points"] += 1
                    
                    if player2_id in standings:
                        standings[player2_id]["matches_played"] += 1
                    
                elif match["result"] == "player2":
                    # Player 2 won
                    if player2_id in standings:
                        standings[player2_id]["matches_played"] += 1
                        standings[player2_id]["points"] += 1
                    
                    if player1_id in standings:
                        standings[player1_id]["matches_played"] += 1
                    
                elif match["result"] == "draw":
                    # Draw
                    if player1_id in standings:
                        standings[player1_id]["matches_played"] += 1
                        standings[player1_id]["points"] += 0.5
                    
                    if player2_id in standings:
                        standings[player2_id]["matches_played"] += 1
                        standings[player2_id]["points"] += 0.5
    
    # Sort players by points (descending), then rating
    sorted_players = sorted(
        standings.values(),
        key=lambda p: (p["points"], p["rating"]),
        reverse=True
    )
    
    # Generate pairings based on tournament format
    pairings = []
    
    if tournament["format"] == "Swiss":
        # Swiss pairing algorithm
        # Group players by points
        point_groups = {}
        for player in sorted_players:
            points = player["points"]
            if points not in point_groups:
                point_groups[points] = []
            point_groups[points].append(player)
        
        # Sort point groups by points (descending)
        sorted_point_groups = sorted(point_groups.items(), key=lambda x: x[0], reverse=True)
        
        # Create a list of players to be paired
        players_to_pair = []
        for points, group in sorted_point_groups:
            players_to_pair.extend(group)
        
        # Create pairings
        while players_to_pair:
            if len(players_to_pair) == 1:
                # Odd number of players, give the last player a bye
                player = players_to_pair.pop(0)
                
                # Check if player already had a bye
                had_bye = False
                for match_id in tournament["matches"]:
                    if match_id in matches["matches"]:
                        match = matches["matches"][match_id]
                        if match["player1_id"] == player["id"] and match["player2_id"] == "BYE":
                            had_bye = True
                            break
                
                if had_bye and len(tournament["participants"]) > 2:
                    # Try to find another player for a bye
                    players_to_pair.insert(0, player)  # Put the player back
                    
                    # Find a player who hasn't had a bye yet
                    bye_candidate = None
                    for i in range(len(players_to_pair) - 1, -1, -1):
                        candidate = players_to_pair[i]
                        candidate_had_bye = False
                        
                        for match_id in tournament["matches"]:
                            if match_id in matches["matches"]:
                                match = matches["matches"][match_id]
                                if match["player1_id"] == candidate["id"] and match["player2_id"] == "BYE":
                                    candidate_had_bye = True
                                    break
                        
                        if not candidate_had_bye:
                            bye_candidate = candidate
                            players_to_pair.pop(i)
                            break
                    
                    if bye_candidate:
                        # Create a bye match for this candidate
                        pairings.append((bye_candidate["id"], "BYE"))
                    else:
                        # No suitable candidate found, give the original player a bye
                        player = players_to_pair.pop(0)
                        pairings.append((player["id"], "BYE"))
                else:
                    # Create a bye match
                    pairings.append((player["id"], "BYE"))
            else:
                # Get the first player
                player1 = players_to_pair.pop(0)
                
                # Find a suitable opponent
                opponent_found = False
                for i in range(len(players_to_pair)):
                    player2 = players_to_pair[i]
                    
                    # Check if these players have already played each other
                    if player2["id"] in player1["opponents"]:
                        continue
                    
                    # Found a suitable opponent
                    opponent_found = True
                    players_to_pair.pop(i)
                    pairings.append((player1["id"], player2["id"]))
                    break
                
                if not opponent_found:
                    # No suitable opponent found, pair with the next available player
                    player2 = players_to_pair.pop(0)
                    pairings.append((player1["id"], player2["id"]))
    
    elif tournament["format"] == "Round Robin":
        # Round Robin pairing algorithm
        n = len(sorted_players)
        
        if n % 2 == 1:
            # Odd number of players, add a "BYE" player
            sorted_players.append({"id": "BYE", "name": "BYE"})
            n += 1
        
        # Calculate which pairs to use for this round
        # For round r, player i plays against player (i + r) % (n-1)
        # Player n-1 always plays against player (n-1 + r) % (n-1) = r
        pairings_for_round = []
        
        for i in range(n // 2):
            if i == 0:
                player1_idx = 0
                player2_idx = (round_number % (n - 1)) + 1
            else:
                player1_idx = i
                player2_idx = (n - 1 - i + round_number) % (n - 1) + 1
            
            if player1_idx >= len(sorted_players) or player2_idx >= len(sorted_players):
                continue
            
            player1 = sorted_players[player1_idx]
            player2 = sorted_players[player2_idx]
            
            if player1["id"] == "BYE":
                pairings_for_round.append((player2["id"], "BYE"))
            elif player2["id"] == "BYE":
                pairings_for_round.append((player1["id"], "BYE"))
            else:
                pairings_for_round.append((player1["id"], player2["id"]))
        
        pairings = pairings_for_round
    
    elif tournament["format"] == "Single Elimination":
        # Single Elimination pairing algorithm
        if round_number == 1:
            # First round, pair players based on seeding
            n = len(sorted_players)
            
            # If not a power of 2, some players get byes
            next_power_of_2 = 1
            while next_power_of_2 < n:
                next_power_of_2 *= 2
            
            byes_needed = next_power_of_2 - n
            
            # Create pairings with byes for the lowest seeds
            for i in range(n // 2):
                if i < byes_needed:
                    # Give a bye to the top seed
                    pairings.append((sorted_players[i]["id"], "BYE"))
                else:
                    # Regular pairing
                    player1_idx = i
                    player2_idx = n - 1 - i
                    
                    if player1_idx >= len(sorted_players) or player2_idx >= len(sorted_players) or player1_idx == player2_idx:
                        continue
                    
                    pairings.append((sorted_players[player1_idx]["id"], sorted_players[player2_idx]["id"]))
        else:
            # Subsequent rounds, pair winners of previous round
            winners = []
            
            # Find winners from previous round
            for match_id in tournament["matches"]:
                if match_id in matches["matches"]:
                    match = matches["matches"][match_id]
                    
                    if match["round"] == round_number - 1 and match["status"] == "Completed":
                        if match["result"] == "player1":
                            winners.append(match["player1_id"])
                        elif match["result"] == "player2":
                            winners.append(match["player2_id"])
                        elif match["result"] == "draw":
                            # In case of a draw, advance player1 (this should be handled better in a real tournament)
                            winners.append(match["player1_id"])
            
            # Pair winners
            for i in range(0, len(winners), 2):
                if i + 1 < len(winners):
                    pairings.append((winners[i], winners[i + 1]))
                else:
                    # Odd number of winners, give a bye
                    pairings.append((winners[i], "BYE"))
    
    # Create match objects for each pairing
    for player1_id, player2_id in pairings:
        # Get player names
        player1_name = "Unknown Player"
        if player1_id in players["players"]:
            player1_name = players["players"][player1_id]["username"]
        
        player2_name = "BYE"
        if player2_id != "BYE" and player2_id in players["players"]:
            player2_name = players["players"][player2_id]["username"]
        
        # Create match
        match_id = generate_id("M")
        
        matches["matches"][match_id] = {
            "id": match_id,
            "tournament_id": tournament_id,
            "round": round_number,
            "player1_id": player1_id,
            "player2_id": player2_id,
            "player1_name": player1_name,
            "player2_name": player2_name,
            "status": "Scheduled",
            "result": None,
            "moves": [],
            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Add match to tournament
        tournament["matches"].append(match_id)
        
        # Auto-complete bye matches
        if player2_id == "BYE":
            matches["matches"][match_id]["status"] = "Completed"
            matches["matches"][match_id]["result"] = "player1"
            matches["matches"][match_id]["completed_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Update player stats
            if player1_id in players["players"]:
                players["players"][player1_id]["wins"] += 1
                if match_id not in players["players"][player1_id]["matches"]:
                    players["players"][player1_id]["matches"].append(match_id)
    
    # Save data
    save_data(MATCHES_FILE, matches)
    save_data(PLAYERS_FILE, players)
    
    return True

# Next Round Command
async def next_round_command(interaction: discord.Interaction, tournament_id: str):
    """Start the next round of a tournament"""
    # Check if user has permission
    has_permission = False
    for role in interaction.user.roles:
        if role.name in ["Tournament Director", "Moderator"]:
            has_permission = True
            break
    
    if not has_permission:
        await interaction.response.send_message("You don't have permission to advance tournament rounds. You need the Tournament Director or Moderator role.", ephemeral=True)
        return
    
    await interaction.response.defer()
    
    if tournament_id not in tournaments["tournaments"]:
        await interaction.followup.send(f"Tournament with ID {tournament_id} not found.")
        return
    
    tournament = tournaments["tournaments"][tournament_id]
    
    # Check if tournament is in progress
    if tournament["status"] != "In Progress":
        await interaction.followup.send(f"Tournament '{tournament['name']}' is not in progress. Current status: {tournament['status']}")
        return
    
    current_round = tournament["current_round"]
    
    # Check if all matches from current round are completed
    all_completed = True
    for match_id in tournament["matches"]:
        if match_id in matches["matches"]:
            match = matches["matches"][match_id]
            if match["round"] == current_round and match["status"] != "Completed":
                all_completed = False
                break
    
    if not all_completed:
        # Create confirmation view
        class ConfirmationView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=60)
            
            @discord.ui.button(label="Force Next Round", style=discord.ButtonStyle.danger)
            async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                # Proceed with next round
                await start_next_round(interaction, tournament_id)
            
            @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
            async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                await interaction.response.send_message("Operation cancelled.", ephemeral=True)
        
        await interaction.followup.send(
            f"Warning: Not all matches from round {current_round} are completed. Do you want to force the next round?",
            view=ConfirmationView()
        )
    else:
        # All matches completed, proceed to next round
        await start_next_round(interaction, tournament_id)

async def start_next_round(interaction: discord.Interaction, tournament_id: str):
    """Helper function to start the next round"""
    tournament = tournaments["tournaments"][tournament_id]
    current_round = tournament["current_round"]
    
    # Check if this was the final round
    if current_round >= tournament["rounds"]:
        # Tournament is complete
        tournament["status"] = "Completed"
        tournament["completed_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        save_data(TOURNAMENTS_FILE, tournaments)
        
        # Create final standings
        embed = discord.Embed(
            title=f"Tournament Completed: {tournament['name']}",
            description="The tournament has concluded. Here are the final standings:",
            color=discord.Color.gold()
        )
        
        # Add link to standings
        embed.add_field(
            name="Final Standings",
            value="Use `/chess tournament standings " + tournament_id + "` to view the final standings.",
            inline=False
        )
        
        await interaction.followup.send(embed=embed)
        return
    
    # Advance to next round
    tournament["current_round"] += 1
    new_round = tournament["current_round"]
    
    # Generate pairings for the new round
    success = await generate_pairings(tournament_id, new_round)
    
    if not success:
        await interaction.followup.send(f"Failed to generate pairings for round {new_round}.")
        return
    
    # Save data
    save_data(TOURNAMENTS_FILE, tournaments)
    
    # Create embed
    embed = discord.Embed(
        title=f"Round {new_round} Started: {tournament['name']}",
        description=f"Round {new_round} pairings have been generated.",
        color=discord.Color.green()
    )
    
    embed.add_field(
        name="View Pairings",
        value="Use `/chess tournament matches " + tournament_id + "` to view the pairings for this round.",
        inline=False
    )
    
    await interaction.followup.send(embed=embed)

# Match Info Command
async def match_info_command(interaction: discord.Interaction, match_id: str):
    """Show detailed information about a match"""
    await interaction.response.defer()
    
    if match_id not in matches["matches"]:
        await interaction.followup.send(f"Match with ID {match_id} not found.")
        return
    
    match = matches["matches"][match_id]
    
    # Get tournament info if available
    tournament_name = "Unknown Tournament"
    if "tournament_id" in match and match["tournament_id"] in tournaments["tournaments"]:
        tournament_name = tournaments["tournaments"][match["tournament_id"]]["name"]
    
    # Create embed
    embed = discord.Embed(
        title=f"Match: {match['player1_name']} vs {match['player2_name']}",
        description=f"Tournament: {tournament_name}, Round {match['round']}",
        color=discord.Color.blue()
    )
    
    # Match status
    status_text = match["status"]
    if match["status"] == "Completed":
        if match["result"] == "player1":
            status_text = f"Completed - {match['player1_name']} won"
        elif match["result"] == "player2":
            status_text = f"Completed - {match['player2_name']} won"
        elif match["result"] == "draw":
            status_text = "Completed - Draw"
    
    embed.add_field(name="Status", value=status_text, inline=True)
    
    # Match dates
    created_at = match["created_at"]
    embed.add_field(name="Created", value=created_at, inline=True)
    
    if "completed_at" in match and match["completed_at"]:
        embed.add_field(name="Completed", value=match["completed_at"], inline=True)
    
    # Move history
    if "moves" in match and match["moves"]:
        move_history = " ".join(match["moves"])
        if len(move_history) > 1024:  # Discord field value limit
            move_history = move_history[-1020:] + "..."
        embed.add_field(name="Move History", value=f"```{move_history}```", inline=False)
    
    # Match ID
    embed.add_field(name="Match ID", value=match_id, inline=False)
    
    # Add buttons for actions
    class MatchInfoView(discord.ui.View):
        def __init__(self, match_id):
            super().__init__(timeout=180)
            self.match_id = match_id
        
        @discord.ui.button(label="Create Match Ticket", style=discord.ButtonStyle.primary)
        async def create_ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            # Check if user has permission or is a player in the match
            user_id = str(interaction.user.id)
            has_permission = False
            
            for role in interaction.user.roles:
                if role.name in ["Tournament Director", "Moderator", "Arbiter"]:
                    has_permission = True
                    break
            
            is_player = (user_id == match["player1_id"] or user_id == match["player2_id"])
            
            if not has_permission and not is_player:
                await interaction.response.send_message("You don't have permission to create a match ticket.", ephemeral=True)
                return
            
            # Check if ticket already exists
            ticket_exists = False
            for ticket_id, ticket in tickets["tickets"].items():
                if ticket["match_id"] == self.match_id:
                    ticket_exists = True
                    
                    # Try to get the channel
                    channel = interaction.guild.get_channel(int(ticket["channel_id"]))
                    
                    if channel:
                        await interaction.response.send_message(f"A match ticket already exists: {channel.mention}", ephemeral=True)
                    else:
                        await interaction.response.send_message("A match ticket already exists but the channel could not be found.", ephemeral=True)
                    
                    return
            
            # Create the ticket
            channel = await MatchTicketSystem.create_match_ticket(interaction.guild, self.match_id)
            
            if channel:
                await interaction.response.send_message(f"Match ticket created: {channel.mention}", ephemeral=True)
            else:
                await interaction.response.send_message("Failed to create match ticket.", ephemeral=True)
        
        @discord.ui.button(label="Report Result", style=discord.ButtonStyle.success)
        async def report_result_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            # Check if match is already completed
            if match["status"] == "Completed":
                await interaction.response.send_message("This match is already completed.", ephemeral=True)
                return
            
            # Check if user has permission or is a player in the match
            user_id = str(interaction.user.id)
            has_permission = False
            
            for role in interaction.user.roles:
                if role.name in ["Tournament Director", "Moderator", "Arbiter"]:
                    has_permission = True
                    break
            
            is_player = (user_id == match["player1_id"] or user_id == match["player2_id"])
            
            if not has_permission and not is_player:
                await interaction.response.send_message("You don't have permission to report match results.", ephemeral=True)
                return
            
            # Create result reporting view
            class ResultReportView(discord.ui.View):
                def __init__(self, match_id):
                    super().__init__(timeout=180)
                    self.match_id = match_id
                
                @discord.ui.button(label=f"{match['player1_name']} Won", style=discord.ButtonStyle.primary)
                async def player1_won_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                    await report_match_result(interaction, self.match_id, "player1")
                
                @discord.ui.button(label="Draw", style=discord.ButtonStyle.secondary)
                async def draw_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                    await report_match_result(interaction, self.match_id, "draw")
                
                @discord.ui.button(label=f"{match['player2_name']} Won", style=discord.ButtonStyle.primary)
                async def player2_won_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                    await report_match_result(interaction, self.match_id, "player2")
            
            await interaction.response.send_message("Please select the match result:", view=ResultReportView(self.match_id), ephemeral=True)
    
    view = MatchInfoView(match_id)
    
    await interaction.followup.send(embed=embed, view=view)

async def report_match_result(interaction: discord.Interaction, match_id: str, result: str):
    """Report the result of a match"""
    if match_id not in matches["matches"]:
        await interaction.response.send_message("Match not found.", ephemeral=True)
        return
    
    match = matches["matches"][match_id]
    
    # Update match status
    match["status"] = "Completed"
    match["result"] = result
    match["completed_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    match["reported_by"] = str(interaction.user.id)
    

    # Update player stats
    player1_id = match["player1_id"]
    player2_id = match["player2_id"]
    
    # Skip updating stats for bye matches
    if player2_id != "BYE":
        # Update player1 stats
        if player1_id in players["players"]:
            if match_id not in players["players"][player1_id]["matches"]:
                players["players"][player1_id]["matches"].append(match_id)
            
            if result == "player1":
                players["players"][player1_id]["wins"] += 1
            elif result == "player2":
                players["players"][player1_id]["losses"] += 1
            elif result == "draw":
                players["players"][player1_id]["draws"] += 1
        
        # Update player2 stats
        if player2_id in players["players"]:
            if match_id not in players["players"][player2_id]["matches"]:
                players["players"][player2_id]["matches"].append(match_id)
            
            if result == "player2":
                players["players"][player2_id]["wins"] += 1
            elif result == "player1":
                players["players"][player2_id]["losses"] += 1
            elif result == "draw":
                players["players"][player2_id]["draws"] += 1
    
    # Save data
    save_data(MATCHES_FILE, matches)
    save_data(PLAYERS_FILE, players)
    
    # Create result message
    if result == "player1":
        result_text = f"**{match['player1_name']}** won against {match['player2_name']}"
    elif result == "player2":
        result_text = f"**{match['player2_name']}** won against {match['player1_name']}"
    else:
        result_text = f"**{match['player1_name']}** and **{match['player2_name']}** drew"
    
    # Send confirmation
    await interaction.response.send_message(f"Match result reported: {result_text}", ephemeral=True)
    
    # Send announcement in the channel
    await interaction.channel.send(f"📢 Match result reported: {result_text}")
    
    # If this match has a ticket, update it
    for ticket_id, ticket in tickets["tickets"].items():
        if ticket["match_id"] == match_id:
            try:
                channel = interaction.guild.get_channel(int(ticket["channel_id"]))
                if channel:
                    await channel.send(f"📢 Match result reported: {result_text}")
                    
                    # Update ticket status
                    ticket["status"] = "Completed"
                    save_data(TICKETS_FILE, tickets)
                    
                    # Send closing message
                    await channel.send("This match ticket will be archived in 24 hours.")
            except:
                pass
            break

# Match Ticket System
class MatchTicketSystem:
    @staticmethod
    async def create_match_ticket(guild, match_id):
        """Create a new match ticket channel"""
        if match_id not in matches["matches"]:
            return None
        
        match = matches["matches"][match_id]
        
        # Check if a ticket already exists for this match
        for ticket_id, ticket in tickets["tickets"].items():
            if ticket["match_id"] == match_id:
                # Try to get the channel
                try:
                    channel = guild.get_channel(int(ticket["channel_id"]))
                    if channel:
                        return channel
                except:
                    pass
        
        # Get player information
        player1_id = match["player1_id"]
        player2_id = match["player2_id"]
        
        # Skip creating tickets for bye matches
        if player2_id == "BYE":
            return None
        
        player1_name = match["player1_name"]
        player2_name = match["player2_name"]
        
        # Get tournament information
        tournament_name = "Unknown Tournament"
        if "tournament_id" in match and match["tournament_id"] in tournaments["tournaments"]:
            tournament_name = tournaments["tournaments"][match["tournament_id"]]["name"]
        
        # Create channel name
        channel_name = f"match-{player1_name.lower()}-vs-{player2_name.lower()}"
        channel_name = channel_name.replace(" ", "-")
        if len(channel_name) > 90:  # Discord channel name limit is 100 chars
            channel_name = channel_name[:90]
        
        # Find or create match tickets category
        category = None
        for cat in guild.categories:
            if cat.name == "Match Tickets":
                category = cat
                break
        
        if not category:
            try:
                # Create the category
                category = await guild.create_category("Match Tickets")
                
                # Set permissions for the category
                everyone_role = guild.default_role
                await category.set_permissions(everyone_role, read_messages=False)
                
                # Grant access to tournament staff
                for role in guild.roles:
                    if role.name in ["Tournament Director", "Moderator", "Arbiter"]:
                        await category.set_permissions(role, read_messages=True, send_messages=True, manage_messages=True)
            except Exception as e:
                print(f"Error creating category: {e}")
                return None
        
        try:
            # Create the channel
            channel = await guild.create_text_channel(
                name=channel_name,
                category=category,
                topic=f"Match ticket for {player1_name} vs {player2_name} - Round {match['round']} of {tournament_name}"
            )
            
            # Set permissions for the players
            try:
                # Player 1
                player1_member = await guild.fetch_member(int(player1_id))
                await channel.set_permissions(player1_member, read_messages=True, send_messages=True)
            except:
                pass
            
            try:
                # Player 2
                player2_member = await guild.fetch_member(int(player2_id))
                await channel.set_permissions(player2_member, read_messages=True, send_messages=True)
            except:
                pass
            
            # Create ticket record
            ticket_id = generate_id("T")
            
            tickets["tickets"][ticket_id] = {
                "id": ticket_id,
                "match_id": match_id,
                "channel_id": str(channel.id),
                "status": "Open",
                "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            save_data(TICKETS_FILE, tickets)
            
            # Send welcome message
            embed = discord.Embed(
                title=f"Match: {player1_name} vs {player2_name}",
                description=f"Welcome to your match ticket for Round {match['round']} of {tournament_name}.",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="Instructions",
                value=(
                    "1. Use this channel to coordinate your match.\n"
                    "2. Share your chess.com/lichess username if needed.\n"
                    "3. Agree on a time to play.\n"
                    "4. After the match, report the result using the buttons below.\n"
                    "5. If you need assistance, use the 'Call Arbiter' button."
                ),
                inline=False
            )
            
            embed.add_field(name="Match ID", value=match_id, inline=True)
            embed.add_field(name="Round", value=str(match["round"]), inline=True)
            
            # Create match control panel
            match_panel = MatchControlPanel(match_id)
            
            await channel.send(
                f"<@{player1_id}> <@{player2_id}> Welcome to your match ticket!",
                embed=embed,
                view=match_panel
            )
            
            return channel
            
        except Exception as e:
            print(f"Error creating match ticket: {e}")
            return None

# Setup function to register commands
def setup(bot):
    # Create a command group for chess commands
    chess_group = app_commands.Group(name="chess", description="Chess tournament commands")
    
    # Tournament management commands
    chess_group.add_command(app_commands.Command(
        name="tournament",
        description="Create a new chess tournament",
        callback=create_tournament_command
    ))
    
    chess_group.add_command(app_commands.Command(
        name="tournaments",
        description="List all chess tournaments",
        callback=list_tournaments_command
    ))
    
    chess_group.add_command(app_commands.Command(
        name="tournament_info",
        description="Show detailed information about a tournament",
        callback=tournament_info_command
    ))
    
    chess_group.add_command(app_commands.Command(
        name="tournament_players",
        description="Show players registered for a tournament",
        callback=tournament_players_command
    ))
    
    chess_group.add_command(app_commands.Command(
        name="tournament_standings",
        description="Show current standings for a tournament",
        callback=tournament_standings_command
    ))
    
    chess_group.add_command(app_commands.Command(
        name="tournament_matches",
        description="Show matches for a tournament",
        callback=tournament_matches_command
    ))
    
    chess_group.add_command(app_commands.Command(
        name="start_tournament",
        description="Start a chess tournament",
        callback=start_tournament_command
    ))
    
    chess_group.add_command(app_commands.Command(
        name="next_round",
        description="Start the next round of a tournament",
        callback=next_round_command
    ))
    
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
    
    # Match commands
    chess_group.add_command(app_commands.Command(
        name="match",
        description="Show detailed information about a match",
        callback=match_info_command
    ))
    
    # Add the group to the command tree
    bot.tree.add_command(chess_group)
    
    # Initialize data files
    load_data()
    
    # Log setup
    print("Chess tournament commands registered as group")
