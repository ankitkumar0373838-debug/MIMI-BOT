import discord
from discord.ext import commands
from datetime import timedelta
import sqlite3
import random
import time
import io
import asyncio
import qrcode

# =========================================================
# 𝙼𝙸𝙼𝙸🌸 — Discord Bot
# =========================================================

TOKEN = "PASTE_YOUR_NEW_BOT_TOKEN_HERE"
PREFIX = "*"
BOT_NAME = "𝙼𝙸𝙼𝙸🌸"
UPI_ID = "Ankittt.3@fam"
PAYMENT_NAME = "ADX ANKIT"

# IMPORTANT:
# Never post your real token in screenshots or public GitHub.
# If your old token was exposed, RESET it in Discord Developer Portal
# and paste the NEW token above.

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

DB = sqlite3.connect("mimi.db", check_same_thread=False)
CUR = DB.cursor()

CUR.execute("""
CREATE TABLE IF NOT EXISTS guild_settings (
    guild_id INTEGER PRIMARY KEY,
    antinuke INTEGER DEFAULT 0,
    welcome INTEGER DEFAULT 0,
    goodbye INTEGER DEFAULT 0,
    autorole_id INTEGER DEFAULT 0
)
""")

CUR.execute("""
CREATE TABLE IF NOT EXISTS warnings (
    guild_id INTEGER,
    user_id INTEGER,
    reason TEXT
)
""")

CUR.execute("""
CREATE TABLE IF NOT EXISTS economy (
    guild_id INTEGER,
    user_id INTEGER,
    wallet INTEGER DEFAULT 0,
    bank INTEGER DEFAULT 0,
    daily_at INTEGER DEFAULT 0,
    PRIMARY KEY (guild_id, user_id)
)
""")

CUR.execute("""
CREATE TABLE IF NOT EXISTS whitelist (
    guild_id INTEGER,
    user_id INTEGER,
    PRIMARY KEY (guild_id, user_id)
)
""")

CUR.execute("""
CREATE TABLE IF NOT EXISTS giveaways (
    message_id INTEGER PRIMARY KEY,
    channel_id INTEGER,
    prize TEXT,
    host_id INTEGER
)
""")

DB.commit()

# =========================================================
# HELPERS
# =========================================================

def make_embed(title, description="", color=0xFF8CC6):
    return discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=discord.utils.utcnow()
    )

def is_whitelisted(guild_id, user_id):
    CUR.execute(
        "SELECT 1 FROM whitelist WHERE guild_id=? AND user_id=?",
        (guild_id, user_id)
    )
    return CUR.fetchone() is not None

def ensure_economy(guild_id, user_id):
    CUR.execute(
        "INSERT OR IGNORE INTO economy(guild_id,user_id,wallet,bank,daily_at) VALUES(?,?,?,?,?)",
        (guild_id, user_id, 0, 0, 0)
    )
    DB.commit()

def get_money(guild_id, user_id):
    ensure_economy(guild_id, user_id)
    CUR.execute(
        "SELECT wallet, bank FROM economy WHERE guild_id=? AND user_id=?",
        (guild_id, user_id)
    )
    row = CUR.fetchone()
    return row if row else (0, 0)

def set_money(guild_id, user_id, wallet=None, bank=None):
    ensure_economy(guild_id, user_id)
    old_wallet, old_bank = get_money(guild_id, user_id)
    if wallet is None:
        wallet = old_wallet
    if bank is None:
        bank = old_bank
    CUR.execute(
        "UPDATE economy SET wallet=?, bank=? WHERE guild_id=? AND user_id=?",
        (wallet, bank, guild_id, user_id)
    )
    DB.commit()

def get_settings(guild_id):
    CUR.execute(
        "SELECT antinuke,welcome,goodbye,autorole_id FROM guild_settings WHERE guild_id=?",
        (guild_id,)
    )
    row = CUR.fetchone()
    if not row:
        CUR.execute(
            "INSERT INTO guild_settings(guild_id) VALUES(?)",
            (guild_id,)
        )
        DB.commit()
        return (0, 0, 0, 0)
    return row

def set_setting(guild_id, column, value):
    allowed = {"antinuke", "welcome", "goodbye", "autorole_id"}
    if column not in allowed:
        return
    CUR.execute(
        f"UPDATE guild_settings SET {column}=? WHERE guild_id=?",
        (value, guild_id)
    )
    DB.commit()

def format_uptime():
    seconds = int(time.time() - START_TIME)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    return f"{days}d {hours}h {minutes}m {seconds}s"

def parse_duration(text):
    try:
        value = int(text[:-1])
        unit = text[-1].lower()
        multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        if unit not in multipliers or value <= 0:
            return None
        return value * multipliers[unit]
    except Exception:
        return None

# =========================================================
# EVENTS
# =========================================================

@bot.event
async def on_ready():
    activity = discord.Activity(
        type=discord.ActivityType.watching,
        name="over you with tiny paws & big love 🐾💗"
    )
    await bot.change_presence(status=discord.Status.online, activity=activity)
    print("=" * 55)
    print(f"🌸 {BOT_NAME} is online as {bot.user}")
    print(f"📚 Prefix: {PREFIX}")
    print(f"🏠 Servers: {len(bot.guilds)}")
    print("🚀 MIMI IS FULLY READY")
    print("=" * 55)

@bot.event
async def on_member_join(member):
    antinuke, welcome, goodbye, autorole_id = get_settings(member.guild.id)

    if autorole_id:
        role = member.guild.get_role(autorole_id)
        if role:
            try:
                await member.add_roles(role, reason="MIMI autorole")
            except discord.HTTPException:
                pass

    if welcome:
        channel = member.guild.system_channel
        if channel:
            try:
                await channel.send(
                    f"🌸 Welcome {member.mention} to **{member.guild.name}**! 🐾💗"
                )
            except discord.HTTPException:
                pass

@bot.event
async def on_member_remove(member):
    _, _, goodbye, _ = get_settings(member.guild.id)
    if goodbye:
        channel = member.guild.system_channel
        if channel:
            try:
                await channel.send(
                    f"👋 **{member.display_name}** left the server. Take care! 🌸"
                )
            except discord.HTTPException:
                pass

# Basic anti-nuke protection for channel/role deletion.
# It only acts when *antinuke is ON* and the actor is not whitelisted.
async def check_antindeletion(guild, target_name):
    antinuke, _, _, _ = get_settings(guild.id)
    if not antinuke:
        return

    try:
        async for entry in guild.audit_logs(limit=1):
            if entry.action not in (
                discord.AuditLogAction.channel_delete,
                discord.AuditLogAction.role_delete
            ):
                return

            actor = entry.user
            if actor.id == bot.user.id or is_whitelisted(guild.id, actor.id):
                return

            try:
                await guild.ban(
                    actor,
                    reason=f"MIMI Anti-Nuke: deleted {target_name}"
                )
            except discord.HTTPException:
                pass
            break
    except (discord.Forbidden, discord.HTTPException):
        pass

@bot.event
async def on_guild_channel_delete(channel):
    await check_antindeletion(channel.guild, "a channel")

@bot.event
async def on_guild_role_delete(role):
    await check_antindeletion(role.guild, "a role")

# =========================================================
# 1. HELP
# =========================================================

@bot.command(name="help")
async def help_command(ctx):
    e = make_embed(
        "🌸 𝙼𝙸𝙼𝙸 — Help Menu",
        f"Prefix: `{PREFIX}`\n**60 commands available**\n\n"
        "💗 **Core & Utility**\n"
        "`*help` `*ping` `*botinfo` `*uptime` `*serverinfo` `*userinfo` "
        "`*avatar` `*roleinfo` `*channelinfo` `*id` `*invite`\n\n"
        "🛡️ **Security**\n"
        "`*antinuke` `*lockdown` `*unlockdown` `*whitelist` "
        "`*unwhitelist` `*security`\n\n"
        "🔨 **Moderation**\n"
        "`*ban` `*unban` `*kick` `*mute` `*unmute` `*warn` `*warnings` "
        "`*clear` `*slowmode` `*nick`\n\n"
        "🌸 **Community**\n"
        "`*welcome` `*goodbye` `*autorole` `*profile`\n\n"
        "💰 **Economy**\n"
        "`*balance` `*daily` `*work` `*deposit` `*withdraw` "
        "`*leaderboard` `*paycoins`\n\n"
        "🎮 **Fun**\n"
        "`*8ball` `*coinflip` `*dice` `*rps` `*joke` `*ship` "
        "`*choose` `*rate` `*say`\n\n"
        "🎉 **Events**\n"
        "`*poll` `*announce` `*giveaway` `*reroll`\n\n"
        "🔧 **Extra Utility**\n"
        "`*remind` `*servericon` `*roles` `*channels` `*members` "
        "`*customize` `*suggest` `*serverbanner` `*membercount`\n\n"
        "🔒 Some owner-only commands are intentionally hidden."
    )
    await ctx.send(embed=e)

# =========================================================
# 2. CORE / UTILITY
# =========================================================

@bot.command()
async def ping(ctx):
    await ctx.send(embed=make_embed("🏓 Pong!", f"`{round(bot.latency * 1000)}ms`"))

@bot.command()
async def botinfo(ctx):
    e = make_embed(
        "🌸 MIMI Bot Info",
        f"**Name:** {BOT_NAME}\n"
        f"**Developer:** ADX ANKIT\n"
        f"**Servers:** {len(bot.guilds)}\n"
        f"**Users:** {len(bot.users)}\n"
        f"**Prefix:** `{PREFIX}`\n"
        f"**Uptime:** {format_uptime()}"
    )
    await ctx.send(embed=e)

@bot.command()
async def uptime(ctx):
    await ctx.send(embed=make_embed("⏱️ Uptime", format_uptime()))

@bot.command()
@commands.guild_only()
async def serverinfo(ctx):
    g = ctx.guild
    e = make_embed(
        f"🏠 {g.name}",
        f"**Owner:** {g.owner.mention if g.owner else 'Unknown'}\n"
        f"**Members:** {g.member_count}\n"
        f"**Channels:** {len(g.channels)}\n"
        f"**Roles:** {len(g.roles)}\n"
        f"**Created:** <t:{int(g.created_at.timestamp())}:D>"
    )
    if g.icon:
        e.set_thumbnail(url=g.icon.url)
    await ctx.send(embed=e)

@bot.command()
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    e = make_embed(
        f"👤 {member.display_name}",
        f"**Username:** {member}\n"
        f"**ID:** `{member.id}`\n"
        f"**Joined:** <t:{int(member.joined_at.timestamp())}:D>\n"
        f"**Created:** <t:{int(member.created_at.timestamp())}:D>\n"
        f"**Top Role:** {member.top_role.mention}"
    )
    e.set_thumbnail(url=member.display_avatar.url)
    await ctx.send(embed=e)

@bot.command()
async def avatar(ctx, member: discord.Member = None):
    member = member or ctx.author
    e = make_embed("🖼️ Avatar", f"[Open Avatar]({member.display_avatar.url})")
    e.set_image(url=member.display_avatar.url)
    await ctx.send(embed=e)

@bot.command()
async def roleinfo(ctx, role: discord.Role):
    await ctx.send(embed=make_embed(
        f"🎭 {role.name}",
        f"**ID:** `{role.id}`\n"
        f"**Members:** {len(role.members)}\n"
        f"**Position:** {role.position}\n"
        f"**Mentionable:** {role.mentionable}"
    ))

@bot.command()
async def channelinfo(ctx, channel: discord.abc.GuildChannel = None):
    channel = channel or ctx.channel
    await ctx.send(embed=make_embed(
        "📺 Channel Info",
        f"**Name:** {channel.name}\n"
        f"**ID:** `{channel.id}`\n"
        f"**Type:** `{channel.type}`\n"
        f"**Created:** <t:{int(channel.created_at.timestamp())}:D>"
    ))

@bot.command()
async def id(ctx, member: discord.Member = None):
    member = member or ctx.author
    await ctx.send(f"🆔 {member.mention}: `{member.id}`")

@bot.command()
async def invite(ctx):
    perms = discord.Permissions(
        view_channel=True,
        send_messages=True,
        embed_links=True,
        attach_files=True,
        read_message_history=True,
        add_reactions=True,
        connect=True,
        speak=True,
        manage_messages=True,
        moderate_members=True
    )
    url = discord.utils.oauth_url(bot.user.id, permissions=perms)
    await ctx.send(embed=make_embed("🔗 Invite MIMI", f"[Click here to invite MIMI]({url})"))

# =========================================================
# 3. SECURITY
# =========================================================

@bot.group(name="antinuke", invoke_without_command=True)
@commands.has_guild_permissions(administrator=True)
async def antinuke(ctx):
    status = get_settings(ctx.guild.id)[0]
    state = "🟢 ON" if status else "🔴 OFF"
    await ctx.send(embed=make_embed(
        "🛡️ Anti-Nuke",
        f"Current status: **{state}**\nUse `*antinuke on` or `*antinuke off`."
    ))

@antinuke.command(name="on")
async def antinuke_on(ctx):
    set_setting(ctx.guild.id, "antinuke", 1)
    await ctx.send(embed=make_embed("🛡️ Anti-Nuke ON", "Basic channel/role deletion protection is enabled."))

@antinuke.command(name="off")
async def antinuke_off(ctx):
    set_setting(ctx.guild.id, "antinuke", 0)
    await ctx.send(embed=make_embed("🛡️ Anti-Nuke OFF", "Anti-Nuke protection is disabled."))

@bot.command()
@commands.has_guild_permissions(administrator=True)
async def lockdown(ctx):
    everyone = ctx.guild.default_role
    changed = 0
    for channel in ctx.guild.text_channels:
        try:
            await channel.set_permissions(
                everyone,
                send_messages=False,
                reason="MIMI lockdown"
            )
            changed += 1
        except discord.HTTPException:
            pass
    await ctx.send(embed=make_embed("🔒 Server Lockdown", f"Locked **{changed}** text channels."))

@bot.command()
@commands.has_guild_permissions(administrator=True)
async def unlockdown(ctx):
    everyone = ctx.guild.default_role
    changed = 0
    for channel in ctx.guild.text_channels:
        try:
            await channel.set_permissions(
                everyone,
                send_messages=None,
                reason="MIMI unlockdown"
            )
            changed += 1
        except discord.HTTPException:
            pass
    await ctx.send(embed=make_embed("🔓 Server Unlocked", f"Unlocked **{changed}** text channels."))

@bot.command()
@commands.has_guild_permissions(administrator=True)
async def whitelist(ctx, member: discord.Member):
    CUR.execute(
        "INSERT OR IGNORE INTO whitelist(guild_id,user_id) VALUES(?,?)",
        (ctx.guild.id, member.id)
    )
    DB.commit()
    await ctx.send(embed=make_embed("✅ Whitelisted", f"{member.mention} is now whitelisted."))

@bot.command()
@commands.has_guild_permissions(administrator=True)
async def unwhitelist(ctx, member: discord.Member):
    CUR.execute(
        "DELETE FROM whitelist WHERE guild_id=? AND user_id=?",
        (ctx.guild.id, member.id)
    )
    DB.commit()
    await ctx.send(embed=make_embed("❌ Removed", f"{member.mention} was removed from whitelist."))

@bot.command()
@commands.has_guild_permissions(administrator=True)
async def security(ctx):
    antinuke, welcome, goodbye, autorole_id = get_settings(ctx.guild.id)
    await ctx.send(embed=make_embed(
        "🛡️ Security Status",
        f"**Anti-Nuke:** {'🟢 ON' if antinuke else '🔴 OFF'}\n"
        f"**Welcome:** {'🟢 ON' if welcome else '🔴 OFF'}\n"
        f"**Goodbye:** {'🟢 ON' if goodbye else '🔴 OFF'}\n"
        f"**Auto Role:** {f'<@&{autorole_id}>' if autorole_id else '🔴 OFF'}"
    ))

# =========================================================
# 4. MODERATION
# =========================================================

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="No reason provided"):
    await member.ban(reason=reason)
    await ctx.send(embed=make_embed("🔨 Banned", f"{member.mention} was banned.\n**Reason:** {reason}"))

@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, user_id: int):
    user = await bot.fetch_user(user_id)
    await ctx.guild.unban(user)
    await ctx.send(embed=make_embed("🔓 Unbanned", f"{user} was unbanned."))

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="No reason provided"):
    await member.kick(reason=reason)
    await ctx.send(embed=make_embed("👢 Kicked", f"{member.mention} was kicked.\n**Reason:** {reason}"))

@bot.command()
@commands.has_permissions(moderate_members=True)
async def mute(ctx, member: discord.Member, minutes: int = 10, *, reason="No reason provided"):
    if minutes < 1 or minutes > 40320:
        return await ctx.send("❌ Minutes must be between 1 and 40320.")
    until = discord.utils.utcnow() + timedelta(minutes=minutes)
    await member.timeout(until, reason=reason)
    await ctx.send(embed=make_embed(
        "🔇 Muted",
        f"{member.mention} timed out for **{minutes} minutes**."
    ))

@bot.command()
@commands.has_permissions(moderate_members=True)
async def unmute(ctx, member: discord.Member):
    await member.timeout(None, reason="MIMI unmute")
    await ctx.send(embed=make_embed("🔊 Unmuted", f"{member.mention} can speak again."))

@bot.command()
@commands.has_permissions(moderate_members=True)
async def warn(ctx, member: discord.Member, *, reason="No reason provided"):
    CUR.execute(
        "INSERT INTO warnings(guild_id,user_id,reason) VALUES(?,?,?)",
        (ctx.guild.id, member.id, reason)
    )
    DB.commit()
    count = CUR.execute(
        "SELECT COUNT(*) FROM warnings WHERE guild_id=? AND user_id=?",
        (ctx.guild.id, member.id)
    ).fetchone()[0]
    await ctx.send(embed=make_embed(
        "⚠️ Warning",
        f"{member.mention} received warning **#{count}**.\n**Reason:** {reason}"
    ))

@bot.command()
@commands.has_permissions(moderate_members=True)
async def warnings(ctx, member: discord.Member = None):
    member = member or ctx.author
    rows = CUR.execute(
        "SELECT reason FROM warnings WHERE guild_id=? AND user_id=?",
        (ctx.guild.id, member.id)
    ).fetchall()
    if not rows:
        return await ctx.send(embed=make_embed("📋 Warnings", f"{member.mention} has no warnings."))
    text = "\n".join(f"**{i}.** {row[0]}" for i, row in enumerate(rows, 1))
    await ctx.send(embed=make_embed(f"📋 Warnings — {member}", text[:4000]))

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 10):
    if amount < 1 or amount > 100:
        return await ctx.send("❌ Amount must be between 1 and 100.")
    deleted = await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(embed=make_embed("🧹 Cleared", f"Deleted **{len(deleted)-1}** messages."))
    await asyncio.sleep(3)
    try:
        await msg.delete()
    except discord.HTTPException:
        pass

@bot.command()
@commands.has_permissions(manage_channels=True)
async def slowmode(ctx, seconds: int = 0):
    if seconds < 0 or seconds > 21600:
        return await ctx.send("❌ Seconds must be between 0 and 21600.")
    await ctx.channel.edit(slowmode_delay=seconds)
    await ctx.send(embed=make_embed("🐢 Slowmode", f"Slowmode set to **{seconds}s**."))

@bot.command()
@commands.has_permissions(manage_nicknames=True)
async def nick(ctx, member: discord.Member, *, nickname: str = None):
    await member.edit(nick=nickname)
    await ctx.send(embed=make_embed("✏️ Nickname Updated", f"Updated nickname for {member.mention}."))

# =========================================================
# 5. COMMUNITY
# =========================================================

@bot.command()
@commands.has_guild_permissions(administrator=True)
async def welcome(ctx, mode: str = None):
    if mode is None:
        state = get_settings(ctx.guild.id)[1]
        return await ctx.send(f"Welcome system: **{'ON' if state else 'OFF'}**. Use `*welcome on/off`.")
    mode = mode.lower()
    if mode not in ("on", "off"):
        return await ctx.send("❌ Use `*welcome on` or `*welcome off`.")
    set_setting(ctx.guild.id, "welcome", 1 if mode == "on" else 0)
    await ctx.send(embed=make_embed("🌸 Welcome", f"Welcome system is now **{mode.upper()}**."))

@bot.command()
@commands.has_guild_permissions(administrator=True)
async def goodbye(ctx, mode: str = None):
    if mode is None:
        state = get_settings(ctx.guild.id)[2]
        return await ctx.send(f"Goodbye system: **{'ON' if state else 'OFF'}**. Use `*goodbye on/off`.")
    mode = mode.lower()
    if mode not in ("on", "off"):
        return await ctx.send("❌ Use `*goodbye on` or `*goodbye off`.")
    set_setting(ctx.guild.id, "goodbye", 1 if mode == "on" else 0)
    await ctx.send(embed=make_embed("👋 Goodbye", f"Goodbye system is now **{mode.upper()}**."))

@bot.command()
@commands.has_guild_permissions(administrator=True)
async def autorole(ctx, role: discord.Role = None):
    if role is None:
        rid = get_settings(ctx.guild.id)[3]
        return await ctx.send(
            f"Auto role: **{ctx.guild.get_role(rid).mention if rid and ctx.guild.get_role(rid) else 'OFF'}**"
        )
    set_setting(ctx.guild.id, "autorole_id", role.id)
    await ctx.send(embed=make_embed("🎭 Auto Role", f"New members will receive {role.mention}."))

@bot.command()
async def profile(ctx, member: discord.Member = None):
    member = member or ctx.author
    wallet, bank = get_money(ctx.guild.id, member.id)
    warns = CUR.execute(
        "SELECT COUNT(*) FROM warnings WHERE guild_id=? AND user_id=?",
        (ctx.guild.id, member.id)
    ).fetchone()[0]
    await ctx.send(embed=make_embed(
        f"🌸 {member.display_name}'s Profile",
        f"**Wallet:** ₹{wallet}\n"
        f"**Bank:** ₹{bank}\n"
        f"**Warnings:** {warns}\n"
        f"**Roles:** {max(0, len(member.roles)-1)}"
    ))

# =========================================================
# 6. ECONOMY
# =========================================================

@bot.command()
async def balance(ctx, member: discord.Member = None):
    member = member or ctx.author
    wallet, bank = get_money(ctx.guild.id, member.id)
    await ctx.send(embed=make_embed(
        f"💰 {member.display_name}'s Balance",
        f"**Wallet:** ₹{wallet}\n**Bank:** ₹{bank}\n**Total:** ₹{wallet+bank}"
    ))

@bot.command()
async def daily(ctx):
    ensure_economy(ctx.guild.id, ctx.author.id)
    now = int(time.time())
    row = CUR.execute(
        "SELECT daily_at FROM economy WHERE guild_id=? AND user_id=?",
        (ctx.guild.id, ctx.author.id)
    ).fetchone()
    last = row[0] if row else 0
    if now - last < 86400:
        remaining = 86400 - (now - last)
        return await ctx.send(f"⏳ Daily is on cooldown. Try again in **{remaining//3600}h {(remaining%3600)//60}m**.")
    reward = random.randint(100, 300)
    wallet, bank = get_money(ctx.guild.id, ctx.author.id)
    set_money(ctx.guild.id, ctx.author.id, wallet + reward, bank)
    CUR.execute(
        "UPDATE economy SET daily_at=? WHERE guild_id=? AND user_id=?",
        (now, ctx.guild.id, ctx.author.id)
    )
    DB.commit()
    await ctx.send(embed=make_embed("🎁 Daily Reward", f"You received **₹{reward}**!"))

@bot.command()
async def work(ctx):
    reward = random.randint(50, 200)
    wallet, bank = get_money(ctx.guild.id, ctx.author.id)
    set_money(ctx.guild.id, ctx.author.id, wallet + reward, bank)
    await ctx.send(embed=make_embed("💼 Work Complete", f"You earned **₹{reward}**."))

@bot.command()
async def deposit(ctx, amount: int):
    wallet, bank = get_money(ctx.guild.id, ctx.author.id)
    if amount <= 0 or amount > wallet:
        return await ctx.send("❌ Invalid amount or insufficient wallet balance.")
    set_money(ctx.guild.id, ctx.author.id, wallet - amount, bank + amount)
    await ctx.send(embed=make_embed("🏦 Deposited", f"Moved **₹{amount}** to your bank."))

@bot.command()
async def withdraw(ctx, amount: int):
    wallet, bank = get_money(ctx.guild.id, ctx.author.id)
    if amount <= 0 or amount > bank:
        return await ctx.send("❌ Invalid amount or insufficient bank balance.")
    set_money(ctx.guild.id, ctx.author.id, wallet + amount, bank - amount)
    await ctx.send(embed=make_embed("🏧 Withdrawn", f"Moved **₹{amount}** to your wallet."))

@bot.command()
async def leaderboard(ctx):
    rows = CUR.execute(
        "SELECT user_id,wallet,bank FROM economy WHERE guild_id=? ORDER BY (wallet+bank) DESC LIMIT 10",
        (ctx.guild.id,)
    ).fetchall()
    if not rows:
        return await ctx.send(embed=make_embed("🏆 Leaderboard", "No economy data yet."))
    lines = []
    for i, (uid, wallet, bank) in enumerate(rows, 1):
        lines.append(f"**{i}.** <@{uid}> — ₹{wallet+bank}")
    await ctx.send(embed=make_embed("🏆 Economy Leaderboard", "\n".join(lines)))

@bot.command()
async def paycoins(ctx, member: discord.Member, amount: int):
    if member.bot or member.id == ctx.author.id:
        return await ctx.send("❌ Choose another human member.")
    if amount <= 0:
        return await ctx.send("❌ Amount must be positive.")
    wallet, bank = get_money(ctx.guild.id, ctx.author.id)
    if amount > wallet:
        return await ctx.send("❌ You don't have enough wallet balance.")
    target_wallet, target_bank = get_money(ctx.guild.id, member.id)
    set_money(ctx.guild.id, ctx.author.id, wallet - amount, bank)
    set_money(ctx.guild.id, member.id, target_wallet + amount, target_bank)
    await ctx.send(embed=make_embed(
        "💸 Payment Sent",
        f"{ctx.author.mention} sent **₹{amount}** to {member.mention}."
    ))

# =========================================================
# 7. FUN
# =========================================================

@bot.command(name="8ball")
async def eightball(ctx, *, question: str):
    answers = [
        "Yes! 🌸", "Nope! 🐾", "Definitely!", "Probably.",
        "Ask me later.", "I think so!", "Not looking good 😭", "Absolutely not!"
    ]
    await ctx.send(embed=make_embed("🎱 8Ball", f"**Question:** {question}\n**Answer:** {random.choice(answers)}"))

@bot.command()
async def coinflip(ctx):
    await ctx.send(embed=make_embed("🪙 Coin Flip", random.choice(["**Heads!**", "**Tails!**"])))

@bot.command()
async def dice(ctx):
    await ctx.send(embed=make_embed("🎲 Dice", f"You rolled **{random.randint(1, 6)}**."))

@bot.command()
async def rps(ctx, choice: str):
    choice = choice.lower()
    choices = ["rock", "paper", "scissors"]
    if choice not in choices:
        return await ctx.send("❌ Choose `rock`, `paper`, or `scissors`.")
    bot_choice = random.choice(choices)
    if choice == bot_choice:
        result = "It's a draw! 🤝"
    elif (choice, bot_choice) in [("rock","scissors"),("paper","rock"),("scissors","paper")]:
        result = "You win! 🎉"
    else:
        result = "MIMI wins! 🌸"
    await ctx.send(embed=make_embed("✊ Rock Paper Scissors", f"You: **{choice}**\nMIMI: **{bot_choice}**\n\n{result}"))

@bot.command()
async def joke(ctx):
    jokes = [
        "Why did the computer get cold? It left its Windows open. 😂",
        "Why was the math book sad? It had too many problems. 😭",
        "Why did the developer go broke? Too many cache misses. 💻"
    ]
    await ctx.send(embed=make_embed("😂 Joke", random.choice(jokes)))

@bot.command()
async def ship(ctx, member1: discord.Member, member2: discord.Member):
    score = random.randint(0, 100)
    await ctx.send(embed=make_embed("💗 Ship", f"{member1.display_name} + {member2.display_name}\n\n**Match:** {score}% 💞"))

@bot.command()
async def choose(ctx, *, options: str):
    items = [x.strip() for x in options.split(",") if x.strip()]
    if len(items) < 2:
        return await ctx.send("❌ Give at least 2 choices separated by commas.")
    await ctx.send(embed=make_embed("🤔 MIMI Chooses", f"**Winner:** {random.choice(items)}"))

@bot.command()
async def rate(ctx, *, thing: str):
    await ctx.send(embed=make_embed("⭐ Rating", f"**{thing}** → **{random.randint(1, 10)}/10**"))

@bot.command()
@commands.has_permissions(manage_messages=True)
async def say(ctx, *, text: str):
    try:
        await ctx.message.delete()
    except discord.HTTPException:
        pass
    await ctx.send(text)

# =========================================================
# 8. EVENTS
# =========================================================

@bot.command()
@commands.has_permissions(manage_messages=True)
async def poll(ctx, *, question: str):
    msg = await ctx.send(embed=make_embed("📊 Poll", f"**{question}**\n\n👍 Yes\n👎 No"))
    await msg.add_reaction("👍")
    await msg.add_reaction("👎")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def announce(ctx, *, message: str):
    await ctx.send(embed=make_embed("📢 Announcement", message))

@bot.command()
@commands.has_permissions(manage_messages=True)
async def giveaway(ctx, duration: str, *, prize: str):
    seconds = parse_duration(duration)
    if seconds is None or seconds > 604800:
        return await ctx.send("❌ Use duration like `10s`, `10m`, `2h`, `1d` (max 7 days).")
    e = make_embed(
        "🎉 Giveaway",
        f"**Prize:** {prize}\n"
        f"**Host:** {ctx.author.mention}\n"
        f"React with 🎉 to enter!\n"
        f"**Ends:** <t:{int(time.time()+seconds)}:R>"
    )
    msg = await ctx.send(embed=e)
    await msg.add_reaction("🎉")
    CUR.execute(
        "INSERT OR REPLACE INTO giveaways(message_id,channel_id,prize,host_id) VALUES(?,?,?,?)",
        (msg.id, ctx.channel.id, prize, ctx.author.id)
    )
    DB.commit()

    await asyncio.sleep(seconds)

    try:
        msg = await ctx.channel.fetch_message(msg.id)
        reaction = discord.utils.get(msg.reactions, emoji="🎉")
        users = []
        if reaction:
            async for user in reaction.users():
                if not user.bot:
                    users.append(user)
        if not users:
            await ctx.send("🎉 Giveaway ended, but nobody entered.")
            return
        winner = random.choice(users)
        await ctx.send(embed=make_embed(
            "🎊 Giveaway Winner!",
            f"Congratulations {winner.mention}!\n**Prize:** {prize}"
        ))
    except discord.HTTPException:
        pass

@bot.command()
@commands.has_permissions(manage_messages=True)
async def reroll(ctx, message_id: int):
    row = CUR.execute(
        "SELECT prize FROM giveaways WHERE message_id=? AND channel_id=?",
        (message_id, ctx.channel.id)
    ).fetchone()
    if not row:
        return await ctx.send("❌ Giveaway not found in this channel.")
    try:
        msg = await ctx.channel.fetch_message(message_id)
        reaction = discord.utils.get(msg.reactions, emoji="🎉")
        users = []
        if reaction:
            async for user in reaction.users():
                if not user.bot:
                    users.append(user)
        if not users:
            return await ctx.send("❌ No eligible entries.")
        winner = random.choice(users)
        await ctx.send(embed=make_embed(
            "🔄 Giveaway Rerolled",
            f"New winner: {winner.mention}\n**Prize:** {row[0]}"
        ))
    except discord.HTTPException:
        await ctx.send("❌ Couldn't fetch that giveaway message.")

# =========================================================
# 9. EXTRA UTILITY
# =========================================================

@bot.command()
async def remind(ctx, duration: str, *, text: str):
    seconds = parse_duration(duration)
    if seconds is None or seconds > 604800:
        return await ctx.send("❌ Use `10s`, `10m`, `2h`, or `1d` (max 7 days).")
    await ctx.send(f"⏰ Reminder set for **{duration}**.")
    await asyncio.sleep(seconds)
    try:
        await ctx.author.send(embed=make_embed("⏰ Reminder", text))
    except discord.HTTPException:
        await ctx.send(f"{ctx.author.mention} ⏰ **Reminder:** {text}")

@bot.command()
async def servericon(ctx):
    if not ctx.guild.icon:
        return await ctx.send("❌ This server has no icon.")
    e = make_embed("🖼️ Server Icon", f"[Open Icon]({ctx.guild.icon.url})")
    e.set_image(url=ctx.guild.icon.url)
    await ctx.send(embed=e)

@bot.command()
async def roles(ctx):
    role_text = "\n".join(
        f"{r.mention} — `{r.id}`" for r in ctx.guild.roles[-30:] if r.name != "@everyone"
    )
    await ctx.send(embed=make_embed("🎭 Server Roles", role_text or "No roles."))

@bot.command()
async def channels(ctx):
    text_channels = "\n".join(f"💬 {c.mention}" for c in ctx.guild.text_channels[:50])
    await ctx.send(embed=make_embed("📺 Text Channels", text_channels or "No text channels."))

@bot.command()
async def members(ctx):
    humans = sum(1 for m in ctx.guild.members if not m.bot)
    bots = sum(1 for m in ctx.guild.members if m.bot)
    await ctx.send(embed=make_embed(
        "👥 Members",
        f"**Humans:** {humans}\n**Bots:** {bots}\n**Total:** {ctx.guild.member_count}"
    ))

@bot.command()
@commands.has_guild_permissions(administrator=True)
async def customize(ctx, *, text: str):
    await ctx.send(embed=make_embed(
        "⚙️ Customize",
        f"Customization request received:\n**{text}**"
    ))

@bot.command()
async def suggest(ctx, *, suggestion: str):
    await ctx.send(embed=make_embed(
        "💡 Suggestion",
        f"Thanks {ctx.author.mention}! Your suggestion was received:\n**{suggestion}**"
    ))

@bot.command()
async def serverbanner(ctx):
    if not ctx.guild.banner:
        return await ctx.send("❌ This server has no banner.")
    e = make_embed("🖼️ Server Banner", f"[Open Banner]({ctx.guild.banner.url})")
    e.set_image(url=ctx.guild.banner.url)
    await ctx.send(embed=e)

@bot.command()
async def membercount(ctx):
    await ctx.send(embed=make_embed(
        "👥 Member Count",
        f"**{ctx.guild.name}:** {ctx.guild.member_count} members"
    ))

# =========================================================
# 10. OWNER-ONLY PAYMENT
# Hidden from public help intentionally.
# =========================================================

@bot.command(name="pay")
@commands.is_owner()
async def pay(ctx, amount: str = None, *, reason: str = "Payment"):
    if amount is None:
        return await ctx.send("❌ Usage: `*pay <amount> <reason>`")

    try:
        value = float(amount)
        if value <= 0:
            raise ValueError
    except ValueError:
        return await ctx.send("❌ Enter a valid positive amount.")

    clean_amount = f"{value:.2f}".rstrip("0").rstrip(".")
    upi_url = (
        "upi://pay"
        f"?pa={UPI_ID}"
        f"&pn={PAYMENT_NAME.replace(' ', '%20')}"
        f"&am={clean_amount}"
        f"&cu=INR"
        f"&tn={reason.replace(' ', '%20')}"
    )

    qr = qrcode.make(upi_url)
    buffer = io.BytesIO()
    qr.save(buffer, format="PNG")
    buffer.seek(0)

    file = discord.File(buffer, filename="mimi_payment_qr.png")
    e = make_embed(
        "💳 MIMI Payment QR",
        f"**Amount:** ₹{clean_amount}\n"
        f"**Reason:** {reason}\n"
        f"**UPI:** `{UPI_ID}`\n"
        f"**Name:** {PAYMENT_NAME}\n\n"
        "Scan the QR with a UPI app."
    )
    e.set_image(url="attachment://mimi_payment_qr.png")
    await ctx.send(embed=e, file=file)

# =========================================================
# ERROR HANDLER
# =========================================================

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.MissingPermissions):
        return await ctx.send("❌ You don't have permission to use this command.")

    if isinstance(error, commands.MissingRequiredArgument):
        return await ctx.send(f"❌ Missing argument. Use `{PREFIX}help` for usage.")

    if isinstance(error, commands.MissingPermissions):
        return await ctx.send("❌ Missing permissions.")

    if isinstance(error, commands.NotOwner):
        return await ctx.send("❌ This command is owner-only.")

    if isinstance(error, commands.BadArgument):
        return await ctx.send("❌ Invalid argument. Check the command format.")

    if isinstance(error, commands.NoPrivateMessage):
        return await ctx.send("❌ This command can only be used in a server.")

    print(f"[ERROR] {type(error).__name__}: {error}")
    await ctx.send("❌ Something went wrong while running that command.")

# =========================================================
# START
# =========================================================

if not TOKEN or TOKEN == "PASTE_YOUR_NEW_BOT_TOKEN_HERE":
    raise RuntimeError(
        "❌ Bot token missing. Put your NEW bot token in the TOKEN variable."
    )

bot.run(TOKEN)
