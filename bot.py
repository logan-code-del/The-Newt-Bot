# bot.py
import os
import sys
import time
import json
import datetime
import asyncio
import discord
from discord.ext import commands

# Function to load settings
def load_settings():
    try:
        with open('settings.json', 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Default settings
        default_settings = {'default_prefix': '!', 'guild_prefixes': {}}
        save_settings(default_settings)
        return default_settings

# Function to save settings
def save_settings(settings):
    with open('settings.json', 'w') as f:
        json.dump(settings, f, indent=4)

# Load settings
settings = load_settings()

# Function to get prefix for a specific guild
def get_prefix(bot, message):
    # DMs will use the default prefix
    if message.guild is None:
        return settings['default_prefix']
    
    # Get guild-specific prefix or use default
    guild_id = str(message.guild.id)
    return settings['guild_prefixes'].get(guild_id, settings['default_prefix'])

# Set up intents
intents = discord.Intents.default()
intents.message_content = True  # Enable message content intent

# Create bot with dynamic prefix
bot = commands.Bot(command_prefix=get_prefix, intents=intents, help_command=commands.DefaultHelpCommand(
    no_category="Commands"
))

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
    
    # Set bot status
    await bot.change_presence(activity=discord.Game(name=f"Type {settings['default_prefix']}help for commands"))
    
    # Log to a file that can be accessed in GitHub Actions logs
    with open('bot_log.txt', 'a') as f:
        f.write(f'[{current_time}] Bot started successfully\n')

@bot.event
async def on_guild_join(guild):
    """Called when the bot joins a new guild"""
    # Use default prefix for new guilds
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f'[{current_time}] Joined new guild: {guild.name} (ID: {guild.id})')
    
    # Log to file
    with open('bot_log.txt', 'a') as f:
        f.write(f'[{current_time}] Joined new guild: {guild.name} (ID: {guild.id})\n')

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Command not found. Try `help` for a list of commands.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Missing required argument. Check `help [command]` for usage.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have permission to use this command.")
    else:
        await ctx.send(f"An error occurred: {str(error)}")
        print(f"[{current_time}] Error: {error}")
        
        # Log errors to a file
        with open('bot_log.txt', 'a') as f:
            f.write(f'[{current_time}] Error: {error}\n')

# Settings command group
@bot.group(name="settings", help="Change bot settings", invoke_without_command=True)
@commands.has_permissions(administrator=True)
async def settings_cmd(ctx):
    """Command group for bot settings"""
    # If no subcommand was specified, show current settings
    prefix = get_prefix(bot, ctx.message)
    
    embed = discord.Embed(
        title="Bot Settings",
        description="Current bot settings for this server",
        color=discord.Color.blue()
    )
    
    embed.add_field(name="Current Prefix", value=f"`{prefix}`", inline=False)
    embed.add_field(name="Available Settings Commands", value=(
        f"`{prefix}settings prefix <new_prefix>` - Change command prefix\n"
        f"`{prefix}settings reset` - Reset to default settings"
    ), inline=False)
    
    await ctx.send(embed=embed)

@settings_cmd.command(name="prefix", help="Change the command prefix")
@commands.has_permissions(administrator=True)
async def settings_prefix(ctx, new_prefix: str):
    """Change the command prefix for this server"""
    if len(new_prefix) > 5:
        await ctx.send("Prefix must be 5 characters or less.")
        return
    
    # Update the prefix for this guild
    guild_id = str(ctx.guild.id)
    settings['guild_prefixes'][guild_id] = new_prefix
    save_settings(settings)
    
    await ctx.send(f"Prefix changed to `{new_prefix}` for this server.")
    
    # Update bot status if this is the default prefix
    if guild_id == settings.get('default_guild'):
        await bot.change_presence(activity=discord.Game(name=f"Type {new_prefix}help for commands"))

@settings_cmd.command(name="reset", help="Reset settings to default")
@commands.has_permissions(administrator=True)
async def settings_reset(ctx):
    """Reset settings to default for this server"""
    guild_id = str(ctx.guild.id)
    
    # Remove custom prefix for this guild if it exists
    if guild_id in settings['guild_prefixes']:
        del settings['guild_prefixes'][guild_id]
        save_settings(settings)
        
    await ctx.send(f"Settings reset to default. Prefix is now `{settings['default_prefix']}`.")

@settings_cmd.error
async def settings_error(ctx, error):
    """Handle errors in the settings command"""
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You need administrator permissions to change bot settings.")
    else:
        # Pass to the global error handler
        await on_command_error(ctx, error)

@bot.command(name="test", help="Test if the bot is responding")
async def test(ctx):
    """Simple test command to check if the bot is working"""
    await ctx.send('Test command works!')

@bot.command(name="hello", help="Get a friendly greeting")
async def hello(ctx):
    """Greets the user who invoked the command"""
    await ctx.send(f'Hello, {ctx.author.mention}!')

@bot.command(name="info", help="Display information about the bot")
async def info(ctx):
    """Shows information about the bot"""
    # Calculate uptime
    uptime = int(time.time() - start_time)
    hours, remainder = divmod(uptime, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{hours}h {minutes}m {seconds}s"
    
    # Get current prefix
    prefix = get_prefix(bot, ctx.message)
    
    embed = discord.Embed(
        title="Bot Information",
        description="A simple Discord bot created with discord.py",
        color=discord.Color.blue()
    )
    embed.add_field(name="Creator", value="Your Name", inline=True)
    embed.add_field(name="Server Count", value=f"{len(bot.guilds)}", inline=True)
    embed.add_field(name="Command Prefix", value=f"`{prefix}`", inline=True)
    embed.add_field(name="Framework", value="discord.py", inline=True)
    embed.add_field(name="Current Uptime", value=uptime_str, inline=True)
    embed.add_field(name="Hosted via", value="GitHub Actions", inline=True)
    embed.set_footer(text="Bot will restart every 6 hours via GitHub Actions")
    await ctx.send(embed=embed)

@bot.command(name="ping", help="Check the bot's latency")
async def ping(ctx):
    """Displays the bot's latency"""
    latency = round(bot.latency * 1000)
    await ctx.send(f'Pong! Latency: {latency}ms')

@bot.command(name="serverinfo", help="Display information about the server")
async def serverinfo(ctx):
    """Shows information about the current server"""
    server = ctx.guild
    
    # Count text and voice channels
    text_channels = len(server.text_channels)
    voice_channels = len(server.voice_channels)
    
    # Get server creation date
    created_at = server.created_at.strftime("%B %d, %Y")
    
    # Get current prefix
    prefix = get_prefix(bot, ctx.message)
    
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
    embed.add_field(name="Command Prefix", value=f"`{prefix}`", inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name="userinfo", help="Display information about a user")
async def userinfo(ctx, member: discord.Member = None):
    """Shows information about a user"""
    # If no member is specified, use the command author
    if member is None:
        member = ctx.author
        
    # Get join dates
    joined_at = member.joined_at.strftime("%B %d, %Y")
    created_at = member.created_at.strftime("%B %d, %Y")
    
    # Create embed
    embed = discord.Embed(
        title=f"User Information - {member.name}",
        color=member.color
    )
    
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="ID", value=member.id, inline=True)
    embed.add_field(name="Nickname", value=member.nick if member.nick else "None", inline=True)
    embed.add_field(name="Account Created", value=created_at, inline=True)
    embed.add_field(name="Joined Server", value=joined_at, inline=True)
    
    # Get the member's top role (highest in hierarchy)
    roles = [role.mention for role in reversed(member.roles) if role.name != "@everyone"]
    if roles:
        embed.add_field(name=f"Roles [{len(roles)}]", value=" ".join(roles) if len(" ".join(roles)) < 1024 else "Too many roles to display", inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name="uptime", help="Check how long the bot has been running")
async def uptime(ctx):
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
    
    await ctx.send(f"Bot has been online for: **{hours}h {minutes}m {seconds}s**{restart_msg}")

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
        
    # Create settings.json if it doesn't exist
    if not os.path.exists('settings.json'):
        default_settings = {'default_prefix': '!', 'guild_prefixes': {}}
        with open('settings.json', 'w') as f:
            json.dump(default_settings, f, indent=4)
    
    bot.run(TOKEN)
