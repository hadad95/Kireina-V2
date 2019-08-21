from enum import Enum, unique
from datetime import datetime
from pymongo import ReturnDocument
import discord

@unique
class CaseType(Enum):
    MUTE = 1
    UNMUTE = 2
    KICK = 3
    BAN = 4

def get_modlog_embed(case_type, case_id, member, moderator, timestamp=None, *, reason='None', unmute_at=None):
    embed = discord.Embed()
    if case_type == CaseType.MUTE:
        embed.set_author(name='Member muted', icon_url=member.avatar_url)
        embed.colour = discord.Colour.gold()
    elif case_type == CaseType.UNMUTE:
        embed.set_author(name='Member unmuted', icon_url=member.avatar_url)
        embed.colour = discord.Colour.green()
    elif case_type == CaseType.KICK:
        embed.set_author(name='Member kicked', icon_url=member.avatar_url)
        embed.colour = discord.Colour.gold()
    elif case_type == CaseType.BAN:
        embed.set_author(name='Member banned', icon_url=member.avatar_url)
        embed.colour = discord.Colour.red()

    embed.add_field(name='User', value=str(member), inline=False)
    embed.add_field(name='Moderator', value=str(moderator), inline=False)
    embed.add_field(name='Reason', value=reason if reason else 'None', inline=False)
    embed.set_thumbnail(url=member.avatar_url)
    if unmute_at:
        txt = unmute_at.strftime('%Y-%m-%d %H:%M UTC')
        embed.set_footer(text=f'Case #{case_id} - Unmute at: {txt}')
    else:
        embed.set_footer(text=f'Case #{case_id}')

    if timestamp:
        embed.timestamp = timestamp
    else:
        embed.timestamp = datetime.utcnow()

    return embed

async def get_next_case_id(db):
    result = await db.modlog.find_one_and_update({'_id': 'current_case'}, {'$inc': {'value': 1}}, return_document=ReturnDocument.AFTER)
    return result['value']

async def create_db_case(db, case_id, case_type, case_msg_id, member, moderator, timestamp=None, reason=''):
    doc = {
        'case_id': case_id,
        'case_type': case_type.value,
        'case_msg_id': case_msg_id,
        'user_id': member.id,
        'mod_id': moderator.id,
        'timestamp': timestamp if timestamp else datetime.utcnow(),
        'reason': reason
    }
    await db.modlog.insert_one(doc)
    return doc

async def get_db_case(db, case_id):
    return await db.modlog.find_one({'case_id': case_id})

async def update_db_case_reason(db, case_id, reason):
    await db.modlog.update_one({'case_id': case_id}, {'$set': {'reason': reason}})
