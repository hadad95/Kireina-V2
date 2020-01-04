import sys
import logging
import discord
from discord.ext import commands
from motor.motor_asyncio import AsyncIOMotorClient
import config

class Kireina(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=';;')
        print('Loading extensions/cogs...')
        cogs = [
            'cogs.events',
            'cogs.mod',
            'cogs.triggers',
            'cogs.owner',
            'cogs.main',
            'cogs.error_handler',
            'cogs.starboard'
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

        self.dbclient = AsyncIOMotorClient('mongodb://localhost:27017/', io_loop=self.loop)
        self.db = self.dbclient.kireina
        self.loop.run_until_complete(self.initialize_db())

    async def on_ready(self):
        print(f'READY! Logged in as {self.user}')

    async def initialize_db(self):
        print('Connecting to database...')
        if not 'modlog' in await self.db.list_collection_names():
            print('"modlog" collection not found. Creating and initializing a new collection...')
            await self.db.create_collection('modlog')
            await self.db.modlog.create_index('case_id', unique=True)
            await self.db.modlog.insert_one({'_id': 'current_case', 'value': 0})

        print('Done initializing database.')

if __name__ == '__main__':
    # logging stuff
    logger = logging.getLogger('discord')
    logger.setLevel(logging.WARNING)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
    logger.addHandler(handler)

    """
    # loading config and starting the bot
    print('Loading config.json...')
    with open('config.json', 'r') as f:
        cfg = json.load(f)
    bot = Kireina(cfg)
    """
    bot = Kireina()
    bot.run(config.TOKEN)
