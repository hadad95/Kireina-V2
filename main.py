import sys
import json
import logging
import discord
from discord.ext import commands

class Kireina(commands.Bot):
    def __init__(self, cfg):
        super().__init__(command_prefix=';;')
        self.config = cfg
        self.load_extension('cogs.logger')
        self.load_extension('cogs.mod')
        self.load_extension('cogs.automation')

    async def on_ready(self):
        print('READY!')

if __name__ == '__main__':
    # logging stuff
    logger = logging.getLogger('discord')
    logger.setLevel(logging.WARNING)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
    logger.addHandler(handler)

    # loading config and starting the bot
    with open('config.json', 'r') as f:
        config = json.load(f)
    bot = Kireina(config)
    bot.run(config['token'])
