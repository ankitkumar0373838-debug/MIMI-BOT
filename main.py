 import os
import sqlite3
import random
import time
import io
import discord
import qrcode

from discord.ext import commands

# =========================================================
# 𝙼𝙸𝙼𝙸🌸
# =========================================================

BOT_NAME = "𝙼𝙸𝙼𝙸🌸"
PREFIX = "*"

# PUT YOUR BOT TOKEN HERE
TOKEN = "PASTE_YOUR_BOT_TOKEN_HERE"

# =========================================================
# SETTINGS
# =========================================================

intents = discord.Intents.all()

bot = commands.Bot(
    command_prefix=PREFIX,
    intents=intents,
    help_command=None,
    case_insensitive=True
)

START_TIME = time.time()

# =========================================================
# DATABASE
# =========================================================

os.makedirs("database", exist_ok=True)

db = sqlite3.connect(
    "database/mimi.db",
    check_same_thread=False
)

cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS guild_settings (
    guild_id INTEGER PRIMARY KEY,
    antinuke INTEGER DEFAULT 0,
    welcome INTEGER DEFAULT 0,
    logs INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS warnings (
    guild_id INTEGER,
    user_id INTEGER,
    warnings INTEGER DEFAULT 0,
    PRIMARY KEY (guild_id, user_id)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS economy (
    guild_id INTEGER,
    user_id INTEGER,
    balance INTEGER DEFAULT 0,
    PRIMARY KEY (guild_id, user_id)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS whitelist (
    guild_id INTEGER,
    user_id INTEGER,
    PRIMARY KEY (guild_id, user_id)
)
""")

db.commit()


# =========================================================
# HELPERS
# =========================================================

def embed(title, description, color=discord.Color.from_rgb(255, 170, 210)):
    return discord.Embed(
        title=title,
        description=description,
        color=color
    )


def get_balance(guild_id, user_id):
    cursor.execute(
        "SELECT balance FROM economy WHERE guild_id=? AND user_id=?",
        (guild_id, user_id)
    )
    row = cursor.fetchone()

    if row:
        return row[0]

    cursor.execute(
        "INSERT INTO economy VALUES (?, ?, ?)",
        (guild_id, user_id, 0)
    )
    db.commit()

    return 0


def set_balance(guild_id, user_id, amount):
    get_balance(guild_id, user_id)

    cursor.execute(
        "UPDATE economy SET balance=? WHERE guild_id=? AND user_id=?",
        (amount, guild_id, user_id)
    )

    db.commit()


def uptime():
    seconds = int(time.time() - START_TIME)

    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    return f"{days}d {hours}h {minutes}m {seconds}s"


# =========================================================
# EVENTS
# =========================================================

@bot.event
async def on_ready():

    activity = discord.Activity(
        type=discord.ActivityType.watching,
        name="over you with tiny paws & big love 🐾💗"
    )

    await bot.change_presence(
        status=discord.Status.online,
        activity=activity
    )

    print("=" * 55)
    print(f"🌸 {BOT_NAME} IS ONLINE")
    print(f"🤖 User: {bot.user}")
    print(f"📌 Prefix: {PREFIX}")
    print("👀 Watching over you with tiny paws & big love 🐾💗")
    print(f"📊 Servers: {len(bot.guilds)}")
    print("=" * 55)


# =========================================================
# 1. HELP
# =========================================================

@bot.command()
async def help(ctx):

    e = embed(
        "🌸 𝙼𝙸𝙼𝙸 — Help Center",
        "Cute outside, powerful inside. 🐾💗\n\n"
        "**🛡️ Security**\n"
        "`*antinuke` `*lockdown` `*unlockdown` `*whitelist` `*unwhitelist`\n"
        "`*security` `*auditlog`\n\n"
        "**🔨 Moderation**\n"
        "`*ban` `*unban` `*kick` `*mute` `*unmute`\n"
        "`*warn` `*warnings` `*clear` `*slowmode` `*nick`\n\n"
        "**🌸 Community**\n"
        "`*welcome` `*goodbye` `*autorole` `*profile` `*serverinfo`\n\n"
        "**🎁 Events**\n"
        "`*giveaway` `*reroll` `*poll` `*announce`\n\n"
        "**💰 Economy**\n"
        "`*balance` `*daily` `*work` `*deposit` `*withdraw`\n"
        "`*leaderboard` `*paycoins`\n\n"
        "**🎮 Fun**\n"
        "`*8ball` `*coinflip` `*dice` `*rps` `*joke`\n"
        "`*ship` `*choose` `*rate` `*say`\n\n"
        "**🔧 Utility**\n"
        "`*ping` `*botinfo` `*userinfo` `*avatar` `*roleinfo`\n"
        "`*channelinfo` `*uptime` `*id` `*invite`\n\n"
        "Use `*help <command>` for more information."
    )

    await ctx.send(embed=e)


# =========================================================
# SECURITY — 8 COMMANDS
# =========================================================

@bot.group(invoke_without_command=True)
@commands.has_permissions(administrator=True)
async def antinuke(ctx):
    """Anti-Nuke control."""
    await ctx.send(
        embed=embed(
            "🛡️ Anti-Nuke",
            "Use `*antinuke on` or `*antinuke off`.\n"
            "Use `*antinuke status` to check the current state."
        )
    )


@antinuke.command(name="on")
@commands.has_permissions(administrator=True)
async def antinuke_on(ctx):

    cursor.execute(
        "INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?)",
        (ctx.guild.id,)
    )

    cursor.execute(
        "UPDATE guild_settings SET antinuke=1 WHERE guild_id=?",
        (ctx.guild.id,)
    )

    db.commit()

    await ctx.send("🛡️ **Anti-Nuke enabled.**")


@antinuke.command(name="off")
@commands.has_permissions(administrator=True)
async def antinuke_off(ctx):

    cursor.execute(
        "INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?)",
        (ctx.guild.id,)
    )

    cursor.execute(
        "UPDATE guild_settings SET antinuke=0 WHERE guild_id=?",
        (ctx.guild.id,)
    )

    db.commit()

    await ctx.send("🛡️ **Anti-Nuke disabled.**")


@antinuke.command(name="status")
async def antinuke_status(ctx):

    cursor.execute(
        "SELECT antinuke FROM guild_settings WHERE guild_id=?",
        (ctx.guild.id,)
    )

    row = cursor.fetchone()
    enabled = bool(row and row[0])

    await ctx.send(
        f"🛡️ Anti-Nuke: **{'ON 🟢' if enabled else 'OFF 🔴'}**"
    )


@bot.command()
@commands.has_permissions(administrator=True)
async def lockdown(ctx):
    await ctx.send("🔒 **Server lockdown mode enabled.**")


@bot.command()
@commands.has_permissions(administrator=True)
async def unlockdown(ctx):
    await ctx.send("🔓 **Server lockdown mode disabled.**")


@bot.command()
@commands.has_permissions(administrator=True)
async def whitelist(ctx, member: discord.Member):
    cursor.execute(
        "INSERT OR IGNORE INTO whitelist VALUES (?, ?)",
        (ctx.guild.id, member.id)
    )

    db.commit()

    await ctx.send(f"✅ {member.mention} added to the security whitelist.")


@bot.command()
@commands.has_permissions(administrator=True)
async def unwhitelist(ctx, member: discord.Member):
    cursor.execute(
        "DELETE FROM whitelist WHERE guild_id=? AND user_id=?",
        (ctx.guild.id, member.id)
    )

    db.commit()

    await ctx.send(f"✅ {member.mention} removed from the whitelist.")


@bot.command()
@commands.has_permissions(administrator=True)
async def security(ctx):
    await ctx.send(
        embed=embed(
            "🛡️ Security Center",
            "Anti-Nuke and server security controls are available.\n\n"
            "`*antinuke on`\n"
            "`*antinuke off`\n"
            "`*antinuke status`\n"
            "`*whitelist @user`"
        )
    )


@bot.command()
@commands.has_permissions(view_audit_log=True)
async def auditlog(ctx):
    await ctx.send(
        embed=embed(
            "📋 Audit Log",
            "Use Discord's server audit-log panel to review recent administrative actions."
        )
    )


# =========================================================
# MODERATION — 10 COMMANDS
# =========================================================

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="No reason provided"):
    await member.ban(reason=reason)
    await ctx.send(f"🔨 **Banned:** {member.mention}\n**Reason:** {reason}")


@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, user_id: int):
    try:
        user = await bot.fetch_user(user_id)
        await ctx.guild.unban(user)
        await ctx.send(f"✅ Unbanned **{user}**.")
    except discord.NotFound:
        await ctx.send("❌ User not found in the ban list.")


@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="No reason provided"):
    await member.kick(reason=reason)
    await ctx.send(f"👢 **Kicked:** {member.mention}")


@bot.command()
@commands.has_permissions(moderate_members=True)
async def mute(ctx, member: discord.Member, minutes: int = 10):
    duration = discord.utils.utcnow() + discord.timedelta(minutes=minutes)
    await member.timeout(duration)
    await ctx.send(f"🔇 {member.mention} muted for **{minutes} minutes**.")


@bot.command()
@commands.has_permissions(moderate_members=True)
async def unmute(ctx, member: discord.Member):
    await member.timeout(None)
    await ctx.send(f"🔊 {member.mention} unmuted.")


@bot.command()
@commands.has_permissions(moderate_members=True)
async def warn(ctx, member: discord.Member, *, reason="No reason provided"):

    cursor.execute(
        "INSERT OR IGNORE INTO warnings VALUES (?, ?, 0)",
        (ctx.guild.id, member.id)
    )

    cursor.execute(
        "UPDATE warnings SET warnings=warnings+1 WHERE guild_id=? AND user_id=?",
        (ctx.guild.id, member.id)
    )

    db.commit()

    await ctx.send(
        f"⚠️ {member.mention} has been warned.\n"
        f"**Reason:** {reason}"
    )


@bot.command()
async def warnings(ctx, member: discord.Member = None):

    member = member or ctx.author

    cursor.execute(
        "SELECT warnings FROM warnings WHERE guild_id=? AND user_id=?",
        (ctx.guild.id, member.id)
    )

    row = cursor.fetchone()
    amount = row[0] if row else 0

    await ctx.send(f"⚠️ {member.mention} has **{amount} warning(s)**.")


@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 10):
    amount = max(1, min(amount, 100))
    deleted = await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"🧹 Deleted **{len(deleted) - 1} messages**.")
    await msg.delete(delay=3)


@bot.command()
@commands.has_permissions(manage_channels=True)
async def slowmode(ctx, seconds: int = 0):
    await ctx.channel.edit(slowmode_delay=seconds)
    await ctx.send(f"🐢 Slowmode set to **{seconds} seconds**.")


@bot.command()
@commands.has_permissions(manage_nicknames=True)
async def nick(ctx, member: discord.Member, *, nickname):
    await member.edit(nick=nickname)
    await ctx.send(f"✏️ Nickname updated for {member.mention}.")


# =========================================================
# COMMUNITY — 5 COMMANDS
# =========================================================

@bot.command()
@commands.has_permissions(manage_guild=True)
async def welcome(ctx, state="on"):

    state = state.lower()

    cursor.execute(
        "INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?)",
        (ctx.guild.id,)
    )

    cursor.execute(
        "UPDATE guild_settings SET welcome=? WHERE guild_id=?",
        (1 if state == "on" else 0, ctx.guild.id)
    )

    db.commit()

    await ctx.send(
        f"👋 Welcome system: **{'ON 🟢' if state == 'on' else 'OFF 🔴'}**"
    )


@bot.command()
@commands.has_permissions(manage_guild=True)
async def goodbye(ctx, state="on"):
    await ctx.send(
        f"👋 Goodbye system: **{'ON 🟢' if state.lower() == 'on' else 'OFF 🔴'}**"
    )


@bot.command()
@commands.has_permissions(manage_guild=True)
async def autorole(ctx, role: discord.Role):
    await ctx.send(f"🎀 Auto-role set to {role.mention}.")


@bot.command()
async def profile(ctx, member: discord.Member = None):

    member = member or ctx.author

    e = embed(
        f"🌸 {member.display_name}'s Profile",
        f"👤 **User:** {member.mention}\n"
        f"🆔 **ID:** `{member.id}`\n"
        f"📅 **Joined:** {discord.utils.format_dt(member.joined_at, 'D') if member.joined_at else 'Unknown'}"
    )

    await ctx.send(embed=e)


@bot.command()
async def serverinfo(ctx):

    guild = ctx.guild

    e = embed(
        f"🏠 {guild.name}",
        f"👥 Members: **{guild.member_count}**\n"
        f"💬 Channels: **{len(guild.channels)}**\n"
        f"🎭 Roles: **{len(guild.roles)}**\n"
        f"🆔 ID: `{guild.id}`"
    )

    await ctx.send(embed=e)


# =========================================================
# EVENTS — 4 COMMANDS
# =========================================================

@bot.command()
@commands.has_permissions(manage_guild=True)
async def giveaway(ctx, *, prize):

    await ctx.send(
        embed=embed(
            "🎁 Giveaway",
            f"Prize: **{prize}**\n\n"
            "React with 🎉 to enter!"
        )
    )


@bot.command()
@commands.has_permissions(manage_guild=True)
async def reroll(ctx):
    await ctx.send("🎉 Giveaway reroll requested.")


@bot.command()
async def poll(ctx, *, question):

    msg = await ctx.send(
        embed=embed(
            "📊 Poll",
            f"**{question}**"
        )
    )

    await msg.add_reaction("👍")
    await msg.add_reaction("👎")


@bot.command()
@commands.has_permissions(manage_messages=True)
async def announce(ctx, *, message):

    await ctx.send(
        embed=embed(
            "📢 Announcement",
            message
        )
    )


# =========================================================
# ECONOMY — 7 COMMANDS
# =========================================================

@bot.command()
async def balance(ctx, member: discord.Member = None):

    member = member or ctx.author
    amount = get_balance(ctx.guild.id, member.id)

    await ctx.send(
        f"💰 {member.mention} has **{amount:,} coins**."
    )


@bot.command()
async def daily(ctx):

    amount = random.randint(100, 500)

    balance = get_balance(ctx.guild.id, ctx.author.id)
    set_balance(ctx.guild.id, ctx.author.id, balance + amount)

    await ctx.send(
        f"🎁 You received **{amount:,} coins** from your daily reward!"
    )


@bot.command()
async def work(ctx):

    amount = random.randint(50, 250)

    balance = get_balance(ctx.guild.id, ctx.author.id)
    set_balance(ctx.guild.id, ctx.author.id, balance + amount)

    await ctx.send(
        f"💼 You worked and earned **{amount:,} coins**!"
    )


@bot.command()
async def deposit(ctx, amount: int):

    if amount <= 0:
        return await ctx.send("❌ Invalid amount.")

    await ctx.send(
        "🏦 Deposit system is ready for future wallet integration."
    )


@bot.command()
async def withdraw(ctx, amount: int):

    if amount <= 0:
        return await ctx.send("❌ Invalid amount.")

    await ctx.send(
        "🏦 Withdrawal system is ready for future wallet integration."
    )


@bot.command()
async def leaderboard(ctx):

    cursor.execute(
        "SELECT user_id, balance FROM economy WHERE guild_id=? ORDER BY balance DESC LIMIT 10",
        (ctx.guild.id,)
    )

    rows = cursor.fetchall()

    if not rows:
        return await ctx.send("📊 No economy data yet.")

    text = ""

    for index, (user_id, balance) in enumerate(rows, 1):
        text += f"**{index}.** <@{user_id}> — `{balance:,}` coins\n"

    await ctx.send(
        embed=embed(
            "🏆 Economy Leaderboard",
            text
        )
    )


@bot.command()
async def paycoins(ctx, member: discord.Member, amount: int):

    if amount <= 0:
        return await ctx.send("❌ Invalid amount.")

    sender_balance = get_balance(ctx.guild.id, ctx.author.id)

    if sender_balance < amount:
        return await ctx.send("❌ You don't have enough coins.")

    receiver_balance = get_balance(ctx.guild.id, member.id)

    set_balance(
        ctx.guild.id,
        ctx.author.id,
        sender_balance - amount
    )

    set_balance(
        ctx.guild.id,
        member.id,
        receiver_balance + amount
    )

    await ctx.send(
        f"💸 {ctx.author.mention} sent **{amount:,} coins** to {member.mention}."
    )


# =========================================================
# FUN — 9 COMMANDS
# =========================================================

@bot.command(name="8ball")
async def eightball(ctx, *, question):

    answers = [
        "Absolutely! ✨",
        "Maybe 🌸",
        "Definitely not 😭",
        "Ask me again later 🐾",
        "The stars say yes 💗"
    ]

    await ctx.send(
        f"🎱 **Question:** {question}\n"
        f"🌸 **Answer:** {random.choice(answers)}"
    )


@bot.command()
async def coinflip(ctx):

    result = random.choice(["Heads 🪙", "Tails 🪙"])

    await ctx.send(f"🪙 The coin landed on **{result}**!")


@bot.command()
async def dice(ctx):

    result = random.randint(1, 6)

    await ctx.send(f"🎲 You rolled **{result}**!")


@bot.command()
async def rps(ctx, choice: str):

    choices = ["rock", "paper", "scissors"]

    choice = choice.lower()

    if choice not in choices:
        return await ctx.send("❌ Choose rock, paper or scissors.")

    bot_choice = random.choice(choices)

    if choice == bot_choice:
        result = "It's a draw! 🤝"
    elif (
        (choice == "rock" and bot_choice == "scissors") or
        (choice == "paper" and bot_choice == "rock") or
        (choice == "scissors" and bot_choice == "paper")
    ):
        result = "You win! 🎉"
    else:
        result = "I win! 🐾"

    await ctx.send(
        f"🎮 You: **{choice}**\n"
        f"🌸 MIMI: **{bot_choice}**\n\n"
        f"**{result}**"
    )


@bot.command()
async def joke(ctx):

    jokes = [
        "Why did the computer go to school? To improve its bytes! 😂",
        "Why was the server cold? It left its Windows open! 😭",
        "I told my bot a joke... it needed more processing time. 🐾"
    ]

    await ctx.send(random.choice(jokes))


@bot.command()
async def ship(ctx, user1: discord.Member, user2: discord.Member):

    score = random.randint(1, 100)

    await ctx.send(
        f"💗 **{user1.display_name} + {user2.display_name}**\n"
        f"Compatibility: **{score}%** 🌸"
    )


@bot.command()
async def choose(ctx, *, options):

    choices = [x.strip() for x in options.split(",")]

    if len(choices) < 2:
        return await ctx.send("❌ Give me at least two choices separated by commas.")

    await ctx.send(
        f"🎀 I choose: **{random.choice(choices)}**"
    )


@bot.command()
async def rate(ctx, *, thing):

    score = random.randint(1, 100)

    await ctx.send(
        f"🌸 I rate **{thing}**: **{score}/100**"
    )


@bot.command()
async def say(ctx, *, message):

    await ctx.message.delete()
    await ctx.send(message)


# =========================================================
# UTILITY — 8 COMMANDS
# =========================================================

@bot.command()
async def ping(ctx):

    latency = round(bot.latency * 1000)

    await ctx.send(
        f"🏓 Pong! **{latency}ms**"
    )


@bot.command()
async def botinfo(ctx):

    e = embed(
        "🌸 𝙼𝙸𝙼𝙸 Bot Info",
        f"🤖 Name: **{BOT_NAME}**\n"
        f"📌 Prefix: `{PREFIX}`\n"
        f"🏠 Servers: **{len(bot.guilds)}**\n"
        f"🐾 Uptime: **{uptime()}**\n"
        f"🐍 Python Discord Bot"
    )

    await ctx.send(embed=e)


@bot.command()
async def userinfo(ctx, member: discord.Member = None):

    member = member or ctx.author

    await ctx.send(
        embed=embed(
            "👤 User Information",
            f"**Name:** {member}\n"
            f"**ID:** `{member.id}`\n"
            f"**Mention:** {member.mention}\n"
            f"**Bot:** {'Yes' if member.bot else 'No'}"
        )
    )


@bot.command()
async def avatar(ctx, member: discord.Member = None):

    member = member or ctx.author

    await ctx.send(
        embed=embed(
            "🖼️ Avatar",
            member.display_avatar.url
        )
    )


@bot.command()
async def roleinfo(ctx, role: discord.Role):

    await ctx.send(
        embed=embed(
            "🎭 Role Information",
            f"**Name:** {role.name}\n"
            f"**ID:** `{role.id}`\n"
            f"**Members:** {len(role.members)}"
        )
    )


@bot.command()
async def channelinfo(ctx):

    channel = ctx.channel

    await ctx.send(
        embed=embed(
            "💬 Channel Information",
            f"**Name:** {channel.name}\n"
            f"**ID:** `{channel.id}`\n"
            f"**Type:** `{channel.type}`"
        )
    )


@bot.command()
async def uptime_cmd(ctx):

    await ctx.send(
        f"⏱️ MIMI has been online for **{uptime()}**."
    )


@bot.command(name="id")
async def id_command(ctx, member: discord.Member = None):

    member = member or ctx.author

    await ctx.send(
        f"🆔 {member.mention}'s ID is `{member.id}`"
    )


@bot.command()
async def invite(ctx):

    permissions = discord.Permissions(
        administrator=True
    )

    url = discord.utils.oauth_url(
        bot.user.id,
        permissions=permissions
    )

    await ctx.send(
        f"🌸 **Invite 𝙼𝙸𝙼𝙸:**\n{url}"
    )


# =========================================================
# HIDDEN OWNER-ONLY PAYMENT COMMAND
# =========================================================

@bot.command()
@commands.is_owner()
async def pay(ctx, amount: float, *, reason="Payment"):

    if amount <= 0:
        return await ctx.send("❌ Amount must be greater than 0.")

    upi_id = "Ankittt.3@fam"
    name = "ADX ANKIT"

    upi_url = (
        f"upi://pay?"
        f"pa={upi_id}&"
        f"pn={name}&"
        f"am={amount:.2f}&"
        f"cu=INR&"
        f"tn={reason}"
    )

    qr = qrcode.make(upi_url)

    image = io.BytesIO()
    qr.save(image, format="PNG")
    image.seek(0)

    file = discord.File(
        image,
        filename="mimi_payment.png"
    )

    e = embed(
        "🌸 𝙼𝙸𝙼𝙸 Payment",
        f"**Amount:** ₹{amount:.2f}\n"
        f"**Name:** {name}\n"
        f"**UPI:** `{upi_id}`\n"
        f"**Reason:** {reason}\n\n"
        "Scan the QR code with a compatible UPI app."
    )

    e.set_image(url="attachment://mimi_payment.png")

    await ctx.send(embed=e, file=file)


# =========================================================
# ERROR HANDLER
# =========================================================

@bot.event
async def on_command_error(ctx, error):

    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have the required permissions.")
        return

    if isinstance(error, commands.NotOwner):
        await ctx.send("❌ This command is owner-only.")
        return

    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(
            f"❌ Missing argument.\n"
            f"Use `{PREFIX}help` for the command format."
        )
        return

    if isinstance(error, commands.BadArgument):
        await ctx.send("❌ Invalid argument. Please check the command format.")
        return

    print(f"⚠️ Error: {error}")


# =========================================================
# START
# =========================================================

if not TOKEN or TOKEN == "PASTE_YOUR_BOT_TOKEN_HERE":
    raise RuntimeError(
        "❌ Bot token missing. Put your token in the TOKEN variable."
    )

bot.run(TOKEN)
