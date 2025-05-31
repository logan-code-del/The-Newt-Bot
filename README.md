# Discord Bot

A simple Discord bot built with discord.py and hosted via GitHub Actions.

## Features

- **Basic Commands**: Test, Hello, Ping
- **Information Commands**: Server info, User info, Bot info
- **Uptime Tracking**: Check how long the bot has been running

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- A Discord account
- A Discord bot token

### Creating a Discord Bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to the "Bot" tab and click "Add Bot"
4. Under the "Privileged Gateway Intents" section, enable:
   - Presence Intent
   - Server Members Intent
   - Message Content Intent
5. Click "Reset Token" to get your bot token (keep this secure!)

### Inviting Your Bot to a Server

1. Go to the "OAuth2" → "URL Generator" tab
2. Select the scopes: `bot` and `applications.commands`
3. Select the bot permissions you need (at minimum: "Send Messages", "Read Messages/View Channels")
4. Copy the generated URL and open it in your browser
5. Select a server and authorize the bot

### Local Setup

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/your-discord-bot.git
   cd your-discord-bot
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file with your bot token:
   ```
   BOT_TOKEN=your_token_here
   ```

4. Run the bot:
   ```
   python bot.py
   ```

### GitHub Actions Setup

This bot is designed to run via GitHub Actions, which will automatically run the bot on a schedule.

1. Fork this repository
2. Go to your repository's Settings → Secrets → Actions
3. Add a new repository secret:
   - Name: `BOT_TOKEN`
   - Value: Your Discord bot token
4. The bot will automatically run according to the schedule in `.github/workflows/bot.yml`
5. You can also manually trigger the workflow from the Actions tab

## Commands

| Command | Description |
|---------|-------------|
| `!test` | Test if the bot is responding |
| `!hello` | Get a friendly greeting |
| `!info` | Display information about the bot |
| `!ping` | Check the bot's latency |
| `!serverinfo` | Display information about the server |
| `!userinfo [member]` | Display information about a user (or yourself if no user is specified) |
| `!uptime` | Check how long the bot has been running |
| `!help` | Show the help message with all commands |

## GitHub Actions Workflow

The bot runs on GitHub Actions with the following schedule:
- Runs every 6 hours
- Each run lasts up to 350 minutes (just under GitHub's 6-hour limit)
- Can be manually triggered from the Actions tab

## Limitations

When hosted on GitHub Actions:
- The bot will restart every 6 hours
- There's a monthly limit of 2,000 minutes of runtime on free GitHub accounts
- The bot may experience brief downtime between scheduled runs

## Extending the Bot

To add new commands, edit the `bot.py` file:

```python
@bot.command(name="command_name", help="Command description")
async def command_name(ctx):
    await ctx.send("Command response")
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [discord.py](https://github.com/Rapptz/discord.py)
- [GitHub Actions](https://github.com/features/actions)
```

## Additional File: .gitignore

```text: \Your\Path\.gitignore
# .gitignore

# Environment variables
.env

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
*.egg-info/
.installed.cfg
*.egg

# Logs
logs/
*.log
bot_log.txt

# IDE specific files
.idea/
.vscode/
*.swp
*.swo
.DS_Store
```

## Additional File: LICENSE

```text: \Your\Path\LICENSE
MIT License

Copyright (c) 2023 Your Name

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
