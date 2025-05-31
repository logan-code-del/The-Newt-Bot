# bot.py
import os
import discord
from discord.ext import commands

# Set up intents
intents = discord.Intents.default()
intents.message_content = True

# Create bot with intents
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} servers')

@bot.command()
async def test(ctx):
    await ctx.send('Test command works!')

# Get token from environment variable
bot.run(os.environ.get('BOT_TOKEN'))
