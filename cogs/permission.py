import json
import os

import discord
from discord.ext import commands
from discord import app_commands


DATA_DIR = "data"
DATA_FILE = os.path.join(DATA_DIR, "permissions.json")


class PermissionManager(commands.Cog):
    permission = app_commands.Group(
        name="permission",
        description="Botの権限を管理します"
    )

    def __init__(self, bot: commands.Bot):
        self.bot = bot

        os.makedirs(DATA_DIR, exist_ok=True)

        if not os.path.exists(DATA_FILE):
            self.save_data({
                "admin_roles": []
            })

    def load_data(self):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_data(self, data):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=4
            )

    def is_admin(self, member: discord.Member) -> bool:
        data = self.load_data()

        admin_roles = data.get("admin_roles", [])

        return any(
            role.id in admin_roles
            for role in member.roles
        )

    # =========================
    # /permission add
    # =========================

    @permission.command(
        name="add",
        description="Adminランクにロールを追加します"
    )
    @app_commands.describe(
        role="Adminランクを付与するロール"
    )
    async def permission_add(
        self,
        interaction: discord.Interaction,
        role: discord.Role
    ):
        if not isinstance(interaction.user, discord.Member):
            return

        # Discordの管理者は常に実行可能
        if not interaction.user.guild_permissions.administrator:
            if not self.is_admin(interaction.user):
                await interaction.response.send_message(
                    "❌ このコマンドを使用する権限がありません。",
                    ephemeral=True
                )
                return

        data = self.load_data()
        admin_roles = data.setdefault("admin_roles", [])

        if role.id in admin_roles:
            await interaction.response.send_message(
                f"⚠️ {role.mention} は既にAdminランクです。",
                ephemeral=True
            )
            return

        admin_roles.append(role.id)
        self.save_data(data)

        await interaction.response.send_message(
            f"✅ {role.mention} をAdminランクに追加しました。",
            ephemeral=True
        )

    # =========================
    # /permission remove
    # =========================

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

        if not interaction.user.guild_permissions.administrator:
            if not self.is_admin(interaction.user):
                await interaction.response.send_message(
                    "❌ このコマンドを使用する権限がありません。",
                    ephemeral=True
                )
                return

        data = self.load_data()
        admin_roles = data.setdefault("admin_roles", [])

        if role.id not in admin_roles:
            await interaction.response.send_message(
                f"⚠️ {role.mention} はAdminランクではありません。",
                ephemeral=True
            )
            return

        admin_roles.remove(role.id)
        self.save_data(data)

        await interaction.response.send_message(
            f"✅ {role.mention} をAdminランクから削除しました。",
            ephemeral=True
        )

    # =========================
    # /permission list
    # =========================

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

        if not interaction.user.guild_permissions.administrator:
            if not self.is_admin(interaction.user):
                await interaction.response.send_message(
                    "❌ このコマンドを使用する権限がありません。",
                    ephemeral=True
                )
                return

        data = self.load_data()
        admin_roles = data.get("admin_roles", [])

        if not admin_roles:
            await interaction.response.send_message(
                "📋 Adminランクに登録されているロールはありません。",
                ephemeral=True
            )
            return

        roles = []

        for role_id in admin_roles:
            role = interaction.guild.get_role(role_id)

            if role is not None:
                roles.append(role.mention)
            else:
                roles.append(f"`Unknown Role ({role_id})`")

        await interaction.response.send_message(
            "📋 **Adminランク**\n\n" +
            "\n".join(f"• {role}" for role in roles),
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(PermissionManager(bot))
