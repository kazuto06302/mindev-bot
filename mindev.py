import os
import discord
from discord.ext import commands

# インテントの設定（必要に応じて権限を追加）
intents = discord.Intents.default()

bot = commands.Bot(command_prefix=[], intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} (ID: {bot.user.id})")
    # スラッシュコマンドをDiscord側へ同期
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")


# スラッシュコマンドの内容
@bot.tree.command(name="ping", description="Returns \"Ping!\"")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"Pong! {latency}ms")


# Botの起動
bot.run(os.getenv("DISCORD_TOKEN"))