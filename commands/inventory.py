import discord
from discord.ext import commands
import os
import aiohttp

# Structure du stock (doit correspondre à generation.py)
STOCK_PATHS = {
    "🆓 Freemium Vault": {
        "Minecraft":   "stock/Minecraft.txt",
        "Steam":       "stock/Steam.txt",
        "Crunchyroll": "stock/Crunchyroll.txt",
        "Mc_Bedrock":  "stock/Mc_Bedrock.txt",
        "Xbox":        "stock/Xbox.txt",
        "Cape":        "stock/Cape.txt",
    },
    "🚀 Booster Vault": {
        "Donut":    "bosststock/Donut.txt",
        "Unbanned": "bosststock/Unbanned.txt",
    },
    "💎 Premium Vault": {
        "Mcfa": "paidstock/Mcfa.txt",
    }
}


class InventoryCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def emoji(self, name, default='📦'):
        return self.bot.config.get('emojis', {}).get(name, default)

    def count(self, path):
        try:
            if not os.path.exists(path):
                return 0
            with open(path, 'r', encoding='utf-8') as f:
                return len([l for l in f.read().splitlines() if l.strip()])
        except Exception:
            return 0

    # ── $stock ───────────────────────────────

    @commands.command(name='stock')
    async def stock(self, ctx):
        """$stock — Affiche le stock disponible"""
        warden = self.emoji('warden', '🛡️')
        star   = self.emoji('s_yellow', '⭐')

        embed = discord.Embed(
            title=f"{warden} WardenCloud — Inventaire",
            color=0x001000
        )
        embed.description = "```État actuel du stock```"

        for vault, services in STOCK_PATHS.items():
            lines = ""
            for name, path in services.items():
                n = self.count(path)
                bar = "🟢" if n > 10 else ("🟡" if n > 0 else "🔴")
                lines += f"{bar} `{name:<12}` → **{n}** unités\n"
            embed.add_field(name=vault, value=lines or "Vide", inline=False)

        embed.set_footer(text="WardenCloud • Système de stock")
        await ctx.send(embed=embed)

    # ── $restock ─────────────────────────────

    @commands.command(name='restock')
    @commands.has_permissions(administrator=True)
    async def restock(self, ctx, vault: str = None, service: str = None):
        """$restock <vault> <service> + fichier .txt joint — Ajoute du stock (admin)"""
        tick  = self.emoji('tick', '✅')
        cross = self.emoji('cross', '❌')

        if not vault or not service:
            e = discord.Embed(title=f"{cross} Usage incorrect", color=0xff0000)
            e.description = "**Usage :** `$restock <vault> <service>`\nJoins un fichier `.txt` à ton message.\n\n**Vaults :** `freemium` | `booster` | `premium`"
            return await ctx.reply(embed=e, mention_author=False)

        # Correspondance vault → clé interne
        vault_map = {
            "freemium": "🆓 Freemium Vault",
            "booster":  "🚀 Booster Vault",
            "premium":  "💎 Premium Vault",
        }
        vault_key = vault_map.get(vault.lower())
        if not vault_key or vault_key not in STOCK_PATHS:
            e = discord.Embed(title=f"{cross} Vault inconnu", color=0xff0000)
            e.description = "Vaults valides : `freemium`, `booster`, `premium`"
            return await ctx.reply(embed=e, mention_author=False)

        # Correspondance service (insensible à la casse)
        service_path = None
        for sname, spath in STOCK_PATHS[vault_key].items():
            if sname.lower() == service.lower():
                service_path = spath
                break

        if not service_path:
            dispo = ', '.join(f'`{s}`' for s in STOCK_PATHS[vault_key])
            e = discord.Embed(title=f"{cross} Service introuvable", color=0xff0000)
            e.description = f"Services disponibles dans **{vault_key}** : {dispo}"
            return await ctx.reply(embed=e, mention_author=False)

        if not ctx.message.attachments:
            e = discord.Embed(title=f"{cross} Fichier manquant", color=0xff0000)
            e.description = "Attache un fichier `.txt` contenant les comptes (un par ligne)."
            return await ctx.reply(embed=e, mention_author=False)

        att = ctx.message.attachments[0]
        if not att.filename.endswith('.txt'):
            e = discord.Embed(title=f"{cross} Format incorrect", color=0xff0000)
            e.description = "Le fichier doit être au format `.txt`."
            return await ctx.reply(embed=e, mention_author=False)

        async with aiohttp.ClientSession() as session:
            async with session.get(att.url) as r:
                text = await r.text(encoding='utf-8', errors='ignore')

        lines = [l.strip() for l in text.splitlines() if l.strip()]
        os.makedirs(os.path.dirname(service_path), exist_ok=True)
        with open(service_path, 'a', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')

        # Annonce dans le salon restock
        restock_ch = int(self.bot.config.get('botConfig', {}).get('restockChannelId', 0))
        if restock_ch:
            ch = self.bot.get_channel(restock_ch)
            if ch:
                ann = discord.Embed(
                    title="🔄 Restock !",
                    description=f"**{service.capitalize()}** vient d'être restocké avec **{len(lines)}** comptes !",
                    color=0x00ff00
                )
                await ch.send(embed=ann)

        e = discord.Embed(title=f"{tick} Restock réussi !", color=0x00ff00)
        e.description = f"**{len(lines)}** compte(s) ajouté(s) à `{service}` dans **{vault_key}**."
        await ctx.reply(embed=e, mention_author=False)

    # ── $removestock ─────────────────────────

    @commands.command(name='removestock')
    @commands.has_permissions(administrator=True)
    async def removestock(self, ctx, service: str = None):
        """$removestock <service|all> — Vide un stock (admin)"""
        tick  = self.emoji('tick', '✅')
        cross = self.emoji('cross', '❌')

        if not service:
            e = discord.Embed(title=f"{cross} Usage incorrect", color=0xff0000)
            e.description = "**Usage :** `$removestock <service>` ou `$removestock all`"
            return await ctx.reply(embed=e, mention_author=False)

        paths = []
        if service.lower() == 'all':
            for vault_services in STOCK_PATHS.values():
                paths.extend(vault_services.values())
        else:
            for vault_services in STOCK_PATHS.values():
                for sname, spath in vault_services.items():
                    if sname.lower() == service.lower():
                        paths.append(spath)

        if not paths:
            e = discord.Embed(title=f"{cross} Introuvable", color=0xff0000)
            e.description = f"Aucun fichier de stock trouvé pour `{service}`."
            return await ctx.reply(embed=e, mention_author=False)

        for p in paths:
            if os.path.exists(p):
                with open(p, 'w', encoding='utf-8') as f:
                    f.truncate(0)

        e = discord.Embed(title=f"{tick} Stock vidé", color=0x00ff00)
        e.description = f"**{len(paths)}** fichier(s) de stock vidé(s)."
        await ctx.reply(embed=e, mention_author=False)


async def setup(bot):
    await bot.add_cog(InventoryCommands(bot))
