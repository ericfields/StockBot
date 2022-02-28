#!/usr/bin/env pytyhon3

from typing import Union
from io import BytesIO
import os
import sys
import traceback

from discord import Embed, File, Client, Intents
from discord.ext import commands
from discord_slash import SlashCommand, SlashContext
from discord_slash.utils.manage_components import create_button, create_actionrow
from discord_slash.model import ButtonStyle
import interactions

from discord_helpers import command, create_commands

from chart.chart import Chart
from exceptions import BadRequestException, NotFoundException

from secrets.discord_credentials import bot_token

import django.core.management
import django
from asgiref.sync import sync_to_async
import threading

bot = interactions.Client(token=bot_token)
def start_bot():
    bot.start()

slash = SlashCommand(bot)

@slash.slash(**command('quote'))
async def quote(ctx: SlashContext, tickers, timespan=None):
    try:
        await send_chart(ctx, tickers, timespan)
    except (NotFoundException, BadRequestException) as e:
        await ctx.send(str(e))
    except Exception as e:
        traceback.print_exc()
        await ctx.send("An internal error occurred")

@slash.slash(**command('market'))
async def market(ctx: SlashContext):
    print("market")
    try:
        await send_chart(ctx, 'EVERYONE', None)
    except (NotFoundException, BadRequestException) as e:
        await ctx.send(str(e))
    except Exception as e:
        traceback.print_exc()
        await ctx.send("An internal error occurred")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.component("refresh")
async def refresh(ctx):
    print("refresh")
    await ctx.send("should refresh")

async def send_chart(ctx: SlashContext, tickers: str, timespan: str):
    chart = await build_chart(tickers, timespan)
    
    file = chart_file(chart)
    embed = Embed(title=chart.title)
    embed.set_image(url=f"attachment://{file.filename}")

    buttons = [
        create_button(style=ButtonStyle.green, label="Refresh", custom_id="refresh"),
        create_button(style=ButtonStyle.blue, label="1 week", custom_id="1w")
    ]
    action_row = create_actionrow(*buttons)

    await ctx.send(embed=embed,file=file, components=[action_row])

def chart_file(chart: Chart):
    return File(BytesIO(chart.get_img_data()), filename='chart.png')

@sync_to_async
def build_chart(tickers, timespan) -> Chart:
    from chart import chart_builder
    return chart_builder.build_chart(tickers, timespan)

def run_django():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'StockBot.settings')

    # Adding 'runserver' to sys.argv seems to be the only way to get Django to load properly
    sys.argv.append('runserver')

    django.setup()

if __name__ == '__main__':
    if 'createcommands' in sys.argv:
        create_commands() or exit("Command creation failed")

    thread = threading.Thread(target=run_django)
    thread.start()

    print("Starting bot...")
    start_bot()
