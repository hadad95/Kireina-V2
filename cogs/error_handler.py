import discord
from discord.ext import commands

class ErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            pass
        elif isinstance(error, (commands.MissingPermissions, commands.MissingRole)):
            await ctx.send('Don\'t play with fire, boi!')
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send('Oops, I\'m missing permissions!')
        elif isinstance(error, (commands.MissingRequiredArgument, commands.BadArgument)):
            await ctx.send_help(ctx.command)
        else:
            print(error)
            await ctx.send(f'An error has occured ({type(error).__name__}):\n```\n{error}\n```')

def setup(bot):
    bot.add_cog(ErrorHandler(bot))
