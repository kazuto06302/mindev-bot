import json

import discord
from discord.ext import commands
from discord import app_commands


CONFIG_CATEGORY_NAME = "Bot"
CONFIG_CHANNEL_NAME = "mindev_bot_config_channel"
CONFIG_MESSAGE_MARKER = "BOT_CONFIG"


class PermissionManager(commands.Cog):
    permission = app_commands.Group(
        name="permission",
        description="Botの権限を管理します"
    )

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ============================================================
    # Config channel
    # ============================================================

    async def get_config_channel(
        self,
        guild: discord.Guild
    ) -> discord.TextChannel:

        # 既存のbot-configを探す
        channel = discord.utils.get(
            guild.text_channels,
            name=CONFIG_CHANNEL_NAME
        )

        if channel is not None:
            return channel

        # Botカテゴリを探す
        category = discord.utils.get(
            guild.categories,
            name=CONFIG_CATEGORY_NAME
        )

        # なければ作成
        if category is None:
            category = await guild.create_category(
                CONFIG_CATEGORY_NAME,
                reason="Creating Bot configuration category"
            )

        # Botだけが見られるチャンネルを作成
        bot_member = guild.me

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=False
            ),
            bot_member: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_messages=True
            )
        }

        channel = await guild.create_text_channel(
            CONFIG_CHANNEL_NAME,
            category=category,
            overwrites=overwrites,
            reason="Creating Bot configuration channel"
        )

        return channel

    # ============================================================
    # Config message
    # ============================================================

    async def get_config_message(
        self,
        guild: discord.Guild,
        channel: discord.TextChannel
    ) -> discord.Message | None:

        async for message in channel.history(limit=50):
            if message.author.id != self.bot.user.id:
                continue

            if message.content.startswith(CONFIG_MESSAGE_MARKER):
                return message

        return None

    # ============================================================
    # Load config
    # ============================================================

    async def load_config(
        self,
        guild: discord.Guild
    ) -> dict:

        channel = await self.get_config_channel(guild)

        message = await self.get_config_message(
            guild,
            channel
        )

        # 初回
        if message is None:
            config = {
                "admin_roles": []
            }

            await self.save_config(
                guild,
                channel,
                config
            )

            return config

        try:
            # マーカー以降をJSONとして読み込む
            json_data = message.content[
                len(CONFIG_MESSAGE_MARKER):
            ].strip()

            return json.loads(json_data)

        except (json.JSONDecodeError, ValueError):
            # 壊れていた場合は初期化
            config = {
                "admin_roles": []
            }

            await self.save_config(
                guild,
                channel,
                config
            )

            return config

    # ============================================================
    # Save config
    # ============================================================

    async def save_config(
        self,
        guild: discord.Guild,
        channel: discord.TextChannel,
        config: dict
    ):

        content = (
            f"{CONFIG_MESSAGE_MARKER}\n"
            f"```json\n"
            f"{json.dumps(config, ensure_ascii=False, indent=2)}"
            f"\n```"
        )

        message = await self.get_config_message(
            guild,
            channel
        )

        if message is None:
            await channel.send(content)

        else:
            await message.edit(content=content)

    # ============================================================
    # Admin check
    # ============================================================

    async def is_admin(
        self,
        member: discord.Member
    ) -> bool:

        # Discord管理者は常に許可
        if member.guild_permissions.administrator:
            return True

        config = await self.load_config(member.guild)

        admin_roles = config.get(
            "admin_roles",
            []
        )

        return any(
            role.id in admin_roles
            for role in member.roles
        )

    # ============================================================
    # /permission add
    # ============================================================

    @permission.command(
        name="add",
        description="Adminランクにロールを追加します"
    )
    @app_commands.describe(
        role="Adminランクに追加するロール"
    )
    async def permission_add(
        self,
        interaction: discord.Interaction,
        role: discord.Role
    ):

        if not isinstance(interaction.user, discord.Member):
            return

        if not await self.is_admin(interaction.user):
            await interaction.response.send_message(
                "❌ このコマンドを使用する権限がありません。",
                ephemeral=True
            )
            return

        config = await self.load_config(
            interaction.guild
        )

        admin_roles = config.setdefault(
            "admin_roles",
            []
        )

        if role.id in admin_roles:
            await interaction.response.send_message(
                f"⚠️ {role.mention} は既にAdminランクです。",
                ephemeral=True
            )
            return

        admin_roles.append(role.id)

        channel = await self.get_config_channel(
            interaction.guild
        )

        await self.save_config(
            interaction.guild,
            channel,
            config
        )

        await interaction.response.send_message(
            f"✅ {role.mention} をAdminランクに追加しました。",
            ephemeral=True
        )

    # ============================================================
    # /permission remove
    # ============================================================

    @permission.command(
        name="remove",
        description="Adminランクからロールを削除します"
    )
    @app_commands.describe(
        role="Adminランクから削除するロール"
    )
    async def permission_remove(
        self,
        interaction: discord.Interaction,
        role: discord.Role
    ):

        if not isinstance(interaction.user, discord.Member):
            return

        if not await self.is_admin(interaction.user):
            await interaction.response.send_message(
                "❌ このコマンドを使用する権限がありません。",
                ephemeral=True
            )
            return

        config = await self.load_config(
            interaction.guild
        )

        admin_roles = config.setdefault(
            "admin_roles",
            []
        )

        if role.id not in admin_roles:
            await interaction.response.send_message(
                f"⚠️ {role.mention} はAdminランクではありません。",
                ephemeral=True
            )
            return

        admin_roles.remove(role.id)

        channel = await self.get_config_channel(
            interaction.guild
        )

        await self.save_config(
            interaction.guild,
            channel,
            config
        )

        await interaction.response.send_message(
            f"✅ {role.mention} をAdminランクから削除しました。",
            ephemeral=True
        )

    # ============================================================
    # /permission list
    # ============================================================

    @permission.command(
        name="list",
        description="Adminランクのロール一覧を表示します"
    )
    async def permission_list(
        self,
        interaction: discord.Interaction
    ):

        if not isinstance(interaction.user, discord.Member):
            return

        if not await self.is_admin(interaction.user):
            await interaction.response.send_message(
                "❌ このコマンドを使用する権限がありません。",
                ephemeral=True
            )
            return

        config = await self.load_config(
            interaction.guild
        )

        admin_roles = config.get(
            "admin_roles",
            []
        )

        if not admin_roles:
            await interaction.response.send_message(
                "📋 Adminランクに登録されているロールはありません。",
                ephemeral=True
            )
            return

        roles = []

        for role_id in admin_roles:
            role = interaction.guild.get_role(role_id)

            if role is None:
                roles.append(
                    f"• `Unknown Role ({role_id})`"
                )
            else:
                roles.append(
                    f"• {role.mention}"
                )

        await interaction.response.send_message(
            "📋 **Adminランク**\n\n" +
            "\n".join(roles),
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(PermissionManager(bot))
