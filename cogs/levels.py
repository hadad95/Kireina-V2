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
        return int((5/6) * level * (2 * level ** 2 + 27 * level + 91))
    
    @staticmethod
    def level_from_xp(xp):
        level = 0
        while xp >= Levels.xp_from_level(level + 1):
            level += 1
        
        return level
    
    @staticmethod
    async def fix_roles(member, level):
        add =[]
        remove = []
        for i in config.LEVELS_ROLES:
            role_id = config.LEVELS_ROLES[i]
            if i <= level and not any(role_id == role.id for role in member.roles): # give missing roles
                #await member.add_roles(discord.Object(id=role_id), reason='Level role rewarded.')
                add.append(discord.Object(id=role_id))
            elif i > level and any(role_id == role.id for role in member.roles): # remove higher level roles
                #await member.remove_roles(discord.Object(id=role_id), reason='Level role revoked.')
                remove.append(discord.Object(id=role_id))
        
        if add:
            await member.add_roles(*add, reason='Level role rewarded.')
        
        if remove:
            await member.remove_roles(*remove, reason='Level role revoked.')
    
    @tasks.loop(seconds=60)
    async def vc_xp_loop(self):
        guild = self.bot.get_guild(config.GUILD)
        for vc in guild.voice_channels:
            for member in vc.members:
                if member.voice and not member.voice.afk and not member.voice.mute and not member.voice.self_mute and len(member.voice.channel.members) > 1:
                    await self.add_xp(member, None, vc=True)
    
    @vc_xp_loop.before_loop
    async def before_vc_loop(self):
        await self.bot.wait_until_ready()
    
    async def level_up(self, member, level, channel):
        if channel:
            await channel.send(f'Congratulations {member.mention}! You are now level {level} :tada:<a:bongohrt:687814808028184601>')
        
        if level in config.LEVELS_ROLES:
            await member.add_roles(discord.Object(id=config.LEVELS_ROLES[level]), reason='Level role rewarded.')
    
    async def add_xp(self, member, channel, vc=False):
        # do db call to get current xp
        gain = random.randint(config.LEVELS_MIN_XP, config.LEVELS_MAX_XP)
        if vc:
            gain = gain // 2
        
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
        if msg.author.bot or (msg.channel.id in config.LEVELS_IGNORED_CHANNELS) or any(role.id == config.ROLE_MUTED for role in msg.author.roles):
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
        """ Check your XP, level, and leaderboard ranking """
        target = member if member else ctx.author
        result = await self.bot.db.levels.find_one({'user_id': target.id})
        if not result:
            await ctx.send("That member doesn't have any XP <a:sadhrt:692106232999182397>")
            return
        
        total_xp = result['xp']
        level = Levels.level_from_xp(total_xp)
        level_xp = Levels.xp_from_level(level + 1)
        rank = await self.bot.db.levels.count_documents({'xp': {'$gt': total_xp}}) + 1
        embed = discord.Embed()
        embed.colour = discord.Colour(0xEA0A8E)
        embed.set_author(name=str(target), icon_url=target.avatar_url)
        embed.set_thumbnail(url=target.avatar_url)
        embed.add_field(name='Level', value=str(level), inline=False)
        embed.add_field(name='XP', value=f'{total_xp}/{level_xp}', inline=False)
        embed.add_field(name='Rank', value=str(rank), inline=False)
        await ctx.send('', embed=embed)
    
    @commands.command(aliases=['lb'])
    async def leaderboard(self, ctx):
        """ View the top 10 users in the server """
        txt = 'Top 10 users in the server\n```less\n'
        rows = []
        i = 1
        async for doc in self.bot.db.levels.find(sort=[('xp', DESCENDING)], limit=10):
            user_id = doc['user_id']
            user = self.bot.get_user(user_id)
            xp = doc['xp']
            level = Levels.level_from_xp(xp)
            #next_level_xp = Levels.xp_from_level(level + 1)
            #txt += f'{i}. {user} ♥ {xp}\n'
            rows.append([f'{i}. {user}', ' ♥', f'Lvl. {level}', f'(XP: {xp})'])
            i += 1
        
        widths = [max(map(len, col)) for col in zip(*rows)]
        for row in rows:
            txt += "  ".join((val.ljust(width) for val, width in zip(row, widths))) + '\n'
        
        txt += '```'
        await ctx.send(txt)
    
    @commands.command()
    @commands.has_any_role(*config.ROLE_STAFF)
    async def setlevel(self, ctx, member: discord.Member, level: int):
        """ Set a user's level """
        xp = Levels.xp_from_level(level)
        await self.bot.db.levels.update_one({'user_id': member.id}, {'$set': {'xp': xp}}, upsert=True)
        await Levels.fix_roles(member, level)
        await ctx.send(f"User {member.mention}'s level has been set to `{level}` <a:bongohrt:687814808028184601>")
        

def setup(bot):
    bot.add_cog(Levels(bot))