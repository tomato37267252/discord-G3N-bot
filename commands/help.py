import discord
from discord.ext import commands


class HelpCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def emoji(self, name, default=''):
        return self.bot.config.get('emojis', {}).get(name, default)

    @commands.command(name='help')
    async def help_cmd(self, ctx):
        """$help — Affiche toutes les commandes disponibles"""
        ice      = self.emoji('ice_cube',   '🧊')
        globe    = self.emoji('globe',      '🌐')
        gold     = self.emoji('gold',       '💰')
        booster  = self.emoji('booster',    '🚀')
        paid     = self.emoji('paid',       '💎')
        stock_e  = self.emoji('stock',      '📦')
        restock  = self.emoji('restock',    '🔄')
        mod      = self.emoji('Moderation', '🛡️')
        hammer   = self.emoji('ban_hammer', '🔨')
        timer    = self.emoji('timer',      '⏱️')
        unlock   = self.emoji('unlock_s',   '🔓')
        stop     = self.emoji('stop_sign',  '🛑')
        books    = self.emoji('books',      '📚')
        search   = self.emoji('search',     '🔍')
        bans_e   = self.emoji('bans',       '🚫')
        notepad  = self.emoji('notepad',    '📝')

        embed = discord.Embed(
            title=f"{ice} WardenCloud — Panneau d'aide",
            color=0x001000
        )
        embed.description = "Utilise les commandes ci-dessous selon ton accès.\nChaque commande doit être utilisée dans le bon salon."

        embed.add_field(
            name=f"{globe}  Génération de comptes",
            value=(
                f"{gold} `$free <service>`       → Compte tier gratuit\n"
                f"{booster} `$bosst <service>`      → Compte tier Booster\n"
                f"{paid} `$vip <service>`        → Compte tier VIP/Premium"
            ),
            inline=False
        )
        embed.add_field(
            name=f"{stock_e}  Stock & Gestion",
            value=(
                f"{stock_e} `$stock`                → Voir tout le stock disponible\n"
                f"{restock} `$restock <v> <s>`      → Ajouter du stock (admin, joindre .txt)\n"
                f"{stop} `$removestock <s>`     → Vider un stock (admin)"
            ),
            inline=False
        )
        embed.add_field(
            name=f"{mod}  Modération du générateur",
            value=(
                f"{hammer} `$ban @user`            → Ban permanent du générateur\n"
                f"{timer} `$tempban @user <min>`  → Ban temporaire\n"
                f"{unlock} `$unban @user`          → Débannir un utilisateur\n"
                f"{bans_e} `$bans`                  → Liste des bannis\n"
                f"{stop} `$setbantime <min>`    → Durée du ban auto (défaut: 30 min)"
            ),
            inline=False
        )
        embed.add_field(
            name=f"{books}  Utilitaires",
            value=(
                f"{search} `$cstatus`              → Vérifier son statut Discord\n"
                f"{notepad} `$pending`              → Voir les vouch en attente (admin)\n"
                f"{notepad} `$setstatus <texte>`    → Changer le texte de statut requis (admin)"
            ),
            inline=False
        )

        embed.set_footer(text="WardenCloud • Guide des commandes")
        await ctx.reply(embed=embed, mention_author=False)


async def setup(bot):
    await bot.add_cog(HelpCommand(bot))
