from datetime import datetime, timedelta
import asyncio
import random
import re
import io
import discord
from discord.ext import commands
import config
import utils

class Logger(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.regex_inv = re.compile(r'discord(?:(app)?\.com\/invite|\.gg)\/([a-z0-9]{1,16})', re.IGNORECASE)
        with open('filtered_words.txt', 'r') as file:
            self.filtered_words = file.read().split('\n')

    @commands.Cog.listener()
    async def on_member_join(self, member):
        welcome = self.bot.get_channel(config.CHAN_WELCOME)
        await welcome.send(f'Welcome to Hearts, {member.mention}! We\'re super happy to have you. Make sure you look at <#499353290841128962> and <#477610336695091240> to stay up to date on things! {random.choice(member.guild.emojis)}')
        embed = discord.Embed()
        embed.set_author(name='Member joined', icon_url=member.avatar_url)
        embed.colour = discord.Colour.green()
        embed.description = f'{member.mention} ({member})'
        embed.set_thumbnail(url=member.avatar_url)
        embed.set_footer(text=f'ID: {member.id}')
        embed.timestamp = datetime.utcnow()
        chan = self.bot.get_channel(config.CHAN_JOINS_LEAVES)
        await chan.send(embed=embed)

        """Add roles from db"""
        roles = await utils.get_db_roles(self.bot.db, member.id)
        if not roles:
            return
        
        roles = [discord.Object(id=x) for x in roles]
        try:
            await member.add_roles(*roles)
        except:
            pass

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        await asyncio.sleep(2) # Added a delay because audit logs seem to be fucked sometimes
        kicks = self.bot.get_channel(config.CHAN_MODLOG)
        leaves = self.bot.get_channel(config.CHAN_JOINS_LEAVES)
        entries = await member.guild.audit_logs(limit=1, action=discord.AuditLogAction.kick).flatten()
        # member got kicked
        if len(entries) == 1 and entries[0].target.id == member.id and (datetime.utcnow() - entries[0].created_at).total_seconds() <= 2:
            await asyncio.sleep(2)
            mod = entries[0].user
            reason = entries[0].reason
            case_id = await utils.get_next_case_id(self.bot.db)
            if mod.id == self.bot.user.id:
                mod_cog = self.bot.get_cog('Mod')
                if mod_cog.last_kick_ctx  and mod_cog.last_kick_ctx.args[2].id == member.id:
                    member = mod_cog.last_kick_ctx.args[2]
                    mod = mod_cog.last_kick_ctx.author
                    mod_cog.last_kick_ctx = None

            timestamp = datetime.utcnow()
            embed = utils.create_modlog_embed(utils.CaseType.KICK, case_id, member, mod, timestamp, reason if reason else 'None', None)
            case_msg = await kicks.send(embed=embed)
            await utils.create_db_case(self.bot.db, case_id, utils.CaseType.KICK, case_msg.id, member, mod, timestamp, reason, None)
        # member normally left
        else:
            if any(config.ROLE_MUTED == role.id for role in member.roles):
                await member.ban(reason='Auto-ban for mute evasion!')

        embed2 = discord.Embed()
        embed2.set_author(name='Member left', icon_url=member.avatar_url)
        embed2.description = f'{member.mention} ({member})'
        embed2.set_thumbnail(url=member.avatar_url)
        embed2.set_footer(text=f'ID: {member.id}')
        embed2.timestamp = datetime.utcnow()
        await leaves.send(embed=embed2)

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        await asyncio.sleep(2) # Added a delay because audit logs seem to be fucked sometimes
        bans = self.bot.get_channel(config.CHAN_MODLOG)
        entries = await guild.audit_logs(limit=1, action=discord.AuditLogAction.ban).flatten()
        mod = entries[0].user
        reason = entries[0].reason
        if mod.id == self.bot.user.id:
            mod_cog = self.bot.get_cog('Mod')
            if mod_cog.last_ban_ctx:
                mod = mod_cog.last_ban_ctx.author
                mod_cog.last_ban_ctx = None
                """
                if mod_cog.last_ban_ctx.command.name == 'ban' and isinstance(mod_cog.last_ban_ctx.args[2], discord.User) and mod_cog.last_ban_ctx.args[2].id == user.id:
                    # potential redundant line
                    # user = mod_cog.last_ban_ctx.args[2]
                    mod = mod_cog.last_ban_ctx.author
                    mod_cog.last_ban_ctx = None
                elif mod_cog.last_ban_ctx.command.name == 'hackban' and mod_cog.last_ban_ctx.args[2] == user.id:
                    # potential redundant line
                    # user = self.bot.get_user(mod_cog.last_ban_ctx.args[2])
                    mod = mod_cog.last_ban_ctx.author
                    mod_cog.last_ban_ctx = None
                """

        case_id = await utils.get_next_case_id(self.bot.db)
        timestamp = datetime.utcnow()
        embed = utils.create_modlog_embed(utils.CaseType.BAN, case_id, user, mod, timestamp, reason if reason else 'None', None)
        case_msg = await bans.send(embed=embed)
        await utils.create_db_case(self.bot.db, case_id, utils.CaseType.BAN, case_msg.id, user, mod, timestamp, reason, None)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.bot:
            return
        
        before_muted = discord.utils.get(before.roles, id=config.ROLE_MUTED) is not None
        after_muted = discord.utils.get(after.roles, id=config.ROLE_MUTED) is not None
        entries = None
        if before_muted is not after_muted:
            await asyncio.sleep(2)
            entries = await before.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_role_update).flatten()
            mod_cog = self.bot.get_cog('Mod')
            mod = entries[0].user
            reason = entries[0].reason
            chan = self.bot.get_channel(config.CHAN_MODLOG)
            case_id = await utils.get_next_case_id(self.bot.db)
            timestamp = datetime.utcnow()
            unmute_at = None

            if mod.id == self.bot.user.id:
                mod_cog = self.bot.get_cog('Mod')
                if mod_cog.last_mute_unmute_ctx is not None and mod_cog.last_mute_unmute_ctx.args[2].id == before.id:
                    mod = mod_cog.last_mute_unmute_ctx.author
                    mod_cog.last_mute_unmute_ctx = None

            if not before_muted and after_muted:
                # user got muted
                time_added, reason = utils.parse_timedelta(reason)
                if time_added:
                    unmute_at = datetime.utcnow() + time_added
                    async with mod_cog.lock:
                        mod_cog.mutes[before.id] = unmute_at

                embed = utils.create_modlog_embed(utils.CaseType.MUTE, case_id, before, mod, timestamp, reason if reason else 'None', unmute_at)
                case_msg = await chan.send(embed=embed)
                await utils.create_db_case(self.bot.db, case_id, utils.CaseType.MUTE, case_msg.id, before, mod, timestamp, reason, unmute_at)
            elif before_muted and not after_muted:
                # user got unmuted
                embed = utils.create_modlog_embed(utils.CaseType.UNMUTE, case_id, before, mod, timestamp, reason if reason else 'None', None)
                case_msg = await chan.send(embed=embed)
                await utils.create_db_case(self.bot.db, case_id, utils.CaseType.UNMUTE, case_msg.id, before, mod, timestamp, reason, None)
        
        if len(before.roles) != len(after.roles):
            case = 1 if len(before.roles) < len(after.roles) else 2 # 1 = role added, 2 = role removed
            list_a = after.roles if case == 1 else before.roles # list_a holds the bigger number of roles
            list_b = after.roles if case == 2 else before.roles

            role = None
            for item in list_a:
                if item not in list_b:
                    role = item
            
            chan = self.bot.get_channel(config.CHAN_EDITS_DELETES)
            embed = discord.Embed()
            embed.set_author(name=str(before), icon_url=before.avatar_url)
            embed.set_thumbnail(url=before.avatar_url)
            embed.description = f'**{before.mention} was {"given" if case == 1 else "removed from"} the `{role.name}` role**'
            embed.timestamp = datetime.utcnow()
            embed.set_footer(text=f'ID: {before.id}')
            await chan.send(embed=embed)

            """Update user roles in db"""

            await utils.update_db_roles(self.bot.db, after.id, [x.id for x in after.roles if x.name != '@everyone'])

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return

        chan = self.bot.get_channel(config.CHAN_VC_LOGS)
        embed = discord.Embed()
        embed.add_field(name='User', value=f'{member.mention} ({member})', inline=False)
        embed.set_thumbnail(url=member.avatar_url)
        if before.channel is None and after.channel is not None:
            embed.title = 'Member joined voice channel'
            embed.add_field(name='Channel', value=after.channel.name, inline=False)
        elif before.channel is not None and after.channel is not None and before.channel is not after.channel:
            embed.title = 'Member switched voice channels'
            embed.add_field(name='Channels', value=f'From {before.channel.name} to {after.channel.name}', inline=False)
        elif before.channel is not None and after.channel is None:
            embed.title = 'Member left voice channel'
            embed.add_field(name='Channel', value=before.channel.name, inline=False)
        else: # return if it's none of the cases up above
            return

        await chan.send(embed=embed)
    
    async def submit_filtered_message(self, msg):
        embed = discord.Embed()
        embed.colour = discord.Colour.red()
        embed.title = 'Flagged message'
        embed.set_thumbnail(url=msg.author.avatar_url)
        embed.add_field(name='Member', value=f'{msg.author.mention} ({msg.author})', inline=False)
        embed.add_field(name='Channel', value=msg.channel.mention, inline=False)
        embed.add_field(name='Message', value=(msg.content[:1020] + '...') if len(msg.content) > 1024 else msg.content, inline=False)
        embed.timestamp = datetime.utcnow()
        embed.set_footer(text=f'Author ID: {msg.author.id}')
        channel = self.bot.get_channel(config.CHAN_FLAGGED_MSGS)
        await channel.send(embed=embed)
        await msg.delete()

    @commands.Cog.listener()
    async def on_message(self, msg):
        if msg.channel.type != discord.ChannelType.text or msg.author.bot:
            return

        await self.bot.db.messages.insert_one({'msg_id': msg.id, 'content': msg.content, 'author_id': msg.author.id, 'channel_id': msg.channel.id})

        # check for invites
        matches = self.regex_inv.findall(msg.content)
        if matches:
            guild_invites = await msg.guild.invites()
            for match in matches:
                if not any(inv.code in match for inv in guild_invites):
                    if discord.utils.find(lambda r: r.id in config.ROLE_STAFF, msg.author.roles) is None and msg.channel.id != config.CHAN_PROMOTIONS:
                        await msg.author.add_roles(discord.Object(id=config.ROLE_MUTED), reason='Auto-mute for sending ads')
                        await self.submit_filtered_message(msg)
        
        # check for filtered words
        content = msg.content.lower()
        for word in self.filtered_words:
            if word.lower() in content:
                await msg.author.add_roles(discord.Object(id=config.ROLE_MUTED), reason='Auto-mute for sending filtered messages')
                await self.submit_filtered_message(msg)


    # gotta remember there's no payload.channel_id in this version
    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload):
        channel_id = int(payload.data['channel_id'])
        if channel_id in config.BLACKLISTED_CHANS:
            return

        msg = await self.bot.db.messages.find_one({'msg_id': payload.message_id, 'channel_id': channel_id})
        if not msg:
            return

        before = msg['content'] if msg['content'] else 'None'
        content = payload.data.get('content')
        if content is None:
            return
        
        after = str(content)
        #raw_author = payload.data.get('author')
        #author = await self.bot.fetch_user(int(raw_author['id'])) if raw_author else None
        author = await self.bot.fetch_user(msg['author_id'])
        channel = self.bot.get_channel(channel_id)

        chan = self.bot.get_channel(config.CHAN_EDITS_DELETES)
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
        if payload.channel_id in config.BLACKLISTED_CHANS:
            return
        
        msg = await self.bot.db.messages.find_one({'msg_id': payload.message_id, 'channel_id': payload.channel_id})
        if not msg:
            return

        author = await self.bot.fetch_user(msg['author_id'])
        channel = self.bot.get_channel(payload.channel_id)
        chan = self.bot.get_channel(config.CHAN_EDITS_DELETES)
        content = msg['content'] if msg['content'] else 'None'
        actual_content = '[Content > 1024 characters]' if len(content) > 1024 else content
        file_upload = discord.File(io.StringIO(content), filename='message.txt') if len(content) > 1024 else None
        embed = discord.Embed()
        embed.set_author(name=f'Message deleted', icon_url=author.avatar_url)
        embed.set_thumbnail(url=author.avatar_url)
        embed.add_field(name='Author', value=f'{author.mention} ({author})', inline=False)
        embed.add_field(name='Channel', value=channel.mention, inline=False)
        embed.add_field(name='Content', value=actual_content, inline=False)
        embed.set_footer(text=f'Author ID: {author.id}')
        embed.timestamp = datetime.utcnow()
        await chan.send(embed=embed, file=file_upload)
        await self.bot.db.messages.delete_many({'msg_id': payload.message_id, 'channel_id': payload.channel_id})

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload):
        msg_ids = sorted(payload.message_ids)
        messages = await self.bot.db.messages.find({'msg_id': {'$in': msg_ids}, 'channel_id':payload.channel_id}).to_list(len(msg_ids))
        channel = self.bot.get_channel(payload.channel_id)
        chan = self.bot.get_channel(config.CHAN_EDITS_DELETES)
        result = ''
        for msg in messages:
            author = self.bot.get_user(msg['author_id'])
            if not author:
                author = await self.bot.fetch_user(msg['author_id'])

            result += f'{author} ({author.id})\n{msg["content"]}\n\n'

        await chan.send(f'Bulk-delete messages from {channel.mention}', file=discord.File(io.StringIO(result), filename='Bulklogs.txt'))
        await self.bot.db.messages.delete_many({'msg_id': {'$in': msg_ids}, 'channel_id':payload.channel_id})



def setup(bot):
    bot.add_cog(Logger(bot))
