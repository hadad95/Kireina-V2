import ast
import textwrap
import discord
from discord.ext import commands
import config

def insert_returns(body):
    # insert return stmt if the last expression is a expression statement
    if isinstance(body[-1], ast.Expr):
        body[-1] = ast.Return(body[-1].value)
        ast.fix_missing_locations(body[-1])

    # for if statements, we insert returns into the body and the orelse
    if isinstance(body[-1], ast.If):
        insert_returns(body[-1].body)
        insert_returns(body[-1].orelse)

    # for with blocks, again we insert returns into the body
    if isinstance(body[-1], ast.With):
        insert_returns(body[-1].body)

class Owner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(hidden=True)
    @commands.is_owner()
    async def reload(self, ctx, cog):
        self.bot.reload_extension(f'cogs.{cog}')
        await ctx.send(f'Reloaded cog `{cog}`')

    @commands.command(hidden=True)
    @commands.is_owner()
    async def eval(self, ctx, *, code):
        fn_name = "_eval_expr"

        # add a layer of indentation
        _code = textwrap.indent(code, '    ')

        # wrap in async def body
        body = f"async def {fn_name}():\n{_code}"

        parsed = ast.parse(body)
        body = parsed.body[0].body

        insert_returns(body)

        env = {
            'self': self,
            'bot': self.bot,
            'commands': commands,
            'ctx': ctx,
            'message': ctx.message,
            'channel': ctx.message.channel,
            'guild': ctx.message.guild,
            'author': ctx.message.author,
            '__import__': __import__
        }

        try:
            exec(compile(parsed, filename="<ast>", mode="exec"), env)
            result = (await eval(f"{fn_name}()", env))
            result = repr(result) if result else str(result)
        except Exception as e:
            result = '{}: {}'.format(type(e).__name__, e)

        code = code.split('\n')
        s = ''
        for i, line in enumerate(code):
            s += '>>> ' if i == 0 else '... '
            s += line + '\n'

        message = f'```py\n{s}\n{result}\n```'

        try:
            await ctx.send(message)
        except discord.HTTPException:
            await ctx.send('Output too large!')

def setup(bot):
    bot.add_cog(Owner(bot))
