import discord
import qrcode
import asyncio
from pytoniq import Address
from discord.ext import commands
from discord import app_commands
from discord.ext.commands.context import Context
from io import BytesIO

import time
from multiprocessing import Process
from os import remove as remove_file

from config import *
from functions import *


class Bot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="?", intents=intents)

    # то что ниже надо будет раскомментить если вы будете настраивать нового бота/сервер
    # async def setup_hook(self):
    #     await self.tree.sync(guild=discord.Object(id=GUILD_ID))
    #     print(f"Synced slash commands for {self.user}.")


bot = Bot()


@bot.hybrid_command(name="connect", with_app_command=True, description="Connect your Tonkeeper")
@app_commands.guilds(discord.Object(id=GUILD_ID))
async def connect(ctx: Context):
    # print(bot.guilds)
    # print(list(map(lambda t: (t.name, t.id), ctx.guild.roles)))
    await ctx.defer(ephemeral=True)
    author_id = ctx.author.id
    last_refresh = last_requests.get(author_id, 0)
    user_wallet = get_wallet(author_id)

    if last_refresh > int(time.time()) - COOLDOWN_TIME:
        await ctx.reply(f"Don't flood! Try again in {COOLDOWN_TIME - int(time.time()) + last_refresh} seconds!")
        return
    elif user_wallet:
        await ctx.reply(f"Your connected wallet address:\n\n`{user_wallet}`\n\n"
                        f"To update data about your roles use the `/get_roles` command")
    else:
        connectors = []
        connectors.append(await get_connector(author_id, "Tonkeeper"))
        connectors.append(await get_connector(author_id, "Tonhub"))
        connectors.append(await get_connector(author_id, "MyTonWallet"))
        connectors.append(await get_connector(author_id, "Wallet"))
        buffered = BytesIO()
        qrcode.make(connectors[0][0]).save(buffered)
        buffered.seek(0)
        bot_msg = await ctx.reply(f"Your personal url for connecting:\n"
                                    f"- [Tonkeeper](<{connectors[0][0]}>)\n"
                                    f"- [Tonhub](<{connectors[1][0]}>)\n"
                                    f"- [MyTonWallet](<{connectors[2][0]}>)\n"
                                    f"- [Tonspace](<{connectors[3][0]}>)\n\n"
                                    f"You can also scan the QR-code below via Tonkeeper app.",
                                    file=discord.File(fp=buffered, filename='tonkeeper-qr.png'))
        
        for _ in range(120):
            await asyncio.sleep(1)
            if any(map(lambda l: l[1].connected, connectors)):
                main_connector = None
                for (_, connector) in connectors: 
                    if not connector.connected and connector._provider:
                        connector._provider.close_connection()
                    elif connector.connected:
                        main_connector = connector

                wallet_address = Address(main_connector.account.address).to_str(True, True, is_bounceable=False)

                if check_wallet(wallet_address):
                    await bot_msg.edit(content=f"This wallet is already connected to someone's account, try to connect another wallet.", attachments=[])
                    await main_connector.disconnect()
                else:
                    add_wallet(author_id, ctx.author.__str__(), wallet_address)
                    await bot_msg.edit(content=f"You have successfully connected your wallet! You can now send the `/get_roles` command to update your roles.", attachments=[])
                    main_connector._provider.pause()
                    last_requests[author_id] = int(time.time())
                return
            
        await bot_msg.edit(content="Timeout error. Try to reconnect your wallet.", attachments=[])
    
    last_requests[author_id] = int(time.time())


@bot.hybrid_command(name="get_roles", with_app_command=True, description="Update your roles")
@app_commands.guilds(discord.Object(id=GUILD_ID))
async def refresh(ctx: Context):
    await ctx.defer(ephemeral=True)
    author_id = ctx.author.id
    wallet = get_wallet(author_id)
    last_request = last_requests.get(author_id, 0)

    if last_request > int(time.time()) - COOLDOWN_TIME:
        await ctx.reply(f"Don't flood! Try again in {COOLDOWN_TIME - int(time.time()) + last_request} seconds!")
        return
    elif not wallet:
        await ctx.reply("You haven't connected your wallet yet. Try the `/connect` command")
    else:
        reply_text = f"Your wallet:\n`{wallet}`\n\n"
        msg = await ctx.reply(reply_text + "Checking your wallet...")

        cur_roles = list(map(lambda t: (t.name, t.id), ctx.author.roles[1:]))
        available_roles = []
        traded_volume = get_traded_volume(wallet)
        reply_text += f"Your traded volume: {traded_volume} TON\n"
        if traded_volume > MIN_TRADED_VOLUME:
            available_roles.extend([("Wallet Connect", ROLE_IDS["Wallet Connect"]), ("DEX user", ROLE_IDS["DEX user"])])
            reply_text += f"✅ You were awarded with the DEX user role as your tradig volume is more than {MIN_TRADED_VOLUME} TON"
        else:
            reply_text += f"❌ You need to make swaps for {MIN_TRADED_VOLUME - traded_volume} more TON to get the DEX user role\n"
        new_roles = []
        for role in available_roles:
            if role not in cur_roles:
                new_roles.append(role[0])
                await ctx.author.add_roles(ctx.guild.get_role(role[1]))
        
        # if new_roles:
        #     reply_text += "You were awarded with following roles:\n"
        #     for role_name in new_roles:
        #         reply_text += f"- {role_name}"
        
        await msg.edit(content=reply_text)
    
    last_requests[author_id] = int(time.time())


@bot.hybrid_command(name="disconnect", with_app_command=True, description="Disconnect wallet")
@app_commands.guilds(discord.Object(id=GUILD_ID))
async def disconnect(ctx: Context):
    await ctx.defer(ephemeral=True)
    author_id = ctx.author.id
    last_request = last_requests.get(author_id, 0)

    if last_request > int(time.time()) - COOLDOWN_TIME:
        await ctx.reply(f"Don't flood! Try again in {COOLDOWN_TIME - int(time.time()) + last_request} seconds!")
        return
    elif remove_wallet(author_id):
        await disconnect_wallet(author_id)
        await ctx.reply("Wallet was successfully disconnected")
        for role in map(lambda l: ctx.guild.get_role(l[1]), ROLE_IDS.items()):
            await ctx.author.remove_roles(role)
    else:
        await ctx.reply("You haven't connected a wallet yet")
    last_requests[author_id] = int(time.time())



# @bot.hybrid_command(name="refresh_all", with_app_command=True, description="Update info about all wallets")
# @app_commands.guilds(discord.Object(id=GUILD_ID))
# async def refresh_all(ctx: Context):
#     await ctx.defer(ephemeral=True)
#     user_roles = list(map(lambda t: t.name, ctx.author.roles[1:]))
#     if "moderator" not in user_roles and "admin" not in user_roles: #and "STON.PRO" not in user_roles:
#         await ctx.reply("You are not allowed to use this command")
#         return

#     f = open("wallets.csv")
#     data = f.read().split('\n')[1:]
#     f.close()
#     deleted_roles = {}
#     for i in range(len(data)):
#         user_nick, user_id, wallet = data[i].split(';')
#         user_roles = list(map(lambda t: (t.name, t.id), (await ctx.guild.fetch_member(user_id)).roles[1:]))
#         possible_roles = check_wallet(wallet)[0]
#         deleted_roles[user_nick] = []

#         for role in user_roles:
#             if role[0] in ROLE_IDS and role not in possible_roles:
#                 deleted_roles[user_nick].append(role[0])
#                 await ctx.author.remove_roles(ctx.guild.get_role(role[1]))

#     await ctx.reply(f"checked {len(data)} wallets\n\nMore info about deleted roles:\n{deleted_roles}")
#     # print(deleted_roles)


if __name__ == "__main__":
    last_requests = {}
    bot.run(BOT_TOKEN)
