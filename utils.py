from enum import Enum, unique
from datetime import datetime, timedelta
import re
from pymongo import ReturnDocument
import discord

@unique
class CaseType(Enum):
    MUTE = 1
    UNMUTE = 2
    KICK = 3
    BAN = 4


regex_time = re.compile(r'^(\d+)([sSmMhHdDwW])\s', re.IGNORECASE)

def create_modlog_embed(case_type, case_id, member, moderator, timestamp, reason, unmute_at):
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

    embed.add_field(name='User', value=f'{member.mention} ({str(member)})', inline=False)
    embed.add_field(name='Moderator', value=str(moderator), inline=False)
    embed.add_field(name='User ID', value=str(member.id), inline=False)
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

async def create_db_case(db, case_id, case_type, case_msg_id, member, moderator, timestamp, reason, unmute_at):
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
    if case_type == CaseType.MUTE and unmute_at is not None:
        obj = {
            'case_id': case_id,
            'user_id': member.id,
            'unmute_at': unmute_at
        }
        await db.mutes.insert_one(obj)

    return doc

async def get_db_case(db, case_id):
    return await db.modlog.find_one({'case_id': case_id})

async def update_db_case_reason(db, case_id, reason, unmute_at):
    modlog = await db.modlog.find_one_and_update({'case_id': case_id}, {'$set': {'reason': reason}}, return_document=ReturnDocument.AFTER)
    if modlog['case_type'] == CaseType.MUTE.value and unmute_at is not None:
        await db.mutes.update_one({'case_id': case_id}, {'$set': {'user_id': modlog['user_id'], 'unmute_at': unmute_at}}, upsert=True)

async def get_all_db_mutes(db):
    result = await db.mutes.find().to_list(length=None)
    return result

async def remove_db_mute(db, user_id):
    await db.mutes.delete_many({'user_id': user_id})

async def update_db_roles(db, user_id, roles_ids):
    await db.roles.update_one({'user_id': user_id}, {'$set': {'roles': roles_ids}}, upsert=True)

async def get_db_roles(db, user_id):
    result = await db.roles.find_one({'user_id': user_id});
    if result:
        return result['roles']
    else:
        return None;

def parse_timedelta(reason):
    if not reason:
        return None

    result = regex_time.search(reason)
    if not result:
        return None

    time = None
    if result[2] == 's':
        time = timedelta(seconds=int(result[1]))
    elif result[2] == 'm':
        time = timedelta(minutes=int(result[1]))
    elif result[2] == 'y':
        time = timedelta(hours=int(result[1]))
    elif result[2] == 'd':
        time = timedelta(days=int(result[1]))
    elif result[2] == 'w':
        time = timedelta(weeks=int(result[1]))
    
    reason = reason[len(result[0]):]
    return time, reason
