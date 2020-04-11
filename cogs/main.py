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

    @commands.command(aliases=['av'])
    async def avatar(self, ctx, member: discord.Member=None):
        """ Display someone's avatar. Pass no arguments to display yours """

        url = None
        name = None
        if member:
            url = str(member.avatar_url)
            name = str(member)
        else:
            url = str(ctx.author.avatar_url)
            name = str(ctx.author)

        embed = discord.Embed()
        embed.title = f"{name}'s avatar"
        embed.colour = discord.Colour.blue()
        embed.set_image(url=url)
        await ctx.send(embed=embed)

    @commands.command()
    async def ping(self, ctx):
        """ Pong! """

        before_ws = int(round(self.bot.latency * 1000, 1))
        before = time.monotonic()
        message = await ctx.send(":ping_pong: Pong")
        ping = (time.monotonic() - before) * 1000
        await message.edit(content=f":ping_pong: WS: {before_ws}ms  |  REST: {int(ping)}ms")

def setup(bot):
    bot.add_cog(Main(bot))
