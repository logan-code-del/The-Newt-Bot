# bot.py
import os
import sys
import time
import json
import datetime
import asyncio
import discord
import pnw_commands
from discord import app_commands
from discord.ext import commands

# Ensure data directory exists
os.makedirs('data', exist_ok=True)

# Settings file path
SETTINGS_FILE = 'data/settings.json'

# Function to load settings
def load_settings():
    try:
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Default settings
        default_settings = {
            'guilds': {}  # Store guild-specific settings here
        }
        save_settings(default_settings)
        return default_settings

# Function to save settings
def save_settings(settings):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=4)

# Load settings
settings = load_settings()

# Set up intents
intents = discord.Intents.default()
intents.message_content = True  # Enable message content intent

# Create bot with intents
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# Get token from environment variable (GitHub Actions sets this from secrets)
TOKEN = os.environ.get('BOT_TOKEN')

# Set a maximum runtime for GitHub Actions (slightly less than the 6-hour limit)
MAX_RUNTIME = 350 * 60  # 350 minutes in seconds
start_time = time.time()

# Background task to check runtime and exit gracefully
async def check_runtime():
    """Check if the bot has been running too long and exit if needed"""
    await bot.wait_until_ready()
    while not bot.is_closed():
        current_runtime = time.time() - start_time
        
        # Log current status every hour
        if int(current_runtime) % 3600 < 10:  # Log within first 10 seconds of each hour
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{current_time}] Bot running for {int(current_runtime/60)} minutes")
            
            # Log to file
            with open('data/bot_log.txt', 'a') as f:
                f.write(f'[{current_time}] Bot running for {int(current_runtime/60)} minutes\n')
        
        # If we're approaching the GitHub Actions timeout, exit gracefully
        if current_runtime >= MAX_RUNTIME:
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{current_time}] Maximum runtime reached ({MAX_RUNTIME/60} minutes). Shutting down...")
            
            # Log to file
            with open('data/bot_log.txt', 'a') as f:
                f.write(f'[{current_time}] Maximum runtime reached. Shutting down...\n')
                
            # Exit the script - GitHub Actions will restart it according to schedule
            await bot.close()
            sys.exit(0)
            
        await asyncio.sleep(10)  # Check every 10 seconds

@bot.event
async def setup_hook():
    """This is called when the bot starts, before it connects to Discord"""
    # Start the runtime check task
    bot.loop.create_task(check_runtime())
    
    # Register Politics & War commands
    pnw_commands.setup(bot)
    
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{current_time}] Bot is setting up...")
    
    # Log to file
    with open('data/bot_log.txt', 'a') as f:
        f.write(f'[{current_time}] Bot is setting up...\n')
@bot.event
async def on_ready():
    """Called when the bot is ready and connected to Discord"""
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f'[{current_time}] {bot.user} has connected to Discord!')
    print(f'[{current_time}] Bot is in {len(bot.guilds)} servers')
    
    # Sync commands with Discord
    try:
        synced = await bot.tree.sync()
        print(f'[{current_time}] Synced {len(synced)} command(s)')
    except Exception as e:
        print(f'[{current_time}] Failed to sync commands: {e}')
    
    # Set bot status
    await bot.change_presence(activity=discord.Game(name="Use /help for commands"))
    
    # Log to a file that can be accessed in GitHub Actions logs
    with open('data/bot_log.txt', 'a') as f:
        f.write(f'[{current_time}] Bot started successfully\n')

@bot.event
async def on_guild_join(guild):
    """Called when the bot joins a new guild"""
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f'[{current_time}] Joined new guild: {guild.name} (ID: {guild.id})')
    
    # Initialize settings for this guild
    guild_id = str(guild.id)
    if guild_id not in settings['guilds']:
        settings['guilds'][guild_id] = {
            'joined_at': datetime.datetime.now().isoformat(),
            'name': guild.name,
            'member_count': guild.member_count
        }
        save_settings(settings)
    
    # Log to file
    with open('data/bot_log.txt', 'a') as f:
        f.write(f'[{current_time}] Joined new guild: {guild.name} (ID: {guild.id})\n')
    
    # Sync commands with the new guild
    try:
        await bot.tree.sync(guild=guild)
    except Exception as e:
        print(f'[{current_time}] Failed to sync commands to new guild: {e}')

# Settings command group
@bot.tree.command(name="settings", description="View or change bot settings")
@app_commands.default_permissions(administrator=True)
async def settings_cmd(interaction: discord.Interaction):
    """View current settings for this server"""
    guild_id = str(interaction.guild.id)
    
    # Get guild settings or initialize if not exists
    if guild_id not in settings['guilds']:
        settings['guilds'][guild_id] = {
            'joined_at': datetime.datetime.now().isoformat(),
            'name': interaction.guild.name,
            'member_count': interaction.guild.member_count,
            'settings_viewed': 0
        }
    
    # Update settings viewed count
    if 'settings_viewed' in settings['guilds'][guild_id]:
        settings['guilds'][guild_id]['settings_viewed'] += 1
    else:
        settings['guilds'][guild_id]['settings_viewed'] = 1
    
    save_settings(settings)
    
    # Create embed with settings info
    embed = discord.Embed(
        title="Server Settings",
        description="Current settings for this server",
        color=discord.Color.blue()
    )
    
    guild_settings = settings['guilds'][guild_id]
    
    # Add fields for each setting
    embed.add_field(name="Server Name", value=interaction.guild.name, inline=True)
    embed.add_field(name="Server ID", value=guild_id, inline=True)
    embed.add_field(name="Member Count", value=str(interaction.guild.member_count), inline=True)
    
    if 'joined_at' in guild_settings:
        try:
            joined_date = datetime.datetime.fromisoformat(guild_settings['joined_at'])
            embed.add_field(name="Bot Joined", value=joined_date.strftime("%Y-%m-%d"), inline=True)
        except (ValueError, TypeError):
            embed.add_field(name="Bot Joined", value="Unknown", inline=True)
    
    embed.add_field(name="Settings Viewed", value=str(guild_settings.get('settings_viewed', 1)), inline=True)
    
    # Add customization info
    embed.add_field(
        name="Customization",
        value="Use the settings subcommands to customize the bot for your server.",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

# Slash Commands
@bot.tree.command(name="help", description="Show available commands")
async def help_command(interaction: discord.Interaction):
    """Shows the help message with all available commands"""
    embed = discord.Embed(
        title="Bot Commands",
        description="Here are all the available slash commands:",
        color=discord.Color.blue()
    )
    
    # Basic commands
    embed.add_field(
        name="Basic Commands",
        value=(
            "`/test` - Test if the bot is responding\n"
            "`/hello` - Get a friendly greeting\n"
            "`/ping` - Check the bot's latency"
        ),
        inline=False
    )
    
    # Info commands
    embed.add_field(
        name="Information Commands",
        value=(
            "`/info` - Display information about the bot\n"
            "`/serverinfo` - Display information about the server\n"
            "`/userinfo [user]` - Display information about a user\n"
            "`/uptime` - Check how long the bot has been running\n"
            "`/settings` - View server settings"
        ),
        inline=False
    )
    
    # Politics & War commands
    embed.add_field(
        name="Politics & War Commands",
        value=(
            "`/pnw_nation [nation_name]` - Look up a nation\n"
            "`/pnw_alliance [alliance_name]` - Look up an alliance\n"
            "`/pnw_wars [nation_name]` - Look up active wars for a nation\n"
            "`/pnw_city [nation_name] [city_name]` - Look up city information\n"
            "`/pnw_prices` - Check current trade prices\n"
            "`/pnw_bank [nation_name]` - View a nation's bank\n"
            "`/pnw_radiation` - Check global radiation levels\n"
            "`/pnw_setapikey [api_key]` - Set your P&W API key (admin only)"
        ),
        inline=False
    )
    
    embed.set_footer(text="Bot will restart every 6 hours via GitHub Actions")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="test", description="Test if the bot is responding")
async def test(interaction: discord.Interaction):
    """Simple test command to check if the bot is working"""
    await interaction.response.send_message('Test command works!')

@bot.tree.command(name="hello", description="Get a friendly greeting")
async def hello(interaction: discord.Interaction):
    """Greets the user who invoked the command"""
    # Track command usage in settings
    guild_id = str(interaction.guild.id)
    if guild_id in settings['guilds']:
        if 'hello_count' in settings['guilds'][guild_id]:
            settings['guilds'][guild_id]['hello_count'] += 1
        else:
            settings['guilds'][guild_id]['hello_count'] = 1
        save_settings(settings)
    
    await interaction.response.send_message(f'Hello, {interaction.user.mention}!')

@bot.tree.command(name="info", description="Display information about the bot")
async def info(interaction: discord.Interaction):
    """Shows information about the bot"""
    # Calculate uptime
    uptime = int(time.time() - start_time)
    hours, remainder = divmod(uptime, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{hours}h {minutes}m {seconds}s"
    
    # Count total servers in settings
    total_tracked_servers = len(settings['guilds'])
    
    embed = discord.Embed(
        title="Bot Information",
        description="A simple Discord bot created with discord.py",
        color=discord.Color.blue()
    )
    embed.add_field(name="Creator", value="Your Name", inline=True)
    embed.add_field(name="Server Count", value=f"{len(bot.guilds)}", inline=True)
    embed.add_field(name="Tracked Servers", value=f"{total_tracked_servers}", inline=True)
    embed.add_field(name="Framework", value="discord.py", inline=True)
    embed.add_field(name="Current Uptime", value=uptime_str, inline=True)
    embed.add_field(name="Hosted via", value="GitHub Actions", inline=True)
    embed.set_footer(text="Bot will restart every 6 hours via GitHub Actions")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="ping", description="Check the bot's latency")
async def ping(interaction: discord.Interaction):
    """Displays the bot's latency"""
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f'Pong! Latency: {latency}ms')

@bot.tree.command(name="serverinfo", description="Display information about the server")
async def serverinfo(interaction: discord.Interaction):
    """Shows information about the current server"""
    server = interaction.guild
    guild_id = str(server.id)
    
    # Count text and voice channels
    text_channels = len(server.text_channels)
    voice_channels = len(server.voice_channels)
    
    # Get server creation date
    created_at = server.created_at.strftime("%B %d, %Y")
    
    # Get guild stats from settings
    if guild_id in settings['guilds']:
        hello_count = settings['guilds'][guild_id].get('hello_count', 0)
        settings_viewed = settings['guilds'][guild_id].get('settings_viewed', 0)
    else:
        hello_count = 0
        settings_viewed = 0
    
    # Create embed
    embed = discord.Embed(
        title=f"{server.name} Server Information",
        description=f"ID: {server.id}",
        color=discord.Color.green()
    )
    
    if server.icon:
        embed.set_thumbnail(url=server.icon.url)
        
    embed.add_field(name="Owner", value=server.owner.mention, inline=True)
    embed.add_field(name="Created On", value=created_at, inline=True)
    embed.add_field(name="Member Count", value=server.member_count, inline=True)
    embed.add_field(name="Channels", value=f"📝 {text_channels} | 🔊 {voice_channels}", inline=True)
    embed.add_field(name="Roles", value=len(server.roles), inline=True)
    embed.add_field(name="Emojis", value=len(server.emojis), inline=True)
    
    # Add bot usage stats
    embed.add_field(name="Bot Usage", value=f"Hello: {hello_count} | Settings: {settings_viewed}", inline=True)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="userinfo", description="Display information about a user")
async def userinfo(interaction: discord.Interaction, user: discord.Member = None):
    """Shows information about a user"""
    # If no member is specified, use the command author
    if user is None:
        user = interaction.user
        
    # Get join dates
    joined_at = user.joined_at.strftime("%B %d, %Y")
    created_at = user.created_at.strftime("%B %d, %Y")
    
    # Create embed
    embed = discord.Embed(
        title=f"User Information - {user.name}",
        color=user.color
    )
    
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.add_field(name="ID", value=user.id, inline=True)
    embed.add_field(name="Nickname", value=user.nick if user.nick else "None", inline=True)
    embed.add_field(name="Account Created", value=created_at, inline=True)
    embed.add_field(name="Joined Server", value=joined_at, inline=True)
    
    # Get the member's top role (highest in hierarchy)
    roles = [role.mention for role in reversed(user.roles) if role.name != "@everyone"]
    if roles:
        embed.add_field(name=f"Roles [{len(roles)}]", value=" ".join(roles) if len(" ".join(roles)) < 1024 else "Too many roles to display", inline=False)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="uptime", description="Check how long the bot has been running")
async def uptime(interaction: discord.Interaction):
    """Shows the current bot uptime"""
    uptime = int(time.time() - start_time)
    hours, remainder = divmod(uptime, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    # Calculate time until restart
    remaining = MAX_RUNTIME - uptime
    if remaining > 0:
        r_hours, r_remainder = divmod(remaining, 3600)
        r_minutes, r_seconds = divmod(r_remainder, 60)
        restart_msg = f"\nRestarting in approximately: {r_hours}h {r_minutes}m {r_seconds}s"
    else:
        restart_msg = "\nRestart imminent"
    
    # Track command usage
    guild_id = str(interaction.guild.id)
    if guild_id in settings['guilds']:
        if 'uptime_checks' in settings['guilds'][guild_id]:
            settings['guilds'][guild_id]['uptime_checks'] += 1
        else:
            settings['guilds'][guild_id]['uptime_checks'] = 1
        save_settings(settings)
    
    await interaction.response.send_message(f"Bot has been online for: **{hours}h {minutes}m {seconds}s**{restart_msg}")

# Custom settings commands
@bot.tree.command(name="theme", description="Set a custom theme color for the server")
@app_commands.describe(color="Color in hex format (e.g., #FF5733)")
@app_commands.default_permissions(administrator=True)
async def theme(interaction: discord.Interaction, color: str):
    """Set a custom theme color for the server"""
    # Validate color format
    if not color.startswith('#') or len(color) != 7:
        await interaction.response.send_message("Invalid color format. Please use hex format (e.g., #FF5733)", ephemeral=True)
        return
    
    try:
        # Try to convert to RGB to validate
        int(color[1:], 16)
    except ValueError:
        await interaction.response.send_message("Invalid color code. Please use hex format (e.g., #FF5733)", ephemeral=True)
        return
    
    # Save the theme color
    guild_id = str(interaction.guild.id)
    if guild_id not in settings['guilds']:
        settings['guilds'][guild_id] = {}
    
    settings['guilds'][guild_id]['theme_color'] = color
    save_settings(settings)
    
    # Create a color preview
    embed = discord.Embed(
        title="Theme Color Updated",
        description=f"Server theme color set to {color}",
        color=int(color[1:], 16)  # Convert hex to int for discord.Color
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="welcome", description="Set a custom welcome message")
@app_commands.describe(message="Welcome message (use {user} for the new member's mention)")
@app_commands.default_permissions(administrator=True)
async def welcome(interaction: discord.Interaction, message: str):
    """Set a custom welcome message for new members"""
    # Save the welcome message
    guild_id = str(interaction.guild.id)
    if guild_id not in settings['guilds']:
        settings['guilds'][guild_id] = {}
    
    settings['guilds'][guild_id]['welcome_message'] = message
    save_settings(settings)
    
    # Preview the message
    preview = message.replace("{user}", interaction.user.mention)
    
    embed = discord.Embed(
        title="Welcome Message Updated",
        description="New members will receive the following message:",
        color=discord.Color.green()
    )
    embed.add_field(name="Preview", value=preview, inline=False)
    
    await interaction.response.send_message(embed=embed)

# Event handler for new members
@bot.event
async def on_member_join(member):
    """Send welcome message when a new member joins"""
    guild_id = str(member.guild.id)
    
    # Check if this guild has a custom welcome message
    if guild_id in settings['guilds'] and 'welcome_message' in settings['guilds'][guild_id]:
        welcome_message = settings['guilds'][guild_id]['welcome_message']
        welcome_message = welcome_message.replace("{user}", member.mention)
        
        # Find the system channel or first text channel we can send to
        channel = member.guild.system_channel
        if not channel:
            for ch in member.guild.text_channels:
                if ch.permissions_for(member.guild.me).send_messages:
                    channel = ch
                    break
        
        if channel:
            await channel.send(welcome_message)
    
    # Track member joins
    if guild_id in settings['guilds']:
        if 'member_joins' in settings['guilds'][guild_id]:
            settings['guilds'][guild_id]['member_joins'] += 1
        else:
            settings['guilds'][guild_id]['member_joins'] = 1
        save_settings(settings)

# Stats command to see usage statistics
@bot.tree.command(name="stats", description="View bot usage statistics for this server")
async def stats(interaction: discord.Interaction):
    """Shows usage statistics for the bot in this server"""
    guild_id = str(interaction.guild.id)
    
    # Get stats from settings
    if guild_id in settings['guilds']:
        guild_settings = settings['guilds'][guild_id]
        hello_count = guild_settings.get('hello_count', 0)
        settings_viewed = guild_settings.get('settings_viewed', 0)
        uptime_checks = guild_settings.get('uptime_checks', 0)
        member_joins = guild_settings.get('member_joins', 0)
    else:
        guild_settings = {}
        hello_count = settings_viewed = uptime_checks = member_joins = 0
    
    # Create embed
    embed = discord.Embed(
        title="Bot Usage Statistics",
        description=f"Statistics for {interaction.guild.name}",
        color=discord.Color.blue()
    )
    
    embed.add_field(name="Hello Command", value=f"{hello_count} uses", inline=True)
    embed.add_field(name="Settings Viewed", value=f"{settings_viewed} times", inline=True)
    embed.add_field(name="Uptime Checks", value=f"{uptime_checks} times", inline=True)
    embed.add_field(name="New Members", value=f"{member_joins} joins", inline=True)
    
    # Add when the bot joined
    if 'joined_at' in guild_settings:
        try:
            joined_date = datetime.datetime.fromisoformat(guild_settings['joined_at'])
            embed.add_field(name="Bot Joined", value=joined_date.strftime("%Y-%m-%d"), inline=True)
        except (ValueError, TypeError):
            embed.add_field(name="Bot Joined", value="Unknown", inline=True)
    
    # Add custom settings info
    custom_settings = []
    if 'theme_color' in guild_settings:
        custom_settings.append(f"Theme Color: {guild_settings['theme_color']}")
    if 'welcome_message' in guild_settings:
        custom_settings.append("Custom Welcome Message: ✓")
    
    if custom_settings:
        embed.add_field(name="Custom Settings", value="\n".join(custom_settings), inline=False)
    
    await interaction.response.send_message(embed=embed)

# Run the bot
if __name__ == "__main__":
    # Make sure we have the token
    if not TOKEN:
        print("Error: No bot token provided. Please set the BOT_TOKEN environment variable.")
        sys.exit(1)
    
    # Start the bot
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{current_time}] Starting bot...")
    
    # Ensure data directory exists
    os.makedirs('data', exist_ok=True)
    
    # Log to file
    with open('data/bot_log.txt', 'a') as f:
        f.write(f'[{current_time}] Starting bot...\n')
        
    bot.run(TOKEN)
