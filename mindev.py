import os
import discord
from discord.ext import commands
import asyncio

from threading import Thread
from flask import Flask

app = Flask("")

TEST_GUILD_ID = 1542198719339040830


@app.route("/")
def home():
    return "Bot is active!"


def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)


Thread(target=run_web, daemon=True).start()


intents = discord.Intents.default()

bot = commands.Bot(
    command_prefix=[],
    intents=intents
)

# global commandに変更する必要あり
@bot.event
async def on_ready():
    print(
        f"Logged in as {bot.user.name} "
        f"(ID: {bot.user.id})",
        flush=True
    )

    print("Clearing global commands...", flush=True)

    bot.tree.clear_commands(guild=None)

    synced = await bot.tree.sync()

    print(
        f"Global commands cleared. "
        f"Synced {len(synced)} command(s).",
        flush=True
    )

    await bot.close()

async def main():
    await bot.start(
        os.getenv("DISCORD_TOKEN")
    )


asyncio.run(main())


asyncio.run(main())
