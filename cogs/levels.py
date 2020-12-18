import config
import discord
from discord.ext import commands, tasks
from pymongo import ReturnDocument, DESCENDING
import random
import time

class Levels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.timestamps = {}
        self.vc_xp_loop.start()
    
    @staticmethod
    def xp_from_level(level):
        return (5/6) * level * (2 * level ** 2 + 27 * level + 91)
    
    @staticmethod
    def level_from_xp(xp):
        level = 0
        while xp >= Levels.xp_from_level(level + 1):
            level += 1
        
        return level
    
    @tasks.loop(seconds=60)
    async def vc_xp_loop(self):
        guild = self.bot.get_guild(config.GUILD)
        for vc in guild.voice_channels:
            for member in vc.members:
                if member.voice and not member.voice.afk and len(member.voice.channel.members) > 1:
                    await self.add_xp(member, None)
    
    async def level_up(self, member, level, channel):
        if channel:
            await channel.send(f'Congratulations {member.mention}! You are now level {level} :tada:<a:bongohrt:687814808028184601>')
        
        if level in config.LEVELS_ROLES:
            await member.add_roles(discord.Object(id=config.LEVELS_ROLES[level]), reason='Role reward for leveling up.')
    
    async def add_xp(self, member, channel):
        # do db call to get current xp
        gain = random.randint(config.LEVELS_MIN_XP, config.LEVELS_MAX_XP)
        result = await self.bot.db.levels.find_one_and_update({'user_id': member.id}, {'$inc': {'xp': gain}}, upsert=True, return_document=ReturnDocument.AFTER)
        #result = await self.bot.db.levels.find_one({'user_id': member.id})
        new_xp = result['xp']
        old_xp = new_xp - gain
        old_level = Levels.level_from_xp(old_xp)
        new_level = Levels.level_from_xp(new_xp)
        if new_level > old_level:
            await self.level_up(member, new_level, channel)
    
    @commands.Cog.listener()
    async def on_message(self, msg):
        if msg.author.bot:
            return
        
        current_time = time.time()
        if msg.author.id in self.timestamps:
            if current_time >= self.timestamps[msg.author.id] + config.LEVELS_TIMEOUT:
                await self.add_xp(msg.author, msg.channel)
                self.timestamps[msg.author.id] = current_time
        else:
            await self.add_xp(msg.author, msg.channel)
            self.timestamps[msg.author.id] = current_time

    @commands.command()
    async def xp(self, ctx, member: discord.Member=None):
        target = member if member else ctx.author
        result = await self.bot.db.levels.find_one({'user_id': target.id})
        if not result:
            await ctx.send("That member doesn't have any XP <a:sadhrt:692106232999182397>")
            return
        
        total_xp = result['xp']
        level = Levels.level_from_xp(total_xp)
        level_xp = int(Levels.xp_from_level(level + 1))
        embed = discord.Embed()
        embed.colour = discord.Colour(0xEA0A8E)
        embed.set_author(name=str(target), icon_url=target.avatar_url)
        embed.set_thumbnail(url=target.avatar_url)
        embed.add_field(name='Level', value=str(level), inline=False)
        embed.add_field(name='XP', value=f'{total_xp}/{level_xp}', inline=False)
        await ctx.send('', embed=embed)
    
    @commands.command()
    async def leaderboard(self, ctx):
        txt = 'Top 10 users in the server\n```less\n'
        i = 1
        async for doc in self.bot.db.levels.find(sort=[('xp', DESCENDING)], limit=1):
            user_id = doc['user_id']
            user = self.bot.get_user(user_id)
            xp = doc['xp']
            level = Levels.level_from_xp(xp)
            #next_level_xp = Levels.xp_from_level(level + 1)
            txt += f'{i}. {user} ♥ {xp}'
            i += 1
        
        txt += '```'
        await ctx.send(txt)
        

def setup(bot):
    bot.add_cog(Levels(bot))