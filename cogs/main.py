import random
import discord
from discord.ext import commands, tasks
import config

class Main(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def hrt(self, ctx, size='smol'):
        """ Send a random hrt emote.
        Size can be 'smol' or 'big'. Default is smol uwu. """
        emoji = random.choice(ctx.guild.emojis)
        if size.lower() == 'big':
            embed = discord.Embed()
            embed.description = emoji.name
            embed.colour = discord.Colour.green()
            embed.set_image(url=emoji.url)
            await ctx.send(embed=embed)
        else:
            await ctx.send(emoji)

def setup(bot):
    bot.add_cog(Main(bot))
