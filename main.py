import sys
import json
import logging
import discord
from discord.ext import commands

class Kireina(commands.Bot):
    def __init__(self, config):
        super().__init__(command_prefix=';;')
        self.running = False
        self.config = config
        self.load_extension('cogs.logger')
        self.load_extension('cogs.mod')
        self.load_extension('cogs.automation')

    async def on_ready(self):
        if not self.running:
            self.running = True
            hrts = self.get_guild(self.config['guild'])
            self.config['messages'] = {}
            for channel in hrts.channels:
                if channel.type == discord.ChannelType.text:
                    messages = await channel.history().flatten()
                    for msg in messages:
                        self.config['messages'][msg.id] = msg

        print('READY!')

    async def on_guild_available(self, guild):
        print(f'Guild {guild} is available')

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
