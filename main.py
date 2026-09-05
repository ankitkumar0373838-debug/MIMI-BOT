import os
import sqlite3
import discord
from discord.ext import commands

# =========================================================
# 𝙼𝙸𝙼𝙸🌸 — Discord Bot
# =========================================================

BOT_NAME = "𝙼𝙸𝙼𝙸🌸"
PREFIX = "*"

# Get secrets from hosting environment variables
TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

# =========================================================
# INTENTS
# =========================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True
intents.guilds = True

# =========================================================
# BOT
# =========================================================

class MIMI(commands.Bot):

    def __init__(self):
        super().__init__(
            command_prefix=PREFIX,
            intents=intents,
            help_command=None,
            case_insensitive=True
        )

    async def setup_hook(self):
        # Create database
        os.makedirs("database", exist_ok=True)

        connection = sqlite3.connect("database/mimi.db")
        cursor = connection.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id INTEGER PRIMARY KEY,
                prefix TEXT DEFAULT '*',
                antinuke INTEGER DEFAULT 0
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS whitelist (
                guild_id INTEGER,
                user_id INTEGER,
                PRIMARY KEY (guild_id, user_id)
            )
        """)

        connection.commit()
        connection.close()

        # Load all Cogs automatically
        if os.path.exists("cogs"):
            for filename in os.listdir("cogs"):
                if filename.endswith(".py") and not filename.startswith("_"):
                    extension = f"cogs.{filename[:-3]}"

                    try:
                        await self.load_extension(extension)
                        print(f"✅ Loaded: {extension}")

                    except Exception as error:
                        print(f"❌ Failed: {extension}")
                        print(f"   Error: {error}")

    async def on_ready(self):
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="over you with tiny paws & big love 🐾💗"
        )

        await self.change_presence(
            status=discord.Status.online,
            activity=activity
        )

        print("=" * 50)
        print(f"🌸 {BOT_NAME} IS ONLINE")
        print(f"🤖 Username : {self.user}")
        print(f"🆔 Bot ID   : {self.user.id}")
        print(f"📌 Prefix   : {PREFIX}")
        print(f"👀 Status   : Watching over you with tiny paws & big love 🐾💗")
        print(f"🧩 Cogs     : {len(self.extensions)}")
        print("=" * 50)


bot = MIMI()

# =========================================================
# BASIC OWNER COMMAND
# =========================================================

@bot.command()
@commands.is_owner()
async def shutdown(ctx):
    """Shutdown the bot."""
    await ctx.send("🌸 MIMI is going offline. See you soon! 🐾")
    await bot.close()


# =========================================================
# ERROR HANDLER
# =========================================================

@bot.event
async def on_command_error(ctx, error):

    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.NotOwner):
        await ctx.send("❌ You don't have permission to use this command.")
        return

    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have the required permissions.")
        return

    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(
            f"❌ Missing argument.\n"
            f"Use `{PREFIX}help` to see the correct usage."
        )
        return

    print(f"⚠️ Command Error: {error}")


# =========================================================
# START BOT
# =========================================================

if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN is missing. "
        "Add your bot token as an environment variable."
    )

bot.run(TOKEN)

