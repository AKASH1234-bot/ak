"""
extra_filters.py — /lang, /quality, /weekly, /top10 commands
All callback_data prefixed with ef_ to avoid conflicts with filters.py
"""

from pyrogram import Client, filters
from pyrogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from database.ia_filterdb import get_search_results

# ─────────────────────────── static data ────────────────────────────────────

WEEKLY_PICKS = [
    "Manjummel Boys (2024) Malayalam",
    "Premalu (2024) Malayalam",
    "Aavesham (2024) Malayalam",
    "Maharaja (2024) Tamil",
    "GOAT (2024) Tamil",
    "Kalki 2898-AD (2024) Hindi/Telugu",
    "Stree 2 (2024) Hindi",
    "Singham Again (2024) Hindi",
    "Alien: Romulus (2024) English",
    "Deadpool & Wolverine (2024) English",
]

TOP10 = [
    ("1",  "Manjummel Boys",       "Malayalam",    "⭐ 8.3"),
    ("2",  "Premalu",              "Malayalam",    "⭐ 8.1"),
    ("3",  "Aavesham",             "Malayalam",    "⭐ 7.9"),
    ("4",  "Maharaja",             "Tamil",        "⭐ 8.5"),
    ("5",  "GOAT",                 "Tamil",        "⭐ 7.2"),
    ("6",  "Kalki 2898-AD",        "Hindi/Telugu", "⭐ 7.5"),
    ("7",  "Stree 2",              "Hindi",        "⭐ 7.8"),
    ("8",  "Pushpa 2",             "Hindi/Telugu", "⭐ 7.6"),
    ("9",  "Alien: Romulus",       "English",      "⭐ 7.4"),
    ("10", "Deadpool & Wolverine", "English",      "⭐ 7.8"),
]

LANGUAGES = ["Malayalam", "Tamil", "Hindi", "English"]
QUALITIES  = ["480p", "720p", "1080p"]


# ─────────────────────────── keyboards ──────────────────────────────────────

def lang_keyboard():
    buttons = [
        [InlineKeyboardButton(f"🌐 {lang}", callback_data=f"ef_lang_{lang}")]
        for lang in LANGUAGES
    ]
    buttons.append([InlineKeyboardButton("❌ Close", callback_data="ef_close")])
    return InlineKeyboardMarkup(buttons)


def quality_keyboard():
    buttons = [
        [InlineKeyboardButton(f"🎬 {q}", callback_data=f"ef_quality_{q}")]
        for q in QUALITIES
    ]
    buttons.append([InlineKeyboardButton("❌ Close", callback_data="ef_close")])
    return InlineKeyboardMarkup(buttons)


# ─────────────────────────── /lang ──────────────────────────────────────────

@Client.on_message(filters.command("lang") & filters.group)
async def lang_command(client: Client, message: Message):
    await message.reply("🌐 **Choose a Language to Filter Movies:**", reply_markup=lang_keyboard())


@Client.on_callback_query(filters.regex(r"^ef_lang_(.+)$"))
async def lang_callback(client: Client, query: CallbackQuery):
    lang = query.matches[0].group(1)
    await query.answer(f"Filtering: {lang}", show_alert=False)
    files, _, total = await get_search_results(lang, max_results=10, offset=0)
    if not files:
        return await query.message.edit_text(f"❌ No **{lang}** movies found.")
    text = f"🌐 **{lang} Movies** — {total} results\n\n"
    for i, f in enumerate(files, 1):
        text += f"`{i}.` {f.file_name}\n"
    await query.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Back", callback_data="ef_lang_back"),
            InlineKeyboardButton("❌ Close", callback_data="ef_close"),
        ]])
    )


@Client.on_callback_query(filters.regex(r"^ef_lang_back$"))
async def lang_back(client: Client, query: CallbackQuery):
    await query.message.edit_text("🌐 **Choose a Language to Filter Movies:**", reply_markup=lang_keyboard())


# ─────────────────────────── /quality ───────────────────────────────────────

@Client.on_message(filters.command("quality") & filters.group)
async def quality_command(client: Client, message: Message):
    await message.reply("🎬 **Choose Quality to Filter Movies:**", reply_markup=quality_keyboard())


@Client.on_callback_query(filters.regex(r"^ef_quality_(.+)$"))
async def quality_callback(client: Client, query: CallbackQuery):
    quality = query.matches[0].group(1)
    await query.answer(f"Filtering: {quality}", show_alert=False)
    files, _, total = await get_search_results(quality, max_results=10, offset=0)
    if not files:
        return await query.message.edit_text(f"❌ No **{quality}** movies found.")
    text = f"🎬 **{quality} Movies** — {total} results\n\n"
    for i, f in enumerate(files, 1):
        text += f"`{i}.` {f.file_name}\n"
    await query.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Back", callback_data="ef_quality_back"),
            InlineKeyboardButton("❌ Close", callback_data="ef_close"),
        ]])
    )


@Client.on_callback_query(filters.regex(r"^ef_quality_back$"))
async def quality_back(client: Client, query: CallbackQuery):
    await query.message.edit_text("🎬 **Choose Quality to Filter Movies:**", reply_markup=quality_keyboard())


# ─────────────────────────── /weekly ────────────────────────────────────────

@Client.on_message(filters.command("weekly"))
async def weekly_command(client: Client, message: Message):
    text = "🗓 **Weekly Movie Recommendations**\n\n"
    for i, movie in enumerate(WEEKLY_PICKS, 1):
        text += f"**{i}.** {movie}\n"
    text += "\n_Updated every week. Use /lang or /quality for filtered results._"
    await message.reply(
        text,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🌐 Filter by Language", callback_data="ef_open_lang"),
            InlineKeyboardButton("🎬 Filter by Quality",  callback_data="ef_open_quality"),
        ]])
    )


@Client.on_callback_query(filters.regex(r"^ef_open_lang$"))
async def open_lang(client: Client, query: CallbackQuery):
    await query.message.edit_text("🌐 **Choose a Language to Filter Movies:**", reply_markup=lang_keyboard())


@Client.on_callback_query(filters.regex(r"^ef_open_quality$"))
async def open_quality(client: Client, query: CallbackQuery):
    await query.message.edit_text("🎬 **Choose Quality to Filter Movies:**", reply_markup=quality_keyboard())


# ─────────────────────────── /top10 ─────────────────────────────────────────

@Client.on_message(filters.command("top10"))
async def top10_command(client: Client, message: Message):
    text = "🏆 **Monthly Top 10 Trending Movies**\n\n"
    for rank, title, lang, rating in TOP10:
        text += f"**{rank}.** {title}  |  _{lang}_  |  {rating}\n"
    text += "\n_Trending this month. Search by name to get the file._"
    await message.reply(text)


# ─────────────────────────── close ──────────────────────────────────────────

@Client.on_callback_query(filters.regex(r"^ef_close$"))
async def close_callback(client: Client, query: CallbackQuery):
    try:
        await query.message.delete()
    except Exception:
        await query.answer("Closed.", show_alert=False)
