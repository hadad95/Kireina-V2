import discord
from discord.ext import commands

MODS_ROLE = 608333944106123294

class Mod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = self.bot.config
        self.muted = self.config['roles']['muted']

    @commands.command()
    @commands.has_any_role(MODS_ROLE)
    async def kick(self, ctx, member: discord.Member, *, reason=''):
        await member.kick(reason=reason)
        await ctx.send(f'Successfully kicked `{member}`!')

    @commands.command()
    @commands.has_any_role(MODS_ROLE)
    async def ban(self, ctx, user: discord.User, *, reason=''):
        await ctx.guild.ban(user, reason=reason)
        await ctx.send(f'Successfully banned `{user}`!')

    @commands.has_any_role(MODS_ROLE)
    @commands.command()
    async def hackban(self, ctx, user_id: int, *, reason=''):
        user = await self.bot.fetch_user(user_id)
        await ctx.guild.ban(user, reason=reason)
        await ctx.send(f'Successfully banned `{user}`!')

    @commands.has_any_role(MODS_ROLE)
    @commands.command()
    async def mute(self, ctx, member: discord.Member, reason=''):
        for role in member.roles:
            if role.id == self.muted:
                await ctx.send(f'`{member}` is already muted')
                return

        await member.add_roles(ctx.guild.get_role(self.muted))
        await ctx.send(f'Muted `{member}` successfully!')

def setup(bot):
    bot.add_cog(Mod(bot))
