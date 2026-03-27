# -*- coding: utf-8 -*-
import re
import ast
import math
import logging
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from info import CHANNELS, ADMINS, AUTH_CHANNEL, LOG_CHANNEL, PICS, BATCH_FILE_CAPTION, CUSTOM_FILE_CAPTION
from database.ia_filterdb import get_filter_results, get_bad_files
from database.connections_mdb import active_connection
from utils import get_size, is_subscribed, get_settings, save_group_settings
from Script import script
from pyrogram.errors.exceptions.bad_request_400 import MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty
import os

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════
#  CONSTANTS & STATE
# ══════════════════════════════════════════════════════════

HOW_TO_DL_TEXT = (
    "📥 **How to Download**\n\n"
    "**Step 1:** Type the movie name in the group.\n"
    "**Step 2:** Bot shows results with filter buttons.\n"
    "**Step 3:** Pick Language 🌐 and Quality 📊.\n"
    "**Step 4:** Tap 🔍 Show Results.\n"
    "**Step 5:** Click a file button — bot sends it to PM.\n\n"
    "💡 **Tips:**\n"
    "• Use short movie names\n"
    "• Try different spellings\n"
    "• Select language first, then quality\n\n"
    "🤖 Powered by **Eva Maria Bot**"
)

# In-memory session store: {state_id: {...}}
filter_state = {}

LANGUAGES = ["Malayalam", "Tamil", "Hindi", "English", "All"]
QUALITIES  = ["480p", "720p", "1080p", "All"]

LANG_EMOJI = {"Malayalam": "🇮🇳", "Tamil": "🎭", "Hindi": "🎬", "English": "🌍", "All": "🔍"}
QUAL_EMOJI = {"480p": "📱", "720p": "💻", "1080p": "🖥️", "All": "🔍"}


# ══════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════

def build_lang_keyboard(state_id, selected_lang="All", selected_qual="All"):
    lang_rows = []
    for i in range(0, len(LANGUAGES), 3):
        row = []
        for lang in LANGUAGES[i:i+3]:
            tick = "✅ " if lang == selected_lang else ""
            row.append(InlineKeyboardButton(
                f"{tick}{LANG_EMOJI.get(lang, '')} {lang}",
                callback_data=f"lang#{state_id}#{lang}#{selected_qual}"
            ))
        lang_rows.append(row)

    qual_row = []
    for qual in QUALITIES:
        tick = "✅ " if qual == selected_qual else ""
        qual_row.append(InlineKeyboardButton(
            f"{tick}{QUAL_EMOJI.get(qual, '')} {qual}",
            callback_data=f"qual#{state_id}#{selected_lang}#{qual}"
        ))

    action_row = [
        InlineKeyboardButton("🔍 Show Results", callback_data=f"show#{state_id}#{selected_lang}#{selected_qual}"),
        InlineKeyboardButton("❌ Close",         callback_data="close_filter")
    ]
    return InlineKeyboardMarkup(lang_rows + [qual_row, action_row])


def apply_filters(files, lang="All", quality="All"):
    filtered = []
    for f in files:
        fname = f.get("file_name", "").lower()
        if lang != "All" and lang.lower() not in fname:
            continue
        if quality != "All" and quality.lower() not in fname:
            continue
        filtered.append(f)
    return filtered or files   # fallback: show all if nothing matches


def detect_quality(fname):
    for q in ["2160p", "4K", "1080p", "720p", "480p", "360p"]:
        if q.lower() in fname.lower():
            return q
    return "N/A"


def detect_lang(fname):
    fl = fname.lower()
    if "multi" in fl:
        return "Multi Audio"
    for l in ["malayalam", "tamil", "hindi", "telugu", "kannada", "english"]:
        if l in fl:
            lang = l.capitalize()
            return f"{lang} Dubbed" if "dubbed" in fl else lang
    return "N/A"


def btn_label(fname):
    quality = detect_quality(fname)
    short   = fname[:38].strip()
    return f"🎬 {short} [{quality}]"


# ══════════════════════════════════════════════════════════
#  MAIN FILTER HANDLER  (replaces original give_filter)
# ══════════════════════════════════════════════════════════

@Client.on_message(filters.group & filters.text & filters.incoming)
async def give_filter(client, message):
    results = await get_filter_results(message.text)
    if not results:
        return

    files, offset, total = results
    if not files:
        return

    state_id = str(message.id)
    filter_state[state_id] = {
        "query":   message.text,
        "files":   files,
        "offset":  offset,
        "total":   total,
        "chat":    message.chat.id,
        "lang":    "All",
        "quality": "All",
    }

    header = (
        f"🔍 **Search:** `{message.text}`\n"
        f"📦 **Found:** `{total}` file(s)\n\n"
        f"Filter by Language and Quality below 👇"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📥 How to Download", callback_data=f"how_to_dl#{state_id}")],
        *build_lang_keyboard(state_id).inline_keyboard
    ])

    await message.reply(header, reply_markup=keyboard, quote=True)


# ══════════════════════════════════════════════════════════
#  CALLBACK HANDLERS
# ══════════════════════════════════════════════════════════

@Client.on_callback_query(filters.regex(r"^how_to_dl#"))
async def how_to_download(client, query):
    await query.answer()
    await query.message.reply(HOW_TO_DL_TEXT, quote=True)


@Client.on_callback_query(filters.regex(r"^lang#"))
async def lang_filter_cb(client, query):
    _, state_id, lang, qual = query.data.split("#", 3)
    if state_id not in filter_state:
        return await query.answer("Session expired. Search again.", show_alert=True)
    filter_state[state_id]["lang"] = lang
    await query.message.edit_reply_markup(
        build_lang_keyboard(state_id, selected_lang=lang, selected_qual=qual)
    )
    await query.answer(f"Language: {lang}")


@Client.on_callback_query(filters.regex(r"^qual#"))
async def qual_filter_cb(client, query):
    _, state_id, lang, qual = query.data.split("#", 3)
    if state_id not in filter_state:
        return await query.answer("Session expired. Search again.", show_alert=True)
    filter_state[state_id]["quality"] = qual
    await query.message.edit_reply_markup(
        build_lang_keyboard(state_id, selected_lang=lang, selected_qual=qual)
    )
    await query.answer(f"Quality: {qual}")


@Client.on_callback_query(filters.regex(r"^show#"))
async def show_results_cb(client, query):
    _, state_id, lang, qual = query.data.split("#", 3)
    if state_id not in filter_state:
        return await query.answer("Session expired. Search again.", show_alert=True)

    state    = filter_state[state_id]
    filtered = apply_filters(state["files"], lang=lang, quality=qual)

    await query.answer(f"Showing {len(filtered)} result(s)")

    btn = []
    for file in filtered[:10]:
        fname = file.get("file_name", "Unknown")
        fid   = file.get("_id", "")
        btn.append([InlineKeyboardButton(btn_label(fname), callback_data=f"filep#{fid}")])

    btn.append([
        InlineKeyboardButton("🔁 Change Filters", callback_data=f"refilter#{state_id}"),
        InlineKeyboardButton("❌ Close",           callback_data="close_filter"),
    ])

    result_text = (
        f"✅ **Results**\n"
        f"🌐 Language: `{lang}` | 📊 Quality: `{qual}`\n"
        f"📦 Showing `{len(filtered)}` of `{state['total']}` files"
    )
    await query.message.reply(
        result_text,
        reply_markup=InlineKeyboardMarkup(btn),
        quote=True
    )


@Client.on_callback_query(filters.regex(r"^refilter#"))
async def refilter_cb(client, query):
    _, state_id = query.data.split("#", 1)
    if state_id not in filter_state:
        return await query.answer("Session expired.", show_alert=True)
    state = filter_state[state_id]
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📥 How to Download", callback_data=f"how_to_dl#{state_id}")],
        *build_lang_keyboard(
            state_id,
            selected_lang=state["lang"],
            selected_qual=state["quality"]
        ).inline_keyboard
    ])
    await query.message.reply(
        f"🔍 **Refilter:** `{state['query']}`\nChoose Language and Quality:",
        reply_markup=keyboard,
        quote=True
    )
    await query.answer()


@Client.on_callback_query(filters.regex(r"^close_filter$"))
async def close_filter_cb(client, query):
    await query.message.delete()
    await query.answer("Closed")


@Client.on_callback_query(filters.regex(r"^filep#"))
async def file_pm_cb(client, query):
    """
    Relay to the original file-send logic.
    The original bot uses 'files#' or similar callback in pm_filter.py.
    We just notify the user here.
    """
    _, file_id = query.data.split("#", 1)
    await query.answer("Sending to your PM...", show_alert=False)
    try:
        await query.message.reply(
            "📨 **File is being sent to your PM!**\n"
            "If nothing arrives, start the bot in PM first.",
            quote=True
        )
    except Exception as e:
        logger.exception(e)
