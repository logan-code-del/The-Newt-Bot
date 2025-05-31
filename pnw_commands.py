# pnw_commands.py - Politics & War commands for Discord bot
import discord
from discord import app_commands
import pnwkit
import datetime
import json
import os
from typing import Optional, List

# Load API key if available
API_KEY = os.environ.get('PNW_API_KEY', '')

# Initialize the PnWKit client with the API key
# If no API key is available, use an empty string - we'll handle authentication later
kit = pnwkit.QueryKit(api_key=API_KEY)

# Create a group for PnW commands
class PnWCommands(app_commands.Group):
    def __init__(self):
        super().__init__(name="pnw", description="Politics & War commands")
        
    # Helper function to format numbers with commas
    @staticmethod
    def format_number(num):
        return f"{int(num):,}"
    
    # Helper function to calculate time difference
    @staticmethod
    def time_since(date_str):
        try:
            date = datetime.datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            now = datetime.datetime.now(datetime.timezone.utc)
            diff = now - date
            
            if diff.days > 0:
                return f"{diff.days} days ago"
            hours = diff.seconds // 3600
            if hours > 0:
                return f"{hours} hours ago"
            minutes = (diff.seconds % 3600) // 60
            return f"{minutes} minutes ago"
        except:
            return "Unknown"


# Nation command
@app_commands.command(name="pnw_nation", description="Look up a Politics & War nation")
@app_commands.describe(nation_name="Name of the nation to look up")
async def nation_command(interaction: discord.Interaction, nation_name: str):
    await interaction.response.defer()
    
    try:
        # Query the nation data
        query = kit.query("nations", {
            "first": 1,
            "nation_name": nation_name
        }, ["id", "nation_name", "leader_name", "alliance_id", "alliance_position", 
            "cities", "score", "soldiers", "tanks", "aircraft", "ships", 
            "last_active", "date", "color", "alliance{id name}"])
        
        result = await query.get()
        
        if not result.nations:
            await interaction.followup.send(f"Nation '{nation_name}' not found.")
            return
        
        nation = result.nations[0]
        
        # Create embed
        embed = discord.Embed(
            title=f"{nation.nation_name}",
            url=f"https://politicsandwar.com/nation/id={nation.id}",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="Leader", value=nation.leader_name, inline=True)
        
        # Alliance info
        if nation.alliance:
            alliance_position = nation.alliance_position.replace("_", " ").title() if nation.alliance_position else "Member"
            embed.add_field(
                name="Alliance", 
                value=f"[{nation.alliance.name}](https://politicsandwar.com/alliance/id={nation.alliance.id}) ({alliance_position})", 
                inline=True
            )
        else:
            embed.add_field(name="Alliance", value="None", inline=True)
        
        embed.add_field(name="Cities", value=nation.cities, inline=True)
        embed.add_field(name="Score", value=PnWCommands.format_number(nation.score), inline=True)
        embed.add_field(name="Color", value=nation.color.title(), inline=True)
        
        # Military
        military = (
            f"👥 Soldiers: {PnWCommands.format_number(nation.soldiers)}\n"
            f"🚗 Tanks: {PnWCommands.format_number(nation.tanks)}\n"
            f"✈️ Aircraft: {PnWCommands.format_number(nation.aircraft)}\n"
            f"🚢 Ships: {PnWCommands.format_number(nation.ships)}"
        )
        embed.add_field(name="Military", value=military, inline=False)
        
        # Activity
        last_active = PnWCommands.time_since(nation.last_active)
        created = datetime.datetime.fromisoformat(nation.date.replace('Z', '+00:00')).strftime("%Y-%m-%d")
        embed.add_field(name="Last Active", value=last_active, inline=True)
        embed.add_field(name="Created", value=created, inline=True)
        
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"Error looking up nation: {str(e)}")

# Alliance command
@app_commands.command(name="pnw_alliance", description="Look up a Politics & War alliance")
@app_commands.describe(alliance_name="Name of the alliance to look up")
async def alliance_command(interaction: discord.Interaction, alliance_name: str):
    await interaction.response.defer()
    
    try:
        # Query the alliance data
        query = kit.query("alliances", {
            "first": 1,
            "name": alliance_name
        }, ["id", "name", "acronym", "score", "color", "rank", "member_count", "average_score", "date"])
        
        result = await query.get()
        
        if not result.alliances:
            await interaction.followup.send(f"Alliance '{alliance_name}' not found.")
            return
        
        alliance = result.alliances[0]
        
        # Create embed
        embed = discord.Embed(
            title=f"{alliance.name} [{alliance.acronym}]",
            url=f"https://politicsandwar.com/alliance/id={alliance.id}",
            color=discord.Color.gold()
        )
        
        embed.add_field(name="Score", value=PnWCommands.format_number(alliance.score), inline=True)
        embed.add_field(name="Rank", value=f"#{alliance.rank}", inline=True)
        embed.add_field(name="Color", value=alliance.color.title(), inline=True)
        embed.add_field(name="Members", value=alliance.member_count, inline=True)
        embed.add_field(name="Average Score", value=PnWCommands.format_number(alliance.average_score), inline=True)
        
        # Creation date
        created = datetime.datetime.fromisoformat(alliance.date.replace('Z', '+00:00')).strftime("%Y-%m-%d")
        embed.add_field(name="Founded", value=created, inline=True)
        
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"Error looking up alliance: {str(e)}")

# War command
@app_commands.command(name="pnw_wars", description="Look up active wars for a nation")
@app_commands.describe(nation_name="Name of the nation to look up wars for")
async def wars_command(interaction: discord.Interaction, nation_name: str):
    await interaction.response.defer()
    
    try:
        # First get the nation ID
        nation_query = kit.query("nations", {
            "first": 1,
            "nation_name": nation_name
        }, ["id", "nation_name"])
        
        nation_result = await nation_query.get()
        
        if not nation_result.nations:
            await interaction.followup.send(f"Nation '{nation_name}' not found.")
            return
        
        nation_id = nation_result.nations[0].id
        
        # Now query active wars
        wars_query = kit.query("wars", {
            "first": 5,
            "active": True,
            "or_aggressor_id_eq": nation_id,
            "or_defender_id_eq": nation_id
        }, ["id", "date", "reason", "war_type", "ground_control", "air_superiority", "naval_blockade", "winner", "turns_left",
            "aggressor{id nation_name alliance{name}}",
            "defender{id nation_name alliance{name}}"])
        
        wars_result = await wars_query.get()
        
        if not wars_result.wars:
            await interaction.followup.send(f"No active wars found for {nation_name}.")
            return
        
        # Create embed
        embed = discord.Embed(
            title=f"Active Wars for {nation_name}",
            color=discord.Color.red()
        )
        
        for war in wars_result.wars:
            # Determine if the nation is the aggressor or defender
            is_aggressor = war.aggressor.id == nation_id
            opponent = war.defender if is_aggressor else war.aggressor
            
            # War status
            status = []
            if war.ground_control:
                status.append(f"Ground: {war.ground_control}")
            if war.air_superiority:
                status.append(f"Air: {war.air_superiority}")
            if war.naval_blockade:
                status.append(f"Naval: {war.naval_blockade}")
            
            status_str = ", ".join(status) if status else "No battles yet"
            
            # War info
            war_info = (
                f"**vs [{opponent.nation_name}](https://politicsandwar.com/nation/id={opponent.id})**\n"
                f"Type: {war.war_type.replace('_', ' ').title()}\n"
                f"Status: {status_str}\n"
                f"Turns left: {war.turns_left}"
            )
            
            # Add alliance info if available
            if opponent.alliance:
                war_info += f"\nAlliance: {opponent.alliance.name}"
            
            # Add field to embed
            embed.add_field(
                name=f"{'Offensive' if is_aggressor else 'Defensive'} War #{war.id}",
                value=war_info,
                inline=False
            )
        
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"Error looking up wars: {str(e)}")

# City command
@app_commands.command(name="pnw_city", description="Look up a city in Politics & War")
@app_commands.describe(nation_name="Name of the nation", city_name="Name of the city (optional)")
async def city_command(interaction: discord.Interaction, nation_name: str, city_name: Optional[str] = None):
    await interaction.response.defer()
    
    try:
        # First get the nation ID
        nation_query = kit.query("nations", {
            "first": 1,
            "nation_name": nation_name
        }, ["id", "nation_name", "cities{id name population infrastructure land powered date}"])
        
        nation_result = await nation_query.get()
        
        if not nation_result.nations:
            await interaction.followup.send(f"Nation '{nation_name}' not found.")
            return
        
        nation = nation_result.nations[0]
        
        # If city name is provided, find that specific city
        if city_name:
            city = next((c for c in nation.cities if c.name.lower() == city_name.lower()), None)
            
            if not city:
                await interaction.followup.send(f"City '{city_name}' not found in {nation_name}.")
                return
            
            # Create embed for single city
            embed = discord.Embed(
                title=f"{city.name} - {nation.nation_name}",
                url=f"https://politicsandwar.com/city/id={city.id}",
                color=discord.Color.green()
            )
            
            embed.add_field(name="Population", value=PnWCommands.format_number(city.population), inline=True)
            embed.add_field(name="Infrastructure", value=PnWCommands.format_number(city.infrastructure), inline=True)
            embed.add_field(name="Land", value=PnWCommands.format_number(city.land), inline=True)
            embed.add_field(name="Powered", value="Yes" if city.powered else "No", inline=True)
            
            # City age
            created = datetime.datetime.fromisoformat(city.date.replace('Z', '+00:00')).strftime("%Y-%m-%d")
            embed.add_field(name="Founded", value=created, inline=True)
            
            await interaction.followup.send(embed=embed)
        else:
            # List all cities
            embed = discord.Embed(
                title=f"Cities of {nation.nation_name}",
                url=f"https://politicsandwar.com/nation/id={nation.id}",
                color=discord.Color.green()
            )
            
            # Sort cities by population
            sorted_cities = sorted(nation.cities, key=lambda c: c.population, reverse=True)
            
            for city in sorted_cities[:10]:  # Limit to 10 cities to avoid hitting Discord limits
                city_info = (
                    f"Population: {PnWCommands.format_number(city.population)}\n"
                    f"Infrastructure: {PnWCommands.format_number(city.infrastructure)}\n"
                    f"Land: {PnWCommands.format_number(city.land)}"
                )
                
                embed.add_field(
                    name=city.name,
                    value=city_info,
                    inline=True
                )
            
            if len(nation.cities) > 10:
                embed.set_footer(text=f"Showing 10 of {len(nation.cities)} cities. Use /pnw city {nation_name} [city_name] to see details for a specific city.")
            
            await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"Error looking up city: {str(e)}")

# Prices command
@app_commands.command(name="pnw_prices", description="Look up current trade prices in Politics & War")
async def prices_command(interaction: discord.Interaction):
    await interaction.response.defer()
    
    try:
        # Query trade prices
        query = kit.query("trade_prices", {}, ["coal", "oil", "uranium", "iron", "bauxite", "lead", "gasoline", 
                                              "munitions", "steel", "aluminum", "food", "credits"])
        
        result = await query.get()
        
        if not result.trade_prices:
            await interaction.followup.send("Could not retrieve trade prices.")
            return
        
        prices = result.trade_prices
        
        # Create embed
        embed = discord.Embed(
            title="Current Trade Prices",
            description="Average global market prices for resources",
            color=discord.Color.gold()
        )
        
        # Resources
        resources = (
            f"Coal: ${prices.coal:,.2f}\n"
            f"Oil: ${prices.oil:,.2f}\n"
            f"Uranium: ${prices.uranium:,.2f}\n"
            f"Iron: ${prices.iron:,.2f}\n"
            f"Bauxite: ${prices.bauxite:,.2f}\n"
            f"Lead: ${prices.lead:,.2f}"
        )
        embed.add_field(name="Raw Resources", value=resources, inline=True)
        
        # Manufactured goods
        manufactured = (
            f"Gasoline: ${prices.gasoline:,.2f}\n"
            f"Munitions: ${prices.munitions:,.2f}\n"
            f"Steel: ${prices.steel:,.2f}\n"
            f"Aluminum: ${prices.aluminum:,.2f}\n"
            f"Food: ${prices.food:,.2f}"
        )
        embed.add_field(name="Manufactured Goods", value=manufactured, inline=True)
        
        # Credits
        embed.add_field(name="Credits", value=f"${prices.credits:,.2f}", inline=False)
        
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"Error looking up prices: {str(e)}")

# Bank command
@app_commands.command(name="pnw_bank", description="Look up a nation's bank in Politics & War")
@app_commands.describe(nation_name="Name of the nation to look up bank for")
async def bank_command(interaction: discord.Interaction, nation_name: str):
    await interaction.response.defer()
    
    try:
        # Query the nation data with bank info
        query = kit.query("nations", {
            "first": 1,
            "nation_name": nation_name
        }, ["id", "nation_name", "alliance_id", 
            "money", "coal", "oil", "uranium", "iron", "bauxite", "lead", 
            "gasoline", "munitions", "steel", "aluminum", "food"])
        
        result = await query.get()
        
        if not result.nations:
            await interaction.followup.send(f"Nation '{nation_name}' not found.")
            return
        
        nation = result.nations[0]
        
        # Create embed
        embed = discord.Embed(
            title=f"{nation.nation_name}'s Bank",
            url=f"https://politicsandwar.com/nation/id={nation.id}",
            color=discord.Color.green()
        )
        
        # Money
        embed.add_field(name="Money", value=f"${PnWCommands.format_number(nation.money)}", inline=False)
        
        # Resources
        raw_resources = (
            f"Coal: {PnWCommands.format_number(nation.coal)}\n"
            f"Oil: {PnWCommands.format_number(nation.oil)}\n"
            f"Uranium: {PnWCommands.format_number(nation.uranium)}\n"
            f"Iron: {PnWCommands.format_number(nation.iron)}\n"
            f"Bauxite: {PnWCommands.format_number(nation.bauxite)}\n"
            f"Lead: {PnWCommands.format_number(nation.lead)}"
        )
        embed.add_field(name="Raw Resources", value=raw_resources, inline=True)
        
        # Manufactured goods
        manufactured = (
            f"Gasoline: {PnWCommands.format_number(nation.gasoline)}\n"
            f"Munitions: {PnWCommands.format_number(nation.munitions)}\n"
            f"Steel: {PnWCommands.format_number(nation.steel)}\n"
            f"Aluminum: {PnWCommands.format_number(nation.aluminum)}\n"
            f"Food: {PnWCommands.format_number(nation.food)}"
        )
        embed.add_field(name="Manufactured Goods", value=manufactured, inline=True)
        
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"Error looking up bank: {str(e)}")

# Radiation command
@app_commands.command(name="pnw_radiation", description="Look up global radiation levels in Politics & War")
async def radiation_command(interaction: discord.Interaction):
    await interaction.response.defer()
    
    try:
        # Query global data
        query = kit.query("game_info", {}, ["radiation{global}"])
        
        result = await query.get()
        
        if not result.game_info or not result.game_info.radiation:
            await interaction.followup.send("Could not retrieve radiation data.")
            return
        
        # Use getattr to access the 'global' property since it's a reserved keyword
        radiation = getattr(result.game_info.radiation, "global")
        
        # Create embed
        embed = discord.Embed(
            title="Global Radiation Levels",
            description=f"Current global radiation: **{radiation}%**",
            color=discord.Color.dark_purple()
        )
        
        # Add effects based on radiation level
        effects = ""
        if radiation < 1:
            effects = "No significant effects."
        elif radiation < 10:
            effects = "Minor reduction in food production."
        elif radiation < 25:
            effects = "Moderate reduction in food production and population growth."
        elif radiation < 50:
            effects = "Significant reduction in food production, population growth, and soldier recruitment."
        elif radiation < 75:
            effects = "Severe reduction in food production, population growth, and soldier recruitment. Increased casualties in war."
        else:
            effects = "Catastrophic reduction in food production, population growth, and soldier recruitment. Greatly increased casualties in war."
        
        embed.add_field(name="Effects", value=effects, inline=False)
        
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"Error looking up radiation: {str(e)}")

# Set API key command
@app_commands.command(name="pnw_setapikey", description="Set your Politics & War API key")
@app_commands.describe(api_key="Your Politics & War API key")
@app_commands.default_permissions(administrator=True)
async def set_api_key_command(interaction: discord.Interaction, api_key: str):
    # Only allow in DMs or by server admins
    if interaction.guild and not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("This command can only be used in DMs or by server administrators.", ephemeral=True)
        return
    
    # Always respond as ephemeral to hide the API key
    await interaction.response.defer(ephemeral=True)
    
    try:
        # Store the API key in settings
        from bot import settings, save_settings
        
        # For DMs, store in user settings
        if not interaction.guild:
            user_id = str(interaction.user.id)
            if 'users' not in settings:
                settings['users'] = {}
            if user_id not in settings['users']:
                settings['users'][user_id] = {}
            
            settings['users'][user_id]['pnw_api_key'] = api_key
        # For servers, store in guild settings
        else:
            guild_id = str(interaction.guild.id)
            if guild_id not in settings['guilds']:
                settings['guilds'][guild_id] = {}
            
            settings['guilds'][guild_id]['pnw_api_key'] = api_key
        
        save_settings(settings)
        
        # Set the API key for the current session
        global API_KEY, kit
        API_KEY = api_key
        
        # Create a new QueryKit instance with the updated API key
        kit = pnwkit.QueryKit(api_key=API_KEY)
        
        await interaction.followup.send("API key set successfully! You can now use commands that require authentication.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"Error setting API key: {str(e)}", ephemeral=True)

# Function to register all PnW commands
def setup(bot):
    # Add individual commands
    bot.tree.add_command(nation_command)
    bot.tree.add_command(alliance_command)
    bot.tree.add_command(wars_command)
    bot.tree.add_command(city_command)
    bot.tree.add_command(prices_command)
    bot.tree.add_command(bank_command)
    bot.tree.add_command(radiation_command)
    bot.tree.add_command(set_api_key_command)
    
    # Log setup
    print("Politics & War commands registered")
