import discord
from discord.ext import commands


class Ping(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @discord.app_commands.command(
        name="ping",
        description='Returns "Ping!"'
    )
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)

        await interaction.response.send_message(
            f"Pong! {latency}ms"
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Ping(bot))
