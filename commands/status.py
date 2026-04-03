import discord
from discord.ext import commands
from discord.ext import tasks


class StatusRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        cfg = self.bot.config.get('botConfig', {})
        self.role_id     = int(cfg.get('statusRoleId',  0))
        self.log_ch_id   = int(cfg.get('logsChannelId', 0))
        self.status_text = cfg.get('statusText', '.gg/warden-cloud : Free MCFA Generator')
        self.check_loop.start()

    def cog_unload(self):
        self.check_loop.cancel()

    def emoji(self, name, default=''):
        return self.bot.config.get('emojis', {}).get(name, default)

    # ── Boucle de vérification ───────────────

    @tasks.loop(minutes=5)
    async def check_loop(self):
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            role = guild.get_role(self.role_id)
            if not role:
                continue
            async for member in guild.fetch_members(limit=None):
                if member.bot:
                    continue
                has_status = any(
                    isinstance(a, discord.CustomActivity) and a.state and self.status_text in a.state
                    for a in member.activities
                )
                try:
                    if has_status and role not in member.roles:
                        await member.add_roles(role)
                    elif not has_status and role in member.roles:
                        await member.remove_roles(role)
                except Exception as e:
                    print(f"⚠️ StatusRole — erreur pour {member}: {e}")

    # ── $cstatus ─────────────────────────────

    @commands.command(name='cstatus')
    async def cstatus(self, ctx):
        """$cstatus — Vérifie ton statut Discord et attribue/retire le rôle"""
        role     = ctx.guild.get_role(self.role_id)
        warning  = self.emoji('warning', '⚠️')
        tick     = self.emoji('tick',    '✅')
        hearts   = self.emoji('hearts_blue', '💙')

        if not role:
            e = discord.Embed(title=f"{warning} Rôle introuvable", color=0xff0000)
            e.description = "Le rôle de statut n'est pas configuré. Contacte un admin."
            return await ctx.reply(embed=e, mention_author=False)

        member     = ctx.author
        has_status = any(
            isinstance(a, discord.CustomActivity) and a.state and self.status_text in a.state
            for a in member.activities
        )

        if has_status:
            if role not in member.roles:
                await member.add_roles(role)
            e = discord.Embed(color=0x2ecc71)
            e.description = (
                f"{hearts} **Statut vérifié !**\n\n"
                f"{tick} Tu as le bon statut. Le rôle a été attribué !\n"
                "Garde ce statut pour conserver le rôle."
            )
        else:
            if role in member.roles:
                await member.remove_roles(role)
            e = discord.Embed(title=f"{warning} Vérification échouée", color=0xff0000)
            e.description = (
                "**Pour obtenir le rôle, tu dois :**\n"
                "1. Être **En ligne, Absent ou Ne pas déranger** (pas Invisible)\n"
                "2. Avoir ce texte exact dans ton Statut Personnalisé :\n"
                f"```\n{self.status_text}\n```"
            )

        await ctx.reply(embed=e, mention_author=False)

    # ── $setstatus ───────────────────────────

    @commands.command(name='setstatus')
    @commands.has_permissions(administrator=True)
    async def setstatus(self, ctx, *, text: str = None):
        """$setstatus <texte> — Change le texte de statut requis (admin)"""
        tick  = self.emoji('tick',  '✅')
        cross = self.emoji('cross', '❌')

        if not text:
            e = discord.Embed(title=f"{cross} Usage incorrect", color=0xff0000)
            e.description = "**Usage :** `$setstatus <texte du statut>`"
            return await ctx.reply(embed=e, mention_author=False)

        self.status_text            = text
        self.bot.status_text        = text   # synchro avec main.py
        e = discord.Embed(title=f"{tick} Statut mis à jour", color=0x00ff00)
        e.description = f"Nouveau texte requis :\n```\n{text}\n```"
        await ctx.reply(embed=e, mention_author=False)


async def setup(bot):
    await bot.add_cog(StatusRole(bot))
