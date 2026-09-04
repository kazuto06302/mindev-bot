import os
import discord
from discord.ext import commands
import asyncio

# Web server
from threading import Thread
from flask import Flask

app = Flask("")


@app.route("/")
def home():
    return "Bot is active!"


def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(
        host="0.0.0.0",
        port=port
    )


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
        f"(ID: {bot.user.id})"
    )

    try:
        synced = await bot.tree.sync()

        print(
            f"Synced {len(synced)} command(s)"
        )

        for command in synced:
            print(
                f"  /{command.name}"
            )

    except Exception as e:
        print(
            f"Failed to sync commands: "
            f"{type(e).__name__}: {e}"
        )


async def main():

    print("=== Loading Cogs ===")

    extensions = [
        "cogs.ping",
        "cogs.permission",
        "cogs.permission_sync",
    ]

    for extension in extensions:

        print(
            f"Loading: {extension}"
        )

        try:
            await bot.load_extension(
                extension
            )

            print(
                f"Loaded: {extension}"
            )

        except Exception as e:

            print(
                f"FAILED: {extension}"
            )

            print(
                f"{type(e).__name__}: {e}"
            )

            raise

    print("=== Loaded Commands ===")

    for command in bot.tree.get_commands():

        print(
            f"/{command.name}"
        )

        if hasattr(command, "commands"):
            for subcommand in command.commands:
                print(
                    f"  /{command.name} "
                    f"{subcommand.name}"
                )

    print("=== Starting Bot ===")

    await bot.start(
        os.getenv("DISCORD_TOKEN")
    )


asyncio.run(main())
