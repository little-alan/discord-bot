import discord
from discord import app_commands
from discord.ext import commands
import random
from dotenv import load_dotenv
import os

# 載入 .env 檔案
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.reactions = True

bot = commands.Bot(command_prefix="/", intents=intents)

reaction_role_mapping = {}
admin_role_name = "管理員"
welcome_settings = {}

@bot.event
async def on_ready():
    print(f'{bot.user.name} 機器人已上線')
    await bot.tree.sync()
    print(f'✅ {bot.user.name} 指令同步完成')

# /help
@bot.tree.command(name="help", description="幫助")
async def help_command(interaction: discord.Interaction):
    help_text = (
        "/help - 查看伺服器幫助\n"
        "/clear - 清除訊息\n"
        "/embed - 發送嵌入式訊息\n"
        "/reactionrole - 設定反應身分組\n"
        "/welcome - 設定歡迎訊息\n"
        "/dice - 擲骰子"
    )
    embed = discord.Embed(title="伺服器指令幫助", description=help_text, color=0xAFEEEE)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# /clear
@bot.tree.command(name="clear", description="清除訊息(管理員指令)")
@app_commands.describe(count="刪除數量")
async def clear(interaction: discord.Interaction, count: int):
    if discord.utils.get(interaction.user.roles, name=admin_role_name):
        try:
            deleted = await interaction.channel.purge(limit=count)
            await interaction.response.send_message(f"✅ 已成功刪除 {len(deleted)} 條訊息", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ 清除訊息時發生錯誤: {e}", ephemeral=True)
    else:
        await interaction.response.send_message("⚠️ 您無法使用此指令", ephemeral=True)

# /embed
@bot.tree.command(name="embed", description="發送嵌入式訊息(管理員指令)")
@app_commands.describe(
    title="標題(可選)",
    description="內文(可選)",
    footer="頁尾(可選)",
    msg="文字訊息(可選)",
    channel="發送頻道(可選)",
    color="顏色(預設 #AFEEEE)"
)
async def embed(interaction: discord.Interaction, title: str = None, description: str = None, footer: str = None, msg: str = None, channel: discord.TextChannel = None, color: str = "0xAFEEEE"):
    if discord.utils.get(interaction.user.roles, name=admin_role_name):
        try:
            embed_color = int(color, 16)
            embed_obj = discord.Embed(color=embed_color)
            if title:
                embed_obj.title = title
            if description:
                embed_obj.description = description
            if footer:
                embed_obj.set_footer(text=footer)

            target_channel = channel or interaction.channel
            if msg:
                await target_channel.send(content=msg)
            await target_channel.send(embed=embed_obj)
            await interaction.response.send_message("✅ 公告已發送", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ 發送公告時發生錯誤: {e}", ephemeral=True)
    else:
        await interaction.response.send_message("⚠️ 您無法使用此指令", ephemeral=True)

# /reactionrole
@bot.tree.command(name="reactionrole", description="設定反應身分組")
@app_commands.describe(message="訊息 ID", emoji="表情符號", role="賦予的身分組")
async def reactionrole(interaction: discord.Interaction, message: str, emoji: str, role: discord.Role):
    if discord.utils.get(interaction.user.roles, name=admin_role_name):
        try:
            msg_id = int(message)
            msg = await interaction.channel.fetch_message(msg_id)
            await msg.add_reaction(emoji)
            if msg_id not in reaction_role_mapping:
                reaction_role_mapping[msg_id] = {}
            reaction_role_mapping[msg_id][emoji] = role.id
            await interaction.response.send_message(f"✅ 設定成功：點選 {emoji} 會賦予角色 {role.name}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ 設定失敗：{e}", ephemeral=True)
    else:
        await interaction.response.send_message("⚠️ 您無法使用此指令", ephemeral=True)

# /welcome
@bot.tree.command(name="welcome", description="設定歡迎訊息 (管理員限定)")
@app_commands.describe(
    mode="新增(add) 或 移除(remove)",
    title="標題文字",
    description="內容文字，可包含 {member} 來顯示加入者名稱",
    channel="要發送的頻道"
)
async def welcome(interaction: discord.Interaction,
                  mode: str,
                  title: str = None,
                  description: str = None,
                  channel: discord.TextChannel = None):
    if not discord.utils.get(interaction.user.roles, name=admin_role_name):
        await interaction.response.send_message("⚠️ 您無法使用此指令", ephemeral=True)
        return

    guild_id = interaction.guild_id

    if mode.lower() == "add":
        if not (title and description and channel):
            await interaction.response.send_message("請完整填寫 title、description、channel。", ephemeral=True)
            return
        welcome_settings[guild_id] = {
            "title": title,
            "description": description,
            "channel": channel
        }
        await interaction.response.send_message("✅ 歡迎訊息設定完成", ephemeral=True)

    elif mode.lower() == "remove":
        if guild_id in welcome_settings:
            del welcome_settings[guild_id]
            await interaction.response.send_message("🗑️ 已移除歡迎訊息設定", ephemeral=True)
        else:
            await interaction.response.send_message("尚未設定歡迎訊息。", ephemeral=True)
    else:
        await interaction.response.send_message("❌ 模式錯誤，請使用 add 或 remove。", ephemeral=True)

# 反應身分組處理
@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return
    msg_id = payload.message_id
    emoji = str(payload.emoji)
    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id)
    if member and msg_id in reaction_role_mapping and emoji in reaction_role_mapping[msg_id]:
        role = guild.get_role(reaction_role_mapping[msg_id][emoji])
        if role:
            try:
                await member.add_roles(role)
            except discord.Forbidden:
                print(f"⚠️ 無法為 {member} 加角色 {role.name}，權限不足")

@bot.event
async def on_raw_reaction_remove(payload):
    msg_id = payload.message_id
    emoji = str(payload.emoji)
    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id)
    if member and msg_id in reaction_role_mapping and emoji in reaction_role_mapping[msg_id]:
        role = guild.get_role(reaction_role_mapping[msg_id][emoji])
        if role:
            try:
                await member.remove_roles(role)
            except discord.Forbidden:
                print(f"⚠️ 無法為 {member} 移除角色 {role.name}，權限不足")

# 成員加入事件
@bot.event
async def on_member_join(member):
    role = discord.utils.get(member.guild.roles, name="脆友")
    if role:
        try:
            await member.add_roles(role)
        except discord.Forbidden:
            print(f"⚠️ 無法為 {member.name} 加入角色 脆友，權限不足")

    setting = welcome_settings.get(member.guild.id)
    if setting:
        channel = setting["channel"]
        title = setting["title"]
        desc = setting["description"].replace("{member}", member.mention)
        embed = discord.Embed(title=title, description=desc, color=discord.Color.blue())
        await channel.send(embed=embed)

# /dice 指令
@bot.tree.command(name="dice", description="擲骰子（可自訂範圍，預設 1~6）")
@app_commands.describe(min="最小值（預設1）", max="最大值（預設6）")
async def dice(interaction: discord.Interaction, min: int = 1, max: int = 6):
    if min < 1 or max > 100 or min > max:
        await interaction.response.send_message("請輸入有效的範圍（1 ≤ min ≤ max ≤ 100）", ephemeral=True)
        return

    result = random.randint(min, max)
    await interaction.response.send_message(f"🎲 擲出數字：{result}", ephemeral=True)

# 啟動機器人
bot.run(TOKEN)
