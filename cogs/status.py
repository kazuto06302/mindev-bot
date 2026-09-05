from datetime import datetime, timezone, timedelta

import discord
from discord.ext import commands, tasks


JST = timezone(timedelta(hours=9))


class Status(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.start_time = datetime.now(timezone.utc)

        self.update_status.start()

    def cog_unload(self):
        self.update_status.cancel()

    @tasks.loop(minutes=1)
    async def update_status(self):

        if not self.bot.is_ready():
            return

        now = datetime.now(JST)

        # 21:00～05:59 → 離席中
        if now.hour >= 21 or now.hour < 6:
            status = discord.Status.idle
        else:
            status = discord.Status.online

        # 稼働時間
        uptime = datetime.now(timezone.utc) - self.start_time

        total_seconds = int(
            uptime.total_seconds()
        )

        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60

        activity = discord.Game(
            name=f"稼働時間: {hours}時間{minutes:02d}分"
        )

        await self.bot.change_presence(
            status=status,
            activity=activity
        )

    @update_status.before_loop
    async def before_update_status(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(
        Status(bot)
    )
