import os
import discord
from discord.ext import commands

# web server
from threading import Thread
from flask import Flask
app = Flask("")
@app.route("/")
def home():
    return "Bot is active!"
def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
Thread(target=run_web).start()


intents = discord.Intents.default()

bot = commands.Bot(
    command_prefix=[],
    intents=intents
)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} (ID: {bot.user.id})")

    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")


async def load_extensions():
    await bot.load_extension("cogs.ping")
    await bot.load_extension("cogs.permission_sync")


async def main():
    async with bot:
        await load_extensions()
        await bot.start(os.getenv("DISCORD_TOKEN"))


import asyncio

asyncio.run(main())
