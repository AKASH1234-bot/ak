import logging
import asyncio
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from imdb import Cinemagoer
from database.users_chats_db import db
from info import ADMINS
from utils import get_settings, save_group_settings

logger = logging.getLogger(__name__)
imdb = Cinemagoer()

GENRE_LANGUAGES = {
    "Malayalam": ["Kayamkulam Kochunni", "Jallikattu", "Drishyam", "Lucifer", "Minnal Murali"],
    "Tamil":     ["Vikram", "Jailer", "Ponniyin Selvan", "Kaithi", "Master"],
    "Hindi":     ["Pathaan", "Jawan", "Animal", "12th Fail", "Dunki"],
    "Telugu":    ["RRR", "Pushpa", "Baahubali", "Kalki 2898 AD", "Devara"],
    "English":   ["Oppenheimer", "Dune", "Avatar", "Top Gun Maverick", "Inception"],
}


def _week_seed() -> int:
    """Deterministic seed based on current ISO week — changes every Monday."""
    now = datetime.utcnow()
    return now.isocalendar().year * 100 + now.isocalendar().week


def _pick_weekly(movies: list, n: int = 5) -> list:
    seed = _week_seed()
    indices = [(seed * (i + 7)) % len(movies) for i in range(n)]
    seen, result = set(), []
    for idx in indices:
        if idx not in seen:
            seen.add(idx)
            result.append(movies[idx])
    return result


async def _fetch_imdb_info(title: str) -> dict | None:
    try:
        results = imdb.search_movie(title, results=1)
        if not results:
            return None
        movie = imdb.get_movie(results[0].movieID)
        return {
            "title": movie.get("title", title),
            "year": movie.get("year", ""),
            "rating": movie.get("rating", "N/A"),
            "genres": ", ".join(movie.get("genres", [])[:3]),
            "plot": (movie.get("plot", [""])[0])[:200] + "..." if movie.get("plot") else "N/A",
            "poster": movie.get("full-size cover url", ""),
            "imdb_id": f"tt{results[0].movieID}",
        }
    except Exception as e:
        logger.error(f"IMDB fetch error for {title}: {e}")
        return None


async def _build_recommendation_text(language: str) -> tuple[str, list]:
    movies_pool = GENRE_LANGUAGES.get(language, GENRE_LANGUAGES["Malayalam"])
    picks = _pick_weekly(movies_pool)
    lines = [f"🎬 **Weekly {language} Movie Picks** — Week {_week_seed() % 100}\n"]
    buttons = []
    for i, title in enumerate(picks, 1):
        info = await _fetch_imdb_info(title)
        if info:
            lines.append(
                f"{i}. **{info['title']}** ({info['year']})\n"
                f"   ⭐ {info['rating']} | 🎭 {info['genres']}\n"
                f"   _{info['plot']}_\n"
            )
            buttons.append([InlineKeyboardButton(
                f"🔍 {info['title']} on IMDb",
                url=f"https://www.imdb.com/title/{info['imdb_id']}"
            )])
        else:
            lines.append(f"{i}. **{title}**\n")
    return "\n".join(lines), buttons


# ── commands ──────────────────────────────────────────────────────────────────

@Client.on_message(filters.command("weekly") & (filters.group | filters.private))
async def weekly_recommendations(client: Client, message: Message):
    args = message.command[1:]
    language = args[0].capitalize() if args else "Malayalam"
    if language not in GENRE_LANGUAGES:
        langs = ", ".join(GENRE_LANGUAGES.keys())
        return await message.reply(f"⚠️ Unknown language. Choose from: {langs}")

    wait = await message.reply("⏳ Fetching weekly picks…")
    text, buttons = await _build_recommendation_text(language)
    markup = InlineKeyboardMarkup(buttons) if buttons else None
    await wait.edit(text, reply_markup=markup)


@Client.on_message(filters.command("setweeklylang") & filters.group)
async def set_weekly_language(client: Client, message: Message):
    if message.from_user.id not in ADMINS:
        return await message.reply("⚠️ Admins only.")
    args = message.command[1:]
    if not args or args[0].capitalize() not in GENRE_LANGUAGES:
        return await message.reply(f"Usage: /setweeklylang <lang>\nOptions: {', '.join(GENRE_LANGUAGES.keys())}")
    await save_group_settings(message.chat.id, "weekly_language", args[0].capitalize())
    await message.reply(f"✅ Weekly language set to **{args[0].capitalize()}**")


# ── scheduler (called from bot.py on start) ───────────────────────────────────

async def weekly_scheduler(client: Client):
    """Send weekly recommendations every Monday at 10:00 UTC."""
    while True:
        now = datetime.utcnow()
        days_ahead = (7 - now.weekday()) % 7 or 7   # days until next Monday
        next_monday = (now + timedelta(days=days_ahead)).replace(
            hour=10, minute=0, second=0, microsecond=0
        )
        wait_seconds = (next_monday - now).total_seconds()
        logger.info(f"[weekly] next broadcast in {wait_seconds:.0f}s")
        await asyncio.sleep(wait_seconds)

        chats = await db.get_all_chats()
        for chat in chats:
            try:
                settings = await db.get_settings(chat["id"])
                language = settings.get("weekly_language", "Malayalam")
                text, buttons = await _build_recommendation_text(language)
                markup = InlineKeyboardMarkup(buttons) if buttons else None
                await client.send_message(chat["id"], text, reply_markup=markup)
            except Exception as e:
                logger.warning(f"[weekly] failed for {chat['id']}: {e}")
            await asyncio.sleep(0.5)
