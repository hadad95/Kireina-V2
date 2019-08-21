from datetime import datetime, timedelta
import asyncio
import re
import discord
from discord.ext import commands, tasks
import config
import utils

class Mod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.regex_reason = re.compile(r'\|((?!.*\|).+)$')
        self.regex_time = re.compile(r'((?P<weeks>\d+?)\s?w[a-zA-Z]*)?\s*((?P<days>\d+?)\s?d[a-zA-Z]*)?\s*((?P<hours>\d+?)\s?h[a-zA-Z]*)?\s*((?P<minutes>\d+?)\s?m[a-zA-Z]*)?\s*((?P<seconds>\d+?)\s?s[a-zA-Z]*)?', re.IGNORECASE)
        self.last_ban_ctx = None
        self.last_kick_ctx = None
        self.mutes = {}
        #self.my_loop.start()

    """
    @tasks.loop(seconds=3)
    async def my_loop(self):
        print('Hello world')
        await asyncio.sleep(10)
    """

    @commands.command()
    async def test(self, ctx, *, arg1='1'):
        print(ctx.kwargs)

    @commands.command()
    @commands.has_role(config.ROLE_STAFF)
    async def kick(self, ctx, user: discord.Member, *, reason=''):
        await user.kick(reason=reason)
        self.last_kick_ctx = ctx
        await ctx.send(f'Successfully kicked `{user}`!')

    @commands.command()
    @commands.has_role(config.ROLE_STAFF)
    async def ban(self, ctx, user: discord.User, *, reason=''):
        await ctx.guild.ban(user, reason=reason)
        self.last_ban_ctx = ctx
        await ctx.send(f'Successfully banned `{user}`!')

    @commands.has_role(config.ROLE_STAFF)
    @commands.command()
    async def hackban(self, ctx, user_id: int, *, reason=''):
        user = await self.bot.fetch_user(user_id)
        await ctx.guild.ban(user, reason=reason)
        self.last_ban_ctx = ctx
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
        unmute_at = None
        time_str = self.regex_reason.search(reason)
        if time_str:
            time_added = self.parse_timedelta(time_str[1].strip())
            unmute_at = datetime.utcnow() + time_added
            self.mutes[member.id] = unmute_at

        embed = utils.get_modlog_embed(utils.CaseType.MUTE, case_id, member, ctx.author, timestamp, reason=reason if reason else 'None', unmute_at=unmute_at)
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
        embed = utils.get_modlog_embed(utils.CaseType.UNMUTE, case_id, member, ctx.author, timestamp, reason=reason if reason else 'None')
        case_msg = await chan.send(embed=embed)
        await utils.create_db_case(self.bot.db, case_id, utils.CaseType.UNMUTE, case_msg.id, member, ctx.author, timestamp, reason)
        await ctx.send(f'Unmuted `{member}` successfully!')

    def parse_timedelta(self, time_str):
        parts = self.regex_time.search(time_str)
        if not parts:
            return None

        parts = parts.groupdict()
        time_params = {}
        for (name, param) in parts.iteritems():
            if param:
                time_params[name] = int(param)

        return timedelta(**time_params)

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
        unmute_at = None
        if case['case_type'] == utils.CaseType.MUTE.value:
            time_str = self.regex_reason.search(reason)
            if time_str:
                time_added = self.parse_timedelta(time_str[1].strip())
                unmute_at = datetime.utcnow() + time_added
                self.mutes[member.id] = unmute_at

        await utils.update_db_case_reason(self.bot.db, case_id, reason)
        embed = utils.get_modlog_embed(utils.CaseType(case['case_type']), case_id, member, ctx.author, case['timestamp'], reason=reason, unmute_at=unmute_at)
        await msg.edit(embed=embed)
        await ctx.send(f'Reason changed for case #{case_id}')


def setup(bot):
    bot.add_cog(Mod(bot))
