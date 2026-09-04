import json

import discord
from discord.ext import commands
from discord import app_commands


CONFIG_CATEGORY_NAME = "Bot"
CONFIG_CHANNEL_NAME = "bot-config"
CONFIG_MESSAGE_MARKER = "BOT_CONFIG"


class PermissionManager(commands.Cog):
    permission = app_commands.Group(
        name="permission",
        description="Botの権限を管理します"
    )

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ============================================================
    # Server Owner Check
    # ============================================================

    async def cog_check(self, interaction: discord.Interaction) -> bool:
        """
        このCogに属するすべてのコマンドを
        サーバー所有者限定にする。
        """

        if interaction.guild is None:
            return False

        return interaction.guild.owner_id == interaction.user.id

    # ============================================================
    # Config Channel
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

        # Bot自身
        bot_member = guild.me

        if bot_member is None:
            raise RuntimeError("Bot member could not be found.")

        # 権限設定
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

        # チャンネル作成
        channel = await guild.create_text_channel(
            CONFIG_CHANNEL_NAME,
            category=category,
            overwrites=overwrites,
            reason="Creating Bot configuration channel"
        )

        return channel

    # ============================================================
    # Config Message
    # ============================================================

    async def get_config_message(
        self,
        channel: discord.TextChannel
    ) -> discord.Message | None:

        async for message in channel.history(limit=50):

            # Bot自身のメッセージだけを見る
            if message.author.id != self.bot.user.id:
                continue

            if message.content.startswith(
                CONFIG_MESSAGE_MARKER
            ):
                return message

        return None

    # ============================================================
    # Load Config
    # ============================================================

    async def load_config(
        self,
        guild: discord.Guild
    ) -> dict:

        channel = await self.get_config_channel(
            guild
        )

        message = await self.get_config_message(
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

            # BOT_CONFIG以降を取得
            json_data = message.content[
                len(CONFIG_MESSAGE_MARKER):
            ].strip()

            # ```json と ``` を削除
            if json_data.startswith("```json"):
                json_data = json_data[7:]

            if json_data.endswith("```"):
                json_data = json_data[:-3]

            json_data = json_data.strip()

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
    # Save Config
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
            f"{json.dumps("
            f"config, "
            f"ensure_ascii=False, "
            f"indent=2"
            f")}\n"
            f"```"
        )

        message = await self.get_config_message(
            channel
        )

        if message is None:

            await channel.send(
                content
            )

        else:

            await message.edit(
                content=content
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

        config = await self.load_config(
            interaction.guild
        )

        admin_roles = config.setdefault(
            "admin_roles",
            []
        )

        # 既に登録済み
        if role.id in admin_roles:

            await interaction.response.send_message(
                f"⚠️ {role.mention} は"
                f"既にAdminランクです。",
                ephemeral=True
            )

            return

        # 追加
        admin_roles.append(
            role.id
        )

        channel = await self.get_config_channel(
            interaction.guild
        )

        await self.save_config(
            interaction.guild,
            channel,
            config
        )

        await interaction.response.send_message(
            f"✅ {role.mention} を"
            f"Adminランクに追加しました。",
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

        config = await self.load_config(
            interaction.guild
        )

        admin_roles = config.setdefault(
            "admin_roles",
            []
        )

        # 登録されていない
        if role.id not in admin_roles:

            await interaction.response.send_message(
                f"⚠️ {role.mention} は"
                f"Adminランクではありません。",
                ephemeral=True
            )

            return

        # 削除
        admin_roles.remove(
            role.id
        )

        channel = await self.get_config_channel(
            interaction.guild
        )

        await self.save_config(
            interaction.guild,
            channel,
            config
        )

        await interaction.response.send_message(
            f"✅ {role.mention} を"
            f"Adminランクから削除しました。",
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

        config = await self.load_config(
            interaction.guild
        )

        admin_roles = config.get(
            "admin_roles",
            []
        )

        # 空
        if not admin_roles:

            await interaction.response.send_message(
                "📋 Adminランクに登録されている"
                "ロールはありません。",
                ephemeral=True
            )

            return

        roles = []

        for role_id in admin_roles:

            role = interaction.guild.get_role(
                role_id
            )

            if role is None:

                roles.append(
                    f"• `Unknown Role ({role_id})`"
                )

            else:

                roles.append(
                    f"• {role.mention}"
                )

        await interaction.response.send_message(
            "📋 **Adminランク**\n\n"
            + "\n".join(roles),
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(
        PermissionManager(bot)
    )
