import discord
from discord.ext import commands


# 権限同期コマンドを使用できるロール
ALLOWED_ROLE_ID = 1542223279090049185


class PermissionSync(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @discord.app_commands.command(
        name="sync_permission",
        description="別のチャンネルから権限設定をコピーします"
    )
    @discord.app_commands.describe(
        target="権限を変更するチャンネル",
        source="権限のコピー元となるチャンネル"
    )
    async def sync_permission(
        self,
        interaction: discord.Interaction,
        target: discord.abc.GuildChannel,
        source: discord.abc.GuildChannel
    ):
        # ロールチェック
        if not isinstance(interaction.user, discord.Member):
            return

        if not any(
            role.id == ALLOWED_ROLE_ID
            for role in interaction.user.roles
        ):
            await interaction.response.send_message(
                "❌ このコマンドを使用する権限がありません。",
                ephemeral=True
            )
            return

        # 同じサーバーか確認
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

        # 同じチャンネルは禁止
        if target.id == source.id:
            await interaction.response.send_message(
                "❌ コピー元とコピー先を同じチャンネルにはできません。",
                ephemeral=True
            )
            return

        # Botの権限確認
        if not interaction.guild.me.guild_permissions.manage_channels:
            await interaction.response.send_message(
                "❌ Botに「チャンネルの管理」権限がありません。",
                ephemeral=True
            )
            return

        try:
            # コピー元の権限設定
            overwrites = source.overwrites

            # コピー先の既存設定を削除
            for target_obj in list(target.overwrites):
                await target.set_permissions(
                    target_obj,
                    overwrite=None,
                    reason=f"Permission sync from #{source.name}"
                )

            # 権限設定をコピー
            for target_obj, overwrite in overwrites.items():
                await target.set_permissions(
                    target_obj,
                    overwrite=overwrite,
                    reason=f"Permission sync from #{source.name}"
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
                f"❌ Discord APIでエラーが発生しました。\n`{e}`",
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(PermissionSync(bot))
