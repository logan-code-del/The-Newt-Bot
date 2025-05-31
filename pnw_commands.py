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
kit = pnwkit.QueryKit(api_key=API_KEY)

# Create a group for PnW commands
class PnWCommands(app_commands.Group):
    def __init__(self):
        super().__init__(name="pnw", description="Politics & War commands")

    # Helper function to safely access data
    @staticmethod
    def safe_get(obj, attr, default="N/A"):
        """Safely get an attribute from an object or dictionary"""
        if obj is None:
            return default
        
        # Handle list case
        if isinstance(obj, list):
            if not obj:  # Empty list
                return default
            obj = obj[0]  # Take first item
        
        # Try attribute access
        try:
            return getattr(obj, attr)
        except (AttributeError, TypeError):
            # Try dictionary access
            try:
                return obj[attr]
            except (KeyError, TypeError):
                return default
        
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
async def nation_command(interaction: discord.Interaction, nation_name: str):
    await interaction.response.defer()
    
    try:
        # Query the nation data
        query = kit.query("nations", {
            "first": 1,
            "nation_name": nation_name
        }, ["id", "nation_name", "leader_name", "alliance_id", "alliance_position", 
            "alliance{id, name, acronym}", "cities", "score", "color", "vacation_mode_turns",
            "last_active", "soldiers", "tanks", "aircraft", "ships", "missiles", "nukes"])
        
        result = await query.get()
        
        # Handle list or empty result
        nations = result.nations
        if not nations:
            await interaction.followup.send(f"Nation '{nation_name}' not found.")
            return
        
        nation = nations[0] if isinstance(nations, list) else nations
        
        # Create embed
        embed = discord.Embed(
            title=safe_get(nation, "nation_name"),
            url=f"https://politicsandwar.com/nation/id={safe_get(nation, 'id')}",
            color=discord.Color.blue()
        )
        
        # Basic info
        embed.add_field(name="Leader", value=safe_get(nation, "leader_name"), inline=True)
        
        # Alliance info
        alliance = safe_get(nation, "alliance")
        alliance_name = "None"
        if alliance:
            alliance_id = safe_get(alliance, "id")
            alliance_name = safe_get(alliance, "name")
            alliance_acronym = safe_get(alliance, "acronym")
            if alliance_id and alliance_name:
                alliance_name = f"[{alliance_acronym or ''}] {alliance_name}"
                alliance_position = safe_get(nation, "alliance_position")
                if alliance_position:
                    alliance_name += f" ({alliance_position})"
        
        embed.add_field(name="Alliance", value=alliance_name, inline=True)
        
        # Nation stats
        embed.add_field(name="Score", value=format_number(safe_get(nation, "score")), inline=True)
        embed.add_field(name="Cities", value=safe_get(nation, "cities"), inline=True)
        embed.add_field(name="Color", value=safe_get(nation, "color"), inline=True)
        
        # Vacation mode
        vacation_turns = safe_get(nation, "vacation_mode_turns")
        vacation_status = f"Yes ({vacation_turns} turns left)" if vacation_turns and int(vacation_turns) > 0 else "No"
        embed.add_field(name="Vacation Mode", value=vacation_status, inline=True)
        
        # Last active
        last_active = safe_get(nation, "last_active")
        embed.add_field(name="Last Active", value=time_since(last_active), inline=True)
        
        # Military
        military = (
            f"Soldiers: {format_number(safe_get(nation, 'soldiers'))}\n"
            f"Tanks: {format_number(safe_get(nation, 'tanks'))}\n"
            f"Aircraft: {format_number(safe_get(nation, 'aircraft'))}\n"
            f"Ships: {format_number(safe_get(nation, 'ships'))}\n"
            f"Missiles: {format_number(safe_get(nation, 'missiles'))}\n"
            f"Nukes: {format_number(safe_get(nation, 'nukes'))}"
        )
        embed.add_field(name="Military", value=military, inline=False)
        
        await interaction.followup.send(embed=embed)
    except Exception as e:
        error_message = f"Error looking up nation: {str(e)}"
        print(f"Debug - Nation command error: {error_message}")
        await interaction.followup.send(error_message)

# Alliance command
async def alliance_command(interaction: discord.Interaction, alliance_name: str):
    await interaction.response.defer()
    
    try:
        # Query the alliance data
        query = kit.query("alliances", {
            "first": 1,
            "name": alliance_name
        }, ["id", "name", "acronym", "score", "color", "rank", "nations", 
            "average_score", "discord", "flag"])
        
        result = await query.get()
        
        # Handle list or empty result
        alliances = result.alliances
        if not alliances:
            await interaction.followup.send(f"Alliance '{alliance_name}' not found.")
            return
        
        alliance = alliances[0] if isinstance(alliances, list) else alliances
        
        # Create embed
        embed = discord.Embed(
            title=f"{safe_get(alliance, 'name')} [{safe_get(alliance, 'acronym')}]",
            url=f"https://politicsandwar.com/alliance/id={safe_get(alliance, 'id')}",
            color=discord.Color.green()
        )
        
        # Set flag as thumbnail if available
        flag = safe_get(alliance, "flag")
        if flag:
            embed.set_thumbnail(url=flag)
        
        # Alliance stats
        embed.add_field(name="Score", value=format_number(safe_get(alliance, "score")), inline=True)
        embed.add_field(name="Rank", value=safe_get(alliance, "rank"), inline=True)
        embed.add_field(name="Color", value=safe_get(alliance, "color"), inline=True)
        embed.add_field(name="Nations", value=safe_get(alliance, "nations"), inline=True)
        embed.add_field(name="Average Score", value=format_number(safe_get(alliance, "average_score")), inline=True)
        
        # Discord link if available
        discord_link = safe_get(alliance, "discord")
        if discord_link:
            embed.add_field(name="Discord", value=discord_link, inline=False)
        
        await interaction.followup.send(embed=embed)
    except Exception as e:
        error_message = f"Error looking up alliance: {str(e)}"
        print(f"Debug - Alliance command error: {error_message}")
        await interaction.followup.send(error_message)

# War command
async def wars_command(interaction: discord.Interaction, nation_name: str):
    await interaction.response.defer()
    
    try:
        # First get the nation ID
        nation_query = kit.query("nations", {
            "first": 1,
            "nation_name": nation_name
        }, ["id", "nation_name"])
        
        nation_result = await nation_query.get()
        
        # Handle list or empty result
        nations = nation_result.nations
        if not nations:
            await interaction.followup.send(f"Nation '{nation_name}' not found.")
            return
        
        nation = nations[0] if isinstance(nations, list) else nations
        nation_id = safe_get(nation, "id")
        
        # Now query the wars
        war_query = kit.query("wars", {
            "first": 10,
            "active": True,
            "nation_id": nation_id
        }, ["id", "date", "winner_id", "attacker{id, nation_name, alliance_id, alliance{name, acronym}}", 
            "defender{id, nation_name, alliance_id, alliance{name, acronym}}", "attacker_war_policy", 
            "defender_war_policy", "ground_control", "air_superiority", "naval_blockade", "winner", "turns_left"])
        
        war_result = await war_query.get()
        
        # Handle list or empty result
        wars = war_result.wars
        if not wars or (isinstance(wars, list) and len(wars) == 0):
            await interaction.followup.send(f"No active wars found for '{nation_name}'.")
            return
        
        # Create embed
        embed = discord.Embed(
            title=f"Active Wars for {safe_get(nation, 'nation_name')}",
            url=f"https://politicsandwar.com/nation/id={nation_id}",
            color=discord.Color.red()
        )
        
        # Process each war
        if isinstance(wars, list):
            for war in wars:
                attacker = safe_get(war, "attacker")
                defender = safe_get(war, "defender")
                
                attacker_name = safe_get(attacker, "nation_name")
                defender_name = safe_get(defender, "nation_name")
                
                # Get alliance info
                attacker_alliance = safe_get(attacker, "alliance")
                defender_alliance = safe_get(defender, "alliance")
                
                attacker_alliance_tag = safe_get(attacker_alliance, "acronym", "")
                defender_alliance_tag = safe_get(defender_alliance, "acronym", "")
                
                if attacker_alliance_tag:
                    attacker_name = f"[{attacker_alliance_tag}] {attacker_name}"
                if defender_alliance_tag:
                    defender_name = f"[{defender_alliance_tag}] {defender_name}"
                
                # War status
                ground_control = safe_get(war, "ground_control", "Contested")
                air_superiority = safe_get(war, "air_superiority", "Contested")
                naval_blockade = safe_get(war, "naval_blockade", "Contested")
                
                turns_left = safe_get(war, "turns_left", "Unknown")
                
                war_info = (
                    f"**{attacker_name}** vs **{defender_name}**\n"
                    f"Ground Control: {ground_control}\n"
                    f"Air Superiority: {air_superiority}\n"
                    f"Naval Blockade: {naval_blockade}\n"
                    f"Turns Left: {turns_left}"
                )
                
                embed.add_field(name=f"War #{safe_get(war, 'id')}", value=war_info, inline=False)
        else:
            # Handle single war case
            attacker = safe_get(wars, "attacker")
            defender = safe_get(wars, "defender")
            
            attacker_name = safe_get(attacker, "nation_name")
            defender_name = safe_get(defender, "nation_name")
            
            # Get alliance info
            attacker_alliance = safe_get(attacker, "alliance")
            defender_alliance = safe_get(defender, "alliance")
            
            attacker_alliance_tag = safe_get(attacker_alliance, "acronym", "")
            defender_alliance_tag = safe_get(defender_alliance, "acronym", "")
            
            if attacker_alliance_tag:
                attacker_name = f"[{attacker_alliance_tag}] {attacker_name}"
            if defender_alliance_tag:
                defender_name = f"[{defender_alliance_tag}] {defender_name}"
            
            # War status
            ground_control = safe_get(wars, "ground_control", "Contested")
            air_superiority = safe_get(wars, "air_superiority", "Contested")
            naval_blockade = safe_get(wars, "naval_blockade", "Contested")
            
            turns_left = safe_get(wars, "turns_left", "Unknown")
            
            war_info = (
                f"**{attacker_name}** vs **{defender_name}**\n"
                f"Ground Control: {ground_control}\n"
                f"Air Superiority: {air_superiority}\n"
                f"Naval Blockade: {naval_blockade}\n"
                f"Turns Left: {turns_left}"
            )
            
            embed.add_field(name=f"War #{safe_get(wars, 'id')}", value=war_info, inline=False)
        
        await interaction.followup.send(embed=embed)
    except Exception as e:
        error_message = f"Error looking up wars: {str(e)}"
        print(f"Debug - Wars command error: {error_message}")
        await interaction.followup.send(error_message)


# City command
async def city_command(interaction: discord.Interaction, nation_name: str, city_name: Optional[str] = None):
    await interaction.response.defer()
    
    try:
        # First get the nation ID
        nation_query = kit.query("nations", {
            "first": 1,
            "nation_name": nation_name
        }, ["id", "nation_name", "cities{id, name, infrastructure, land, powered, oil_power, wind_power, coal_power, nuclear_power, coal_mine, oil_well, uranium_mine, iron_mine, lead_mine, bauxite_mine, farm, police_station, hospital, recycling_center, subway, supermarket, bank, shopping_mall, stadium, barracks, factory, hangar, drydock, date}"])
        
        nation_result = await nation_query.get()
        
        # Handle list or empty result
        nations = nation_result.nations
        if not nations:
            await interaction.followup.send(f"Nation '{nation_name}' not found.")
            return
        
        nation = nations[0] if isinstance(nations, list) else nations
        nation_id = safe_get(nation, "id")
        
        # Get cities
        cities = safe_get(nation, "cities", [])
        if isinstance(cities, dict):
            cities = [cities]  # Convert dict to list with single item
        
        if not cities:
            await interaction.followup.send(f"No cities found for '{nation_name}'.")
            return
        
        # If city name is provided, filter for that city
        if city_name:
            matching_cities = [city for city in cities if safe_get(city, "name", "").lower() == city_name.lower()]
            if not matching_cities:
                await interaction.followup.send(f"City '{city_name}' not found for nation '{nation_name}'.")
                return
            cities = matching_cities
        
        # Create embed
        embed = discord.Embed(
            title=f"Cities of {safe_get(nation, 'nation_name')}",
            url=f"https://politicsandwar.com/nation/id={nation_id}",
            color=discord.Color.blue()
        )
        
        # Show details for each city (up to 5 to avoid hitting Discord limits)
        for city in cities[:5]:
            city_name = safe_get(city, "name")
            infra = safe_get(city, "infrastructure")
            land = safe_get(city, "land")
            
            # Power sources
            powered = "Yes" if safe_get(city, "powered") else "No"
            power_sources = []
            if safe_get(city, "oil_power"):
                power_sources.append("Oil")
            if safe_get(city, "wind_power"):
                power_sources.append("Wind")
            if safe_get(city, "coal_power"):
                power_sources.append("Coal")
            if safe_get(city, "nuclear_power"):
                power_sources.append("Nuclear")
            
            power_info = ", ".join(power_sources) if power_sources else "None"
            
            # Resources
            resources = []
            if safe_get(city, "coal_mine"):
                resources.append("Coal")
            if safe_get(city, "oil_well"):
                resources.append("Oil")
            if safe_get(city, "uranium_mine"):
                resources.append("Uranium")
            if safe_get(city, "iron_mine"):
                resources.append("Iron")
            if safe_get(city, "lead_mine"):
                resources.append("Lead")
            if safe_get(city, "bauxite_mine"):
                resources.append("Bauxite")
            if safe_get(city, "farm"):
                resources.append("Farm")
            
            resource_info = ", ".join(resources) if resources else "None"
            
            # Improvements
            improvements = []
            if safe_get(city, "police_station"):
                improvements.append("Police")
            if safe_get(city, "hospital"):
                improvements.append("Hospital")
            if safe_get(city, "recycling_center"):
                improvements.append("Recycling")
            if safe_get(city, "subway"):
                improvements.append("Subway")
            if safe_get(city, "supermarket"):
                improvements.append("Supermarket")
            if safe_get(city, "bank"):
                improvements.append("Bank")
            if safe_get(city, "shopping_mall"):
                improvements.append("Mall")
            if safe_get(city, "stadium"):
                improvements.append("Stadium")
            
            improvement_info = ", ".join(improvements) if improvements else "None"
            
            # Military
            military = []
            if safe_get(city, "barracks"):
                military.append("Barracks")
            if safe_get(city, "factory"):
                military.append("Factory")
            if safe_get(city, "hangar"):
                military.append("Hangar")
            if safe_get(city, "drydock"):
                military.append("Drydock")
            
            military_info = ", ".join(military) if military else "None"
            
            # City age
            city_date = safe_get(city, "date")
            age = time_since(city_date) if city_date else "Unknown"
            
            city_info = (
                f"Infrastructure: {format_number(infra)}\n"
                f"Land: {format_number(land)}\n"
                f"Powered: {powered} ({power_info})\n"
                f"Resources: {resource_info}\n"
                f"Improvements: {improvement_info}\n"
                f"Military: {military_info}\n"
                f"Age: {age}"
            )
            
            embed.add_field(name=city_name, value=city_info, inline=False)
        
        # If there are more cities than we displayed
        if len(cities) > 5:
            embed.set_footer(text=f"Showing 5 of {len(cities)} cities. Use /pnw city {nation_name} [city_name] to see a specific city.")
        
        await interaction.followup.send(embed=embed)
    except Exception as e:
        error_message = f"Error looking up city: {str(e)}"
        print(f"Debug - City command error: {error_message}")
        await interaction.followup.send(error_message)



async def prices_command(interaction: discord.Interaction):
    await interaction.response.defer()
    
    try:
        # Query trade prices
        query = kit.query("trade_prices", {}, ["coal", "oil", "uranium", "iron", "bauxite", "lead", "gasoline", 
                                              "munitions", "steel", "aluminum", "food", "credits"])
        
        result = await query.get()
        
        # Handle list or empty result
        prices = result.trade_prices
        if not prices:
            await interaction.followup.send("Could not retrieve trade prices.")
            return
        
        # Handle list case
        if isinstance(prices, list):
            if not prices:
                await interaction.followup.send("Could not retrieve trade prices (empty list).")
                return
            prices = prices[0]  # Take the first item
        
        # Create embed
        embed = discord.Embed(
            title="Current Trade Prices",
            description="Average global market prices for resources",
            color=discord.Color.gold()
        )
        
        # Resources
        resources = (
            f"Coal: ${format_number(safe_get(prices, 'coal'))}\n"
            f"Oil: ${format_number(safe_get(prices, 'oil'))}\n"
            f"Uranium: ${format_number(safe_get(prices, 'uranium'))}\n"
            f"Iron: ${format_number(safe_get(prices, 'iron'))}\n"
            f"Bauxite: ${format_number(safe_get(prices, 'bauxite'))}\n"
            f"Lead: ${format_number(safe_get(prices, 'lead'))}"
        )
        embed.add_field(name="Raw Resources", value=resources, inline=True)
        
        # Manufactured goods
        manufactured = (
            f"Gasoline: ${format_number(safe_get(prices, 'gasoline'))}\n"
            f"Munitions: ${format_number(safe_get(prices, 'munitions'))}\n"
            f"Steel: ${format_number(safe_get(prices, 'steel'))}\n"
            f"Aluminum: ${format_number(safe_get(prices, 'aluminum'))}\n"
            f"Food: ${format_number(safe_get(prices, 'food'))}"
        )
        embed.add_field(name="Manufactured Goods", value=manufactured, inline=True)
        
        # Credits
        embed.add_field(name="Credits", value=f"${format_number(safe_get(prices, 'credits'))}", inline=False)
        
        await interaction.followup.send(embed=embed)
    except Exception as e:
        error_message = f"Error looking up prices: {str(e)}"
        print(f"Debug - Price command error: {error_message}")
        await interaction.followup.send(error_message)

# Bank command
async def bank_command(interaction: discord.Interaction, nation_name: str):
    await interaction.response.defer()
    
    try:
        # First get the nation ID
        nation_query = kit.query("nations", {
            "first": 1,
            "nation_name": nation_name
        }, ["id", "nation_name", "alliance_id", "alliance{name, acronym}"])
        
        nation_result = await nation_query.get()
        
        # Handle list or empty result
        nations = nation_result.nations
        if not nations:
            await interaction.followup.send(f"Nation '{nation_name}' not found.")
            return
        
        nation = nations[0] if isinstance(nations, list) else nations
        nation_id = safe_get(nation, "id")
        
        # Get alliance info for bank query
        alliance_id = safe_get(nation, "alliance_id")
        if not alliance_id:
            await interaction.followup.send(f"Nation '{nation_name}' is not in an alliance.")
            return
        
        # Query bank records
        bank_query = kit.query("banks", {
            "alliance_id": alliance_id,
            "receiver_id": nation_id
        }, ["id", "date", "money", "coal", "oil", "uranium", "iron", "bauxite", "lead", "gasoline", 
            "munitions", "steel", "aluminum", "food", "sender{id, nation_name}", "note"])
        
        bank_result = await bank_query.get()
        
        # Handle list or empty result
        banks = bank_result.banks
        if not banks or (isinstance(banks, list) and len(banks) == 0):
            await interaction.followup.send(f"No bank records found for '{nation_name}'.")
            return
        
        # Get alliance info for display
        alliance = safe_get(nation, "alliance")
        alliance_name = safe_get(alliance, "name", "Unknown Alliance")
        alliance_acronym = safe_get(alliance, "acronym", "")
        
        if alliance_acronym:
            alliance_display = f"[{alliance_acronym}] {alliance_name}"
        else:
            alliance_display = alliance_name
        
        # Create embed
        embed = discord.Embed(
            title=f"Bank Records for {safe_get(nation, 'nation_name')}",
            description=f"Alliance: {alliance_display}",
            color=discord.Color.gold()
        )
        
        # Process bank records (up to 5 most recent)
        if isinstance(banks, list):
            # Sort by date (most recent first)
            banks.sort(key=lambda x: safe_get(x, "date", ""), reverse=True)
            banks = banks[:5]  # Take up to 5 most recent
            
            for bank in banks:
                date = safe_get(bank, "date")
                sender = safe_get(bank, "sender")
                sender_name = safe_get(sender, "nation_name", "Unknown")
                
                # Resources
                resources = []
                money = safe_get(bank, "money")
                if money and float(money) != 0:
                    resources.append(f"${format_number(money)}")
                
                for resource in ["coal", "oil", "uranium", "iron", "bauxite", "lead", 
                                "gasoline", "munitions", "steel", "aluminum", "food"]:
                    amount = safe_get(bank, resource)
                    if amount and float(amount) != 0:
                        resources.append(f"{format_number(amount)} {resource.capitalize()}")
                
                resource_text = ", ".join(resources) if resources else "None"
                
                # Note
                note = safe_get(bank, "note", "")
                if note:
                    note = f"\nNote: {note}"
                
                bank_info = (
                    f"From: {sender_name}\n"
                    f"Date: {time_since(date)}\n"
                    f"Resources: {resource_text}"
                    f"{note}"
                )
                
                embed.add_field(name=f"Transaction #{safe_get(bank, 'id')}", value=bank_info, inline=False)
        else:
            # Handle single bank record case
            date = safe_get(banks, "date")
            sender = safe_get(banks, "sender")
            sender_name = safe_get(sender, "nation_name", "Unknown")
            
            # Resources
            resources = []
            money = safe_get(banks, "money")
            if money and float(money) != 0:
                resources.append(f"${format_number(money)}")
            
            for resource in ["coal", "oil", "uranium", "iron", "bauxite", "lead", 
                            "gasoline", "munitions", "steel", "aluminum", "food"]:
                amount = safe_get(banks, resource)
                if amount and float(amount) != 0:
                    resources.append(f"{format_number(amount)} {resource.capitalize()}")
            
            resource_text = ", ".join(resources) if resources else "None"
            
            # Note
            note = safe_get(banks, "note", "")
            if note:
                note = f"\nNote: {note}"
            
            bank_info = (
                f"From: {sender_name}\n"
                f"Date: {time_since(date)}\n"
                f"Resources: {resource_text}"
                f"{note}"
            )
            
            embed.add_field(name=f"Transaction #{safe_get(banks, 'id')}", value=bank_info, inline=False)
        
        await interaction.followup.send(embed=embed)
    except Exception as e:
        error_message = f"Error looking up bank records: {str(e)}"
        print(f"Debug - Bank command error: {error_message}")
        await interaction.followup.send(error_message)


# Radiation command
async def radiation_command(interaction: discord.Interaction):
    await interaction.response.defer()
    
    try:
        # Query global data
        query = kit.query("game_info", {}, ["radiation{global}"])
        
        result = await query.get()
        
        if not result.game_info or not result.game_info.radiation:
            await interaction.followup.send("Could not retrieve radiation data.")
            return
        
        # Use safe_get to handle different data structures
        radiation_data = safe_get(result.game_info, "radiation")
        radiation = None
        
        # Try different ways to access the global radiation value
        if radiation_data:
            # Try attribute access first
            try:
                radiation = getattr(radiation_data, "global")
            except (AttributeError, TypeError):
                # Try dictionary access
                try:
                    radiation = radiation_data["global"]
                except (KeyError, TypeError):
                    # If it's a list, try the first item
                    if isinstance(radiation_data, list) and len(radiation_data) > 0:
                        first_item = radiation_data[0]
                        try:
                            radiation = getattr(first_item, "global")
                        except (AttributeError, TypeError):
                            try:
                                radiation = first_item["global"]
                            except (KeyError, TypeError):
                                radiation = None
        
        if radiation is None:
            # Last resort - try to parse the raw data
            print(f"Debug - Radiation data structure: {type(radiation_data)}")
            print(f"Debug - Radiation data content: {radiation_data}")
            await interaction.followup.send("Could not parse radiation data. Please check the logs.")
            return
        
        # Create embed
        embed = discord.Embed(
            title="Global Radiation Levels",
            description=f"Current global radiation: **{radiation}%**",
            color=discord.Color.dark_purple()
        )
        
        # Add effects based on radiation level
        effects = ""
        radiation_value = float(radiation)
        if radiation_value < 1:
            effects = "No significant effects."
        elif radiation_value < 10:
            effects = "Minor reduction in food production."
        elif radiation_value < 25:
            effects = "Moderate reduction in food production and population growth."
        elif radiation_value < 50:
            effects = "Significant reduction in food production, population growth, and soldier recruitment."
        elif radiation_value < 75:
            effects = "Severe reduction in food production, population growth, and soldier recruitment. Increased casualties in war."
        else:
            effects = "Catastrophic reduction in food production, population growth, and soldier recruitment. Greatly increased casualties in war."
        
        embed.add_field(name="Effects", value=effects, inline=False)
        
        await interaction.followup.send(embed=embed)
    except Exception as e:
        error_message = f"Error looking up radiation: {str(e)}"
        print(f"Debug - Radiation command error: {error_message}")
        await interaction.followup.send(error_message)


# Set API key command
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
            if 'guilds' not in settings:
                settings['guilds'] = {}
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
        error_message = f"Error setting API key: {str(e)}"
        print(f"Debug - Set API key command error: {error_message}")
        await interaction.followup.send(error_message, ephemeral=True)

# Debug command for developers
async def debug_command(interaction: discord.Interaction, command: str):
    """Debug command to help diagnose issues"""
    # Only allow for bot owner
    if interaction.user.id != 123456789:  # Replace with your user ID
        await interaction.response.send_message("This command is only available to the bot owner.", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    try:
        if command == "prices":
            # Debug prices command
            query = kit.query("trade_prices", {}, ["coal", "oil", "uranium", "iron", "bauxite", "lead", "gasoline", 
                                                  "munitions", "steel", "aluminum", "food", "credits"])
            
            result = await query.get()
            
            # Print raw data for debugging
            raw_data = str(result.trade_prices)
            data_type = str(type(result.trade_prices))
            
            debug_info = f"Data type: {data_type}\nRaw data: {raw_data[:1900]}"  # Limit to Discord message size
            
            await interaction.followup.send(f"```{debug_info}```", ephemeral=True)
        
        elif command == "radiation":
            # Debug radiation command
            query = kit.query("game_info", {}, ["radiation{global}"])
            
            result = await query.get()
            
            # Print raw data for debugging
            raw_data = str(result.game_info)
            data_type = str(type(result.game_info))
            
            if result.game_info and result.game_info.radiation:
                radiation_type = str(type(result.game_info.radiation))
                radiation_data = str(result.game_info.radiation)
                debug_info = f"Game info type: {data_type}\nRadiation type: {radiation_type}\nRadiation data: {radiation_data[:1900]}"
            else:
                debug_info = f"Game info type: {data_type}\nRaw data: {raw_data[:1900]}"
            
            await interaction.followup.send(f"```{debug_info}```", ephemeral=True)
        
        else:
            await interaction.followup.send(f"Unknown debug command: {command}", ephemeral=True)
    
    except Exception as e:
        await interaction.followup.send(f"Debug error: {str(e)}", ephemeral=True)

# Function to register all PnW commands
def setup(bot):
    # Create a command group for PnW commands
    pnw_group = app_commands.Group(name="pnw", description="Politics & War commands")
    
    # Add commands to the group
    pnw_group.add_command(app_commands.Command(
        name="nation",
        description="Look up a Politics & War nation",
        callback=nation_command
    ))
    
    pnw_group.add_command(app_commands.Command(
        name="alliance",
        description="Look up a Politics & War alliance",
        callback=alliance_command
    ))
    
    pnw_group.add_command(app_commands.Command(
        name="wars",
        description="Look up active wars for a nation",
        callback=wars_command
    ))
    
    pnw_group.add_command(app_commands.Command(
        name="city",
        description="Look up a city in Politics & War",
        callback=city_command
    ))
    
    pnw_group.add_command(app_commands.Command(
        name="prices",
        description="Look up current trade prices in Politics & War",
        callback=prices_command
    ))
    
    pnw_group.add_command(app_commands.Command(
        name="bank",
        description="Look up a nation's bank in Politics & War",
        callback=bank_command
    ))
    
    pnw_group.add_command(app_commands.Command(
        name="radiation",
        description="Look up global radiation levels in Politics & War",
        callback=radiation_command
    ))
    
    pnw_group.add_command(app_commands.Command(
        name="setapikey",
        description="Set your Politics & War API key",
        callback=set_api_key_command
    ))
    
    # Add debug command (hidden from normal users)
    pnw_group.add_command(app_commands.Command(
        name="debug",
        description="Debug command for developers",
        callback=debug_command
    ))
    
    # Add the group to the command tree
    bot.tree.add_command(pnw_group)
    
    # Log setup
    print("Politics & War commands registered as group")
