import discord
from discord.ext import commands
from discord import app_commands


class RoleMessage(commands.Cog):

    rolemessage = app_commands.Group(
        name="rolemessage",
        description="リアクションでロールを付与するメッセージを管理します"
    )

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ============================================================
    # PermissionManager
    # ============================================================

    async def is_admin(
        self,
        member: discord.Member
    ) -> bool:

        permission_manager = self.bot.get_cog(
            "PermissionManager"
        )

        if permission_manager is None:
            return False

        return await permission_manager.is_admin(
            member
        )

    # ============================================================
    # Config
    # ============================================================

    async def get_config(
        self,
        guild: discord.Guild
    ) -> dict:

        permission_manager = self.bot.get_cog(
            "PermissionManager"
        )

        if permission_manager is None:
            raise RuntimeError(
                "PermissionManager is not loaded."
            )

        return await permission_manager.load_config(
            guild
        )

    async def save_config(
        self,
        guild: discord.Guild,
        config: dict
    ):

        permission_manager = self.bot.get_cog(
            "PermissionManager"
        )

        if permission_manager is None:
            raise RuntimeError(
                "PermissionManager is not loaded."
            )

        channel = await permission_manager.get_config_channel(
            guild
        )

        await permission_manager.save_config(
            guild,
            channel,
            config
        )

    # ============================================================
    # Emoji Utilities
    # ============================================================

    def normalize_unicode_emoji(
        self,
        emoji: str
    ) -> str:

        # Variation Selector-16 を除去
        return emoji.strip().replace(
            "\ufe0f",
            ""
        )

    def emoji_key(
        self,
        emoji
    ) -> str:

        # Unicode emoji
        if isinstance(
            emoji,
            str
        ):

            return (
                "unicode:"
                + self.normalize_unicode_emoji(
                    emoji
                )
            )

        # PartialEmoji / Emoji
        if isinstance(
            emoji,
            discord.PartialEmoji
        ):

            if emoji.id is not None:

                return (
                    "custom:"
                    + str(emoji.id)
                )

            return (
                "unicode:"
                + self.normalize_unicode_emoji(
                    emoji.name or ""
                )
            )

        return str(emoji)

    def emoji_display(
        self,
        emoji
    ) -> str:

        if isinstance(
            emoji,
            str
        ):

            return emoji.strip()

        return str(emoji)

    def parse_emoji(
        self,
        value: str
    ) -> discord.PartialEmoji:

        value = value.strip()

        # --------------------------------------------------------
        # Custom emoji
        #
        # <:name:id>
        # <a:name:id>
        # --------------------------------------------------------

        custom_emoji = discord.PartialEmoji.from_str(
            value
        )

        if custom_emoji.id is not None:

            return custom_emoji

        # --------------------------------------------------------
        # Unicode emoji
        # --------------------------------------------------------

        return discord.PartialEmoji(
            name=value
        )

    # ============================================================
    # Find Role Message
    # ============================================================

    def find_role_message(
        self,
        config: dict,
        message_id: int
    ):

        for role_message in config.get(
            "role_messages",
            []
        ):

            if role_message.get(
                "message_id"
            ) == message_id:

                return role_message

        return None

    # ============================================================
    # Find Emoji
    # ============================================================

    def find_emoji_role(
        self,
        role_message: dict,
        emoji
    ):

        key = self.emoji_key(
            emoji
        )

        for role_data in role_message.get(
            "roles",
            []
        ):

            stored_emoji = role_data.get(
                "emoji"
            )

            if self.emoji_key(
                stored_emoji
            ) == key:

                return role_data

        return None

    # ============================================================
    # /rolemessage add
    # ============================================================

    @rolemessage.command(
        name="add",
        description="リアクションとロールの組み合わせを追加します"
    )
    @app_commands.describe(
        message_id="対象メッセージのID",
        emoji="使用する絵文字",
        role="リアクション時に付与するロール"
    )
    async def rolemessage_add(
        self,
        interaction: discord.Interaction,
        message_id: str,
        emoji: str,
        role: discord.Role
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

            await interaction.response.send_message(
                "❌ ユーザー情報を取得できませんでした。",
                ephemeral=True
            )

            return

        # --------------------------------------------------------
        # Admin check
        # --------------------------------------------------------

        if not await self.is_admin(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ このコマンドを使用する権限がありません。",
                ephemeral=True
            )

            return

        # --------------------------------------------------------
        # Message ID
        # --------------------------------------------------------

        try:

            message_id_int = int(
                message_id
            )

        except ValueError:

            await interaction.response.send_message(
                "❌ メッセージIDが正しくありません。",
                ephemeral=True
            )

            return

        # --------------------------------------------------------
        # Emoji
        # --------------------------------------------------------

        emoji = emoji.strip()

        if not emoji:

            await interaction.response.send_message(
                "❌ 絵文字を指定してください。",
                ephemeral=True
            )

            return

        try:

            parsed_emoji = self.parse_emoji(
                emoji
            )

        except Exception:

            await interaction.response.send_message(
                "❌ 絵文字を解析できませんでした。",
                ephemeral=True
            )

            return

        # --------------------------------------------------------
        # Role hierarchy
        # --------------------------------------------------------

        bot_member = interaction.guild.me

        if bot_member is None:

            await interaction.response.send_message(
                "❌ Botの情報を取得できませんでした。",
                ephemeral=True
            )

            return

        if role.is_default():

            await interaction.response.send_message(
                "❌ @everyone ロールは指定できません。",
                ephemeral=True
            )

            return

        if role >= bot_member.top_role:

            await interaction.response.send_message(
                "❌ そのロールはBotの最高位ロールより下に配置してください。",
                ephemeral=True
            )

            return

        # --------------------------------------------------------
        # Message
        # --------------------------------------------------------

        try:

            message = await interaction.channel.fetch_message(
                message_id_int
            )

        except discord.NotFound:

            await interaction.response.send_message(
                "❌ 指定されたメッセージが見つかりません。",
                ephemeral=True
            )

            return

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ メッセージを取得する権限がありません。",
                ephemeral=True
            )

            return

        except discord.HTTPException as e:

            await interaction.response.send_message(
                f"❌ Discord APIでエラーが発生しました。\n"
                f"`{e}`",
                ephemeral=True
            )

            return

        # --------------------------------------------------------
        # Config
        # --------------------------------------------------------

        try:

            config = await self.get_config(
                interaction.guild
            )

        except Exception as e:

            await interaction.response.send_message(
                f"❌ 設定の読み込みに失敗しました。\n"
                f"`{e}`",
                ephemeral=True
            )

            return

        role_messages = config.setdefault(
            "role_messages",
            []
        )

        role_message = self.find_role_message(
            config,
            message.id
        )

        if role_message is None:

            role_message = {
                "message_id": message.id,
                "roles": []
            }

            role_messages.append(
                role_message
            )

        # --------------------------------------------------------
        # Duplicate check
        # --------------------------------------------------------

        if self.find_emoji_role(
            role_message,
            parsed_emoji
        ) is not None:

            await interaction.response.send_message(
                f"⚠️ {self.emoji_display(parsed_emoji)} "
                f"は既にこのメッセージに登録されています。",
                ephemeral=True
            )

            return

        # --------------------------------------------------------
        # Add reaction
        # --------------------------------------------------------

        try:

            await message.add_reaction(
                parsed_emoji
            )

        except discord.NotFound:

            await interaction.response.send_message(
                "❌ 指定された絵文字が存在しないか、"
                "メッセージが見つかりません。",
                ephemeral=True
            )

            return

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ Botにリアクションを追加する権限がありません。",
                ephemeral=True
            )

            return

        except discord.HTTPException as e:

            await interaction.response.send_message(
                f"❌ リアクションの追加に失敗しました。\n"
                f"`{e}`",
                ephemeral=True
            )

            return

        # --------------------------------------------------------
        # Save
        # --------------------------------------------------------

        role_message["roles"].append(
            {
                "emoji": self.emoji_display(
                    parsed_emoji
                ),
                "role_id": role.id
            }
        )

        try:

            await self.save_config(
                interaction.guild,
                config
            )

        except Exception as e:

            await interaction.response.send_message(
                f"⚠️ リアクションは追加されましたが、"
                f"設定の保存に失敗しました。\n"
                f"`{e}`",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            f"✅ {self.emoji_display(parsed_emoji)} → "
            f"{role.mention} を登録しました。\n"
            f"メッセージID: `{message.id}`",
            ephemeral=True
        )

    # ============================================================
    # /rolemessage remove
    # ============================================================

    @rolemessage.command(
        name="remove",
        description="リアクションとロールの組み合わせを削除します"
    )
    @app_commands.describe(
        message_id="対象メッセージのID",
        emoji="削除する絵文字"
    )
    async def rolemessage_remove(
        self,
        interaction: discord.Interaction,
        message_id: str,
        emoji: str
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

        if not await self.is_admin(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ このコマンドを使用する権限がありません。",
                ephemeral=True
            )

            return

        try:

            message_id_int = int(
                message_id
            )

        except ValueError:

            await interaction.response.send_message(
                "❌ メッセージIDが正しくありません。",
                ephemeral=True
            )

            return

        try:

            parsed_emoji = self.parse_emoji(
                emoji
            )

        except Exception:

            await interaction.response.send_message(
                "❌ 絵文字を解析できませんでした。",
                ephemeral=True
            )

            return

        config = await self.get_config(
            interaction.guild
        )

        role_message = self.find_role_message(
            config,
            message_id_int
        )

        if role_message is None:

            await interaction.response.send_message(
                "❌ そのメッセージはRole Messageとして登録されていません。",
                ephemeral=True
            )

            return

        role_data = self.find_emoji_role(
            role_message,
            parsed_emoji
        )

        if role_data is None:

            await interaction.response.send_message(
                f"❌ {self.emoji_display(parsed_emoji)} "
                f"は登録されていません。",
                ephemeral=True
            )

            return

        role_message["roles"].remove(
            role_data
        )

        # --------------------------------------------------------
        # Remove bot reaction
        # --------------------------------------------------------

        try:

            message = await interaction.channel.fetch_message(
                message_id_int
            )

            await message.clear_reaction(
                parsed_emoji
            )

        except (
            discord.NotFound,
            discord.Forbidden,
            discord.HTTPException
        ):

            pass

        if not role_message["roles"]:

            config["role_messages"].remove(
                role_message
            )

        await self.save_config(
            interaction.guild,
            config
        )

        await interaction.response.send_message(
            f"✅ {self.emoji_display(parsed_emoji)} "
            f"のRole Message設定を削除しました。",
            ephemeral=True
        )

    # ============================================================
    # /rolemessage list
    # ============================================================

    @rolemessage.command(
        name="list",
        description="Role Messageの設定を表示します"
    )
    @app_commands.describe(
        message_id="対象メッセージのID"
    )
    async def rolemessage_list(
        self,
        interaction: discord.Interaction,
        message_id: str
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

        if not await self.is_admin(
            interaction.user
        ):

            await interaction.response.send_message(
                "❌ このコマンドを使用する権限がありません。",
                ephemeral=True
            )

            return

        try:

            message_id_int = int(
                message_id
            )

        except ValueError:

            await interaction.response.send_message(
                "❌ メッセージIDが正しくありません。",
                ephemeral=True
            )

            return

        config = await self.get_config(
            interaction.guild
        )

        role_message = self.find_role_message(
            config,
            message_id_int
        )

        if role_message is None:

            await interaction.response.send_message(
                "📋 このメッセージにはRole Message設定がありません。",
                ephemeral=True
            )

            return

        lines = []

        for role_data in role_message.get(
            "roles",
            []
        ):

            emoji = role_data.get(
                "emoji",
                "?"
            )

            role_id = role_data.get(
                "role_id"
            )

            role = interaction.guild.get_role(
                role_id
            )

            if role is None:

                role_text = (
                    f"`Unknown Role ({role_id})`"
                )

            else:

                role_text = role.mention

            lines.append(
                f"{emoji} → {role_text}"
            )

        await interaction.response.send_message(
            f"📋 **Role Message**\n"
            f"メッセージID: `{message_id_int}`\n\n"
            + "\n".join(lines),
            ephemeral=True
        )

    # ============================================================
    # Reaction Add
    # ============================================================

    @commands.Cog.listener()
    async def on_raw_reaction_add(
        self,
        payload: discord.RawReactionActionEvent
    ):

        if payload.guild_id is None:
            return

        if self.bot.user is not None:
            if payload.user_id == self.bot.user.id:
                return

        guild = self.bot.get_guild(
            payload.guild_id
        )

        if guild is None:
            return

        config = await self.get_config(
            guild
        )

        role_message = self.find_role_message(
            config,
            payload.message_id
        )

        if role_message is None:
            return

        role_data = self.find_emoji_role(
            role_message,
            payload.emoji
        )

        if role_data is None:
            return

        member = guild.get_member(
            payload.user_id
        )

        if member is None:

            try:

                member = await guild.fetch_member(
                    payload.user_id
                )

            except (
                discord.NotFound,
                discord.Forbidden,
                discord.HTTPException
            ):

                return

        role = guild.get_role(
            role_data.get("role_id")
        )

        if role is None:
            return

        bot_member = guild.me

        if bot_member is None:
            return

        if role >= bot_member.top_role:
            return

        try:

            await member.add_roles(
                role,
                reason="Role Message reaction"
            )

        except (
            discord.Forbidden,
            discord.HTTPException
        ):

            pass

    # ============================================================
    # Reaction Remove
    # ============================================================

    @commands.Cog.listener()
    async def on_raw_reaction_remove(
        self,
        payload: discord.RawReactionActionEvent
    ):

        if payload.guild_id is None:
            return

        if self.bot.user is not None:
            if payload.user_id == self.bot.user.id:
                return

        guild = self.bot.get_guild(
            payload.guild_id
        )

        if guild is None:
            return

        config = await self.get_config(
            guild
        )

        role_message = self.find_role_message(
            config,
            payload.message_id
        )

        if role_message is None:
            return

        role_data = self.find_emoji_role(
            role_message,
            payload.emoji
        )

        if role_data is None:
            return

        member = guild.get_member(
            payload.user_id
        )

        if member is None:

            try:

                member = await guild.fetch_member(
                    payload.user_id
                )

            except (
                discord.NotFound,
                discord.Forbidden,
                discord.HTTPException
            ):

                return

        role = guild.get_role(
            role_data.get("role_id")
        )

        if role is None:
            return

        bot_member = guild.me

        if bot_member is None:
            return

        if role >= bot_member.top_role:
            return

        try:

            await member.remove_roles(
                role,
                reason="Role Message reaction"
            )

        except (
            discord.Forbidden,
            discord.HTTPException
        ):

            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(
        RoleMessage(bot)
    )
