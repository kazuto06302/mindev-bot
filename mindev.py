import os
import discord
from discord.ext import commands
from threading import Thread
from flask import Flask
import asyncio

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


@bot.event
async def on_ready():
    print(
        f"Logged in as {bot.user.name} "
        f"(ID: {bot.user.id})",
        flush=True
    )

    guild = discord.Object(id=TEST_GUILD_ID)

    try:
        bot.tree.copy_global_to(guild=guild)

        synced = await bot.tree.sync(
            guild=guild
        )

        print(
            f"Synced {len(synced)} command(s) "
            f"to guild {TEST_GUILD_ID}",
            flush=True
        )

        for command in synced:
            print(
                f"  /{command.name}",
                flush=True
            )

    except Exception as e:
        print(
            f"Failed to sync commands: "
            f"{type(e).__name__}: {e}",
            flush=True
        )


async def main():

    extensions = [
        "cogs.ping",
        "cogs.permission",
        "cogs.permission_sync",
        "cogs.role_message"
    ]

    for extension in extensions:
        print(
            f"Loading: {extension}",
            flush=True
        )

        try:
            await asyncio.wait_for(
                bot.load_extension(extension),
                timeout=10
            )

            print(
                f"{extension} loaded successfully",
                flush=True
            )

        except asyncio.TimeoutError:
            print(
                f"ERROR: {extension} load timed out!",
                flush=True
            )
            raise

        except Exception as e:
            print(
                f"ERROR loading {extension}: "
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

        if hasattr(command, "commands"):
            for subcommand in command.commands:
                print(
                    f"  /{command.name} {subcommand.name}",
                    flush=True
                )

    await bot.start(
        os.getenv("DISCORD_TOKEN")
    )


asyncio.run(main())
