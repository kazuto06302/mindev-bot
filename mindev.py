import os
import discord
from discord.ext import commands
import asyncio

from threading import Thread
from flask import Flask

app = Flask("")


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


@bot.event
async def on_ready():
    print(
        f"Logged in as {bot.user.name} "
        f"(ID: {bot.user.id})",
        flush=True
    )

    try:
        synced = await bot.tree.sync()

        print(
            f"Synced {len(synced)} command(s)",
            flush=True
        )

    except Exception as e:
        print(
            f"Failed to sync commands: "
            f"{type(e).__name__}: {e}",
            flush=True
        )


async def main():

    print("=== BEFORE LOAD ===", flush=True)

    print("Loading cogs.ping...", flush=True)

    try:
        await asyncio.wait_for(
            bot.load_extension("cogs.ping"),
            timeout=10
        )

        print(
            "cogs.ping loaded successfully",
            flush=True
        )

    except asyncio.TimeoutError:
        print(
            "ERROR: cogs.ping load timed out!",
            flush=True
        )
        raise

    except Exception as e:
        print(
            f"ERROR loading cogs.ping: "
            f"{type(e).__name__}: {e}",
            flush=True
        )
        raise

    print("=== COMMANDS ===", flush=True)

    for command in bot.tree.get_commands():
        print(
            f"/{command.name}",
            flush=True
        )

    print("=== STARTING BOT ===", flush=True)

    await bot.start(
        os.getenv("DISCORD_TOKEN")
    )


asyncio.run(main())
