# bot.py
import os
import sys
import time
import datetime
import asyncio
import discord
from discord import app_commands
from discord.ext import commands

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
            with open('bot_log.txt', 'a') as f:
                f.write(f'[{current_time}] Bot running for {int(current_runtime/60)} minutes\n')
        
        # If we're approaching the GitHub Actions timeout, exit gracefully
        if current_runtime >= MAX_RUNTIME:
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{current_time}] Maximum runtime reached ({MAX_RUNTIME/60} minutes). Shutting down...")
            
            # Log to file
            with open('bot_log.txt', 'a') as f:
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
    
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{current_time}] Bot is setting up...")
    
    # Log to file
    with open('bot_log.txt', 'a') as f:
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
    with open('bot_log.txt', 'a') as f:
        f.write(f'[{current_time}] Bot started successfully\n')

@bot.event
async def on_guild_join(guild):
    """Called when the bot joins a new guild"""
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f'[{current_time}] Joined new guild: {guild.name} (ID: {guild.id})')
    
    # Log to file
    with open('bot_log.txt', 'a') as f:
        f.write(f'[{current_time}] Joined new guild: {guild.name} (ID: {guild.id})\n')
    
    # Sync commands with the new guild
    try:
        await bot.tree.sync(guild=guild)
    except Exception as e:
        print(f'[{current_time}] Failed to sync commands to new guild: {e}')

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
            "`/uptime` - Check how long the bot has been running"
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
    await interaction.response.send_message(f'Hello, {interaction.user.mention}!')

@bot.tree.command(name="info", description="Display information about the bot")
async def info(interaction: discord.Interaction):
    """Shows information about the bot"""
    # Calculate uptime
    uptime = int(time.time() - start_time)
    hours, remainder = divmod(uptime, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{hours}h {minutes}m {seconds}s"
    
    embed = discord.Embed(
        title="Bot Information",
        description="A simple Discord bot created with discord.py",
        color=discord.Color.blue()
    )
    embed.add_field(name="Creator", value="Your Name", inline=True)
    embed.add_field(name="Server Count", value=f"{len(bot.guilds)}", inline=True)
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
    
    # Count text and voice channels
    text_channels = len(server.text_channels)
    voice_channels = len(server.voice_channels)
    
    # Get server creation date
    created_at = server.created_at.strftime("%B %d, %Y")
    
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
    
    await interaction.response.send_message(f"Bot has been online for: **{hours}h {minutes}m {seconds}s**{restart_msg}")

# Run the bot
if __name__ == "__main__":
    # Make sure we have the token
    if not TOKEN:
        print("Error: No bot token provided. Please set the BOT_TOKEN environment variable.")
        sys.exit(1)
    
    # Start the bot
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{current_time}] Starting bot...")
    
    # Log to file
    with open('bot_log.txt', 'a') as f:
        f.write(f'[{current_time}] Starting bot...\n')
        
    bot.run(TOKEN)
