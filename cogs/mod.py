from datetime import datetime
import asyncio
import typing
import discord
from discord.ext import commands, tasks
import config
import utils

class Mod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_ban_ctx = None
        self.last_kick_ctx = None
        self.last_mute_unmute_ctx = None
        self.lock = asyncio.Lock(loop=self.bot.loop)
        self.mutes = {}
        self.unmute_loop.start()

    @tasks.loop(seconds=3)
    async def unmute_loop(self):
        to_be_removed = None
        async with self.lock:
            for member_id, time in self.mutes.items():
                if datetime.utcnow() > time:
                    print(f'Unmuting {member_id}...')
                    guild = self.bot.get_guild(config.GUILD)
                    # chan = self.bot.get_channel(config.CHAN_MODLOG)
                    member = guild.get_member(member_id)
                    reason = 'Time\'s up!'
                    try:
                        await member.remove_roles(discord.Object(id=config.ROLE_MUTED), reason=reason)
                    except:
                        pass

                    to_be_removed = member_id
                    break

            if to_be_removed:
                self.mutes.pop(to_be_removed, None)
                await utils.remove_db_mute(self.bot.db, to_be_removed)

    @unmute_loop.before_loop
    async def before_unmute_loop(self):
        await self.bot.wait_until_ready()
        results = await utils.get_all_db_mutes(self.bot.db)
        for result in results:
            self.mutes[result['user_id']] = result['unmute_at']

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

        await member.add_roles(discord.Object(id=config.ROLE_MUTED), reason=reason)
        self.last_mute_unmute_ctx = ctx
        await ctx.send(f'Muted `{member}` successfully!')

    @commands.has_role(config.ROLE_STAFF)
    @commands.command()
    async def unmute(self, ctx, member: discord.Member, *, reason=''):
        if not any(config.ROLE_MUTED == role.id for role in member.roles):
            await ctx.send('That member is not muted you dumdum')
            return

        await member.remove_roles(ctx.guild.get_role(config.ROLE_MUTED), reason=reason)
        self.last_mute_unmute_ctx = ctx
        async with self.lock:
            self.mutes.pop(member.id, None)

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
        member = await self.bot.fetch_user(case['user_id'])
        unmute_at = None
        if case['case_type'] == utils.CaseType.MUTE.value:
            time_added = utils.parse_timedelta(reason)
            if time_added:
                unmute_at = case['timestamp'] + time_added
                async with self.lock:
                    self.mutes[member.id] = unmute_at
            else:
                async with self.lock:
                    if member.id in self.mutes:
                        self.mutes.pop(member.id, None)
                        await utils.remove_db_mute(self.bot.db, member.id)

        await utils.update_db_case_reason(self.bot.db, case_id, reason, unmute_at)
        embed = utils.create_modlog_embed(utils.CaseType(case['case_type']), case_id, member, ctx.author, case['timestamp'], reason, unmute_at)
        await msg.edit(embed=embed)
        await ctx.send(f'Reason changed for case #{case_id}')

    @commands.has_role(config.ROLE_STAFF)
    @commands.command()
    async def clean(self, ctx, target: typing.Union[discord.Member, str], limit=200):
        if limit > 2000:
            await ctx.send('The maximum limit is 2000 messages')
            return

        deleted = None
        if isinstance(target, discord.Member):
            def is_member(msg):
                return msg.author.id == target.id

            deleted = await ctx.channel.purge(limit=limit, check=is_member)
        elif isinstance(target, str) and 'bot' in target.lower():
            def is_bot(msg):
                return msg.author.bot

            deleted = await ctx.channel.purge(limit=limit, check=is_bot)

        await ctx.send(f'Done! Deleted {len(deleted)} messages.', delete_after=5)

def setup(bot):
    bot.add_cog(Mod(bot))
