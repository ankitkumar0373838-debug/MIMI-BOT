 import discord
from discord.ext import commands, tasks
from discord.ui import View, Select, Button
from datetime import timedelta
import sqlite3
import random
import time
import io
import asyncio
import re
import qrcode
from urllib.parse import quote

# =========================================================
# 𝙼𝙸𝙼𝙸🌸 
# =========================================================

TOKEN = "PASTE_YOUR_NEW_BOT_TOKEN_HERE"
PREFIX = "*"

BOT_NAME = "𝙼𝙸𝙼𝙸🌸"
DEVELOPER = "ADX ANKIT"

UPI_ID = "Ankittt.3@fam"
PAYMENT_NAME = "ADX ANKIT"

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

DB = sqlite3.connect(
    "mimi.db",
    check_same_thread=False
)

CUR = DB.cursor()

CUR.execute("""
CREATE TABLE IF NOT EXISTS guild_settings (
    guild_id INTEGER PRIMARY KEY,
    antinuke INTEGER DEFAULT 0,
    welcome INTEGER DEFAULT 0,
    goodbye INTEGER DEFAULT 0,
    autorole_id INTEGER DEFAULT 0,
    automod_link INTEGER DEFAULT 0,
    automod_spam INTEGER DEFAULT 0,
    automod_invite INTEGER DEFAULT 0,
    automod_caps INTEGER DEFAULT 0,
    automod_mention INTEGER DEFAULT 0,
    automod_words INTEGER DEFAULT 0,
    automod_delete INTEGER DEFAULT 1,
    automod_warn INTEGER DEFAULT 0,
    automod_timeout INTEGER DEFAULT 0,
    ticket_category_id INTEGER DEFAULT 0,
    ticket_staff_role_id INTEGER DEFAULT 0,
    suggestion_channel_id INTEGER DEFAULT 0
)
""")

CUR.execute("""
CREATE TABLE IF NOT EXISTS warnings (
    guild_id INTEGER,
    user_id INTEGER,
    reason TEXT,
    created_at INTEGER DEFAULT 0
)
""")

CUR.execute("""
CREATE TABLE IF NOT EXISTS economy (
    guild_id INTEGER,
    user_id INTEGER,
    wallet INTEGER DEFAULT 0,
    bank INTEGER DEFAULT 0,
    daily_at INTEGER DEFAULT 0,
    work_at INTEGER DEFAULT 0,
    PRIMARY KEY(guild_id, user_id)
)
""")

CUR.execute("""
CREATE TABLE IF NOT EXISTS whitelist (
    guild_id INTEGER,
    user_id INTEGER,
    PRIMARY KEY(guild_id, user_id)
)
""")

CUR.execute("""
CREATE TABLE IF NOT EXISTS levels (
    guild_id INTEGER,
    user_id INTEGER,
    xp INTEGER DEFAULT 0,
    level INTEGER DEFAULT 0,
    PRIMARY KEY(guild_id, user_id)
)
""")

CUR.execute("""
CREATE TABLE IF NOT EXISTS shop (
    guild_id INTEGER,
    item TEXT,
    price INTEGER,
    PRIMARY KEY(guild_id, item)
)
""")

CUR.execute("""
CREATE TABLE IF NOT EXISTS giveaways (
    message_id INTEGER PRIMARY KEY,
    channel_id INTEGER,
    prize TEXT,
    host_id INTEGER,
    ends_at INTEGER,
    winner_id INTEGER DEFAULT 0
)
""")

CUR.execute("""
CREATE TABLE IF NOT EXISTS giveaway_entries (
    message_id INTEGER,
    user_id INTEGER,
    PRIMARY KEY(message_id, user_id)
)
""")

CUR.execute("""
CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    channel_id INTEGER,
    text TEXT,
    due_at INTEGER
)
""")

DB.commit()

# =========================================================
# DATABASE MIGRATION
# =========================================================

def table_columns(table):
    return {
        row[1]
        for row in CUR.execute(
            f"PRAGMA table_info({table})"
        ).fetchall()
    }


MIGRATIONS = {
    "guild_settings": {
        "automod_link": "INTEGER DEFAULT 0",
        "automod_spam": "INTEGER DEFAULT 0",
        "automod_invite": "INTEGER DEFAULT 0",
        "automod_caps": "INTEGER DEFAULT 0",
        "automod_mention": "INTEGER DEFAULT 0",
        "automod_words": "INTEGER DEFAULT 0",
        "automod_delete": "INTEGER DEFAULT 1",
        "automod_warn": "INTEGER DEFAULT 0",
        "automod_timeout": "INTEGER DEFAULT 0",
        "ticket_category_id": "INTEGER DEFAULT 0",
        "ticket_staff_role_id": "INTEGER DEFAULT 0",
        "suggestion_channel_id": "INTEGER DEFAULT 0"
    },
    "economy": {
        "work_at": "INTEGER DEFAULT 0"
    },
    "warnings": {
        "created_at": "INTEGER DEFAULT 0"
    }
}


for table, fields in MIGRATIONS.items():

    existing = table_columns(table)

    for field, field_type in fields.items():

        if field not in existing:

            CUR.execute(
                f"ALTER TABLE {table} "
                f"ADD COLUMN {field} {field_type}"
            )

DB.commit()

# =========================================================
# HELPERS
# =========================================================

def make_embed(
    title,
    description="",
    color=0xFF8CC6
):

    return discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=discord.utils.utcnow()
    )


def get_settings(guild_id):

    CUR.execute(
        "SELECT * FROM guild_settings WHERE guild_id=?",
        (guild_id,)
    )

    row = CUR.fetchone()

    if row is None:

        CUR.execute(
            "INSERT INTO guild_settings(guild_id) VALUES(?)",
            (guild_id,)
        )

        DB.commit()

        return get_settings(guild_id)

    return row


def set_setting(
    guild_id,
    column,
    value
):

    allowed = table_columns("guild_settings")

    if column not in allowed:
        return

    CUR.execute(
        f"""
        UPDATE guild_settings
        SET {column}=?
        WHERE guild_id=?
        """,
        (value, guild_id)
    )

    DB.commit()


def is_whitelisted(
    guild_id,
    user_id
):

    row = CUR.execute(
        """
        SELECT 1
        FROM whitelist
        WHERE guild_id=? AND user_id=?
        """,
        (guild_id, user_id)
    ).fetchone()

    return row is not None


def ensure_economy(
    guild_id,
    user_id
):

    CUR.execute(
        """
        INSERT OR IGNORE INTO economy
        (guild_id,user_id,wallet,bank,daily_at,work_at)
        VALUES(?,?,?,?,?,?)
        """,
        (
            guild_id,
            user_id,
            0,
            0,
            0,
            0
        )
    )

    DB.commit()


def get_money(
    guild_id,
    user_id
):

    ensure_economy(
        guild_id,
        user_id
    )

    return CUR.execute(
        """
        SELECT wallet,bank
        FROM economy
        WHERE guild_id=? AND user_id=?
        """,
        (guild_id, user_id)
    ).fetchone()


def set_money(
    guild_id,
    user_id,
    wallet=None,
    bank=None
):

    old_wallet, old_bank = get_money(
        guild_id,
        user_id
    )

    if wallet is None:
        wallet = old_wallet

    if bank is None:
        bank = old_bank

    CUR.execute(
        """
        UPDATE economy
        SET wallet=?,bank=?
        WHERE guild_id=? AND user_id=?
        """,
        (
            wallet,
            bank,
            guild_id,
            user_id
        )
    )

    DB.commit()


def parse_duration(text):

    match = re.fullmatch(
        r"(\d+)(s|m|h|d)",
        text.lower()
    )

    if not match:
        return None

    number, unit = match.groups()

    multipliers = {
        "s": 1,
        "m": 60,
        "h": 3600,
        "d": 86400
    }

    seconds = int(number) * multipliers[unit]

    return seconds


def format_uptime():

    seconds = int(
        time.time() - START_TIME
    )

    days, seconds = divmod(
        seconds,
        86400
    )

    hours, seconds = divmod(
        seconds,
        3600
    )

    minutes, seconds = divmod(
        seconds,
        60
    )

    return (
        f"{days}d "
        f"{hours}h "
        f"{minutes}m "
        f"{seconds}s"
    )


def administrator():

    return commands.has_guild_permissions(
        administrator=True
    )


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

    print("=" * 60)
    print(f"🌸 {BOT_NAME} ONLINE")
    print(f"👤 User: {bot.user}")
    print(f"🏠 Servers: {len(bot.guilds)}")
    print(f"⚡ Prefix: {PREFIX}")
    print("🚀 MIMI V2 READY")
    print("=" * 60)


@bot.event
async def on_member_join(member):

    settings = get_settings(
        member.guild.id
    )

    autorole_id = settings[4]

    if autorole_id:

        role = member.guild.get_role(
            autorole_id
        )

        if role:

            try:
                await member.add_roles(
                    role,
                    reason="MIMI AutoRole"
                )
            except discord.HTTPException:
                pass

    if settings[2]:

        channel = member.guild.system_channel

        if channel:

            try:

                await channel.send(
                    f"🌸 Welcome {member.mention} "
                    f"to **{member.guild.name}**! 🐾💗"
                )

            except discord.HTTPException:
                pass


@bot.event
async def on_member_remove(member):

    settings = get_settings(
        member.guild.id
    )

    if settings[3]:

        channel = member.guild.system_channel

        if channel:

            try:

                await channel.send(
                    f"👋 **{member.display_name}** "
                    f"left the server. Take care! 🌸"
                )

            except discord.HTTPException:
                pass


# =========================================================
# AUTOMOD
# =========================================================

BAD_WORDS = {
    "badword1",
    "badword2",
    "badword3"
}

spam_tracker = {}


@bot.event
async def on_message(message):

    if (
        message.author.bot
        or message.guild is None
    ):
        return await bot.process_commands(
            message
        )

    s = get_settings(
        message.guild.id
    )

    content = message.content.lower()

    violations = []

    # Anti-Link
    if s[5]:

        if re.search(
            r"https?://|www\.",
            content
        ):

            violations.append(
                "Anti-Link"
            )

    # Anti-Invite
    if s[7]:

        if re.search(
            r"(discord\.gg/|discord\.com/invite/)",
            content
        ):

            violations.append(
                "Anti-Invite"
            )

    # Anti-Caps
    letters = [
        c for c in message.content
        if c.isalpha()
    ]

    if (
        s[8]
        and len(letters) >= 8
        and (
            sum(
                c.isupper()
                for c in letters
            ) / len(letters)
        ) >= 0.75
    ):

        violations.append(
            "Anti-Caps"
        )

    # Anti-Mention Spam
    if (
        s[9]
        and len(message.mentions) >= 5
    ):

        violations.append(
            "Mention Spam"
        )

    # Bad Words
    if s[10]:

        words = set(
            re.findall(
                r"\b\w+\b",
                content
            )
        )

        if words & BAD_WORDS:

            violations.append(
                "Bad Word Filter"
            )

    # Anti-Spam
    now = time.time()

    key = (
        message.guild.id,
        message.author.id
    )

    history = spam_tracker.get(
        key,
        []
    )

    history = [
        t for t in history
        if now - t < 5
    ]

    history.append(now)

    spam_tracker[key] = history

    if (
        s[6]
        and len(history) >= 6
    ):

        violations.append(
            "Anti-Spam"
        )

    # Apply AutoMod
    if violations:

        if s[11]:

            try:
                await message.delete()
            except discord.HTTPException:
                pass

        if s[12]:

            CUR.execute(
                """
                INSERT INTO warnings
                (guild_id,user_id,reason,created_at)
                VALUES(?,?,?,?)
                """,
                (
                    message.guild.id,
                    message.author.id,
                    "AutoMod: "
                    + ", ".join(violations),
                    int(now)
                )
            )

            DB.commit()

        if s[13]:

            try:

                await message.author.timeout(
                    discord.utils.utcnow()
                    + timedelta(minutes=5),
                    reason="MIMI AutoMod"
                )

            except discord.HTTPException:
                pass

        try:

            await message.channel.send(
                f"⚠️ {message.author.mention} "
                f"AutoMod detected: "
                f"**{', '.join(violations)}**",
                delete_after=5
            )

        except discord.HTTPException:
            pass

    await bot.process_commands(
        message
    )


# =========================================================
# ANTI-NUKE
# =========================================================

async def anti_delete_check(
    guild,
    target_type
):

    settings = get_settings(
        guild.id
    )

    if not settings[1]:
        return

    try:

        async for entry in guild.audit_logs(
            limit=1
        ):

            if entry.action not in (
                discord.AuditLogAction.channel_delete,
                discord.AuditLogAction.role_delete
            ):
                return

            actor = entry.user

            if (
                actor.bot
                or is_whitelisted(
                    guild.id,
                    actor.id
                )
            ):
                return

            try:

                await guild.ban(
                    actor,
                    reason=(
                        "MIMI Anti-Nuke: "
                        f"deleted {target_type}"
                    )
                )

            except discord.HTTPException:
                pass

            return

    except (
        discord.Forbidden,
        discord.HTTPException
    ):
        pass


@bot.event
async def on_guild_channel_delete(channel):

    await anti_delete_check(
        channel.guild,
        "channel"
    )


@bot.event
async def on_guild_role_delete(role):

    await anti_delete_check(
        role.guild,
        "role"
    )


# =========================================================
# CORE COMMANDS
# =========================================================

@bot.command()
async def ping(ctx):

    await ctx.send(
        embed=make_embed(
            "🏓 Pong!",
            f"Latency: "
            f"`{round(bot.latency * 1000)}ms`"
        )
    )


@bot.command()
async def botinfo(ctx):

    await ctx.send(
        embed=make_embed(
            "🌸 𝙼𝙸𝙼𝙸 Bot",
            f"**Developer:** {DEVELOPER}\n"
            f"**Servers:** {len(bot.guilds)}\n"
            f"**Users:** {len(bot.users)}\n"
            f"**Prefix:** `{PREFIX}`\n"
            f"**Uptime:** {format_uptime()}"
        )
    )


@bot.command()
async def uptime(ctx):

    await ctx.send(
        embed=make_embed(
            "⏱️ Bot Uptime",
            format_uptime()
        )
    )


@bot.command()
async def serverinfo(ctx):

    guild = ctx.guild

    owner = (
        guild.owner.mention
        if guild.owner
        else "Unknown"
    )

    await ctx.send(
        embed=make_embed(
            f"🏠 {guild.name}",
            f"**Owner:** {owner}\n"
            f"**Members:** {guild.member_count}\n"
            f"**Channels:** {len(guild.channels)}\n"
            f"**Roles:** {len(guild.roles)}\n"
            f"**Created:** "
            f"<t:{int(guild.created_at.timestamp())}:D>"
        )
    )


@bot.command()
async def userinfo(
    ctx,
    member: discord.Member = None
):

    member = member or ctx.author

    joined = (
        f"<t:{int(member.joined_at.timestamp())}:D>"
        if member.joined_at
        else "Unknown"
    )

    await ctx.send(
        embed=make_embed(
            f"👤 {member.display_name}",
            f"**Username:** {member}\n"
            f"**ID:** `{member.id}`\n"
            f"**Joined:** {joined}\n"
            f"**Created:** "
            f"<t:{int(member.created_at.timestamp())}:D>\n"
            f"**Top Role:** "
            f"{member.top_role.mention}"
        )
    )


@bot.command()
async def avatar(
    ctx,
    member: discord.Member = None
):

    member = member or ctx.author

    e = make_embed(
        "🖼️ Avatar",
        f"[Open Avatar]({member.display_avatar.url})"
    )

    e.set_image(
        url=member.display_avatar.url
    )

    await ctx.send(
        embed=e
    )


@bot.command()
async def id(
    ctx,
    member: discord.Member = None
):

    member = member or ctx.author

    await ctx.send(
        f"🆔 {member.mention}: `{member.id}`"
    )


@bot.command()
async def roleinfo(
    ctx,
    role: discord.Role
):

    await ctx.send(
        embed=make_embed(
            f"🎭 {role.name}",
            f"**ID:** `{role.id}`\n"
            f"**Members:** {len(role.members)}\n"
            f"**Position:** {role.position}\n"
            f"**Mentionable:** {role.mentionable}"
        )
    )


@bot.command()
async def channelinfo(
    ctx,
    channel: discord.abc.GuildChannel = None
):

    channel = channel or ctx.channel

    await ctx.send(
        embed=make_embed(
            "📺 Channel Info",
            f"**Name:** {channel.name}\n"
            f"**ID:** `{channel.id}`\n"
            f"**Type:** `{channel.type}`"
        )
    )


@bot.command()
async def invite(ctx):

    permissions = discord.Permissions(
        view_channel=True,
        send_messages=True,
        embed_links=True,
        attach_files=True,
        read_message_history=True,
        add_reactions=True,
        connect=True,
        speak=True,
        manage_messages=True,
        moderate_members=True,
        manage_channels=True
    )

    url = discord.utils.oauth_url(
        bot.user.id,
        permissions=permissions
    )

    await ctx.send(
        embed=make_embed(
            "🔗 Invite 𝙼𝙸𝙼𝙸",
            f"[Click here to invite MIMI]({url})"
        )
    )


# =========================================================
# SECURITY
# =========================================================

@bot.group(
    name="antinuke",
    invoke_without_command=True
)
@administrator()
async def antinuke(ctx):

    status = (
        "🟢 ON"
        if get_settings(ctx.guild.id)[1]
        else "🔴 OFF"
    )

    await ctx.send(
        embed=make_embed(
            "🛡️ Anti-Nuke",
            f"Status: **{status}**\n\n"
            f"`{PREFIX}antinuke on`\n"
            f"`{PREFIX}antinuke off`"
        )
    )


@antinuke.command(name="on")
async def antinuke_on(ctx):

    set_setting(
        ctx.guild.id,
        "antinuke",
        1
    )

    await ctx.send(
        "🛡️ Anti-Nuke **ON**."
    )


@antinuke.command(name="off")
async def antinuke_off(ctx):

    set_setting(
        ctx.guild.id,
        "antinuke",
        0
    )

    await ctx.send(
        "🛡️ Anti-Nuke **OFF**."
    )


@bot.command()
@administrator()
async def lockdown(ctx):

    count = 0

    for channel in ctx.guild.text_channels:

        try:

            await channel.set_permissions(
                ctx.guild.default_role,
                send_messages=False,
                reason="MIMI lockdown"
            )

            count += 1

        except discord.HTTPException:
            pass

    await ctx.send(
        f"🔒 Locked **{count}** text channels."
    )


@bot.command()
@administrator()
async def unlockdown(ctx):

    count = 0

    for channel in ctx.guild.text_channels:

        try:

            await channel.set_permissions(
                ctx.guild.default_role,
                send_messages=None,
                reason="MIMI unlockdown"
            )

            count += 1

        except discord.HTTPException:
            pass

    await ctx.send(
        f"🔓 Unlocked **{count}** text channels."
    )


@bot.command()
@administrator()
async def whitelist(
    ctx,
    member: discord.Member
):

    CUR.execute(
        """
        INSERT OR IGNORE INTO whitelist
        (guild_id,user_id)
        VALUES(?,?)
        """,
        (
            ctx.guild.id,
            member.id
        )
    )

    DB.commit()

    await ctx.send(
        f"✅ {member.mention} "
        f"is now whitelisted."
    )


@bot.command()
@administrator()
async def unwhitelist(
    ctx,
    member: discord.Member
):

    CUR.execute(
        """
        DELETE FROM whitelist
        WHERE guild_id=? AND user_id=?
        """,
        (
            ctx.guild.id,
            member.id
        )
    )

    DB.commit()

    await ctx.send(
        f"❌ {member.mention} "
        f"removed from whitelist."
    )


@bot.command()
@administrator()
async def security(ctx):

    s = get_settings(
        ctx.guild.id
    )

    await ctx.send(
        embed=make_embed(
            "🛡️ Security Status",
            f"**Anti-Nuke:** "
            f"{'🟢 ON' if s[1] else '🔴 OFF'}\n"
            f"**Welcome:** "
            f"{'🟢 ON' if s[2] else '🔴 OFF'}\n"
            f"**Goodbye:** "
            f"{'🟢 ON' if s[3] else '🔴 OFF'}\n"
            f"**AutoRole:** "
            f"{'🟢 ON' if s[4] else '🔴 OFF'}"
        )
)
    # =========================================================
# MODERATION
# =========================================================

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="No reason provided"):

    if member == ctx.author:
        return await ctx.send("❌ You cannot ban yourself.")

    if member.top_role >= ctx.author.top_role:
        return await ctx.send(
            "❌ You cannot ban a member with an equal/higher role."
        )

    try:
        await member.ban(reason=reason)

        await ctx.send(
            embed=make_embed(
                "🔨 Member Banned",
                f"**Member:** {member.mention}\n"
                f"**Moderator:** {ctx.author.mention}\n"
                f"**Reason:** {reason}"
            )
        )

    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to ban that member.")


@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, user_id: int):

    try:
        user = await bot.fetch_user(user_id)
        await ctx.guild.unban(user)

        await ctx.send(
            f"✅ **{user}** has been unbanned."
        )

    except discord.NotFound:
        await ctx.send("❌ User is not banned or ID is invalid.")

    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to unban users.")


@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(
    ctx,
    member: discord.Member,
    *,
    reason="No reason provided"
):

    if member == ctx.author:
        return await ctx.send(
            "❌ You cannot kick yourself."
        )

    if member.top_role >= ctx.author.top_role:
        return await ctx.send(
            "❌ You cannot kick a member with an equal/higher role."
        )

    try:

        await member.kick(
            reason=reason
        )

        await ctx.send(
            embed=make_embed(
                "👢 Member Kicked",
                f"**Member:** {member.mention}\n"
                f"**Moderator:** {ctx.author.mention}\n"
                f"**Reason:** {reason}"
            )
        )

    except discord.Forbidden:
        await ctx.send(
            "❌ I don't have permission to kick that member."
        )


@bot.command()
@commands.has_permissions(moderate_members=True)
async def mute(
    ctx,
    member: discord.Member,
    duration: str = "10m",
    *,
    reason="No reason provided"
):

    seconds = parse_duration(duration)

    if seconds is None:
        return await ctx.send(
            "❌ Invalid duration. Examples: `10s`, `10m`, `2h`, `1d`."
        )

    if member.top_role >= ctx.author.top_role:
        return await ctx.send(
            "❌ You cannot mute a member with an equal/higher role."
        )

    until = discord.utils.utcnow() + timedelta(
        seconds=seconds
    )

    try:

        await member.timeout(
            until,
            reason=reason
        )

        await ctx.send(
            embed=make_embed(
                "🔇 Member Timed Out",
                f"**Member:** {member.mention}\n"
                f"**Duration:** `{duration}`\n"
                f"**Reason:** {reason}"
            )
        )

    except discord.Forbidden:
        await ctx.send(
            "❌ I don't have permission to timeout that member."
        )


@bot.command()
@commands.has_permissions(moderate_members=True)
async def unmute(ctx, member: discord.Member):

    try:

        await member.timeout(
            None,
            reason="MIMI unmute"
        )

        await ctx.send(
            f"🔊 {member.mention} has been unmuted."
        )

    except discord.Forbidden:
        await ctx.send(
            "❌ I don't have permission to remove the timeout."
        )


@bot.command()
@commands.has_permissions(moderate_members=True)
async def warn(
    ctx,
    member: discord.Member,
    *,
    reason="No reason provided"
):

    CUR.execute(
        """
        INSERT INTO warnings
        (guild_id,user_id,reason,created_at)
        VALUES(?,?,?,?)
        """,
        (
            ctx.guild.id,
            member.id,
            reason,
            int(time.time())
        )
    )

    DB.commit()

    await ctx.send(
        embed=make_embed(
            "⚠️ Warning Added",
            f"**Member:** {member.mention}\n"
            f"**Reason:** {reason}\n"
            f"**Moderator:** {ctx.author.mention}"
        )
    )


@bot.command()
@commands.has_permissions(moderate_members=True)
async def warnings(
    ctx,
    member: discord.Member = None
):

    member = member or ctx.author

    rows = CUR.execute(
        """
        SELECT reason,created_at
        FROM warnings
        WHERE guild_id=? AND user_id=?
        ORDER BY created_at DESC
        LIMIT 15
        """,
        (
            ctx.guild.id,
            member.id
        )
    ).fetchall()

    if not rows:
        return await ctx.send(
            f"✅ {member.mention} has no warnings."
        )

    text = []

    for i, (reason, created) in enumerate(
        rows,
        1
    ):

        if created:
            date = f"<t:{created}:R>"
        else:
            date = "Unknown"

        text.append(
            f"**{i}.** {reason} — {date}"
        )

    await ctx.send(
        embed=make_embed(
            f"⚠️ Warnings — {member.display_name}",
            "\n".join(text)
        )
    )


@bot.command()
@commands.has_permissions(moderate_members=True)
async def clear(
    ctx,
    amount: int
):

    if amount < 1 or amount > 100:
        return await ctx.send(
            "❌ Amount must be between `1` and `100`."
        )

    try:

        deleted = await ctx.channel.purge(
            limit=amount + 1
        )

        msg = await ctx.send(
            f"🧹 Deleted **{len(deleted) - 1}** messages."
        )

        await asyncio.sleep(3)

        try:
            await msg.delete()
        except discord.HTTPException:
            pass

    except discord.Forbidden:
        await ctx.send(
            "❌ I don't have permission to manage messages."
        )


@bot.command()
@commands.has_permissions(moderate_members=True)
async def purge(
    ctx,
    amount: int
):

    if amount < 1 or amount > 100:
        return await ctx.send(
            "❌ Amount must be between `1` and `100`."
        )

    deleted = await ctx.channel.purge(
        limit=amount + 1
    )

    msg = await ctx.send(
        f"🧹 Purged **{len(deleted) - 1}** messages."
    )

    await asyncio.sleep(3)

    try:
        await msg.delete()
    except discord.HTTPException:
        pass


@bot.command()
@commands.has_permissions(manage_messages=True)
async def purgeuser(
    ctx,
    member: discord.Member,
    amount: int = 100
):

    amount = max(
        1,
        min(amount, 100)
    )

    deleted = await ctx.channel.purge(
        limit=amount + 1,
        check=lambda m: m.author.id == member.id
    )

    await ctx.send(
        f"🧹 Deleted **{len(deleted)}** messages "
        f"from {member.mention}.",
        delete_after=4
    )


@bot.command()
@commands.has_permissions(manage_messages=True)
async def purgebots(
    ctx,
    amount: int = 100
):

    amount = max(
        1,
        min(amount, 100)
    )

    deleted = await ctx.channel.purge(
        limit=amount + 1,
        check=lambda m: m.author.bot
    )

    await ctx.send(
        f"🤖 Deleted **{len(deleted)}** bot messages.",
        delete_after=4
    )


@bot.command()
@commands.has_permissions(manage_channels=True)
async def slowmode(
    ctx,
    seconds: int
):

    if seconds < 0 or seconds > 21600:
        return await ctx.send(
            "❌ Slowmode must be between `0` and `21600` seconds."
        )

    await ctx.channel.edit(
        slowmode_delay=seconds
    )

    if seconds == 0:
        text = "disabled"
    else:
        text = f"`{seconds}` seconds"

    await ctx.send(
        f"🐢 Slowmode {text}."
    )


@bot.command()
@commands.has_permissions(manage_nicknames=True)
async def nick(
    ctx,
    member: discord.Member,
    *,
    nickname: str = None
):

    try:

        await member.edit(
            nick=nickname,
            reason=f"MIMI nick command by {ctx.author}"
        )

        if nickname:
            await ctx.send(
                f"✏️ Nickname changed to **{nickname}**."
            )
        else:
            await ctx.send(
                "✏️ Nickname reset."
            )

    except discord.Forbidden:
        await ctx.send(
            "❌ I cannot change that member's nickname."
        )


# =========================================================
# WELCOME / GOODBYE
# =========================================================

@bot.group(
    name="welcome",
    invoke_without_command=True
)
@administrator()
async def welcome(ctx):

    status = get_settings(
        ctx.guild.id
    )[2]

    await ctx.send(
        embed=make_embed(
            "🌸 Welcome System",
            f"Status: "
            f"{'🟢 ON' if status else '🔴 OFF'}\n\n"
            f"`{PREFIX}welcome on`\n"
            f"`{PREFIX}welcome off`"
        )
    )


@welcome.command(name="on")
async def welcome_on(ctx):

    set_setting(
        ctx.guild.id,
        "welcome",
        1
    )

    await ctx.send(
        "🌸 Welcome messages **enabled**."
    )


@welcome.command(name="off")
async def welcome_off(ctx):

    set_setting(
        ctx.guild.id,
        "welcome",
        0
    )

    await ctx.send(
        "🌸 Welcome messages **disabled**."
    )


@bot.group(
    name="goodbye",
    invoke_without_command=True
)
@administrator()
async def goodbye(ctx):

    status = get_settings(
        ctx.guild.id
    )[3]

    await ctx.send(
        embed=make_embed(
            "👋 Goodbye System",
            f"Status: "
            f"{'🟢 ON' if status else '🔴 OFF'}\n\n"
            f"`{PREFIX}goodbye on`\n"
            f"`{PREFIX}goodbye off`"
        )
    )


@goodbye.command(name="on")
async def goodbye_on(ctx):

    set_setting(
        ctx.guild.id,
        "goodbye",
        1
    )

    await ctx.send(
        "👋 Goodbye messages **enabled**."
    )


@goodbye.command(name="off")
async def goodbye_off(ctx):

    set_setting(
        ctx.guild.id,
        "goodbye",
        0
    )

    await ctx.send(
        "👋 Goodbye messages **disabled**."
    )


@bot.command()
@administrator()
async def autorole(
    ctx,
    role: discord.Role = None
):

    if role is None:

        current = get_settings(
            ctx.guild.id
        )[4]

        if current:

            current_role = ctx.guild.get_role(
                current
            )

            if current_role:

                return await ctx.send(
                    f"🎭 Current AutoRole: "
                    f"{current_role.mention}"
                )

        return await ctx.send(
            "🎭 AutoRole is not configured."
        )

    if role >= ctx.guild.me.top_role:
        return await ctx.send(
            "❌ That role is higher than or equal to my highest role."
        )

    set_setting(
        ctx.guild.id,
        "autorole_id",
        role.id
    )

    await ctx.send(
        f"✅ AutoRole set to {role.mention}."
    )


# =========================================================
# AUTOMOD COMMANDS
# =========================================================

AUTOMOD_OPTIONS = {
    "link": "automod_link",
    "spam": "automod_spam",
    "invite": "automod_invite",
    "caps": "automod_caps",
    "mention": "automod_mention",
    "words": "automod_words",
    "delete": "automod_delete",
    "warn": "automod_warn",
    "timeout": "automod_timeout"
}


def automod_status_text(guild_id):

    s = get_settings(guild_id)

    names = [
        ("Link", s[5]),
        ("Spam", s[6]),
        ("Invite", s[7]),
        ("Caps", s[8]),
        ("Mention", s[9]),
        ("Bad Words", s[10]),
        ("Delete", s[11]),
        ("Warn", s[12]),
        ("Timeout", s[13])
    ]

    return "\n".join(
        f"**{name}:** "
        f"{'🟢 ON' if value else '🔴 OFF'}"
        for name, value in names
    )


@bot.group(
    name="automod",
    invoke_without_command=True
)
@administrator()
async def automod(ctx):

    await ctx.send(
        embed=make_embed(
            "🤖 AutoMod",
            automod_status_text(
                ctx.guild.id
            )
            + "\n\n"
            f"Use `{PREFIX}automod <option> on/off`."
        )
    )


async def automod_toggle(
    ctx,
    option,
    state
):

    column = AUTOMOD_OPTIONS.get(
        option.lower()
    )

    if column is None:
        return await ctx.send(
            "❌ Invalid option.\n"
            "Available: `link`, `spam`, `invite`, "
            "`caps`, `mention`, `words`, `delete`, "
            "`warn`, `timeout`."
        )

    if state.lower() not in (
        "on",
        "off"
    ):
        return await ctx.send(
            "❌ Use `on` or `off`."
        )

    value = 1 if state.lower() == "on" else 0

    set_setting(
        ctx.guild.id,
        column,
        value
    )

    await ctx.send(
        f"🤖 AutoMod **{option}** "
        f"{'enabled 🟢' if value else 'disabled 🔴'}."
    )


@automod.command(name="link")
async def automod_link(
    ctx,
    state: str
):

    await automod_toggle(
        ctx,
        "link",
        state
    )


@automod.command(name="spam")
async def automod_spam(
    ctx,
    state: str
):

    await automod_toggle(
        ctx,
        "spam",
        state
    )


@automod.command(name="invite")
async def automod_invite(
    ctx,
    state: str
):

    await automod_toggle(
        ctx,
        "invite",
        state
    )


@automod.command(name="caps")
async def automod_caps(
    ctx,
    state: str
):

    await automod_toggle(
        ctx,
        "caps",
        state
    )


@automod.command(name="mention")
async def automod_mention(
    ctx,
    state: str
):

    await automod_toggle(
        ctx,
        "mention",
        state
    )


@automod.command(name="words")
async def automod_words(
    ctx,
    state: str
):

    await automod_toggle(
        ctx,
        "words",
        state
    )


@automod.command(name="delete")
async def automod_delete(
    ctx,
    state: str
):

    await automod_toggle(
        ctx,
        "delete",
        state
    )


@automod.command(name="warn")
async def automod_warn(
    ctx,
    state: str
):

    await automod_toggle(
        ctx,
        "warn",
        state
    )


@automod.command(name="timeout")
async def automod_timeout(
    ctx,
    state: str
):

    await automod_toggle(
        ctx,
        "timeout",
        state
    )


@bot.command()
@administrator()
async def automodstatus(ctx):

    await ctx.send(
        embed=make_embed(
            "🤖 AutoMod Status",
            automod_status_text(
                ctx.guild.id
            )
        )
    )


# =========================================================
# ERROR HANDLER
# =========================================================

@bot.event
async def on_command_error(
    ctx,
    error
):

    if isinstance(
        error,
        commands.CommandNotFound
    ):
        return

    if isinstance(
        error,
        commands.MissingPermissions
    ):
        return await ctx.send(
            "❌ You don't have permission to use this command."
        )

    if isinstance(
        error,
        commands.MissingRequiredArgument
    ):
        return await ctx.send(
            f"❌ Missing argument.\n"
            f"Use `{PREFIX}help` for command usage."
        )

    if isinstance(
        error,
        commands.BadArgument
    ):
        return await ctx.send(
            "❌ Invalid argument. Please check the member, role, channel or number."
        )

    if isinstance(
        error,
        commands.BotMissingPermissions
    ):
        return await ctx.send(
            "❌ I don't have the required permissions."
        )

    print(
        f"[ERROR] {ctx.command}: {repr(error)}"
    )

    await ctx.send(
        "❌ Something went wrong while executing that command."
    )
    # =========================================================
# TICKETS
# =========================================================

class TicketView(View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Create Ticket",
        emoji="🎫",
        style=discord.ButtonStyle.blurple,
        custom_id="mimi:create_ticket"
    )
    async def create_ticket(
        self,
        interaction: discord.Interaction,
        button: Button
    ):

        guild = interaction.guild
        user = interaction.user

        existing = discord.utils.get(
            guild.text_channels,
            name=f"ticket-{user.id}"
        )

        if existing:
            return await interaction.response.send_message(
                f"❌ You already have a ticket: {existing.mention}",
                ephemeral=True
            )

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=False
            ),
            user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_channels=True,
                manage_messages=True
            )
        }

        channel = await guild.create_text_channel(
            f"ticket-{user.id}",
            overwrites=overwrites,
            reason="MIMI Ticket System"
        )

        await interaction.response.send_message(
            f"🎫 Ticket created: {channel.mention}",
            ephemeral=True
        )

        view = CloseTicketView()

        await channel.send(
            embed=make_embed(
                "🎫 Support Ticket",
                f"Hello {user.mention}! 💗\n\n"
                "Please explain your issue here.\n"
                "A staff member will help you shortly.\n\n"
                "Click **Close Ticket** when finished."
            ),
            view=view
        )


class CloseTicketView(View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Close Ticket",
        emoji="🔒",
        style=discord.ButtonStyle.red,
        custom_id="mimi:close_ticket"
    )
    async def close_ticket(
        self,
        interaction: discord.Interaction,
        button: Button
    ):

        if not interaction.channel.name.startswith("ticket-"):
            return await interaction.response.send_message(
                "❌ This is not a ticket channel.",
                ephemeral=True
            )

        await interaction.response.send_message(
            "🔒 Closing ticket in 5 seconds..."
        )

        await asyncio.sleep(5)

        try:
            await interaction.channel.delete(
                reason=f"Ticket closed by {interaction.user}"
            )
        except discord.HTTPException:
            pass


@bot.command()
@commands.has_permissions(manage_channels=True)
async def ticketpanel(ctx):

    await ctx.send(
        embed=make_embed(
            "🎫 MIMI Support",
            "Need help?\n\n"
            "Click the button below to create a private support ticket."
        ),
        view=TicketView()
    )


@bot.command()
@commands.has_permissions(manage_channels=True)
async def closeticket(ctx):

    if not ctx.channel.name.startswith("ticket-"):
        return await ctx.send(
            "❌ This is not a ticket channel."
        )

    await ctx.send(
        "🔒 Closing ticket in 5 seconds..."
    )

    await asyncio.sleep(5)

    await ctx.channel.delete(
        reason=f"Ticket closed by {ctx.author}"
    )


# =========================================================
# ECONOMY
# =========================================================

@bot.command()
async def balance(ctx, member: discord.Member = None):

    member = member or ctx.author

    wallet, bank = get_money(
        ctx.guild.id,
        member.id
    )

    total = wallet + bank

    await ctx.send(
        embed=make_embed(
            f"💰 {member.display_name}'s Wallet",
            f"💵 Wallet: **{wallet:,} coins**\n"
            f"🏦 Bank: **{bank:,} coins**\n"
            f"💎 Total: **{total:,} coins**"
        )
    )


@bot.command()
async def bal(ctx, member: discord.Member = None):

    await balance.callback(
        ctx,
        member
    )


@bot.command()
@commands.cooldown(1, 86400, commands.BucketType.user)
async def daily(ctx):

    wallet, bank = get_money(
        ctx.guild.id,
        ctx.author.id
    )

    reward = random.randint(
        500,
        1500
    )

    set_money(
        ctx.guild.id,
        ctx.author.id,
        wallet + reward,
        bank
    )

    CUR.execute(
        """
        UPDATE economy
        SET daily_at=?
        WHERE guild_id=? AND user_id=?
        """,
        (
            int(time.time()),
            ctx.guild.id,
            ctx.author.id
        )
    )

    DB.commit()

    await ctx.send(
        f"🎁 {ctx.author.mention} received "
        f"**{reward:,} coins** from daily!"
    )


@daily.error
async def daily_error(ctx, error):

    if isinstance(
        error,
        commands.CommandOnCooldown
    ):

        seconds = int(
            error.retry_after
        )

        await ctx.send(
            f"⏳ You can claim daily again in "
            f"**{seconds // 3600}h "
            f"{(seconds % 3600) // 60}m**."
        )


@bot.command()
@commands.cooldown(
    1,
    300,
    commands.BucketType.user
)
async def work(ctx):

    reward = random.randint(
        100,
        500
    )

    wallet, bank = get_money(
        ctx.guild.id,
        ctx.author.id
    )

    set_money(
        ctx.guild.id,
        ctx.author.id,
        wallet + reward,
        bank
    )

    jobs = [
        "developer",
        "designer",
        "moderator",
        "streamer",
        "builder",
        "shopkeeper"
    ]

    job = random.choice(jobs)

    await ctx.send(
        f"💼 You worked as a **{job}** "
        f"and earned **{reward:,} coins**!"
    )


@work.error
async def work_error(ctx, error):

    if isinstance(
        error,
        commands.CommandOnCooldown
    ):

        await ctx.send(
            f"⏳ Try again in "
            f"**{int(error.retry_after)} seconds**."
        )


@bot.command()
async def deposit(
    ctx,
    amount: str
):

    wallet, bank = get_money(
        ctx.guild.id,
        ctx.author.id
    )

    if amount.lower() == "all":
        amount = wallet
    else:
        try:
            amount = int(amount)
        except ValueError:
            return await ctx.send(
                "❌ Enter a valid amount."
            )

    if amount <= 0:
        return await ctx.send(
            "❌ Amount must be greater than zero."
        )

    if amount > wallet:
        return await ctx.send(
            "❌ You don't have enough coins in your wallet."
        )

    set_money(
        ctx.guild.id,
        ctx.author.id,
        wallet - amount,
        bank + amount
    )

    await ctx.send(
        f"🏦 Deposited **{amount:,} coins**."
    )


@bot.command()
async def withdraw(
    ctx,
    amount: str
):

    wallet, bank = get_money(
        ctx.guild.id,
        ctx.author.id
    )

    if amount.lower() == "all":
        amount = bank
    else:
        try:
            amount = int(amount)
        except ValueError:
            return await ctx.send(
                "❌ Enter a valid amount."
            )

    if amount <= 0:
        return await ctx.send(
            "❌ Amount must be greater than zero."
        )

    if amount > bank:
        return await ctx.send(
            "❌ You don't have enough coins in your bank."
        )

    set_money(
        ctx.guild.id,
        ctx.author.id,
        wallet + amount,
        bank - amount
    )

    await ctx.send(
        f"💵 Withdrew **{amount:,} coins**."
    )


@bot.command()
async def paycoins(
    ctx,
    member: discord.Member,
    amount: int
):

    if member == ctx.author:
        return await ctx.send(
            "❌ You cannot pay yourself."
        )

    if amount <= 0:
        return await ctx.send(
            "❌ Amount must be greater than zero."
        )

    wallet, bank = get_money(
        ctx.guild.id,
        ctx.author.id
    )

    if amount > wallet:
        return await ctx.send(
            "❌ Insufficient wallet balance."
        )

    target_wallet, target_bank = get_money(
        ctx.guild.id,
        member.id
    )

    set_money(
        ctx.guild.id,
        ctx.author.id,
        wallet - amount,
        bank
    )

    set_money(
        ctx.guild.id,
        member.id,
        target_wallet + amount,
        target_bank
    )

    await ctx.send(
        f"💸 {ctx.author.mention} paid "
        f"**{amount:,} coins** to {member.mention}."
    )


@bot.command()
async def leaderboard(ctx):

    rows = CUR.execute(
        """
        SELECT user_id,wallet,bank
        FROM economy
        WHERE guild_id=?
        ORDER BY (wallet+bank) DESC
        LIMIT 10
        """,
        (ctx.guild.id,)
    ).fetchall()

    if not rows:
        return await ctx.send(
            "📊 No economy data yet."
        )

    lines = []

    for i, (uid, wallet, bank) in enumerate(
        rows,
        1
    ):

        member = ctx.guild.get_member(uid)

        name = (
            member.display_name
            if member
            else f"User {uid}"
        )

        total = wallet + bank

        lines.append(
            f"**{i}.** {name} — "
            f"💰 **{total:,}**"
        )

    await ctx.send(
        embed=make_embed(
            "🏆 Economy Leaderboard",
            "\n".join(lines)
        )
    )


# =========================================================
# SHOP
# =========================================================

DEFAULT_SHOP = [
    ("VIP Role", 5000),
    ("Custom Color", 3000),
    ("Special Access", 10000),
    ("Mystery Reward", 15000)
]


@bot.command()
async def shop(ctx):

    lines = []

    for i, (name, price) in enumerate(
        DEFAULT_SHOP,
        1
    ):
        lines.append(
            f"**{i}. {name}** — "
            f"💰 `{price:,}` coins"
        )

    await ctx.send(
        embed=make_embed(
            "🛒 MIMI Shop",
            "\n".join(lines)
            + "\n\n"
            f"Buy with `{PREFIX}buy <number>`."
        )
    )


@bot.command()
async def buy(
    ctx,
    item: int
):

    if item < 1 or item > len(DEFAULT_SHOP):
        return await ctx.send(
            "❌ Invalid shop item."
        )

    name, price = DEFAULT_SHOP[
        item - 1
    ]

    wallet, bank = get_money(
        ctx.guild.id,
        ctx.author.id
    )

    if wallet < price:
        return await ctx.send(
            f"❌ You need **{price:,} coins**."
        )

    set_money(
        ctx.guild.id,
        ctx.author.id,
        wallet - price,
        bank
    )

    await ctx.send(
        embed=make_embed(
            "🛒 Purchase Complete",
            f"**Item:** {name}\n"
            f"**Price:** {price:,} coins\n\n"
            "✅ Purchase recorded successfully."
        )
    )


# =========================================================
# XP / LEVEL SYSTEM
# =========================================================

async def add_xp(
    message
):

    if message.author.bot:
        return

    guild_id = message.guild.id
    user_id = message.author.id

    row = CUR.execute(
        """
        SELECT xp,level
        FROM levels
        WHERE guild_id=? AND user_id=?
        """,
        (
            guild_id,
            user_id
        )
    ).fetchone()

    if row:
        xp, level = row
    else:
        xp, level = 0, 0

    gained = random.randint(
        5,
        15
    )

    xp += gained

    needed = 100 + (
        level * 50
    )

    if xp >= needed:

        xp -= needed
        level += 1

        CUR.execute(
            """
            UPDATE levels
            SET xp=?,level=?
            WHERE guild_id=? AND user_id=?
            """,
            (
                xp,
                level,
                guild_id,
                user_id
            )
        )

        DB.commit()

        try:
            await message.channel.send(
                f"🎉 {message.author.mention} "
                f"reached **Level {level}**!"
            )
        except discord.HTTPException:
            pass

    else:

        CUR.execute(
            """
            INSERT OR REPLACE INTO levels
            (guild_id,user_id,xp,level)
            VALUES(?,?,?,?)
            """,
            (
                guild_id,
                user_id,
                xp,
                level
            )
        )

        DB.commit()


@bot.command()
async def rank(
    ctx,
    member: discord.Member = None
):

    member = member or ctx.author

    row = CUR.execute(
        """
        SELECT xp,level
        FROM levels
        WHERE guild_id=? AND user_id=?
        """,
        (
            ctx.guild.id,
            member.id
        )
    ).fetchone()

    xp, level = row if row else (0, 0)

    needed = 100 + (
        level * 50
    )

    await ctx.send(
        embed=make_embed(
            f"🏆 {member.display_name}'s Rank",
            f"**Level:** `{level}`\n"
            f"**XP:** `{xp}/{needed}`\n"
            f"**Progress:** `{xp / needed * 100:.1f}%`"
        )
    )


@bot.command(name="levels")
async def levels(ctx):

    rows = CUR.execute(
        """
        SELECT user_id,xp,level
        FROM levels
        WHERE guild_id=?
        ORDER BY level DESC,xp DESC
        LIMIT 10
        """,
        (ctx.guild.id,)
    ).fetchall()

    if not rows:
        return await ctx.send(
            "🏆 No XP data yet."
        )

    lines = []

    for i, (uid, xp, level) in enumerate(
        rows,
        1
    ):

        member = ctx.guild.get_member(uid)

        name = (
            member.display_name
            if member
            else f"User {uid}"
        )

        lines.append(
            f"**{i}.** {name} — "
            f"Level `{level}` • XP `{xp}`"
        )

    await ctx.send(
        embed=make_embed(
            "🏆 Level Leaderboard",
            "\n".join(lines)
        )
    )


# =========================================================
# XP MESSAGE HOOK
# =========================================================

_old_on_message = bot.on_message


@bot.event
async def on_message(message):

    if message.guild and not message.author.bot:
        try:
            await add_xp(message)
        except Exception as e:
            print(
                f"[XP ERROR] {e}"
            )

    await bot.process_commands(
        message
    )
    # =========================================================
# FUN
# =========================================================

@bot.command()
async def coinflip(ctx):

    result = random.choice(
        ["Heads", "Tails"]
    )

    await ctx.send(
        f"🪙 The coin landed on **{result}**!"
    )


@bot.command()
async def dice(ctx):

    result = random.randint(
        1,
        6
    )

    await ctx.send(
        f"🎲 You rolled **{result}**!"
    )


@bot.command()
async def eightball(
    ctx,
    *,
    question: str
):

    answers = [
        "Yes.",
        "No.",
        "Definitely.",
        "Probably.",
        "Ask again later.",
        "I'm not sure.",
        "Absolutely!",
        "Not likely."
    ]

    await ctx.send(
        embed=make_embed(
            "🔮 8Ball",
            f"**Question:** {question}\n\n"
            f"**Answer:** {random.choice(answers)}"
        )
    )


@bot.command()
async def rps(
    ctx,
    choice: str
):

    choice = choice.lower()

    options = [
        "rock",
        "paper",
        "scissors"
    ]

    if choice not in options:
        return await ctx.send(
            "❌ Choose `rock`, `paper`, or `scissors`."
        )

    bot_choice = random.choice(
        options
    )

    if choice == bot_choice:
        result = "It's a draw! 🤝"

    elif (
        (choice == "rock" and bot_choice == "scissors")
        or
        (choice == "paper" and bot_choice == "rock")
        or
        (choice == "scissors" and bot_choice == "paper")
    ):
        result = "You win! 🎉"

    else:
        result = "I win! 😎"

    await ctx.send(
        embed=make_embed(
            "✊ Rock Paper Scissors",
            f"You: **{choice}**\n"
            f"MIMI: **{bot_choice}**\n\n"
            f"{result}"
        )
    )


@bot.command()
async def choose(
    ctx,
    *,
    choices: str
):

    items = [
        x.strip()
        for x in choices.split("|")
        if x.strip()
    ]

    if len(items) < 2:
        return await ctx.send(
            f"❌ Use `{PREFIX}choose option1 | option2`"
        )

    await ctx.send(
        f"🎯 I choose: **{random.choice(items)}**"
    )


@bot.command()
async def rate(
    ctx,
    *,
    thing: str
):

    score = random.randint(
        1,
        100
    )

    await ctx.send(
        f"💗 I rate **{thing}** "
        f"**{score}/100**."
    )


@bot.command()
async def ship(
    ctx,
    user1: discord.Member,
    user2: discord.Member
):

    score = random.randint(
        0,
        100
    )

    await ctx.send(
        embed=make_embed(
            "💞 Compatibility",
            f"{user1.mention} × {user2.mention}\n\n"
            f"💕 Match: **{score}%**"
        )
    )


@bot.command()
async def joke(ctx):

    jokes = [
        "Why did the computer get cold? Because it left its Windows open. 😂",
        "Why was the keyboard tired? It had too many shifts. 😂",
        "Why did the developer go broke? Too many cache problems. 😂"
    ]

    await ctx.send(
        random.choice(jokes)
    )


@bot.command()
async def say(
    ctx,
    *,
    text: str
):

    if not ctx.author.guild_permissions.manage_messages:
        return await ctx.send(
            "❌ You need Manage Messages."
        )

    try:
        await ctx.message.delete()
    except discord.HTTPException:
        pass

    await ctx.send(
        text
    )


# =========================================================
# POLL
# =========================================================

@bot.command()
@commands.has_permissions(
    manage_messages=True
)
async def poll(
    ctx,
    *,
    question: str
):

    embed = make_embed(
        "📊 Poll",
        question
        + "\n\n"
        "👍 = Yes\n"
        "👎 = No"
    )

    message = await ctx.send(
        embed=embed
    )

    await message.add_reaction("👍")
    await message.add_reaction("👎")


# =========================================================
# ANNOUNCEMENT
# =========================================================

@bot.command()
@commands.has_permissions(
    manage_messages=True
)
async def announce(
    ctx,
    *,
    message: str
):

    await ctx.send(
        embed=make_embed(
            "📢 Announcement",
            message
        )
    )


# =========================================================
# GIVEAWAY
# =========================================================

class GiveawayView(View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Enter Giveaway",
        emoji="🎉",
        style=discord.ButtonStyle.green,
        custom_id="mimi:giveaway_enter"
    )
    async def enter(
        self,
        interaction: discord.Interaction,
        button: Button
    ):

        giveaway = CUR.execute(
            """
            SELECT prize
            FROM giveaways
            WHERE message_id=?
            """,
            (
                interaction.message.id,
            )
        ).fetchone()

        if not giveaway:
            return await interaction.response.send_message(
                "❌ This giveaway is no longer active.",
                ephemeral=True
            )

        exists = CUR.execute(
            """
            SELECT 1
            FROM giveaway_entries
            WHERE message_id=? AND user_id=?
            """,
            (
                interaction.message.id,
                interaction.user.id
            )
        ).fetchone()

        if exists:
            return await interaction.response.send_message(
                "⚠️ You already entered!",
                ephemeral=True
            )

        CUR.execute(
            """
            INSERT INTO giveaway_entries
            (message_id,user_id)
            VALUES(?,?)
            """,
            (
                interaction.message.id,
                interaction.user.id
            )
        )

        DB.commit()

        await interaction.response.send_message(
            "🎉 You entered the giveaway!",
            ephemeral=True
        )


@bot.command()
@commands.has_permissions(
    manage_guild=True
)
async def giveaway(
    ctx,
    duration: str,
    *,
    prize: str
):

    seconds = parse_duration(
        duration
    )

    if seconds is None or seconds < 5:
        return await ctx.send(
            "❌ Invalid duration. Example: `10m`, `1h`, `1d`."
        )

    end_time = int(
        time.time() + seconds
    )

    embed = make_embed(
        "🎉 GIVEAWAY",
        f"🎁 **Prize:** {prize}\n\n"
        f"⏰ Ends: <t:{end_time}:R>\n\n"
        "Click **Enter Giveaway** to participate!"
    )

    message = await ctx.send(
        embed=embed,
        view=GiveawayView()
    )

    CUR.execute(
        """
        INSERT OR REPLACE INTO giveaways
        (message_id,channel_id,prize,host_id,end_at)
        VALUES(?,?,?,?,?)
        """,
        (
            message.id,
            ctx.channel.id,
            prize,
            ctx.author.id,
            end_time
        )
    )

    DB.commit()

    await ctx.send(
        f"✅ Giveaway created! Ends <t:{end_time}:R>."
    )

    await asyncio.sleep(
        seconds
    )

    entries = CUR.execute(
        """
        SELECT user_id
        FROM giveaway_entries
        WHERE message_id=?
        """,
        (
            message.id,
        )
    ).fetchall()

    if not entries:
        return await ctx.send(
            "😢 Giveaway ended with no entries."
        )

    winner_id = random.choice(
        entries
    )[0]

    winner = ctx.guild.get_member(
        winner_id
    )

    if winner:
        await ctx.send(
            f"🎉 Congratulations {winner.mention}! "
            f"You won **{prize}**!"
        )

    CUR.execute(
        """
        DELETE FROM giveaways
        WHERE message_id=?
        """,
        (
            message.id,
        )
    )

    DB.commit()


@bot.command()
@commands.has_permissions(
    manage_guild=True
)
async def reroll(
    ctx,
    message_id: int
):

    entries = CUR.execute(
        """
        SELECT user_id
        FROM giveaway_entries
        WHERE message_id=?
        """,
        (
            message_id,
        )
    ).fetchall()

    if not entries:
        return await ctx.send(
            "❌ No giveaway entries found."
        )

    winner_id = random.choice(
        entries
    )[0]

    winner = ctx.guild.get_member(
        winner_id
    )

    if winner:
        await ctx.send(
            f"🎉 New winner: {winner.mention}!"
        )
    else:
        await ctx.send(
            f"🎉 New winner ID: `{winner_id}`"
        )


# =========================================================
# REMINDERS
# =========================================================

@bot.command()
async def remind(
    ctx,
    duration: str,
    *,
    text: str
):

    seconds = parse_duration(
        duration
    )

    if seconds is None:
        return await ctx.send(
            "❌ Invalid duration."
        )

    if seconds > 604800:
        return await ctx.send(
            "❌ Maximum reminder duration is 7 days."
        )

    remind_at = int(
        time.time() + seconds
    )

    CUR.execute(
        """
        INSERT INTO reminders
        (user_id,channel_id,text,remind_at)
        VALUES(?,?,?,?)
        """,
        (
            ctx.author.id,
            ctx.channel.id,
            text,
            remind_at
        )
    )

    DB.commit()

    await ctx.send(
        f"⏰ Reminder set for <t:{remind_at}:R>."
    )


@tasks.loop(seconds=10)
async def reminder_worker():

    now = int(
        time.time()
    )

    rows = CUR.execute(
        """
        SELECT id,user_id,channel_id,text
        FROM reminders
        WHERE remind_at<=?
        """,
        (
            now,
        )
    ).fetchall()

    for rid, uid, cid, text in rows:

        channel = bot.get_channel(
            cid
        )

        if channel:

            try:
                await channel.send(
                    f"⏰ <@{uid}> Reminder: **{text}**"
                )
            except discord.HTTPException:
                pass

        CUR.execute(
            """
            DELETE FROM reminders
            WHERE id=?
            """,
            (
                rid,
            )
        )

    DB.commit()


# =========================================================
# SERVER STATISTICS
# =========================================================

@bot.command()
async def membercount(ctx):

    await ctx.send(
        f"👥 **Members:** {ctx.guild.member_count:,}"
    )


@bot.command()
async def channels(ctx):

    await ctx.send(
        embed=make_embed(
            "📊 Channel Statistics",
            f"💬 Text: **{len(ctx.guild.text_channels)}**\n"
            f"🔊 Voice: **{len(ctx.guild.voice_channels)}**\n"
            f"📁 Categories: **{len(ctx.guild.categories)}**"
        )
    )


@bot.command()
async def roles(ctx):

    role_list = [
        role.mention
        for role in ctx.guild.roles
        if role != ctx.guild.default_role
    ]

    if not role_list:
        return await ctx.send(
            "🎭 No custom roles."
        )

    text = "\n".join(
        role_list[:50]
    )

    await ctx.send(
        embed=make_embed(
            "🎭 Server Roles",
            text
        )
    )


@bot.command()
async def servericon(ctx):

    if not ctx.guild.icon:
        return await ctx.send(
            "❌ This server doesn't have an icon."
        )

    await ctx.send(
        ctx.guild.icon.url
    )


@bot.command()
async def serverbanner(ctx):

    if not ctx.guild.banner:
        return await ctx.send(
            "❌ This server doesn't have a banner."
        )

    await ctx.send(
        ctx.guild.banner.url
    )


# =========================================================
# PROFILE
# =========================================================

@bot.command()
async def profile(
    ctx,
    member: discord.Member = None
):

    member = member or ctx.author

    wallet, bank = get_money(
        ctx.guild.id,
        member.id
    )

    level_data = CUR.execute(
        """
        SELECT xp,level
        FROM levels
        WHERE guild_id=? AND user_id=?
        """,
        (
            ctx.guild.id,
            member.id
        )
    ).fetchone()

    xp, level = (
        level_data
        if level_data
        else (0, 0)
    )

    await ctx.send(
        embed=make_embed(
            f"🌸 {member.display_name}",
            f"💰 Coins: **{wallet + bank:,}**\n"
            f"🏆 Level: **{level}**\n"
            f"✨ XP: **{xp}**\n"
            f"🆔 ID: `{member.id}`"
        )
    )


# =========================================================
# SUGGESTIONS
# =========================================================

@bot.command()
async def suggest(
    ctx,
    *,
    suggestion: str
):

    embed = make_embed(
        "💡 New Suggestion",
        f"{suggestion}\n\n"
        f"Suggested by {ctx.author.mention}"
    )

    message = await ctx.send(
        embed=embed
    )

    await message.add_reaction("👍")
    await message.add_reaction("👎")


# =========================================================
# CUSTOMIZE
# =========================================================

@bot.command()
@commands.has_permissions(
    manage_guild=True
)
async def customize(
    ctx,
    *,
    text: str
):

    await ctx.send(
        embed=make_embed(
            "🎨 Server Customization",
            f"Customization request:\n\n{text}\n\n"
            "Use the server's settings to apply permanent changes."
        )
    )


# =========================================================
# OWNER / DEVELOPER
# =========================================================

@bot.command()
@commands.is_owner()
async def shutdown(ctx):

    await ctx.send(
        "👋 Shutting down..."
    )

    await bot.close()


@bot.command()
@commands.is_owner()
async def sayowner(
    ctx,
    *,
    text: str
):

    try:
        await ctx.message.delete()
    except discord.HTTPException:
        pass

    await ctx.send(
        text
    )


@bot.command()
@commands.is_owner()
async def dbstats(ctx):

    tables = [
        "guild_settings",
        "warnings",
        "economy",
        "levels",
        "giveaways",
        "giveaway_entries",
        "reminders"
    ]

    lines = []

    for table in tables:

        try:
            count = CUR.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]

            lines.append(
                f"**{table}:** `{count}`"
            )

        except sqlite3.Error:
            pass

    await ctx.send(
        embed=make_embed(
            "🗄️ Database Statistics",
            "\n".join(lines)
        )
    )


@bot.command()
@commands.is_owner()
async def reloadbot(ctx):

    await ctx.send(
        "🔄 Restart the bot process to fully reload all code."
    )


# =========================================================
# FINAL COMMANDS
# =========================================================

@bot.command()
async def helpme(ctx):

    await ctx.send(
        embed=make_embed(
            "🌸 𝙼𝙸𝙼𝙸 Help",
            f"Prefix: `{PREFIX}`\n\n"
            "🛡️ Security\n"
            "🔨 Moderation\n"
            "🎫 Tickets\n"
            "💰 Economy\n"
            "🛒 Shop\n"
            "🏆 Levels\n"
            "🎮 Fun\n"
            "🎉 Giveaways\n"
            "📊 Statistics\n"
            "⏰ Reminders\n"
            "💡 Suggestions\n"
            "👑 Developer\n\n"
            f"Use `{PREFIX}commands` to see the command list."
        )
    )


@bot.command(name="commands")
async def commands_list(ctx):

    groups = {
        "🛡️ Security": [
            "antinuke",
            "lockdown",
            "unlockdown",
            "whitelist",
            "unwhitelist",
            "security"
        ],
        "🔨 Moderation": [
            "ban",
            "unban",
            "kick",
            "mute",
            "unmute",
            "warn",
            "warnings",
            "clear",
            "purge",
            "purgeuser",
            "purgebots",
            "slowmode",
            "nick"
        ],
        "🌸 Server": [
            "welcome",
            "goodbye",
            "autorole",
            "automod",
            "automodstatus"
        ],
        "🎫 Tickets": [
            "ticketpanel",
            "closeticket"
        ],
        "💰 Economy": [
            "balance",
            "bal",
            "daily",
            "work",
            "deposit",
            "withdraw",
            "paycoins",
            "leaderboard"
        ],
        "🛒 Shop": [
            "shop",
            "buy"
        ],
        "🏆 Levels": [
            "rank",
            "levels"
        ],
        "🎮 Fun": [
            "coinflip",
            "dice",
            "eightball",
            "rps",
            "choose",
            "rate",
            "ship",
            "joke",
            "say"
        ],
        "🎉 Events": [
            "poll",
            "announce",
            "giveaway",
            "reroll"
        ],
        "📊 Utility": [
            "remind",
            "membercount",
            "channels",
            "roles",
            "servericon",
            "serverbanner",
            "profile",
            "suggest",
            "customize"
        ],
        "👑 Owner": [
            "shutdown",
            "sayowner",
            "dbstats",
            "reloadbot"
        ]
    }

    text = ""

    for category, cmds in groups.items():

        text += (
            f"\n**{category}**\n"
            + " • ".join(
                f"`{PREFIX}{x}`"
                for x in cmds
            )
            + "\n"
        )

    await ctx.send(
        embed=make_embed(
            "📚 𝙼𝙸𝙼𝙸 Commands",
            text
        )
    )


# =========================================================
# STARTUP
# =========================================================

@bot.event
async def on_ready():

    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="over you with tiny paws 🐾💗"
        )
    )

    print(
        f"🌸 Logged in as {bot.user}"
    )

    print(
        f"📚 Commands: {len(bot.commands)}"
    )

    if not reminder_worker.is_running():
        reminder_worker.start()


# =========================================================
# TOKEN CHECK + RUN
# =========================================================

if TOKEN == "PASTE_YOUR_NEW_BOT_TOKEN_HERE":

    print(
        "❌ Please put your Discord bot token in TOKEN."
    )

else:

    bot.run(TOKEN)
