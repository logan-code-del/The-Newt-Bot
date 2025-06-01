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

def format_number(num):
    if num == "N/A":
        return num
    try:
        return f"{int(float(num)):,}"
    except (ValueError, TypeError):
        return str(num)

def time_since(date_str):
    """Calculate time since a date string"""
    if not date_str:
        return "Unknown"
        
    # If date_str is a list, try to use the first element
    if isinstance(date_str, list):
        if not date_str:  # Empty list
            return "Unknown"
        date_str = date_str[0]  # Take the first item
        
    # Ensure date_str is a string
    date_str = str(date_str)
        
    try:
        # Handle different date formats
        if 'Z' in date_str:
            date = datetime.datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        else:
            date = datetime.datetime.fromisoformat(date_str)
            
        now = datetime.datetime.now(datetime.timezone.utc)
        diff = now - date
            
        if diff.days > 0:
            return f"{diff.days} days ago"
        hours = diff.seconds // 3600
        if hours > 0:
            return f"{hours} hours ago"
        minutes = (diff.seconds % 3600) // 60
        return f"{minutes} minutes ago"
    except Exception as e:
        print(f"Error parsing date: {e}, date_str: {date_str}, type: {type(date_str)}")
        return "Unknown"

# Create a group for PnW commands
class PnWCommands(app_commands.Group):
    def __init__(self):
        super().__init__(name="pnw", description="Politics & War commands")
    
# Nation command
async def nation_command(interaction: discord.Interaction, nation_name: str):
    await interaction.response.defer()
    
    try:
        # Query nation data using the correct syntax
        query = kit.query(
            "nations",
            {"first": 1, "nation_name": nation_name},
            "id", "nation_name", "leader_name", "alliance_id", "alliance_position",
            pnwkit.Field("alliance", {}, "id", "name", "acronym"),
            pnwkit.Field("cities", {}, "id", "name"),  # Specify which city fields you want
            "score", "color", "vacation_mode_turns",
            "last_active", "soldiers", "tanks", "aircraft", "ships", "missiles", "nukes"
        )
            
        result = await query.get_async()
            
        # Handle list or empty result
        nations = result.nations
        if not nations:
            await interaction.followup.send(f"Nation '{nation_name}' not found.")
            return
            
        nation = nations[0] if isinstance(nations, list) else nations
            
        # Create embed
        embed = discord.Embed(
            title=safe_get(nation, "nation_name", "Unknown Nation"),
            url=f"https://politicsandwar.com/nation/id={safe_get(nation, 'id', '0')}",
            color=discord.Color.blue()
        )
            
        # Basic info
        leader_name = safe_get(nation, "leader_name", "Unknown")
        embed.add_field(name="Leader", value=leader_name, inline=True)
            
        # Alliance info
        alliance = safe_get(nation, "alliance", None)
        alliance_name = "None"
        if alliance:
            alliance_id = safe_get(alliance, "id", "0")
            alliance_name = safe_get(alliance, "name", "Unknown Alliance")
            alliance_acronym = safe_get(alliance, "acronym", "")
                
            if alliance_acronym:
                alliance_display = f"[{alliance_acronym}] {alliance_name}"
            else:
                alliance_display = alliance_name
                
            alliance_position = safe_get(nation, "alliance_position", "Member")
            alliance_name = f"[{alliance_display}](https://politicsandwar.com/alliance/id={alliance_id}) ({alliance_position})"
            
        embed.add_field(name="Alliance", value=alliance_name, inline=True)
            
        # Score and cities
        score = format_number(safe_get(nation, "score", 0))
        cities = safe_get(nation, "cities", [])
        city_count = len(cities) if isinstance(cities, list) else 0
            
        embed.add_field(name="Score", value=score, inline=True)
        embed.add_field(name="Cities", value=str(city_count), inline=True)
            
        # Color
        color = safe_get(nation, "color", "None")
        embed.add_field(name="Color", value=color, inline=True)
            
        # Activity
        last_active = safe_get(nation, "last_active", "Unknown")
        vacation_mode = safe_get(nation, "vacation_mode_turns", 0)
            
        activity = time_since(last_active)
        if vacation_mode and int(vacation_mode) > 0:
            activity += f" (Vacation Mode: {vacation_mode} turns)"
            
        embed.add_field(name="Last Active", value=activity, inline=True)
            
        # Military
        military = (
            f"Soldiers: {format_number(safe_get(nation, 'soldiers', 0))}\n"
            f"Tanks: {format_number(safe_get(nation, 'tanks', 0))}\n"
            f"Aircraft: {format_number(safe_get(nation, 'aircraft', 0))}\n"
            f"Ships: {format_number(safe_get(nation, 'ships', 0))}\n"
            f"Missiles: {format_number(safe_get(nation, 'missiles', 0))}\n"
            f"Nukes: {format_number(safe_get(nation, 'nukes', 0))}"
        )
            
        embed.add_field(name="Military", value=military, inline=False)
            
        await interaction.followup.send(embed=embed)
    except Exception as e:
        error_message = f"Error looking up nation: {str(e)}"
        print(f"Debug - Nation command error: {error_message}")
        await interaction.followup.send(error_message)

# Alliance command with pagination
async def alliance_command(interaction: discord.Interaction, alliance_name: str):
    await interaction.response.defer()
    
    try:
        # Query the alliance data with nations
        query = kit.query(
            "alliances", 
            {"first": 1, "name": alliance_name},
            "id", "name", "acronym", "score", "color", "rank", 
            "average_score", "discord_link", "flag",
            pnwkit.Field("nations", {}, 
                "id", "nation_name", "leader_name", "score", 
                pnwkit.Field("cities", {}, "id"),  # Just query city IDs to count them
                "vacation_mode_turns", "color", "last_active"
            )
        )
        
        result = await query.get_async()
        
        # Handle list or empty result
        alliances = result.alliances
        if not alliances:
            await interaction.followup.send(f"Alliance '{alliance_name}' not found.")
            return
        
        alliance = alliances[0] if isinstance(alliances, list) else alliances
        
        # Get nations list
        nations = safe_get(alliance, "nations", [])
        if isinstance(nations, dict):
            nations = [nations]
        
        # Sort nations by score (descending)
        nations.sort(key=lambda x: float(safe_get(x, "score", 0)), reverse=True)
        
        # Create paginator
        paginator = AlliancePaginator(interaction, alliance, nations)
        await paginator.start()
        
    except Exception as e:
        error_message = f"Error looking up alliance: {str(e)}"
        print(f"Debug - Alliance command error: {error_message}")
        await interaction.followup.send(error_message)

# Alliance Paginator class
class AlliancePaginator(discord.ui.View):
    def __init__(self, interaction, alliance, nations, timeout=180):
        super().__init__(timeout=timeout)
        self.interaction = interaction
        self.alliance = alliance
        self.nations = nations
        self.current_page = 0
        self.nations_per_page = 10
        self.max_pages = 1 + (len(nations) + self.nations_per_page - 1) // self.nations_per_page  # Overview + nation pages
        self.message = None
    
    async def start(self):
        """Send the initial message with the paginator"""
        embed = self.get_current_page_embed()
        self.message = await self.interaction.followup.send(embed=embed, view=self)
    
    def get_current_page_embed(self):
        """Generate the embed for the current page"""
        if self.current_page == 0:
            # Overview page
            return self.get_overview_embed()
        else:
            # Nation list pages
            return self.get_nations_page_embed()
    
    def get_overview_embed(self):
        """Generate the alliance overview embed"""
        alliance = self.alliance
        
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
        embed.add_field(name="Nations", value=str(len(self.nations)), inline=True)
        embed.add_field(name="Average Score", value=format_number(safe_get(alliance, "average_score")), inline=True)
        
        # Discord link if available
        discord_link = safe_get(alliance, "discord_link")
        if discord_link:
            embed.add_field(name="Discord", value=discord_link, inline=False)
        
        embed.set_footer(text=f"Page 1/{self.max_pages} • Overview • Use buttons to navigate")
        return embed
    
    def get_nations_page_embed(self):
        """Generate the nations list embed for the current page"""
        alliance = self.alliance
        
        # Calculate which nations to show on this page
        start_idx = (self.current_page - 1) * self.nations_per_page
        end_idx = min(start_idx + self.nations_per_page, len(self.nations))
        page_nations = self.nations[start_idx:end_idx]
        
        embed = discord.Embed(
            title=f"{safe_get(alliance, 'name')} [{safe_get(alliance, 'acronym')}] - Nations",
            url=f"https://politicsandwar.com/alliance/id={safe_get(alliance, 'id')}",
            color=discord.Color.green()
        )
        
        # Add each nation to the embed
        for nation in page_nations:
            nation_name = safe_get(nation, "nation_name")
            nation_id = safe_get(nation, "id")
            leader_name = safe_get(nation, "leader_name")
            score = format_number(safe_get(nation, "score"))
            
            # Count cities
            cities = safe_get(nation, "cities", [])
            city_count = len(cities) if isinstance(cities, list) else 0
            
            # Check vacation mode
            vacation = safe_get(nation, "vacation_mode_turns")
            vacation_text = f" (VM: {vacation})" if vacation and int(vacation) > 0 else ""
            
            # Last active
            last_active = safe_get(nation, "last_active")
            activity = time_since(last_active) if last_active else "Unknown"
            
            nation_info = (
                f"Leader: {leader_name}\n"
                f"Score: {score}\n"
                f"Cities: {city_count}\n"
                f"Last Active: {activity}{vacation_text}"
            )
            
            embed.add_field(
                name=f"{nation_name}",
                value=nation_info,
                inline=True
            )
        
        embed.set_footer(text=f"Page {self.current_page + 1}/{self.max_pages} • Nations {start_idx + 1}-{end_idx} of {len(self.nations)}")
        return embed
    
    @discord.ui.button(label="◀️ Previous", style=discord.ButtonStyle.gray)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        if self.current_page > 0:
            self.current_page -= 1
            await self.update_message()
    
    @discord.ui.button(label="Overview", style=discord.ButtonStyle.blurple)
    async def overview_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        self.current_page = 0
        await self.update_message()
    
    @discord.ui.button(label="Next ▶️", style=discord.ButtonStyle.gray)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        if self.current_page < self.max_pages - 1:
            self.current_page += 1
            await self.update_message()
    
    async def update_message(self):
        """Update the message with the current page"""
        embed = self.get_current_page_embed()
        await self.message.edit(embed=embed, view=self)
    
    async def on_timeout(self):
        """Disable buttons when the view times out"""
        for item in self.children:
            item.disabled = True
        
        try:
            await self.message.edit(view=self)
        except:
            pass

# War command
async def wars_command(interaction: discord.Interaction, nation_name: str):
    await interaction.response.defer()
    
    try:
        # First get the nation ID
        nation_query = kit.query(
            "nations",
            {"first": 1, "nation_name": nation_name},
            "id", "nation_name"
        )
        
        nation_result = await nation_query.get_async()
        
        # Handle list or empty result
        nations = nation_result.nations
        if not nations:
            await interaction.followup.send(f"Nation '{nation_name}' not found.")
            return
            
        nation = nations[0] if isinstance(nations, list) else nations
        nation_id = safe_get(nation, "id")
            
        # Now query the wars
        war_query = kit.query(
            "wars",
            {"first": 10, "active": True, "nation_id": nation_id},
            "id", "date", "winner_id", 
            pnwkit.Field("attacker", {}, "id", "nation_name", "alliance_id",
                         pnwkit.Field("alliance", {}, "name", "acronym")),
            pnwkit.Field("defender", {}, "id", "nation_name", "alliance_id",
                         pnwkit.Field("alliance", {}, "name", "acronym")), 
            "ground_control", "air_superiority", "naval_blockade", "winner", "turns_left"
        )
            
        war_result = await war_query.get_async()
        
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
        nation_query = kit.query(
            "nations",
            {"first": 1, "nation_name": nation_name},
            "id", "nation_name", 
            pnwkit.Field("cities", {}, 
                "id", "name", "infrastructure", "land", "powered", 
                "oil_power", "wind_power", "coal_power", "nuclear_power", 
                "coal_mine", "oil_well", "uranium_mine", "iron_mine", 
                "lead_mine", "bauxite_mine", "farm", "police_station", 
                "hospital", "recycling_center", "subway", "supermarket", 
                "bank", "shopping_mall", "stadium", "barracks", "factory", 
                "hangar", "drydock", "date"
            )
        )
        
        nation_result = await nation_query.get_async()
        
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

# Prices command
async def prices_command(interaction: discord.Interaction):
    await interaction.response.defer()
    
    try:
        # Query trade prices using the correct syntax
        query = kit.query(
            "tradeprices",  # This is the correct endpoint name
            {},
            "coal", "oil", "uranium", "iron", "bauxite", "lead", 
            "gasoline", "munitions", "steel", "aluminum", "food", "credits"
        )
        
        result = await query.get_async()
        
        # Handle empty result
        if not result.tradeprices:
            await interaction.followup.send("Could not retrieve trade prices.")
            return
        
        # Get the first item if it's a list
        prices = result.tradeprices
        if isinstance(prices, list) and prices:
            prices = prices[0]
        
        # Create embed
        embed = discord.Embed(
            title="Current Trade Prices",
            description="Average global market prices for resources",
            color=discord.Color.gold()
        )
        
        # Resources
        resources = (
            f"Coal: ${format_number(safe_get(prices, 'coal', 'N/A'))}\n"
            f"Oil: ${format_number(safe_get(prices, 'oil', 'N/A'))}\n"
            f"Uranium: ${format_number(safe_get(prices, 'uranium', 'N/A'))}\n"
            f"Iron: ${format_number(safe_get(prices, 'iron', 'N/A'))}\n"
            f"Bauxite: ${format_number(safe_get(prices, 'bauxite', 'N/A'))}\n"
            f"Lead: ${format_number(safe_get(prices, 'lead', 'N/A'))}"
        )
        embed.add_field(name="Raw Resources", value=resources, inline=True)
        
        # Manufactured goods
        manufactured = (
            f"Gasoline: ${format_number(safe_get(prices, 'gasoline', 'N/A'))}\n"
            f"Munitions: ${format_number(safe_get(prices, 'munitions', 'N/A'))}\n"
            f"Steel: ${format_number(safe_get(prices, 'steel', 'N/A'))}\n"
            f"Aluminum: ${format_number(safe_get(prices, 'aluminum', 'N/A'))}\n"
            f"Food: ${format_number(safe_get(prices, 'food', 'N/A'))}"
        )
        embed.add_field(name="Manufactured Goods", value=manufactured, inline=True)
        
        # Credits
        embed.add_field(name="Credits", value=f"${format_number(safe_get(prices, 'credits', 'N/A'))}", inline=False)
        
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
        nation_query = kit.query(
            "nations",
            {"first": 1, "nation_name": nation_name},
            "id", "nation_name", "alliance_id", 
            pnwkit.Field("alliance", {}, "name", "acronym")
        )
        
        nation_result = await nation_query.get_async()
        
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
        
        # Query bank records with updated parameters
        bank_query = kit.query(
            "bankrecs",
            {
                "nation_id": nation_id,  # Use nation_id instead of receiver_id
                # No alliance_id parameter needed
                "first": 10  # Limit to 10 records
            },
            "id", "date", "money", "coal", "oil", "uranium", "iron", "bauxite", "lead", "gasoline",
            "munitions", "steel", "aluminum", "food", 
            pnwkit.Field("sender", {}, "id", "nation_name"),
            "note"
        )
        
        bank_result = await bank_query.get_async()
        
        # Handle list or empty result
        bankrecs = bank_result.bankrecs
        if not bankrecs or (isinstance(bankrecs, list) and len(bankrecs) == 0):
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
        if isinstance(bankrecs, list):
            # Sort by date (most recent first)
            bankrecs.sort(key=lambda x: safe_get(x, "date", ""), reverse=True)
            bankrecs = bankrecs[:5]  # Take up to 5 most recent
            
            for bank in bankrecs:
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
            date = safe_get(bankrecs, "date")
            sender = safe_get(bankrecs, "sender")
            sender_name = safe_get(sender, "nation_name", "Unknown")
            
            # Resources
            resources = []
            money = safe_get(bankrecs, "money")
            if money and float(money) != 0:
                resources.append(f"${format_number(money)}")
            
            for resource in ["coal", "oil", "uranium", "iron", "bauxite", "lead",
                             "gasoline", "munitions", "steel", "aluminum", "food"]:
                amount = safe_get(bankrecs, resource)
                if amount and float(amount) != 0:
                    resources.append(f"{format_number(amount)} {resource.capitalize()}")
            
            resource_text = ", ".join(resources) if resources else "None"
            
            # Note
            note = safe_get(bankrecs, "note", "")
            if note:
                note = f"\nNote: {note}"
            
            bank_info = (
                f"From: {sender_name}\n"
                f"Date: {time_since(date)}\n"
                f"Resources: {resource_text}"
                f"{note}"
            )
            
            embed.add_field(name=f"Transaction #{safe_get(bankrecs, 'id')}", value=bank_info, inline=False)
        
        await interaction.followup.send(embed=embed)
    except Exception as e:
        error_message = f"Error looking up bank records: {str(e)}"
        print(f"Debug - Bank command error: {error_message}")
        await interaction.followup.send(error_message)

async def radiation_command(interaction: discord.Interaction):
    await interaction.response.defer()
    
    try:
        # Query radiation with proper sub-selection
        query = kit.query(
            "game_info",
            {},
            pnwkit.Field("radiation", {}, "global")  # Specify the sub-field "global"
        )
        
        result = await query.get_async()
        
        # Debug the result structure
        print(f"Radiation result: {result}")
        if hasattr(result, "game_info"):
            print(f"Game info: {result.game_info}")
            if hasattr(result.game_info, "radiation"):
                print(f"Radiation: {result.game_info.radiation}")
        
        # Handle empty result
        if not result or not hasattr(result, "game_info"):
            await interaction.followup.send("Could not retrieve radiation information.")
            return
        
        # Access the radiation data safely
        radiation_value = None
        
        # Try different ways to access the data
        try:
            if hasattr(result.game_info, "radiation"):
                # Try direct attribute access
                if hasattr(result.game_info.radiation, "global"):
                    radiation_value = result.game_info.radiation["global"]
                # Try dictionary-style access
                elif hasattr(result.game_info.radiation, "__getitem__"):
                    radiation_value = result.game_info.radiation["global"]
        except Exception as e:
            print(f"Error accessing radiation data: {e}")
        
        # If still None, try another approach
        if radiation_value is None:
            try:
                # Try to convert to dictionary
                game_info_dict = vars(result.game_info)
                if "radiation" in game_info_dict:
                    radiation_dict = vars(game_info_dict["radiation"])
                    if "global" in radiation_dict:
                        radiation_value = radiation_dict["global"]
            except Exception as e:
                print(f"Error converting to dict: {e}")
        
        if radiation_value is None:
            await interaction.followup.send("Could not retrieve radiation information. Please try again later.")
            return
        
        # Create embed
        embed = discord.Embed(
            title="Global Radiation Levels",
            description=f"Current global radiation: {radiation_value}%",
            color=discord.Color.green() if float(radiation_value) < 15 else discord.Color.red()
        )
        
        # Add effects based on radiation level
        effects = []
        rad_value = float(radiation_value)
        
        if rad_value < 15:
            effects.append("No significant effects")
        if rad_value >= 15:
            effects.append("15%+ : -1% Population Growth")
        if rad_value >= 30:
            effects.append("30%+ : -2% Population Growth")
        if rad_value >= 50:
            effects.append("50%+ : -3% Population Growth")
        if rad_value >= 75:
            effects.append("75%+ : -4% Population Growth")
        if rad_value >= 100:
            effects.append("100%+ : -5% Population Growth")
        
        embed.add_field(name="Effects", value="\n".join(effects), inline=False)
        
        # Add information about radiation decay
        embed.add_field(
            name="Radiation Decay",
            value="Global radiation decreases by 1% every 12 hours.",
            inline=False
        )
        
        await interaction.followup.send(embed=embed)
    except Exception as e:
        error_message = f"Error looking up radiation: {str(e)}"
        print(f"Debug - Radiation command error: {error_message}")
        
        # Add more detailed error information
        import traceback
        traceback_str = traceback.format_exc()
        print(f"Traceback: {traceback_str}")
        
        await interaction.followup.send(f"Error looking up radiation: {str(e)}")

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

# Debug command to test pnwkit queries
async def debug_query_command(interaction: discord.Interaction, query_type: str):
    await interaction.response.defer(ephemeral=True)
    
    try:
        result = None
        query_info = f"Testing query type: {query_type}"
        
        if query_type == "radiation":
            query = kit.query(
                "game_info",
                {},
                pnwkit.Field("radiation", {}, "global")
            )
            result = await query.get_async()
            
        elif query_type == "prices":
            query = kit.query(
                "trade_prices",
                {},
                "coal", "oil", "uranium", "iron", "bauxite", "lead",
                "gasoline", "munitions", "steel", "aluminum", "food", "credits"
            )
            result = await query.get()
            
        elif query_type == "nation":
            query = kit.query(
                "nations",
                {"first": 1},
                "id", "nation_name", "leader_name"
            )
            result = await query.get()
            
        elif query_type == "alliance":
            query = kit.query(
                "alliances",
                {"first": 1},
                "id", "name", "acronym"
            )
            result = await query.get()
            
        else:
            await interaction.followup.send(f"Unknown query type: {query_type}")
            return
        
        # Debug info
        debug_info = []
        debug_info.append(query_info)
        debug_info.append(f"Result type: {type(result)}")
        debug_info.append(f"Result attributes: {dir(result)[:20]}")
        
        if result:
            debug_info.append(f"Raw result: {str(result)[:1000]}")
        
        # Send debug info
        debug_text = "\n".join(debug_info)
        await interaction.followup.send(f"```{debug_text}```")
        
    except Exception as e:
        error_message = f"Debug query error: {str(e)}"
        print(f"Debug command error: {error_message}")
        import traceback
        await interaction.followup.send(f"Error: {error_message}\n```{traceback.format_exc()[:1500]}```")

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
    
    pnw_group.add_command(app_commands.Command(
        name="debug",
        description="Debug pnwkit queries",
        callback=debug_query_command
    ))
    # Add the group to the command tree
    bot.tree.add_command(pnw_group)
    
    # Log setup
    print("Politics & War commands registered as group")
