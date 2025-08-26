import discord
from discord.ext import commands
import functools
import json
import os
import asyncio
from aiohttp import web

WEB_PORT = 8080
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
chanell_id = 1
token = ""

JSON_FILE = "news.json"
messages_data = []
message_lock = asyncio.Lock()


class WebServer:
    def __init__(self):
        self.app = web.Application()
        self.setup_routes()
        self.runner = None
        self.site = None

    def setup_routes(self):
        self.app.router.add_get('/news', self.handle_get_messages)

    async def handle_get_messages(self, request):
        try:
            async with message_lock:
                with open(JSON_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)

            return web.json_response({
                'status': 'success',
                'count': len(data),
                'messages': data
            })
        except Exception as e:
            return web.json_response({
                'status': 'error',
                'message': str(e)
            }, status=500)

    async def start(self):
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, 'localhost', WEB_PORT)
        await self.site.start()

    async def stop(self):
        if self.runner:
            await self.runner.cleanup()


webserver = WebServer()


@bot.event
async def on_ready():
    await webserver.start()


async def save_message(message):
    try:
        message_data = {
            'id': message.id,
            'channel_id': message.channel.id,
            'channel_name': message.channel.name,
            'author_id': message.author.id,
            'author_name': str(message.author),
            'content': message.content,
            'timestamp': message.created_at.isoformat(),
            'attachments': [att.url for att in message.attachments],
            'embeds': len(message.embeds)
        }

        async with message_lock:
            if os.path.exists(JSON_FILE):
                with open(JSON_FILE, 'r', encoding='utf-8') as f:
                    try:
                        data = json.load(f)
                    except json.JSONDecodeError:
                        data = []
            else:
                data = []
            data.append(message_data)
            with open(JSON_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    except Exception as e:
        print(f"Ошибка при сохранении сообщения в JSON файле: {e}")


@bot.event
async def on_message(message):
    if message.channel.id == chanell_id:
        asyncio.create_task(save_message(message))


bot.run(token)
