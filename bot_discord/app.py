import discord
from discord.ext import commands

intents = discord.Intents.default()

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"{bot.user} đã online")

    # Đồng bộ slash command lên Discord
    try:
        synced = await bot.tree.sync()
        print(f"Đã đồng bộ {len(synced)} lệnh")
    except Exception as e:
        print(e)


# /ping
@bot.tree.command(name="ping", description="Kiểm tra bot có hoạt động không")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(
        f"Pong! {round(bot.latency * 1000)}ms"
    )


# /help
@bot.tree.command(name="help", description="Hiển thị danh sách lệnh")
async def help_command(interaction: discord.Interaction):

    embed = discord.Embed(
        title="Danh sách lệnh",
        description="Các lệnh hiện có của bot",
    )

    embed.add_field(
        name="/ping",
        value="Kiểm tra độ trễ của bot",
        inline=False
    )

    embed.add_field(
        name="/help",
        value="Hiển thị danh sách lệnh",
        inline=False
    )

    await interaction.response.send_message(embed=embed)


bot.run("MTUxODMxNTA1NzcwNzIyMTE2Mg.Gsb-rq.kBcusvyAub3gClF4EoEoRnlKIxE4-THp3Q-uck")