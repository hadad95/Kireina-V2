from datetime import datetime
import random
import discord
from discord.ext import commands

class Logger(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = bot.config

    @commands.Cog.listener()
    async def on_member_join(self, member):
        welcome = self.bot.get_channel(self.config['channels']['welcome'])
        await welcome.send(f'Welcome to Hearts, {member.mention}! We\'re super happy to have you. Make sure you look at RULES_CHANNEL_MENTION and ANNOUNCEMENTS_CHANNEL_MENTION to stay up to date on things! {random.choices(member.guild.emojis)}')
        embed = discord.Embed()
        embed.set_author(name='Member joined', icon_url=member.avatar_url)
        embed.colour = discord.Colour.green()
        embed.add_field(name='User', value=f'{member.mention} ({member})', inline=False)
        embed.set_thumbnail(url=member.avatar_url)
        embed.timestamp = datetime.utcnow()
        chan = self.bot.get_channel(self.config['channels']['joins_leaves'])
        await chan.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        kicks = self.bot.get_channel(self.config['channels']['kicks_bans_mutes'])
        leaves = self.bot.get_channel(self.config['channels']['joins_leaves'])
        entries = await member.guild.audit_logs(limit=1, action=discord.AuditLogAction.kick).flatten()
        # member got kicked
        if len(entries) == 1 and entries[0].target.id == member.id and (datetime.utcnow() - entries[0].created_at).total_seconds() <= 2:
            embed = discord.Embed()
            embed.set_author(name='Member kicked', icon_url=member.avatar_url)
            embed.add_field(name='User', value=f'{member.mention} ({member})', inline=False)
            embed.add_field(name='Moderator', value=str(entries[0].user), inline=False)
            embed.add_field(name='Reason', value=entries[0].reason if entries[0].reason else 'None', inline=False)
            embed.colour = discord.Colour.gold()
            embed.set_thumbnail(url=member.avatar_url)
            embed.timestamp = datetime.utcnow()
            await kicks.send(embed=embed)
        # member normally left
        else:
            if any(self.config['roles']['muted_role'] == role.id for role in member.roles):
                await member.ban(reason='Auto-ban for mute evasion!')

        embed2 = discord.Embed()
        embed2.set_author(name='Member left', icon_url=member.avatar_url)
        embed2.add_field(name='User', value=f'{member.mention} ({member})', inline=False)
        embed2.set_thumbnail(url=member.avatar_url)
        embed2.timestamp = datetime.utcnow()
        await leaves.send(embed=embed2)

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        bans = self.bot.get_channel(self.config['channels']['kicks_bans_mutes'])
        embed = discord.Embed()
        entries = await guild.audit_logs(limit=1, action=discord.AuditLogAction.ban).flatten()
        embed.set_author(name='Member banned', icon_url=user.avatar_url)
        embed.set_thumbnail(url=user.avatar_url)
        embed.add_field(name='User', value=str(user), inline=False)
        embed.add_field(name='Moderator', value=str(entries[0].user), inline=False)
        embed.add_field(name='Reason', value=entries[0].reason if entries[0].reason else 'None', inline=False)
        embed.colour = discord.Colour.red()
        await bans.send(embed=embed)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return

        chan = self.bot.get_channel(self.config['channels']['vc_join'])
        embed = discord.Embed()
        embed.add_field(name='User', value=f'{member.mention} ({member})', inline=False)
        embed.set_thumbnail(url=member.avatar_url)
        if before.channel is None and after.channel is not None:
            embed.title = 'Member joined voice channel'
            embed.add_field(name='Channel', value=after.channel.name, inline=False)
        elif before.channel is not None and after.channel is not None and before.channel is not after.channel:
            embed.title = 'Member switched voice channels'
            embed.add_field(name='Channels', value=f'From {before.channel.name} to {after.channel.name}', inline=False)
        else:
            return
        #elif before.channel is not None and after.channel is None:
            #await chan.send(f'{member.display_name} left {before.channel.name}')

        await chan.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, msg):
        if msg.channel.type != discord.ChannelType.text:
            return

        await self.bot.db.messages.insert_one({'msg_id': msg.id, 'content': msg.content, 'author_id': msg.author.id, 'channel_id': msg.channel.id})

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot:
            return

        chan = self.bot.get_channel(self.config['channels']['edits_deletes'])
        embed = discord.Embed()
        embed.set_author(name=f'{before.author} edited a message', icon_url=before.author.avatar_url)
        embed.set_thumbnail(url=before.author.avatar_url)
        embed.add_field(name='Channel', value=before.channel.mention, inline=False)
        embed.add_field(name='Before', value=before.content, inline=False)
        embed.add_field(name='After', value=after.content, inline=False)
        embed.timestamp = datetime.utcnow()
        await chan.send(embed=embed)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload):
        message = None

        if payload.cached_message:
            message = payload.cached_message
        elif self.config['messages'][payload.message_id] and self.config['messages'][payload.message_id].channel.id == payload.channel_id:
            message = self.config['messages'][payload.message_id]

        if message and message.author.bot:
            return

        chan = self.bot.get_channel(self.config['channels']['edits_deletes'])
        embed = discord.Embed()

        if message:
            embed.set_author(name=f'{message.author} deleted a message', icon_url=message.author.avatar_url)
            embed.set_thumbnail(url=message.author.avatar_url)
            embed.add_field(name='Channel', value=message.channel.mention, inline=False)
            embed.add_field(name='Content', value=message.content if message.content else 'None', inline=False)
        else:
            embed.set_author(name='Menssage deleted')
            embed.add_field(name='Channel', value=message.channel.mention, inline=False)
            embed.add_field(name='Content', value='None', inline=False)

        embed.timestamp = datetime.utcnow()
        await chan.send(embed=embed)


def setup(bot):
    bot.add_cog(Logger(bot))
