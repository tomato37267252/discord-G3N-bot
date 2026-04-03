import discord
from discord.ext import commands
import json
import os

# ──────────────────────────────────────────
#  Chargement de la config
# ──────────────────────────────────────────
try:
    with open('config.json', 'r') as f:
        config_data = json.load(f)
except Exception:
    config_data = {}


class WardenBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.presences = True
        super().__init__(command_prefix='$', intents=intents, help_command=None)
        self.config = config_data
        cfg = self.config.get('botConfig', {})
        self.gen_channel_id      = int(cfg.get('genChannelId',      0))
        self.logs_channel_id     = int(cfg.get('logsChannelId',     0))
        self.status_role_id      = int(cfg.get('statusRoleId',      0))
        self.status_text         = cfg.get('statusText', '.gg/warden-cloud : Free MCFA Generator')

    async def setup_hook(self):
        print("🔍 Chargement des extensions...")
        for filename in os.listdir('./commands'):
            if filename.endswith('.py') and filename != '__init__.py':
                try:
                    await self.load_extension(f'commands.{filename[:-3]}')
                    print(f"  ✅ {filename}")
                except Exception as e:
                    print(f"  ❌ {filename} : {e}")

    async def on_ready(self):
        print(f'\n✅ Connecté en tant que {self.user} (ID: {self.user.id})')
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=".gg/wardencloud"
            )
        )
        try:
            synced = await self.tree.sync()
            print(f"✅ {len(synced)} slash-command(s) synchronisée(s)\n")
        except Exception as e:
            print(f"❌ Sync échouée : {e}")

    async def on_message(self, message):
        if message.author.bot:
            return

        # Système de vouch
        vouch = self.get_cog('VouchSystem')
        if vouch and hasattr(vouch, 'handle_message'):
            await vouch.handle_message(message)

        if message.content.startswith('$'):
            await self.process_commands(message)

    async def on_presence_update(self, before, after):
        if after.bot or not after.guild:
            return
        custom_status = next(
            (a for a in after.activities if isinstance(a, discord.CustomActivity)), None
        )
        has_target = custom_status and custom_status.state and self.status_text in custom_status.state
        role = after.guild.get_role(self.status_role_id)
        if not role:
            return
        log_channel = self.get_channel(self.logs_channel_id)
        try:
            if has_target and role not in after.roles:
                await after.add_roles(role)
                if log_channel:
                    await log_channel.send(f"✅ **{after}** a le bon statut → rôle ajouté")
            elif not has_target and role in after.roles:
                await after.remove_roles(role)
                if log_channel:
                    await log_channel.send(f"❌ **{after}** a changé/retiré son statut → rôle retiré")
        except Exception as e:
            print(f"⚠️ Mise à jour du rôle échouée pour {after} : {e}")


bot = WardenBot()

if __name__ == "__main__":
    token = (
        config_data.get('botConfig', {}).get('token')
        or os.environ.get("DISCORD_TOKEN")
    )
    if not token:
        print("❌ Aucun token trouvé ! Remplis 'token' dans config.json ou la variable DISCORD_TOKEN.")
    else:
        bot.run(token)
