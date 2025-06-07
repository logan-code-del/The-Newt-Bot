# chess_activity.py - Discord Activity integration for chess games
import discord
import json
import os
import random
import datetime
import asyncio
from discord import app_commands

# Constants for Discord Activity
CHESS_ACTIVITY_ID = "832012774040141894"  # Discord's Chess in the Park activity ID

class ChessActivityManager:
    def __init__(self, bot):
        self.bot = bot
        self.active_games = {}  # Store active game sessions
        self.match_channels = {}  # Map match_ids to channels
    
    async def create_chess_activity(self, match_id, player1_id, player2_id, tournament_id=None):
        """Create a new chess activity for a match"""
        try:
            # Get player objects - with better error handling
            guild = None
            
            # Find a guild where both players are members
            for g in self.bot.guilds:
                try:
                    # Try to get both members from this guild
                    player1 = await g.fetch_member(int(player1_id))
                    player2 = await g.fetch_member(int(player2_id))
                    
                    if player1 and player2:
                        guild = g
                        break
                except discord.errors.NotFound:
                    # One or both members not in this guild, try the next one
                    continue
            
            # If we couldn't find both players in any guild
            if not guild:
                # Try to get player names from the match data
                import chess_commands
                player1_name = "Player 1"
                player2_name = "Player 2"
                
                if match_id in chess_commands.matches["matches"]:
                    match = chess_commands.matches["matches"][match_id]
                    player1_name = match.get("player1_name", "Player 1")
                    player2_name = match.get("player2_name", "Player 2")
                
                return False, f"Could not find players in any shared server. Make sure both {player1_name} and {player2_name} are in the same server as the bot."
            
            # Create or get the live games channel
            live_games_channel = None
            for channel in guild.text_channels:
                if channel.name == "live-games":
                    live_games_channel = channel
                    break
            
            if not live_games_channel:
                # Create the channel if it doesn't exist
                try:
                    # Find the Tournament category
                    tournament_category = None
                    for category in guild.categories:
                        if category.name == "Tournament":
                            tournament_category = category
                            break
                    
                    if not tournament_category:
                        # Create the category if it doesn't exist
                        tournament_category = await guild.create_category("Tournament")
                    
                    # Create the live-games channel
                    live_games_channel = await guild.create_text_channel(
                        "live-games", 
                        category=tournament_category,
                        topic="Watch ongoing chess matches in the tournament"
                    )
                except Exception as e:
                    return False, f"Failed to create live-games channel: {str(e)}"
            
            # Store the channel for this match
            self.match_channels[match_id] = live_games_channel.id
            
            # Create an invite to the activity
            try:
                invite = await live_games_channel.create_invite(
                    max_age=86400,  # 24 hours
                    max_uses=0,
                    target_application_id=CHESS_ACTIVITY_ID,
                    target_type=discord.InviteTarget.embedded_application
                )
            except Exception as e:
                return False, f"Failed to create activity invite: {str(e)}"
            
            # Store the active game
            self.active_games[match_id] = {
                "player1_id": player1_id,
                "player2_id": player2_id,
                "tournament_id": tournament_id,
                "channel_id": live_games_channel.id,
                "invite_url": invite.url,
                "started_at": datetime.datetime.now().isoformat(),
                "status": "Active"
            }
            
            # Create an embed for the live-games channel
            embed = discord.Embed(
                title=f"Chess Match: {player1.display_name} vs {player2.display_name}",
                description=f"A chess match has been started for tournament match ID: {match_id}",
                color=discord.Color.blue()
            )
            
            embed.add_field(name="How to Join", value=f"Click the link below to join the chess game directly in Discord!", inline=False)
            embed.add_field(name="Match ID", value=match_id, inline=True)
            
            if tournament_id:
                embed.add_field(name="Tournament", value=tournament_id, inline=True)
            
            embed.add_field(name="Started At", value=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), inline=True)
            
            # Send the embed to the live-games channel
            try:
                message = await live_games_channel.send(
                    content=f"{player1.mention} {player2.mention} Your chess match is ready!",
                    embed=embed
                )
                
                # Add the invite button
                view = discord.ui.View()
                view.add_item(discord.ui.Button(label="Join Chess Game", url=invite.url, style=discord.ButtonStyle.url))
                await message.edit(view=view)
            except Exception as e:
                print(f"Error sending match message: {e}")
                # Continue even if this fails
            
            # DM both players with the invite
            try:
                dm_embed = discord.Embed(
                    title=f"Your Chess Match is Ready!",
                    description=f"You have been paired against {player2.display_name if player1_id == player1.id else player1.display_name} for a chess match.",
                    color=discord.Color.green()
                )
                
                dm_embed.add_field(name="How to Join", value=f"Click the button below to join the chess game directly in Discord!", inline=False)
                dm_embed.add_field(name="Match ID", value=match_id, inline=True)
                
                if tournament_id:
                    dm_embed.add_field(name="Tournament", value=tournament_id, inline=True)
                
                dm_view = discord.ui.View()
                dm_view.add_item(discord.ui.Button(label="Join Chess Game", url=invite.url, style=discord.ButtonStyle.url))
                
                try:
                    await player1.send(embed=dm_embed, view=dm_view)
                except:
                    print(f"Could not DM player 1 ({player1.display_name})")
                
                try:
                    await player2.send(embed=dm_embed, view=dm_view)
                except:
                    print(f"Could not DM player 2 ({player2.display_name})")
            except Exception as e:
                print(f"Error sending DMs: {e}")
                # Continue even if DMs fail
            
            return True, invite.url
            
        except Exception as e:
            import traceback
            traceback_str = traceback.format_exc()
            print(f"Chess activity error: {traceback_str}")
            return False, f"Failed to create chess activity: {str(e)}"
    
    async def end_chess_activity(self, match_id, winner_id=None, result="draw"):
        """End a chess activity and record the result"""
        if match_id not in self.active_games:
            return False, "Match not found"
        
        game = self.active_games[match_id]
        
        # Update the game status
        game["status"] = "Completed"
        game["ended_at"] = datetime.datetime.now().isoformat()
        
        if winner_id:
            game["winner_id"] = winner_id
            
            # Determine the result
            if winner_id == game["player1_id"]:
                game["result"] = "player1"
            elif winner_id == game["player2_id"]:
                game["result"] = "player2"
            else:
                game["result"] = result
        else:
            game["result"] = result
        
        # Try to update the match in the tournament system
        try:
            # Import the chess_commands module to access the tournament data
            import chess_commands
            
            # Find the match in the matches data
            if match_id in chess_commands.matches["matches"]:
                match = chess_commands.matches["matches"][match_id]
                
                # Update match status
                match["status"] = "Completed"
                match["result"] = game["result"]
                match["completed_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Update player stats
                player1_id = match["player1_id"]
                player2_id = match["player2_id"]
                
                # Skip updating stats for bye matches
                if player2_id != "BYE":
                    # Update player1 stats
                    if player1_id in chess_commands.players["players"]:
                        if match_id not in chess_commands.players["players"][player1_id]["matches"]:
                            chess_commands.players["players"][player1_id]["matches"].append(match_id)
                        
                        if game["result"] == "player1":
                            chess_commands.players["players"][player1_id]["wins"] += 1
                        elif game["result"] == "player2":
                            chess_commands.players["players"][player1_id]["losses"] += 1
                        elif game["result"] == "draw":
                            chess_commands.players["players"][player1_id]["draws"] += 1
                    
                    # Update player2 stats
                    if player2_id in chess_commands.players["players"]:
                        if match_id not in chess_commands.players["players"][player2_id]["matches"]:
                            chess_commands.players["players"][player2_id]["matches"].append(match_id)
                        
                        if game["result"] == "player2":
                            chess_commands.players["players"][player2_id]["wins"] += 1
                        elif game["result"] == "player1":
                            chess_commands.players["players"][player2_id]["losses"] += 1
                        elif game["result"] == "draw":
                            chess_commands.players["players"][player2_id]["draws"] += 1
                
                # Save data
                chess_commands.save_data(chess_commands.MATCHES_FILE, chess_commands.matches)
                chess_commands.save_data(chess_commands.PLAYERS_FILE, chess_commands.players)
                
                # Try to send a message to the channel
                if match_id in self.match_channels:
                    try:
                        channel_id = self.match_channels[match_id]
                        channel = self.bot.get_channel(channel_id)
                        
                        if channel:
                            # Create result message
                            if game["result"] == "player1":
                                result_text = f"**{match['player1_name']}** won against {match['player2_name']}"
                            elif game["result"] == "player2":
                                result_text = f"**{match['player2_name']}** won against {match['player1_name']}"
                            else:
                                result_text = f"**{match['player1_name']}** and **{match['player2_name']}** drew"
                            
                            await channel.send(f"📢 Match result recorded: {result_text}")
                    except:
                        pass
        except Exception as e:
            return False, f"Failed to update tournament data: {str(e)}"
        
        return True, "Chess activity ended and results recorded"

# Command to start a chess game for a match
async def start_chess_game(interaction: discord.Interaction, match_id: str):
    """Start a chess game for a match"""
    await interaction.response.defer()
    
    # Import chess_commands to access match data
    import chess_commands
    
    # Check if the match exists
    if match_id not in chess_commands.matches["matches"]:
        await interaction.followup.send("Match not found.")
        return
    
    match = chess_commands.matches["matches"][match_id]
    
    # Check if match is already completed
    if match["status"] == "Completed":
        await interaction.followup.send("This match is already completed.")
        return
    
    # Check if user has permission or is a player in the match
    user_id = str(interaction.user.id)
    is_player = (user_id == match["player1_id"] or user_id == match["player2_id"])
    
    has_permission = False
    for role in interaction.user.roles:
        if role.name in ["Tournament Director", "Moderator", "Arbiter"]:
            has_permission = True
            break
    
    if not is_player and not has_permission:
        await interaction.followup.send("Only players in this match or tournament staff can start the chess game.", ephemeral=True)
        return
    
    # Get the chess activity manager
    if not hasattr(interaction.client, "chess_activity_manager"):
        interaction.client.chess_activity_manager = ChessActivityManager(interaction.client)
    
    # Create the chess activity
    success, result = await interaction.client.chess_activity_manager.create_chess_activity(
        match_id,
        match["player1_id"],
        match["player2_id"],
        match.get("tournament_id")
    )
    
    if success:
        await interaction.followup.send(f"Chess game created! Players have been notified and can join using this link: {result}")
    else:
        await interaction.followup.send(f"Failed to create chess game: {result}")

# Command to report the result of a chess game
async def report_chess_result(interaction: discord.Interaction, match_id: str, result: str):
    """Report the result of a chess game"""
    await interaction.response.defer(ephemeral=True)
    
    # Import chess_commands to access match data
    import chess_commands
    
    # Check if the match exists
    if match_id not in chess_commands.matches["matches"]:
        await interaction.followup.send("Match not found.")
        return
    
    match = chess_commands.matches["matches"][match_id]
    
    # Check if match is already completed
    if match["status"] == "Completed":
        await interaction.followup.send("This match is already completed.")
        return
    
    # Check if user has permission or is a player in the match
    user_id = str(interaction.user.id)
    is_player = (user_id == match["player1_id"] or user_id == match["player2_id"])
    
    has_permission = False
    for role in interaction.user.roles:
        if role.name in ["Tournament Director", "Moderator", "Arbiter"]:
            has_permission = True
            break
    
    if not is_player and not has_permission:
        await interaction.followup.send("Only players in this match or tournament staff can report results.", ephemeral=True)
        return
    
    # Validate result
    valid_results = ["player1", "player2", "draw"]
    if result not in valid_results:
        await interaction.followup.send(f"Invalid result. Must be one of: {', '.join(valid_results)}")
        return
    
    # Get the chess activity manager
    if not hasattr(interaction.client, "chess_activity_manager"):
        interaction.client.chess_activity_manager = ChessActivityManager(interaction.client)
    
    # Determine winner ID
    winner_id = None
    if result == "player1":
        winner_id = match["player1_id"]
    elif result == "player2":
        winner_id = match["player2_id"]
    
    # End the chess activity
    success, message = await interaction.client.chess_activity_manager.end_chess_activity(
        match_id,
        winner_id,
        result
    )
    
    if success:
        await interaction.followup.send("Match result recorded successfully!")
    else:
        await interaction.followup.send(f"Failed to record match result: {message}")

# Setup function to register commands
def setup(bot):
    # Create a chess activity manager
    bot.chess_activity_manager = ChessActivityManager(bot)
    
    # Add commands to the chess group
    chess_group = None
    for command in bot.tree.get_commands():
        if command.name == "chess":
            chess_group = command
            break
    
    if chess_group:
        # Add the start chess game command
        chess_group.add_command(app_commands.Command(
            name="play",
            description="Start a chess game for a match",
            callback=start_chess_game
        ))
        
        # Add the report result command
        chess_group.add_command(app_commands.Command(
            name="report",
            description="Report the result of a chess game",
            callback=report_chess_result
        ))
    
    # Log setup
    print("Chess activity integration registered")

# Add a button to start a chess game in the match control panel
class ChessGameButton(discord.ui.Button):
    def __init__(self, match_id):
        super().__init__(
            label="Play Chess in Discord",
            style=discord.ButtonStyle.primary,
            emoji="♟️"
        )
        self.match_id = match_id
    
    async def callback(self, interaction: discord.Interaction):
        """Start a chess game when the button is clicked"""
        # Import chess_commands to access match data
        import chess_commands
        
        # Check if the match exists
        if self.match_id not in chess_commands.matches["matches"]:
            await interaction.response.send_message("Match not found.", ephemeral=True)
            return
        
        match = chess_commands.matches["matches"][self.match_id]
        
        # Check if match is already completed
        if match["status"] == "Completed":
            await interaction.response.send_message("This match is already completed.", ephemeral=True)
            return
        
        # Check if user has permission or is a player in the match
        user_id = str(interaction.user.id)
        is_player = (user_id == match["player1_id"] or user_id == match["player2_id"])
        
        has_permission = False
        for role in interaction.user.roles:
            if role.name in ["Tournament Director", "Moderator", "Arbiter"]:
                has_permission = True
                break
        
        if not is_player and not has_permission:
            await interaction.response.send_message("Only players in this match or tournament staff can start the chess game.", ephemeral=True)
            return
        
        # Get the chess activity manager
        if not hasattr(interaction.client, "chess_activity_manager"):
            interaction.client.chess_activity_manager = ChessActivityManager(interaction.client)
        
        # Create the chess activity
        await interaction.response.defer()
        
        success, result = await interaction.client.chess_activity_manager.create_chess_activity(
            self.match_id,
            match["player1_id"],
            match["player2_id"],
            match.get("tournament_id")
        )
        
        if success:
            await interaction.followup.send(f"Chess game created! Players have been notified and can join using this link: {result}")
        else:
            await interaction.followup.send(f"Failed to create chess game: {result}")

# Add a listener for Discord Activity state changes
async def setup_activity_listeners(bot):
    """Set up listeners for Discord Activity state changes"""
    @bot.event
    async def on_presence_update(before, after):
        """Listen for presence updates to detect when chess games end"""
        # Check if the user was in a chess activity before
        was_in_chess = False
        for activity in before.activities:
            if activity.type == discord.ActivityType.playing and activity.name == "Chess in the Park":
                was_in_chess = True
                break
        
        # Check if the user is no longer in a chess activity
        now_in_chess = False
        for activity in after.activities:
            if activity.type == discord.ActivityType.playing and activity.name == "Chess in the Park":
                now_in_chess = True
                break
        
        # If the user left a chess activity, check if it was a tournament match
        if was_in_chess and not now_in_chess:
            # Get the chess activity manager
            if not hasattr(bot, "chess_activity_manager"):
                return
            
            # Check if this user is in any active games
            user_id = str(after.id)
            for match_id, game in bot.chess_activity_manager.active_games.items():
                if game["status"] == "Active" and (user_id == game["player1_id"] or user_id == game["player2_id"]):
                    # Ask the user for the result
                    try:
                        # Create an embed to ask for the result
                        embed = discord.Embed(
                            title="Chess Match Ended",
                            description="It looks like your chess match has ended. Please report the result:",
                            color=discord.Color.blue()
                        )
                        
                        # Create a view with buttons for the result
                        class ResultView(discord.ui.View):
                            def __init__(self, match_id, player1_id, player2_id):
                                super().__init__(timeout=3600)  # 1 hour timeout
                                self.match_id = match_id
                                self.player1_id = player1_id
                                self.player2_id = player2_id
                            
                            @discord.ui.button(label="I Won", style=discord.ButtonStyle.success)
                            async def i_won_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                                user_id = str(interaction.user.id)
                                
                                # Determine the result
                                result = "player1" if user_id == self.player1_id else "player2"
                                
                                # End the chess activity
                                success, message = await bot.chess_activity_manager.end_chess_activity(
                                    self.match_id,
                                    user_id,
                                    result
                                )
                                
                                if success:
                                    await interaction.response.send_message("Thank you! Your win has been recorded.")
                                else:
                                    await interaction.response.send_message(f"Failed to record result: {message}")
                                
                                # Disable all buttons
                                for item in self.children:
                                    item.disabled = True
                                
                                await interaction.message.edit(view=self)
                            
                            @discord.ui.button(label="Draw", style=discord.ButtonStyle.secondary)
                            async def draw_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                                # End the chess activity
                                success, message = await bot.chess_activity_manager.end_chess_activity(
                                    self.match_id,
                                    None,
                                    "draw"
                                )
                                
                                if success:
                                    await interaction.response.send_message("Thank you! The draw has been recorded.")
                                else:
                                    await interaction.response.send_message(f"Failed to record result: {message}")
                                
                                # Disable all buttons
                                for item in self.children:
                                    item.disabled = True
                                
                                await interaction.message.edit(view=self)
                            
                            @discord.ui.button(label="I Lost", style=discord.ButtonStyle.danger)
                            async def i_lost_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                                user_id = str(interaction.user.id)
                                
                                # Determine the winner
                                winner_id = self.player2_id if user_id == self.player1_id else self.player1_id
                                
                                # Determine the result
                                result = "player2" if user_id == self.player1_id else "player1"
                                
                                # End the chess activity
                                success, message = await bot.chess_activity_manager.end_chess_activity(
                                    self.match_id,
                                    winner_id,
                                    result
                                )
                                
                                if success:
                                    await interaction.response.send_message("Thank you! Your loss has been recorded.")
                                else:
                                    await interaction.response.send_message(f"Failed to record result: {message}")
                                
                                # Disable all buttons
                                for item in self.children:
                                    item.disabled = True
                                
                                await interaction.message.edit(view=self)
                        
                        # Send the message to the user
                        view = ResultView(match_id, game["player1_id"], game["player2_id"])
                        await after.send(embed=embed, view=view)
                    except:
                        # Continue even if DM fails
                        pass

# Function to modify the MatchControlPanel to include the chess game button
def add_chess_button_to_match_panel():
    """Add the chess game button to the match control panel"""
    import chess_commands
    
    # Check if MatchControlPanel exists
    if not hasattr(chess_commands, 'MatchControlPanel'):
        print("Warning: MatchControlPanel not found in chess_commands module. Chess button will not be added to match panels.")
        return
    
    try:
        # Store the original __init__ method
        original_init = chess_commands.MatchControlPanel.__init__
        
        # Define a new __init__ method that adds our button
        def new_init(self, match_id):
            original_init(self, match_id)
            self.add_item(ChessGameButton(match_id))
        
        # Replace the original __init__ method
        chess_commands.MatchControlPanel.__init__ = new_init
        print("Successfully added chess button to match control panel")
    except Exception as e:
        print(f"Error adding chess button to match control panel: {e}")

# Function to initialize the chess activity system
def initialize(bot):
    """Initialize the chess activity system"""
    try:
        # Create the chess activity manager
        bot.chess_activity_manager = ChessActivityManager(bot)
        
        # Set up activity listeners
        asyncio.create_task(setup_activity_listeners(bot))
        
        # Try to add the chess button to match panels
        add_chess_button_to_match_panel()
        
        # Log initialization
        print("Chess activity system initialized")
    except Exception as e:
        print(f"Error initializing chess activity system: {e}")
        # Continue anyway to not block the bot from starting
