import discord
from discord.ext import commands
import config

STAR = '\u2b50'    # The star emoji
MIN_REACTIONS = 1

class Starboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        await self.reaction_action('add', payload)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        await self.reaction_action('remove', payload)

    async def add_entry(self, channel_id, msg, count):
        print("Creating embed")
        embed = discord.Embed()
        embed.set_author(name=str(msg.author), icon_url=msg.author.avatar_url)
        embed.set_footer(text=f'ID: {msg.id}')
        embed.timestamp = msg.created_at
        embed.description = msg.content
        if msg.attachments:
            file = msg.attachments[0]
            if file.url.lower().endswith(('png', 'jpeg', 'jpg', 'gif', 'webp')):
                embed.set_image(url=file.url)
            else:
                embed.add_field(name='Attachment', value=f'[{file.filename}]({file.url})', inline=False)
        
        embed.add_field(name='Jump to message', value=f'[Jump](https://discordapp.com/channels/{msg.guild.id}/{msg.channel.id}/{msg.id})', inline=False)
        print("Sending message")
        star_msg = await self.bot.get_channel(config.CHAN_STARBOARD).send(f'{STAR} {count} {msg.channel.mention}'. embed=embed)
        await self.bot.db.starboard.insert_one({
            'channel_id': channel_id,
            'message_id': msg.id,
            'author_id': msg.author.id,
            'star_message_id': star_msg.id
        })

    async def remove_entry(self, channel_id, msg, star_message_id):
        await self.bot.db.starboard.delete_one({'channel_id': channel_id, 'message_id': msg.id, 'star_message_id': star_message_id})
        o = discord.Object(id=star_message_id + 1)
        star_msg = await self.bot.get_channel(config.CHAN_STARBOARD).history(limit=1, before=o).next()
        await star_msg.delete()
    
    async def update_entry(self, msg, count):
        o = discord.Object(id=star_message_id + 1)
        star_msg = await self.bot.get_channel(config.CHAN_STARBOARD).history(limit=1, before=o).next()
        await star_msg.edit(content=f'{STAR} {count} {msg.channel.mention}')

    async def reaction_action(self, action, payload):
        if str(payload.emoji) != STAR:
            return
        
        channel = self.bot.get_channel(payload.channel_id)
        if not isinstance(channel, discord.TextChannel):
            return
        
        o = discord.Object(id=payload.message_id + 1)
        msg = await channel.history(limit=1, before=o).next()
        
        reaction = discord.utils.find(lambda e: str(e) == STAR, msg.reactions)
        count = 0
        if reaction:
            count = reaction.count
            owner_reacted = discord.utils.get(await reaction.users().flatten(), id=msg.author.id)
            if owner_reacted:
                count -= 1

        if action == 'add':
            print('Entered "add"')
            if count < MIN_REACTIONS:
                return
            
            entry = await self.bot.db.starboard.find_one({'channel_id': payload.channel_id, 'message_id': msg.id})
            if not entry:
                await self.add_entry(payload.channel_id, msg, count)
            else:
                await self.update_entry(msg, count)
                
        elif action == 'remove':
            print('Entered "remove"')
            entry = await self.bot.db.starboard.find_one({'channel_id': payload.channel_id, 'message_id': msg.id})
            if not entry and count >= MIN_REACTIONS:
                await self.add_entry(payload.channel_id, msg, count)
            elif entry:
                if count < MIN_REACTIONS:
                    await self.remove_entry(payload.channel_id, msg, entry['star_message_id'])
                else:
                    await self.update_entry(msg, count)

def setup(bot):
    bot.add_cog(Starboard(bot))
