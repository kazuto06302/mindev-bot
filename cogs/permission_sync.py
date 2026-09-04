import discord
from discord.ext import commands
from discord import app_commands


class PermissionSync(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def is_admin(
        self,
        member: discord.Member
    ) -> bool:

        permission_manager = self.bot.get_cog(
            "PermissionManager"
        )

        if permission_manager is None:
            return False

        return await permission_manager.is_admin(member)

    @app_commands.command(
        name="sync_permission",
        description="別のチャンネルから権限設定をコピーします"
    )
    @app_commands.describe(
        target="権限を変更するチャンネル",
        source="権限のコピー元となるチャンネル"
    )
    async def sync_permission(
        self,
        interaction: discord.Interaction,
        target: discord.abc.GuildChannel,
        source: discord.abc.GuildChannel
    ):

        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ このコマンドはサーバー内でのみ使用できます。",
                ephemeral=True
            )
            return

        if not isinstance(
            interaction.user,
            discord.Member
        ):
            return

        # Adminランクチェック
        if not await self.is_admin(
            interaction.user
        ):
            await interaction.response.send_message(
                "❌ このコマンドを使用する権限がありません。",
                ephemeral=True
            )
            return

        if target.guild.id != interaction.guild.id:
            await interaction.response.send_message(
                "❌ コピー先チャンネルがこのサーバーにありません。",
                ephemeral=True
            )
            return

        if source.guild.id != interaction.guild.id:
            await interaction.response.send_message(
                "❌ コピー元チャンネルがこのサーバーにありません。",
                ephemeral=True
            )
            return

        if target.id == source.id:
            await interaction.response.send_message(
                "❌ コピー元とコピー先を同じチャンネルにはできません。",
                ephemeral=True
            )
            return

        bot_member = interaction.guild.me

        if bot_member is None:
            await interaction.response.send_message(
                "❌ Botの情報を取得できませんでした。",
                ephemeral=True
            )
            return

        if not bot_member.guild_permissions.manage_channels:
            await interaction.response.send_message(
                "❌ Botに「チャンネルの管理」権限がありません。",
                ephemeral=True
            )
            return

        try:

            overwrites = source.overwrites

            # コピー先の既存権限を削除
            for target_obj in list(
                target.overwrites
            ):
                await target.set_permissions(
                    target_obj,
                    overwrite=None,
                    reason=(
                        f"Permission sync "
                        f"from #{source.name}"
                    )
                )

            # コピー元の権限をコピー
            for target_obj, overwrite in overwrites.items():
                await target.set_permissions(
                    target_obj,
                    overwrite=overwrite,
                    reason=(
                        f"Permission sync "
                        f"from #{source.name}"
                    )
                )

            await interaction.response.send_message(
                f"✅ {source.mention} の権限を "
                f"{target.mention} に同期しました。",
                ephemeral=True
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ チャンネルの権限を変更する権限がありません。",
                ephemeral=True
            )

        except discord.HTTPException as e:

            await interaction.response.send_message(
                f"❌ Discord APIでエラーが発生しました。\n"
                f"`{e}`",
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(
        PermissionSync(bot)
    )
