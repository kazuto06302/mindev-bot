import re

import discord
from discord.ext import commands
from discord import app_commands


class RoleMessage(commands.Cog):

    rolemessage = app_commands.Group(
        name="rolemessage",
        description="リアクションでロールを付与する設定を管理します"
    )

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ============================================================
    # Permission
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

        return await permission_manager.is_admin(member)

    # ============================================================
    # PermissionManager
    # ============================================================

    def get_permission_manager(self):
        manager = self.bot.get_cog(
            "PermissionManager"
        )

        if manager is None:
            raise RuntimeError(
                "PermissionManager is not loaded."
            )

        return manager

    async def load_config(
        self,
        guild: discord.Guild
    ) -> dict:

        manager = self.get_permission_manager()

        return await manager.load_config(guild)

    async def save_config(
        self,
        guild: discord.Guild,
        config: dict
    ):

        manager = self.get_permission_manager()

        channel = await manager.get_config_channel(guild)

        await manager.save_config(
            guild,
            channel,
            config
        )

    # ============================================================
    # Emoji
    # ============================================================

    def parse_emoji(
        self,
        value: str
    ):
        """
        Unicode emoji:
            😀
            ✅
            ❤️

        Custom emoji:
            <:name:123456789>
            <a:name:123456789>
        """

        value = value.strip()

        # Custom emoji
        match = re.fullmatch(
            r"<(a?):([a-zA-Z0-9_]+):(\d+)>",
            value
        )

        if match:
            animated = bool(match.group(1))
            name = match.group(2)
            emoji_id = int(match.group(3))

            return discord.PartialEmoji(
                name=name,
                id=emoji_id,
                animated=animated
            )

        # Unicode emoji
        return self.normalize_unicode_emoji(value)

    def normalize_unicode_emoji(
        self,
        emoji: str
    ) -> str:

        # Discord reactionではVariation Selector-16が
        # 問題になる場合があるため除去する
        return emoji.replace("\ufe0f", "")

    def emoji_key(
        self,
        emoji
    ) -> str:

        if isinstance(
            emoji,
            discord.PartialEmoji
        ):
            if emoji.id is not None:
                return (
                    f"custom:{emoji.id}"
                )

            return (
                "unicode:"
                + self.normalize_unicode_emoji(
                    emoji.name or ""
                )
            )

        return (
            "unicode:"
            + self.normalize_unicode_emoji(
                str(emoji)
            )
        )

    # ============================================================
    # Config helpers
    # ============================================================

    def find_message_config(
        self,
        config: dict,
        message_id: int
    ):

        for message_config in config.get(
            "role_messages",
            []
        ):
            if message_config.get(
                "message_id"
            ) == message_id:
                return message_config

        return None

    def find_role_config(
        self,
        message_config: dict,
        emoji
    ):

        key = self.emoji_key(emoji)

        for role_config in message_config.get(
            "roles",
            []
        ):
            stored_emoji = self.parse_emoji(
                role_config["emoji"]
            )

            if self.emoji_key(
                stored_emoji
            ) == key:
                return role_config

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

        # --------------------------------------------------------
        # Guild check
        # --------------------------------------------------------

        if interaction.guild is None:
            await interaction.response.send_message(
                "❌ このコマンドはサーバー内でのみ使用できます。",
                ephemeral=True
            )
            return

        # --------------------------------------------------------
        # Permission check
        # --------------------------------------------------------

        if not isinstance(
            interaction.user,
            discord.Member
        ):
            await interaction.response.send_message(
                "❌ メンバー情報を取得できませんでした。",
                ephemeral=True
            )
            return

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
            target_message_id = int(
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

        parsed_emoji = self.parse_emoji(
            emoji
        )

        if not parsed_emoji:
            await interaction.response.send_message(
                "❌ 絵文字が正しくありません。",
                ephemeral=True
            )
            return

        # --------------------------------------------------------
        # Bot permissions
        # --------------------------------------------------------

        bot_member = interaction.guild.me

        if bot_member is None:
            await interaction.response.send_message(
                "❌ Botの情報を取得できませんでした。",
                ephemeral=True
            )
            return

        if not bot_member.guild_permissions.manage_roles:
            await interaction.response.send_message(
                "❌ Botに「ロールの管理」権限がありません。",
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
                "❌ Botより上位または同じ位置のロールは操作できません。",
                ephemeral=True
            )
            return

        # --------------------------------------------------------
        # Get target message
        #
        # メッセージIDだけではチャンネルを特定できないため、
        # コマンドを実行したチャンネルから取得する。
        # --------------------------------------------------------

        if not isinstance(
            interaction.channel,
            discord.abc.Messageable
        ):
            await interaction.response.send_message(
                "❌ このチャンネルでは使用できません。",
                ephemeral=True
            )
            return

        try:
            message = await interaction.channel.fetch_message(
                target_message_id
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
                f"❌ メッセージの取得に失敗しました。\n"
                f"`{e}`",
                ephemeral=True
            )
            return

        # --------------------------------------------------------
        # Load config
        # --------------------------------------------------------

        try:
            config = await self.load_config(
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

        message_config = self.find_message_config(
            config,
            target_message_id
        )

        # --------------------------------------------------------
        # Check duplicate
        # --------------------------------------------------------

        if message_config is not None:

            existing = self.find_role_config(
                message_config,
                parsed_emoji
            )

            if existing is not None:
                await interaction.response.send_message(
                    "⚠️ このメッセージには、その絵文字が既に登録されています。",
                    ephemeral=True
                )
                return

        # --------------------------------------------------------
        # Add reaction FIRST
        # --------------------------------------------------------

        try:

            if isinstance(
                parsed_emoji,
                discord.PartialEmoji
            ):
                if parsed_emoji.id is not None:
                    await message.add_reaction(
                        parsed_emoji
                    )
                else:
                    await message.add_reaction(
                        self.normalize_unicode_emoji(
                            parsed_emoji.name or ""
                        )
                    )

            else:
                await message.add_reaction(
                    parsed_emoji
                )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Botがリアクションを追加する権限を持っていません。",
                ephemeral=True
            )
            return

        except discord.NotFound:
            await interaction.response.send_message(
                "❌ 指定された絵文字が存在しないか、"
                "使用できない絵文字です。",
                ephemeral=True
            )
            return

        except discord.HTTPException as e:
            await interaction.response.send_message(
                f"❌ リアクションを追加できませんでした。\n"
                f"`{e}`",
                ephemeral=True
            )
            return

        # --------------------------------------------------------
        # Reaction succeeded -> Save config
        # --------------------------------------------------------

        if message_config is None:

            message_config = {
                "message_id": target_message_id,
                "roles": []
            }

            role_messages.append(
                message_config
            )

        # Store normalized/canonical emoji
        if parsed_emoji.id is not None:
            stored_emoji = str(
                parsed_emoji
            )
        else:
            stored_emoji = self.normalize_unicode_emoji(
                parsed_emoji.name or ""
            )

        message_config["roles"].append(
            {
                "emoji": stored_emoji,
                "role_id": role.id
            }
        )

        try:

            await self.save_config(
                interaction.guild,
                config
            )

        except Exception as e:

            # 設定保存に失敗した場合、
            # 追加したリアクションを可能なら削除する
            try:
                await message.clear_reaction(
                    parsed_emoji
                )
            except Exception:
                pass

            await interaction.response.send_message(
                f"❌ 設定の保存に失敗しました。\n"
                f"`{e}`",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"✅ {parsed_emoji} → {role.mention} "
            f"を登録しました。",
            ephemeral=True
        )

    # ============================================================
    # /rolemessage remove
    # ============================================================

    @rolemessage.command(
        name="remove",
        description="リアクションとロールの設定を削除します"
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
            target_message_id = int(
                message_id
            )

        except ValueError:
            await interaction.response.send_message(
                "❌ メッセージIDが正しくありません。",
                ephemeral=True
            )
            return

        parsed_emoji = self.parse_emoji(
            emoji
        )

        config = await self.load_config(
            interaction.guild
        )

        message_config = self.find_message_config(
            config,
            target_message_id
        )

        if message_config is None:
            await interaction.response.send_message(
                "❌ 指定されたメッセージには設定がありません。",
                ephemeral=True
            )
            return

        role_config = self.find_role_config(
            message_config,
            parsed_emoji
        )

        if role_config is None:
            await interaction.response.send_message(
                "❌ その絵文字は登録されていません。",
                ephemeral=True
            )
            return

        message_config["roles"].remove(
            role_config
        )

        # rolesが空になったらメッセージ設定も削除
        if not message_config["roles"]:
            config["role_messages"].remove(
                message_config
            )

        await self.save_config(
            interaction.guild,
            config
        )

        # --------------------------------------------------------
        # Remove bot reaction
        # --------------------------------------------------------

        if isinstance(
            interaction.channel,
            discord.abc.Messageable
        ):
            try:
                message = await interaction.channel.fetch_message(
                    target_message_id
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

        await interaction.response.send_message(
            f"✅ {parsed_emoji} の設定を削除しました。",
            ephemeral=True
        )

    # ============================================================
    # /rolemessage list
    # ============================================================

    @rolemessage.command(
        name="list",
        description="メッセージに設定されているロール一覧を表示します"
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
            target_message_id = int(
                message_id
            )

        except ValueError:
            await interaction.response.send_message(
                "❌ メッセージIDが正しくありません。",
                ephemeral=True
            )
            return

        config = await self.load_config(
            interaction.guild
        )

        message_config = self.find_message_config(
            config,
            target_message_id
        )

        if message_config is None:
            await interaction.response.send_message(
                "📋 このメッセージにはロール設定がありません。",
                ephemeral=True
            )
            return

        lines = []

        for role_config in message_config.get(
            "roles",
            []
        ):

            emoji = role_config.get(
                "emoji",
                "?"
            )

            role_id = role_config.get(
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
            f"メッセージID: `{target_message_id}`\n\n"
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

        # Bot自身のリアクションは無視
        if self.bot.user is not None:
            if payload.user_id == self.bot.user.id:
                return

        guild = self.bot.get_guild(
            payload.guild_id
        )

        if guild is None:
            return

        config = await self.load_config(
            guild
        )

        message_config = self.find_message_config(
            config,
            payload.message_id
        )

        if message_config is None:
            return

        role_config = self.find_role_config(
            message_config,
            payload.emoji
        )

        if role_config is None:
            return

        role = guild.get_role(
            role_config["role_id"]
        )

        if role is None:
            return

        try:
            member = guild.get_member(
                payload.user_id
            )

            if member is None:
                member = await guild.fetch_member(
                    payload.user_id
                )

            bot_member = guild.me

            if bot_member is None:
                return

            if role >= bot_member.top_role:
                return

            if role in member.roles:
                return

            await member.add_roles(
                role,
                reason="Role message reaction"
            )

        except (
            discord.NotFound,
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

        # Bot自身のリアクションは無視
        if self.bot.user is not None:
            if payload.user_id == self.bot.user.id:
                return

        guild = self.bot.get_guild(
            payload.guild_id
        )

        if guild is None:
            return

        config = await self.load_config(
            guild
        )

        message_config = self.find_message_config(
            config,
            payload.message_id
        )

        if message_config is None:
            return

        role_config = self.find_role_config(
            message_config,
            payload.emoji
        )

        if role_config is None:
            return

        role = guild.get_role(
            role_config["role_id"]
        )

        if role is None:
            return

        try:

            member = guild.get_member(
                payload.user_id
            )

            if member is None:
                member = await guild.fetch_member(
                    payload.user_id
                )

            if role not in member.roles:
                return

            await member.remove_roles(
                role,
                reason="Role message reaction removed"
            )

        except (
            discord.NotFound,
            discord.Forbidden,
            discord.HTTPException
        ):
            pass


async def setup(
    bot: commands.Bot
):
    await bot.add_cog(
        RoleMessage(bot)
    )
