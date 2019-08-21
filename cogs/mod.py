from datetime import datetime
import asyncio
import discord
from discord.ext import commands, tasks
import config
import utils
import re

class Mod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        #self.my_loop.start()

"""
    @tasks.loop(seconds=3)
    async def my_loop(self):
        print('Hello world')
        await asyncio.sleep(10)
"""

    @commands.command()
    @commands.has_role(config.ROLE_STAFF)
    async def kick(self, ctx, member: discord.Member, *, reason=''):
        await member.kick(reason=reason)
        await ctx.send(f'Successfully kicked `{member}`!')

    @commands.command()
    @commands.has_role(config.ROLE_STAFF)
    async def ban(self, ctx, user: discord.User, *, reason=''):
        await ctx.guild.ban(user, reason=reason)
        await ctx.send(f'Successfully banned `{user}`!')

    @commands.has_role(config.ROLE_STAFF)
    @commands.command()
    async def hackban(self, ctx, user_id: int, *, reason=''):
        user = await self.bot.fetch_user(user_id)
        await ctx.guild.ban(user, reason=reason)
        await ctx.send(f'Successfully banned `{user}`!')

    @commands.has_role(config.ROLE_STAFF)
    @commands.command()
    async def mute(self, ctx, member: discord.Member, *, reason=''):
        if any(role.id == config.ROLE_MUTED for role in member.roles): #role.id == config.ROLE_MUTED:
            await ctx.send(f'`{member}` is already muted')
            return

        chan = self.bot.get_channel(config.CHAN_MODLOG)
        await member.add_roles(ctx.guild.get_role(config.ROLE_MUTED), reason=reason)
        case_id = await utils.get_next_case_id(self.bot.db)
        timestamp = datetime.utcnow()
        embed = utils.get_modlog_embed(utils.CaseType.MUTE, case_id, member, ctx.author, timestamp, reason if reason else 'None')
        case_msg = await chan.send(embed=embed)
        await utils.create_db_case(self.bot.db, case_id, utils.CaseType.MUTE, case_msg.id, member, ctx.author, timestamp, reason)
        await ctx.send(f'Muted `{member}` successfully!')

    @commands.has_role(config.ROLE_STAFF)
    @commands.command()
    async def unmute(self, ctx, member: discord.Member, *, reason=''):
        if not any(config.ROLE_MUTED == role.id for role in member.roles):
            await ctx.send('That member is not muted you dumdum')
            return

        chan = self.bot.get_channel(config.CHAN_MODLOG)
        await member.remove_roles(ctx.guild.get_role(config.ROLE_MUTED), reason=reason)
        case_id = await utils.get_next_case_id(self.bot.db)
        timestamp = datetime.utcnow()
        embed = utils.get_modlog_embed(utils.CaseType.UNMUTE, case_id, member, ctx.author, timestamp, reason if reason else 'None')
        case_msg = await chan.send(embed=embed)
        await utils.create_db_case(self.bot.db, case_id, utils.CaseType.UNMUTE, case_msg.id, member, ctx.author, timestamp, reason)
        await ctx.send(f'Unmuted `{member}` successfully!')

    @commands.has_role(config.ROLE_STAFF)
    @commands.command()
    async def reason(self, ctx, case_id: int, *, reason):
        case = await utils.get_db_case(self.bot.db, case_id)
        if not case:
            await ctx.send(f'Case #{case_id} not found!')
            return

        chan = self.bot.get_channel(config.CHAN_MODLOG)
        msg = await chan.fetch_message(case['case_msg_id'])
        member = self.bot.get_user(case['user_id'])
        await utils.update_db_case_reason(self.bot.db, case_id, reason)
        embed = utils.get_modlog_embed(utils.CaseType(case['case_type']), case_id, member, ctx.author, case['timestamp'], reason)
        await msg.edit(embed=embed)
        await ctx.send(f'Reason changed for case #{case_id}')


def setup(bot):
    bot.add_cog(Mod(bot))
