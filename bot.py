import os
import sys
import logging
import json
import math
import random
import ast
import aiohttp
import asyncio
import async_timeout
import ssl
import string
from aiotg import Bot, chat

greeting = """
這是 Rex 的網易雲音樂解析 bot !
是基於[網易雲音樂解析]({}})的服務。
使用方式參見 /help
""".format(os.environ.get('HOST'))

help = """
輸入 `音樂網址 .音質` 來解析
例如 : `http://music.163.com/#/m/song?id=31587429 .320`
或 `音樂ID .音質`
例如 : `31587429 .320`
"""

not_found = """
找不到資料 :/
"""
bye = """
掰掰! 😢
"""

global host
global api
host = os.environ.get('HOST')
api = os.environ.get('API')
logger = logging.getLogger(os.environ.get('BOT_NAME_EN'))
logChannelID = os.environ.get('LOGCHANNELID')
bot = Bot(
    api_token=os.environ.get('TOKEN'),
    name=os.environ.get('BOT_NAME_TW'),
)

async def getAdmin(ID=logChannelID):
    raw = ast.literal_eval(str(await bot.api_call("getChatAdministrators",chat_id=ID)))
    adminDict = [{
        'id':i['user']['id'],
        'username':i['user']['username'],
        'first_name':i['user']['first_name'],
        'last_name':i['user']['last_name'] if 'last_name' in i['user'] else ''
    } for i in raw['result']]
    return adminDict

async def isAdmin(ID):
    adminList = await getAdmin()

    for i in adminList:
        if i['id'] == ID:
            return True
    return False

async def fetch(session, url):
    with async_timeout.timeout(10):
        async with session.get(url) as response:
            return await response.text()

async def log(string):
    logger.info(string)
    await bot.send_message(logChannelID, string)
    return

def idGen(sizeSettings=random.randint(5,64), charSettings='ad'):
    chars = ''
    if 'a' in charSettings:
        chars += string.ascii_letters
    if 'l' in charSettings:
        chars += string.ascii_lowercase
    if 'L' in charSettings:
        chars += string.ascii_uppercase
    if 'd' in charSettings:
        chars += string.digits
    if 'm' in charSettings:
        chars += string.punctuation

    sizeSettings = str(sizeSettings)
    if sizeSettings.isnumeric:
        size = int(sizeSettings)
    elif ',' in sizeSettings:
        sizeRange1, sizeRange2 = sizeSettings.split(',')
        size = random.randint(sizeRange1, sizeRange2)
    
    return ''.join(random.choice(chars) for _ in range(size))

async def getJSON(URL, verify_ssl=False):
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(verify_ssl=verify_ssl)) as session:
        data = await fetch(session, URL)
        return data

async def search_tracks(ID, bitrate):
    global host
    global api
    bitrate = str(int(bitrate)*1000)

    musicJson = json.loads(await getJSON(host + api +'/'+ ID +'/'+ bitrate))
    musicJson.setdefault('URL', host +'/'+ ID +'/'+ bitrate +'/'+ musicJson['sign'])
    return musicJson

def getArtist(musicJson):
    musicArtistMD = ''
    musicArtistText = ''
    
    for i in musicJson['song']['artist']:
        musicArtistMD += ('[' + i['name']+ ']' + '(http://music.163.com/#/artist?id=' + str(i['id']) + ') / ')
        musicArtistText += i['name'] + ' / '
    return {'markdown' : musicArtistMD[:-3], 'text' : musicArtistText[:-3]}

def inlineRes(music, caption=''):
    results = {
        'type': 'audio',
        'id': idGen(),
        'title' : music['song']['name'],
        'audio_url': music['URL'],
        'performer': getArtist(music)['text'],
        'caption': caption
    }
    return results

def getMusicId(musicInfo):
    if musicInfo.isnumeric():
        return musicInfo
    elif "//music.163.com/song/" in musicInfo:
        return musicInfo.split('//music.163.com/song/')[1].split('/')[0]
    elif "song?id=" in musicInfo:
        return ''.join(i for i in musicInfo.split('id=')[1] if i.isdigit())
    else:
        return 'ERROR'

@bot.command(r'/admin')
async def admin(chat, match):
    if not await isAdmin(chat.sender['id']):
        await log("{} 查詢了管理員名單，遭到拒絕。".format(chat.sender))
        await chat.send_text("存取遭拒。")
        return
    else:
        await log("{} 查詢了管理員名單".format(chat.sender))
        raw = await getAdmin()
        adminStr = ''.join(i['first_name']+' '+i['last_name']+'\n' for i in raw)
        await chat.send_text(adminStr)
        return

@bot.default
async def default(chat, message):
    info = message['text'].split(' .')

    if len(info) != 2:
        musicInfo, bitrate = info[0], ''
    else:
        musicInfo, bitrate = info

    if bitrate not in ['128', '192', '320']:
        chat.send_text('音質錯誤!將音質設為 320kbps。')
        await log("{} 輸入了錯誤的音質。".format(chat.sender))
        bitrate = '320'

    musicId = getMusicId(musicInfo)
    if not musicId.isnumeric():
        chat.send_text('輸入錯誤，無法解析!')
        await log("{} 的查詢發生了未知的錯誤。".format(chat.sender))
        return

    musicJson = await search_tracks(musicId, bitrate)
    musicArtist = getArtist(musicJson)
    musicInfoMD = "曲名:{}\n歌手:{}\n\n[解析網址]({})".format(musicJson['song']['name'], musicArtist['markdown'], musicJson['URL'])

    await log("{} 查詢了 {}kbps 的 {} - {}".format(chat.sender, bitrate, musicArtist['text'], musicJson['song']['name']))

    await chat.reply(musicInfoMD, parse_mode='Markdown')
    await chat.send_audio(audio=musicJson['URL'], title=musicJson['song']['name'], performer=musicArtist['text'])
    return

@bot.inline
async def inline(iq):
    if not iq.query:
        return await iq.answer([])
    
    info = iq.query.split(' .')
    if len(info) != 2:
        musicInfo, bitrate = info[0], ''
    else:
        musicInfo, bitrate = info

    if bitrate not in ['128', '192', '320']:
        await log("[inline] {} 輸入了錯誤的音質。".format(iq.sender))
        bitrate = '320'

    musicId = getMusicId(musicInfo)
    if not musicId.isnumeric:
        await log("[inline] {} 的查詢發生了未知的錯誤。".format(iq.sender))
        await iq.answer([])
        return

    musicJson = await search_tracks(musicId, bitrate)
    musicArtist = getArtist(musicJson)

    await iq.answer([inlineRes(musicJson)])
    await log("[inline] {} 查詢了 {}kbps 的 {} - {}".format(iq.sender, bitrate, musicArtist['text'], musicJson['song']['name']))
    return

@bot.command(r'/start')
async def start(chat, match):
    await chat.send_text(greeting, parse_mode='Markdown')


@bot.command(r'/stop')
async def stop(chat, match):
    tuid = chat.sender["id"]
    await db.users.remove({ "id": tuid })

    await log("{} 退出了".format(chat.sender))
    await chat.send_text(bye, parse_mode='Markdown')


@bot.command(r'/help')
async def usage(chat, match):
    return await chat.send_text(help, parse_mode='Markdown')