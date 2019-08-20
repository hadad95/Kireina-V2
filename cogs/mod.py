from datetime import datetime
import discord
from discord.ext import commands
from pymongo import ReturnDocument

STAFF_ROLE = 608333944106123294

class Mod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = self.bot.config
        self.muted_role = self.config['roles']['muted']
        self.mutes = {}

    @commands.command()
    @commands.has_role(STAFF_ROLE)
    async def kick(self, ctx, member: discord.Member, *, reason=''):
        await member.kick(reason=reason)
        await ctx.send(f'Successfully kicked `{member}`!')

    @commands.command()
    @commands.has_role(STAFF_ROLE)
    async def ban(self, ctx, user: discord.User, *, reason=''):
        await ctx.guild.ban(user, reason=reason)
        await ctx.send(f'Successfully banned `{user}`!')

    @commands.has_role(STAFF_ROLE)
    @commands.command()
    async def hackban(self, ctx, user_id: int, *, reason=''):
        user = await self.bot.fetch_user(user_id)
        await ctx.guild.ban(user, reason=reason)
        await ctx.send(f'Successfully banned `{user}`!')

    @commands.has_role(STAFF_ROLE)
    @commands.command()
    async def mute(self, ctx, member: discord.Member, *, reason=''):
        if any(self.muted_role == role.id for role in member.roles): #role.id == self.muted_role:
            await ctx.send(f'`{member}` is already muted')
            return

        chan = self.bot.get_channel(self.config['channels']['kicks_bans_mutes'])
        await member.add_roles(ctx.guild.get_role(self.muted_role), reason=reason)

        result = await self.bot.db.mutes.find_one_and_update({'_id': 'current_case'}, {'$inc': {'value': 1}}, return_document=ReturnDocument.AFTER)
        case_id = result['value']

        embed = discord.Embed()
        embed.set_author(name='Member muted', icon_url=member.avatar_url)
        embed.add_field(name='User', value=member, inline=False)
        embed.add_field(name='Moderator', value=ctx.author, inline=False)
        embed.add_field(name='Reason', value=reason if reason else f'None', inline=False)
        embed.set_thumbnail(url=member.avatar_url)
        embed.colour = discord.Colour.gold()
        embed.timestamp = datetime.utcnow()
        embed.set_footer(text=f'Case #{case_id}')
        case_msg = await chan.send(embed=embed)

        doc = {'case_id': case_id, 'case_msg_id': case_msg.id, 'muted_user_id': member.id, 'mod_id': ctx.author.id, 'timestamp': embed.timestamp, 'reason': reason}
        await self.bot.db.mutes.insert_one(doc)
        await ctx.send(f'Muted `{member}` successfully!')
        self.mutes[case_id] = doc

    @commands.has_role(STAFF_ROLE)
    @commands.command()
    async def unmute(self, ctx, member: discord.Member, *, reason=''):
        if not any(self.muted_role == role.id for role in member.roles):
            await ctx.send('That member is not muted you dumdum')
            return

        chan = self.bot.get_channel(self.config['channels']['kicks_bans_mutes'])
        await member.remove_roles(ctx.guild.get_role(self.muted_role), reason=reason)

        result = await self.bot.db.mutes.find_one_and_delete({'muted_user_id': member.id})
        if result:
            case_id = result['case_id']
            try:
                del self.mutes[case_id]
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
        await chan.send(embed=embed)
        await ctx.send(f'Unmuted `{member}` successfully!')

    @commands.has_role(STAFF_ROLE)
    @commands.command()
    async def reason(self, ctx, case_id: int, *, reason):
        case = await self.bot.db.mutes.find_one({'case_id': case_id})
        if not case:
            await ctx.send(f'Case #{case_id} not found!')
            return

        chan = self.bot.get_channel(self.config['channels']['kicks_bans_mutes'])
        msg = await chan.fetch_message(case['case_msg_id'])
        member = ctx.guild.get_member(case['muted_user_id'])
        await self.bot.db.mutes.update_one({'case_id': case_id}, {'$set': {'reason': reason}})
        embed = discord.Embed()
        embed.set_author(name='Member muted', icon_url=member.avatar_url)
        embed.add_field(name='User', value=member, inline=False)
        embed.add_field(name='Moderator', value=ctx.author, inline=False)
        embed.add_field(name='Reason', value=reason, inline=False)
        embed.set_thumbnail(url=member.avatar_url)
        embed.colour = discord.Colour.gold()
        embed.timestamp = case['timestamp']
        embed.set_footer(text=f'Case #{case_id}')

        await msg.edit(embed=embed)
        await ctx.send(f'Reason changed for case #{case_id}')


def setup(bot):
    bot.add_cog(Mod(bot))
