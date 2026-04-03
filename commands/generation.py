import discord
from discord.ext import commands
import os
import datetime

# ──────────────────────────────────────────
#  Services disponibles par tier
# ──────────────────────────────────────────
SERVICES = {
    "free": {
        "config_key": "genChannelId",
        "services": {
            "minecraft":   "stock/Minecraft.txt",
            "steam":       "stock/Steam.txt",
            "crunchyroll": "stock/Crunchyroll.txt",
            "mc_bedrock":  "stock/Mc_Bedrock.txt",
            "xbox":        "stock/Xbox.txt",
            "cape":        "stock/Cape.txt",
        }
    },
    "booster": {
        "config_key": "boosterChannelId",
        "services": {
            "donut":    "bosststock/Donut.txt",
            "unbanned": "bosststock/Unbanned.txt",
        }
    },
    "vip": {
        "config_key": "vipChannelId",
        "services": {
            "mcfa": "paidstock/Mcfa.txt",
        }
    }
}


class GenerationCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        cfg = self.bot.config.get('botConfig', {})
        # Résoudre les channel IDs depuis la config
        self.channel_ids = {
            tier: int(cfg.get(data["config_key"], 0))
            for tier, data in SERVICES.items()
        }

    # ── Helpers ──────────────────────────────

    def emoji(self, name, default=''):
        return self.bot.config.get('emojis', {}).get(name, default)

    def get_account(self, file_path):
        """Retire et retourne la première ligne d'un fichier stock."""
        if not os.path.exists(file_path):
            return None
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = [l for l in f.read().splitlines() if l.strip()]
            if not lines:
                return None
            account = lines.pop(0)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines) + ('\n' if lines else ''))
            return account
        except Exception:
            return None

    # ── Logique principale ───────────────────

    async def run_gen(self, ctx, tier: str, service_name: str | None):
        tier_data   = SERVICES[tier]
        channel_id  = self.channel_ids[tier]

        cross   = self.emoji('cross',     '❌')
        arrow   = self.emoji('arrow_arrow','➡️')
        excl    = self.emoji('red_excl',  '🚨')
        star    = self.emoji('s_yellow',  '⭐')
        mail    = self.emoji('mail',      '📧')
        pwd     = self.emoji('password',  '🔑')
        success = self.emoji('success',   '✅')
        upload  = self.emoji('upload',    '📤')

        # Mauvais salon
        if ctx.channel.id != channel_id:
            e = discord.Embed(title=f"{cross} Mauvais salon", color=0xff0000)
            e.description = f"{arrow} Utilise cette commande dans <#{channel_id}>."
            return await ctx.reply(embed=e, mention_author=False)

        # Service manquant
        if not service_name:
            e = discord.Embed(title=f"{cross} Service manquant", color=0xff0000)
            e.description = f"{arrow} Précise un service. Exemple : `$free minecraft`\nVoir `$stock` pour la liste."
            return await ctx.reply(embed=e, mention_author=False)

        service_name = service_name.lower()
        file_path    = tier_data["services"].get(service_name)

        # Service inconnu
        if not file_path:
            dispo = ', '.join(f'`{s}`' for s in tier_data["services"])
            e = discord.Embed(title=f"{excl} Service introuvable", color=0xff0000)
            e.description = f"{arrow} Services disponibles pour ce tier : {dispo}"
            return await ctx.reply(embed=e, mention_author=False)

        # Utilisateur banni
        vouch = self.bot.get_cog('VouchSystem')
        if vouch and vouch.is_blocked(ctx.guild, ctx.author.id):
            e = discord.Embed(title=f"{cross} Accès bloqué", color=0xff0000)
            e.description = (
                f"{arrow} Tu es temporairement bloqué du générateur.\n"
                f"**Raison :** Tu n'as pas vouché à temps.\n"
                f"**Appel :** <#{self.bot.config.get('botConfig',{}).get('appealChannelId',0)}>"
            )
            return await ctx.reply(embed=e, mention_author=False)

        # Récupérer le compte
        account = self.get_account(file_path)
        if not account:
            e = discord.Embed(title=f"{excl} Stock épuisé", color=0xff0000)
            e.description = f"{arrow} Ce service est actuellement en rupture de stock."
            return await ctx.reply(embed=e, mention_author=False)

        # Enregistrer pour le système de vouch
        if vouch:
            vouch.pending.setdefault(str(ctx.guild.id), {})[str(ctx.author.id)] = {
                "time": datetime.datetime.now(),
                "service": service_name
            }

        # Envoi en DM
        try:
            parts = account.split(':', 1)
            dm = discord.Embed(title=f"{star} Ton compte est là ! {star}", color=0x00ff00)
            if len(parts) == 2:
                dm.add_field(name=f"{mail} Email",       value=f"||`{parts[0]}`||", inline=True)
                dm.add_field(name=f"{pwd} Mot de passe", value=f"||`{parts[1]}`||", inline=True)
            dm.add_field(name=f"{star} Combo", value=f"||```\n{account}\n```||", inline=False)
            vouch_ch = self.bot.config.get('botConfig', {}).get('vouchChannelId', 0)
            dm.add_field(
                name=f"🚨 Obligation de vouch",
                value=f"Pense à voucher dans <#{vouch_ch}> sinon tu seras bloqué !",
                inline=False
            )
            await ctx.author.send(embed=dm)
        except discord.Forbidden:
            # DM fermés → on envoie en éphémère si possible
            e = discord.Embed(title=f"{excl} DMs fermés", color=0xff0000)
            e.description = f"{arrow} Impossible de t'envoyer ton compte en DM. Ouvre tes DMs et réessaie."
            return await ctx.reply(embed=e, mention_author=False)

        # Confirmation publique
        pub = discord.Embed(title=f"{success} Compte généré !", color=0x00ff00)
        pub.description = (
            f"{upload} Ton compte a été envoyé en DM.\n\n"
            f"{star} Service : **{service_name}**\n"
            f"{star} Généré par : {ctx.author.mention}\n\n"
            f"⚠️ Vouche ou tu seras bloqué du générateur."
        )
        await ctx.reply(embed=pub, mention_author=False)

    # ── Commandes ────────────────────────────

    @commands.command(name='free')
    async def free(self, ctx, service: str = None):
        """$free <service> — Génère un compte Free tier"""
        await self.run_gen(ctx, "free", service)

    @commands.command(name='bosst')
    async def bosst(self, ctx, service: str = None):
        """$bosst <service> — Génère un compte Booster tier"""
        await self.run_gen(ctx, "booster", service)

    @commands.command(name='vip')
    async def vip(self, ctx, service: str = None):
        """$vip <service> — Génère un compte VIP tier"""
        await self.run_gen(ctx, "vip", service)


async def setup(bot):
    await bot.add_cog(GenerationCommands(bot))
