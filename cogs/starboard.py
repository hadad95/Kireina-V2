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
    
    async def get_entry(self, channel_id, message_id):
        pass

    async def add_entry(self, channel_id, starred_message_id, author_id, count, entry_message_id):
        pass

    async def reaction_action(self, action, payload):
        if str(payload.emoji) != EMOJI:
            return
        
        channel = self.bot.get_channel(payload.channel_id)
        if not isinstance(channel, discord.TextChannel):
            return
        
        o = discord.Object(id=payload.message_id + 1)
        msg = await channel.history(limit=1, before=o).next()
        
        reaction = discord.utils.find(lambda e: str(e) == STAR, message.reactions)
        count = reaction.count
        if owner_reacted = discord.utils.get(await reaction.users().flatten(), id=payload.user_id):
            count -= 1

        if action == 'add':
            if count < MIN_REACTIONS:
                return
            
            entry = self.bot.db.starboard.find_one({'channel_id': payload.channel_id, 'starred_message_id': msg.id})
            if not entry:
                embed = discord.Embed()
                embed.set_author(name=str(msg.author), icon_url=msg.author.avatar_url)
                embed.set_footer(text=f'ID: {msg.id}')
                embed.timestamp = msg.created_at
                embed.content = msg.content
                if msg.attachments:
                    file = msg.attachments[0]
                    if file.url.lower().endswwith(('png', 'jpeg', 'jpg', 'gif', 'webp')):
                        embed.set_image(url=file.url)
                    else:
                        embed.add_field(name='Attachment', value=f'[{file.filename}]({file.url})', inline=False)
                
                embed.add_field(name='Jump to message', value=f'[Jump](https://discordapp.com/channels/{msg.guild.id}/{msg.channel.id}/{msg.id})', inline=False)
                await self.bot.get_channel(config.CHAN_STARBOARD).send(embed=embed)
                
        elif action == 'remove':
            pass

def setup(bot):
    bot.add_cog(Starboard(bot))
