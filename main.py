import sys
import json
import logging
import discord
from discord.ext import commands
from motor.motor_asyncio import AsyncIOMotorClient

class Kireina(commands.Bot):
    def __init__(self, config):
        super().__init__(command_prefix=';;')
        self.config = config
        print('Loading extensions/cogs...')
        cogs = [
            'cogs.logger',
            'cogs.mod',
            'cogs.automation',
            'cogs.owner'
        ]

        for cog in cogs:
            try:
                self.load_extension(cog)
                print(f'Loaded "{cog}" successfully!')
            except SyntaxError:
                print(f'Failed to load "{cog}" because of a syntaxerror.')
            except ImportError as ex:
                print(f'Failed to load "{cog}" because of an importerror.')
                print(ex)

        self.dbclient = AsyncIOMotorClient('mongodb://localhost:27017/')
        self.db = self.dbclient.kireina
        self.loop.run_until_complete(self.initialize_db())

    async def on_ready(self):
        print(f'READY! Logged in as {self.user}')

    async def initialize_db(self):
        print('Connecting to database...')
        if not 'mutes' in await self.db.list_collection_names():
            print('"mutes" collection not found. Creating and initializing a new collection...')
            await self.db.create_collection('mutes')
            await self.db.mutes.create_index('case_id', unique=True)
            await self.db.mutes.insert_one({'_id': 'current_case', 'value': 0})

if __name__ == '__main__':
    # logging stuff
    logger = logging.getLogger('discord')
    logger.setLevel(logging.WARNING)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
    logger.addHandler(handler)

    # loading config and starting the bot
    print('Loading config.json...')
    with open('config.json', 'r') as f:
        cfg = json.load(f)
    bot = Kireina(cfg)
    bot.run(cfg['token'])
