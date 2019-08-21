from datetime import datetime
import discord
from discord.ext import commands
import config
import utils

class Mod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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

        """
        result = await self.bot.db.modlog.find_one_and_update({'_id': 'current_case'}, {'$inc': {'value': 1}}, return_document=ReturnDocument.AFTER)
        case_id = result['value']
        """
        case_id = await utils.get_next_case_id(self.bot.db)
        """
        embed = discord.Embed()
        embed.set_author(name='Member muted', icon_url=member.avatar_url)
        embed.add_field(name='User', value=member, inline=False)
        embed.add_field(name='Moderator', value=ctx.author, inline=False)
        embed.add_field(name='Reason', value=reason if reason else f'None', inline=False)
        embed.set_thumbnail(url=member.avatar_url)
        embed.colour = discord.Colour.gold()
        embed.timestamp = datetime.utcnow()
        embed.set_footer(text=f'Case #{case_id}')
        """
        timestamp = datetime.utcnow()
        embed = utils.get_modlog_embed(utils.CaseType.MUTE, case_id, member, ctx.author, timestamp, reason if reason else 'None')
        case_msg = await chan.send(embed=embed)
        """
        doc = {'case_id': case_id, 'case_type': utils.CaseType.MUTE.value, 'case_msg_id': case_msg.id, 'user_id': member.id, 'mod_id': ctx.author.id, 'timestamp': embed.timestamp, 'reason': reason}
        await self.bot.db.modlog.insert_one(doc)
        """
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

        """
        result = await self.bot.db.modlog.find_one_and_delete({'user_id': member.id})
        if result:
            case_id = result['case_id']
            try:
                del self.modlog[case_id]
            except:
                pass

        embed = discord.Embed()
        embed.set_author(name='Member unmuted', icon_url=member.avatar_url)
        embed.add_field(name='User', value=member, inline=False)
        embed.add_field(name='Moderator', value=ctx.author, inline=False)
        embed.add_field(name='Reason', value=reason if reason else 'None', inline=False)
        embed.set_thumbnail(url=member.avatar_url)
        embed.colour = discord.Colour.green()
        embed.timestamp = datetime.utcnow()
        """
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
        member = ctx.guild.get_member(case['user_id'])
        await utils.update_db_case_reason(self.bot.db, case_id, reason)
        """
        await self.bot.db.modlog.update_one({'case_id': case_id}, {'$set': {'reason': reason}})
        embed = discord.Embed()
        embed.set_author(name='Member muted', icon_url=member.avatar_url)
        embed.add_field(name='User', value=member, inline=False)
        embed.add_field(name='Moderator', value=ctx.author, inline=False)
        embed.add_field(name='Reason', value=reason, inline=False)
        embed.set_thumbnail(url=member.avatar_url)
        embed.colour = discord.Colour.gold()
        embed.timestamp = case['timestamp']
        embed.set_footer(text=f'Case #{case_id}')
        """
        embed = utils.get_modlog_embed(utils.CaseType(case['case_type']), case_id, member, ctx.author, case['timestamp'], reason)

        await msg.edit(embed=embed)
        await ctx.send(f'Reason changed for case #{case_id}')


def setup(bot):
    bot.add_cog(Mod(bot))
