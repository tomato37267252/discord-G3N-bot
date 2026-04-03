import discord
from discord.ext import commands
import json
import os
import datetime
import re
import asyncio

DATA_FILE   = 'data.json'
COUNTDOWN   = 300    # secondes pour voucher après une génération
BAN_MINUTES = 30     # durée de ban par défaut si pas de vouch

ALLOWED_SERVICES = [
    "mc_bedrock", "xbox", "minecraft", "steam",
    "cape", "unbanned", "mcfa", "crunchyroll", "donut"
]


class VouchSystem(commands.Cog):
    def __init__(self, bot):
        self.bot     = bot
        self.data    = {"permBlocks": {}, "tempBlocks": {}}
        self.pending = {}   # {guild_id: {user_id: asyncio.Task}}
        self.load_data()

        cfg = self.bot.config.get('botConfig', {})
        self.vouch_channel_id    = int(cfg.get('vouchChannelId',          0))
        self.vouch_target_id     = int(cfg.get('vouchTargetId',           0))
        self.failure_log_id      = int(cfg.get('vouchFailureLogChannelId', 0))
        self.appeal_channel_id   = int(cfg.get('appealChannelId',         0))

        items_re = "|".join(re.escape(s) for s in ALLOWED_SERVICES)
        self.vouch_regex   = re.compile(
            rf"^Legit\s+got\s+({items_re})\s+by\s+<@!?(\d+)>$", re.I
        )
        self.attempt_regex = re.compile(r"^(vouch|legit|got)\b.*", re.I)

    # ── Data ─────────────────────────────────

    def emoji(self, name, default=''):
        return self.bot.config.get('emojis', {}).get(name, default)

    def load_data(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r') as f:
                    self.data = json.load(f)
                    return
            except Exception:
                pass
        self.save_data()

    def save_data(self):
        with open(DATA_FILE, 'w') as f:
            json.dump(self.data, f, indent=2)

    def ensure_guild(self, gid):
        gid = str(gid)
        self.data["permBlocks"].setdefault(gid, {})
        self.data["tempBlocks"].setdefault(gid, {})
        self.pending.setdefault(gid, {})

    # ── Vérifications ────────────────────────

    def is_blocked(self, guild, user_id) -> bool:
        gid = str(guild.id)
        uid = str(user_id)
        self.ensure_guild(gid)
        if self.data["permBlocks"][gid].get(uid):
            return True
        ts = self.data["tempBlocks"][gid].get(uid)
        if ts and datetime.datetime.now().timestamp() <= ts:
            return True
        return False

    def is_valid_vouch(self, content: str) -> bool:
        m = self.vouch_regex.match(content.strip())
        return bool(m) and int(m.group(2)) == self.vouch_target_id

    # ── Blocage automatique ──────────────────

    async def block_user(self, guild, member, reason: str):
        gid = str(guild.id)
        mid = str(member.id)
        self.ensure_guild(gid)
        if mid in self.data["tempBlocks"][gid]:
            return

        expires_ts = int(
            (datetime.datetime.now() + datetime.timedelta(minutes=BAN_MINUTES)).timestamp()
        )
        bans    = self.emoji('bans',     '🚫')
        lock    = self.emoji('lock_key', '🔒')
        notepad = self.emoji('notepad',  '📝')
        timer   = self.emoji('timer',    '⏱️')

        embed = discord.Embed(title=f"{bans} Banni temporairement", color=0x000000)
        embed.description = f"{lock} {member.mention} est **bloqué temporairement** du générateur."
        embed.add_field(name=f"{notepad} Raison",   value=f"> {reason}",                      inline=False)
        embed.add_field(name=f"{timer} Durée",      value=f"> {BAN_MINUTES} minutes",         inline=True)
        embed.add_field(name=f"{timer} Expire",     value=f"> <t:{expires_ts}:R>",            inline=True)
        embed.add_field(name=f"{notepad} Appel",    value=f"> <#{self.appeal_channel_id}>",   inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)

        log_ch = self.bot.get_channel(self.failure_log_id)
        if log_ch:
            await log_ch.send(content=member.mention, embed=embed)
        try:
            await member.send(embed=embed)
        except Exception:
            pass

        self.data["tempBlocks"][gid][mid] = expires_ts
        self.save_data()

        # Déblocage automatique après la durée
        await asyncio.sleep(BAN_MINUTES * 60)
        if self.data["tempBlocks"].get(gid, {}).get(mid) == expires_ts:
            del self.data["tempBlocks"][gid][mid]
            self.save_data()
            unban = self.emoji('unban', '🔓')
            unban_embed = discord.Embed(
                title=f"{unban} Ban expiré",
                description=f"🎉 {member.mention} peut à nouveau utiliser le générateur.",
                color=0x00ff80
            )
            if log_ch:
                await log_ch.send(content=member.mention, embed=unban_embed)
            try:
                await member.send(embed=unban_embed)
            except Exception:
                pass

    # ── Countdown après génération ───────────

    def register_pending(self, guild, member):
        gid = str(guild.id)
        mid = str(member.id)
        self.ensure_guild(gid)

        # Annuler le précédent si existant
        old = self.pending[gid].get(mid)
        if old and not old.done():
            old.cancel()

        async def countdown():
            await asyncio.sleep(COUNTDOWN)
            if self.pending.get(gid, {}).get(mid):
                asyncio.create_task(
                    self.block_user(guild, member, "N'a pas vouché après avoir généré un compte")
                )
                self.pending[gid].pop(mid, None)

        self.pending[gid][mid] = asyncio.create_task(countdown())

    # ── Listener de messages ─────────────────

    async def handle_message(self, message):
        if message.author.bot or not message.guild:
            return
        if message.channel.id != self.vouch_channel_id:
            return

        gid = str(message.guild.id)
        mid = str(message.author.id)
        self.ensure_guild(gid)
        content = message.content.strip()

        looks_like_vouch = self.attempt_regex.match(content)
        valid            = self.is_valid_vouch(content)

        if looks_like_vouch and not valid:
            try:
                await message.delete()
            except Exception:
                pass
            cross = self.emoji('cross', '❌')
            await message.channel.send(
                f"{message.author.mention} {cross} Vouch invalide.\n"
                f"Format attendu : `Legit got <service> by <@{self.vouch_target_id}>`",
                delete_after=8
            )
            return

        if valid and mid in self.pending.get(gid, {}):
            task = self.pending[gid].pop(mid, None)
            if task and not task.done():
                task.cancel()
            tick = self.emoji('tick', '✅')
            await message.add_reaction(tick or '✅')

    # ── Commandes admin ──────────────────────

    @commands.command(name='setbantime')
    @commands.has_permissions(administrator=True)
    async def setbantime(self, ctx, minutes: int = None):
        """$setbantime <minutes> — Définit la durée du ban auto (admin)"""
        global BAN_MINUTES
        tick  = self.emoji('tick',  '✅')
        cross = self.emoji('cross', '❌')

        if not minutes or minutes <= 0:
            e = discord.Embed(title=f"{cross} Usage incorrect", color=0xff0000)
            e.description = "**Usage :** `$setbantime <minutes>`"
            return await ctx.reply(embed=e, mention_author=False)

        BAN_MINUTES = minutes
        e = discord.Embed(title=f"{tick} Durée mise à jour", color=0x00ff00)
        e.description = f"La durée du ban auto est maintenant de **{minutes} minute(s)**."
        await ctx.reply(embed=e, mention_author=False)

    @commands.command(name='pending')
    @commands.has_permissions(administrator=True)
    async def show_pending(self, ctx):
        """$pending — Affiche les utilisateurs qui n'ont pas encore vouché (admin)"""
        gid   = str(ctx.guild.id)
        self.ensure_guild(gid)
        users = self.pending.get(gid, {})

        if not users:
            return await ctx.reply("✅ Personne n'est en attente de vouch.", mention_author=False)

        lines = []
        for uid in users:
            member = ctx.guild.get_member(int(uid))
            lines.append(f"• {member.mention if member else f'<@{uid}>'}")

        e = discord.Embed(title="⏳ En attente de vouch", color=0xffaa00)
        e.description = "\n".join(lines)
        await ctx.reply(embed=e, mention_author=False)


async def setup(bot):
    await bot.add_cog(VouchSystem(bot))
