from discord.ext import commands
import discord

class Automation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = bot.config

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        elif message.content.lower().startswith('hey kireina play despacito'):
            await message.channel.send(f'hEy KiReiNa pLaY dEsPaC...\n\nWhat do you think I am?! A music bot?!')

def setup(bot):
    bot.add_cog(Automation(bot))
