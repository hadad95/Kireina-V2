from datetime import datetime
import random
import discord
from discord.ext import commands
import re

class Logger(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = bot.config
        self.inv_exp = re.compile(r'discord(?:app\.com\/invite|\.gg)\/([a-z0-9]{1,16})', re.IGNORECASE)

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
        if msg.channel.type != discord.ChannelType.text or msg.author.bot:
            return

        await self.bot.db.messages.insert_one({'msg_id': msg.id, 'content': msg.content, 'author_id': msg.author.id, 'channel_id': msg.channel.id})

        # check for invites
        matches = self.inv_exp.findall(msg.content)
        if matches:
            guild_invites = await msg.guild.invites()
            for match in matches:
                if not any(match == inv.code for inv in guild_invites):
                    if discord.utils.get(msg.author.roles, id=self.config['roles']['staff']) is None and msg.channel.id != self.config['channels']['promotions']:
                        await msg.delete()

    """
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
    """

    # gotta remember there's no payload.channel_id in this version
    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload):
        channel_id = int(payload.data['channel_id'])
        msg = await self.bot.db.messages.find_one({'msg_id': payload.message_id, 'channel_id': channel_id})
        if not msg:
            return

        before = msg['content'] if msg['content'] else 'None'
        content = payload.data.get('content')
        after = str(content)
        raw_author = payload.data.get('author')
        author = self.bot.get_user(int(raw_author['id'])) if raw_author else None
        channel = self.bot.get_channel(channel_id)

        chan = self.bot.get_channel(self.config['channels']['edits_deletes'])
        embed = discord.Embed()
        if author:
            embed.set_author(name=f'{author} edited a message', icon_url=author.avatar_url)
            embed.set_thumbnail(url=author.avatar_url)
        else:
            embed.set_author(name='Unknown edited a message')

        embed.add_field(name='Channel', value=channel.mention, inline=False)
        embed.add_field(name='Before', value=before, inline=False)
        embed.add_field(name='After', value=after, inline=False)
        embed.timestamp = datetime.utcnow()
        await chan.send(embed=embed)
        await self.bot.db.messages.update_one({'msg_id': payload.message_id, 'channel_id': channel_id}, {'$set': {'content': content if content else ''}})

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload):
        msg = await self.bot.db.messages.find_one({'msg_id': payload.message_id, 'channel_id': payload.channel_id})
        if not msg:
            return

        author = self.bot.get_user(msg['author_id'])
        channel = self.bot.get_channel(payload.channel_id)
        chan = self.bot.get_channel(self.config['channels']['edits_deletes'])
        embed = discord.Embed()
        embed.set_author(name=f'{author} deleted a message', icon_url=author.avatar_url)
        embed.set_thumbnail(url=author.avatar_url)
        embed.add_field(name='Channel', value=channel.mention, inline=False)
        embed.add_field(name='Content', value=msg['content'] if msg['content'] else 'None', inline=False)
        embed.timestamp = datetime.utcnow()
        await chan.send(embed=embed)
        await self.bot.db.messages.delete_many({'msg_id': payload.message_id, 'channel_id': payload.channel_id})


def setup(bot):
    bot.add_cog(Logger(bot))
