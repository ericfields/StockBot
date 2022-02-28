#!/usr/bin/env python3

import requests
from secrets.discord_credentials import application_id, bot_token
from discord_slash import SlashCommandOptionType

guild_id = 946181383448064050

commands = [
    {
        "name": "quote",
        "description": "Provide a price chart for one or more stocks or indexes",
        "options": [
            {
                "name": "tickers",
                "description": "Stock tickers or index identifiers to quote, comma-separated",
                "type": SlashCommandOptionType.STRING,
                "required": True
            },
            {
                "name": "timespan",
                "description": "Timespan for the stock chart. Number of days, weeks, months, or years. Examples: 2d, 3w, 6m, 5y",
                "type": SlashCommandOptionType.STRING,
                "required": False
            }
        ]
    },
    {
        "name": "market",
        "description": "Provide a price chart for all indexes in the server",
    }
]

def command(name: str):
    for command in commands:
        if command['name'] == name:
            return command
    raise Exception(f"No command found with name '{name}")

def create_commands():
    url = f"https://discord.com/api/v8/applications/{application_id}"
    if guild_id:
        url += f"/guilds/{guild_id}"
    url += "/commands"

    headers = {
        "Authorization": f"Bot {bot_token}"
    }

    commands = [
        {
            "name": "quote",
            "type": 1,
            "description": "Provide a price chart for one or more stocks or indexes",
            "options": [
                {
                    "name": "tickers",
                    "description": "Stock tickers or index identifiers to quote, comma-separated",
                    "type": SlashCommandOptionType.STRING,
                    "required": True
                },
                {
                    "name": "timespan",
                    "description": "Timespan for the stock chart. Number of days, weeks, months, or years. Examples: 2d, 3w, 6m, 5y",
                    "type": SlashCommandOptionType.STRING,
                    "required": False
                }
            ]
        },
        {
            "name": "market",
            "type": 1,
            "description": "Provide a price chart for all indexes in the server",
        }
    ]

    for command in commands:
        print("Creating command " + command['name'])
        r = requests.post(url, headers=headers, json=command)
        if not 200 <= r.status_code <= 299:
            print(f"""Error creating '{command['name']}' command
                {r.status_code} {r.reason}\n
                {r.content}""")
            return False

    print("All commands created successfully")
    return True