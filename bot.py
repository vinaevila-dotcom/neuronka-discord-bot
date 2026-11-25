"""Discord-бот: отвечает, когда его упоминают. Модель — бесплатный API Pollinations."""

import os
from pathlib import Path

import aiohttp
import discord

BASE = Path(__file__).resolve().parent


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env(BASE / ".env")

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise SystemExit("Нет DISCORD_TOKEN. Положи токен в файл .env рядом с bot.py")

API_URL = os.getenv("AI_API_URL", "https://text.pollinations.ai/openai")
MODEL = os.getenv("AI_MODEL", "openai-fast")

SYSTEM_PROMPT = (
    "Ты дружелюбный чат-бот в сервере друзей. Отвечай по-русски, коротко и по делу, "
    "без лишних объяснений и без markdown-разметки. Если не знаешь — так и скажи. "
    "Максимум 800 символов."
)

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)


async def ask(message: str) -> str:
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message[:4000]},
        ],
    }
    timeout = aiohttp.ClientTimeout(total=45)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(API_URL, json=payload) as response:
            response.raise_for_status()
            data = await response.json()
    return data["choices"][0]["message"]["content"].strip()


def split(text: str, size: int = 1900):
    while text:
        if len(text) <= size:
            yield text
            break
        cut = text.rfind("\n", 0, size)
        if cut < size // 2:
            cut = size
        yield text[:cut].rstrip()
        text = text[cut:].lstrip()


@client.event
async def on_ready():
    print(f"Бот запущен: {client.user} (серверов: {len(client.guilds)})", flush=True)


@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    mentioned = client.user in message.mentions
    by_name = "нейронка" in message.content.lower()
    if not (mentioned or by_name):
        return

    print(f"Запрос от {message.author}: {message.content[:120]}", flush=True)

    question = message.content
    for mention in (f"<@{client.user.id}>", f"<@!{client.user.id}>"):
        question = question.replace(mention, "")
    for word in ("Нейронка", "нейронка", "НЕЙРОНКА"):
        question = question.replace(word, "")
    question = question.strip(" ,@:-") or "Привет! Что ты умеешь?"

    async with message.channel.typing():
        try:
            answer = await ask(question)
        except Exception as exc:
            print(f"Ошибка API: {type(exc).__name__}: {exc}", flush=True)
            answer = f"Не получилось ответить: {type(exc).__name__}: {exc}"

    for part in split(answer or "..."):
        await message.reply(part, allowed_mentions=discord.AllowedMentions.none())


if __name__ == "__main__":
    client.run(TOKEN)
