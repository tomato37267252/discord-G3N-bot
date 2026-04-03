import discord
from discord.ext import commands


class BanCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def emoji(self, name, default=''):
        return self.bot.config.get('emojis', {}).get(name, default)

    def vouch(self):
        return self.bot.get_cog('VouchSystem')

    # ── $ban ─────────────────────────────────

    @commands.command(name='ban')
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member = None):
        """$ban @user — Bannit définitivement un utilisateur du générateur"""
        cross  = self.emoji('cross',      '❌')
        hammer = self.emoji('ban_hammer', '🔨')

        if not member:
            e = discord.Embed(title=f"{cross} Usage incorrect", color=0xff0000)
            e.description = "**Usage :** `$ban @utilisateur`"
            return await ctx.reply(embed=e, mention_author=False)

        if member.id == ctx.author.id:
            return await ctx.reply("❌ Tu ne peux pas te bannir toi-même.", mention_author=False)

        v = self.vouch()
        if not v:
            return await ctx.reply("❌ Système de vouch indisponible.", mention_author=False)

        gid = str(ctx.guild.id)
        mid = str(member.id)
        v.ensure_guild(gid)
        v.data["permBlocks"][gid][mid] = True
        # Supprimer ban temp si existant
        v.data["tempBlocks"][gid].pop(mid, None)
        v.save_data()

        e = discord.Embed(title=f"{hammer} Ban permanent", color=0xff0000)
        e.description = f"**{member}** est définitivement bloqué du générateur."
        e.add_field(name="Banni par", value=str(ctx.author), inline=True)
        e.add_field(name="ID",        value=str(member.id),  inline=True)
        await ctx.send(embed=e)

    # ── $tempban ─────────────────────────────

    @commands.command(name='tempban')
    @commands.has_permissions(ban_members=True)
    async def tempban(self, ctx, member: discord.Member = None, minutes: int = None):
        """$tempban @user <minutes> — Bannit temporairement un utilisateur du générateur"""
        cross = self.emoji('cross', '❌')
        timer = self.emoji('timer', '⏱️')

        if not member or minutes is None:
            e = discord.Embed(title=f"{cross} Usage incorrect", color=0xff0000)
            e.description = "**Usage :** `$tempban @utilisateur <minutes>`"
            return await ctx.reply(embed=e, mention_author=False)

        if minutes <= 0:
            return await ctx.reply("❌ La durée doit être supérieure à 0.", mention_author=False)

        if member.id == ctx.author.id:
            return await ctx.reply("❌ Tu ne peux pas te bannir toi-même.", mention_author=False)

        v = self.vouch()
        if not v:
            return await ctx.reply("❌ Système de vouch indisponible.", mention_author=False)

        gid = str(ctx.guild.id)
        mid = str(member.id)
        v.ensure_guild(gid)

        if v.data["permBlocks"][gid].get(mid):
            return await ctx.reply(f"❌ **{member}** est déjà banni définitivement. Utilise `$unban` d'abord.", mention_author=False)

        import discord as _d
        expires = int(_d.utils.utcnow().timestamp() + minutes * 60)
        v.data["tempBlocks"][gid][mid] = expires
        v.save_data()

        e = discord.Embed(title=f"{timer} Ban temporaire", color=0xff8800)
        e.description = f"**{member}** est bloqué du générateur pendant **{minutes} minute(s)**."
        e.add_field(name="Banni par", value=str(ctx.author),         inline=True)
        e.add_field(name="Durée",     value=f"{minutes} min",        inline=True)
        e.add_field(name="Expire",    value=f"<t:{expires}:R>",      inline=False)
        await ctx.send(embed=e)

    # ── $unban ───────────────────────────────

    @commands.command(name='unban')
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, member: discord.Member = None):
        """$unban @user — Débloque un utilisateur du générateur"""
        cross = self.emoji('cross', '❌')
        unban = self.emoji('unban', '🔓')

        if not member:
            e = discord.Embed(title=f"{cross} Usage incorrect", color=0xff0000)
            e.description = "**Usage :** `$unban @utilisateur`"
            return await ctx.reply(embed=e, mention_author=False)

        v = self.vouch()
        if not v:
            return await ctx.reply("❌ Système de vouch indisponible.", mention_author=False)

        gid = str(ctx.guild.id)
        mid = str(member.id)
        v.ensure_guild(gid)

        perm = v.data["permBlocks"][gid].pop(mid, None)
        temp = v.data["tempBlocks"][gid].pop(mid, None)

        if not perm and not temp:
            return await ctx.reply(f"❌ **{member}** n'est pas banni.", mention_author=False)

        v.save_data()

        types = []
        if perm: types.append("Ban permanent")
        if temp: types.append("Ban temporaire")

        e = discord.Embed(title=f"{unban} Utilisateur débanni", color=0x00ff00)
        e.description = f"**{member}** peut à nouveau utiliser le générateur."
        e.add_field(name="Débanni par",    value=str(ctx.author),      inline=True)
        e.add_field(name="Type supprimé",  value=" + ".join(types),    inline=True)
        await ctx.send(embed=e)

    # ── $bans ────────────────────────────────

    @commands.command(name='bans')
    @commands.has_permissions(ban_members=True)
    async def bans(self, ctx):
        """$bans — Liste tous les utilisateurs bannis du générateur (admin)"""
        v = self.vouch()
        if not v:
            return await ctx.reply("❌ Système de vouch indisponible.", mention_author=False)

        gid  = str(ctx.guild.id)
        v.ensure_guild(gid)

        perm_ids = list(v.data["permBlocks"][gid].keys())
        temp_ids = list(v.data["tempBlocks"][gid].keys())

        e = discord.Embed(title="🚫 Bannis du générateur", color=0xff0000)

        perm_lines = [f"• <@{uid}>" for uid in perm_ids] or ["Aucun"]
        temp_lines = []
        import datetime as _dt
        now_ts = _dt.datetime.now().timestamp()
        for uid, ts in v.data["tempBlocks"][gid].items():
            if now_ts <= ts:
                temp_lines.append(f"• <@{uid}> — expire <t:{ts}:R>")
        if not temp_lines:
            temp_lines = ["Aucun"]

        e.add_field(name="🔒 Permanents",  value="\n".join(perm_lines), inline=False)
        e.add_field(name="⏱️ Temporaires", value="\n".join(temp_lines), inline=False)
        await ctx.send(embed=e)


async def setup(bot):
    await bot.add_cog(BanCommands(bot))
