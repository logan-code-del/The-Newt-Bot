# bot.py
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')

# Set up intents
intents = discord.Intents.default()
intents.message_content = True  # Enable message content intent

# Create bot with intents
bot = commands.Bot(command_prefix='/', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

@bot.command()
async def test(ctx):
    await ctx.send('Test command works!')

bot.run(TOKEN)