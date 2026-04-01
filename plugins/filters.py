# -*- coding: utf-8 -*-
import re
import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database.ia_filterdb import get_search_results
from utils import get_size

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════════

AUTO_DELETE_SECS = 300
filter_state  = {}
_search_cache = {}   # capped at 200 entries

LANGUAGES = ["Malayalam", "Tamil", "Hindi", "English", "All"]
QUALITIES  = ["480p", "720p", "1080p", "All"]

HOW_TO_DL_TEXT = (
    "📥 <b>How to Download</b>\n\n"
    "1️⃣ Type the movie name in the group.\n"
    "2️⃣ Bot shows all results instantly.\n"
    "3️⃣ Use Language / Quality buttons to filter.\n"
    "4️⃣ Tap <b>Show Results</b> to list files.\n"
    "5️⃣ Click a file button — it will be sent to your PM.\n\n"
    "<b>Tips:</b>\n"
    "• Use short movie names\n"
    "• Try different spellings\n"
    "• Files auto-delete after 5 minutes ⏳\n\n"
    "<i>Powered by Eva Maria Bot</i>"
)

QUALITY_PRIORITY = {"2160p": 5, "4k": 5, "1080p": 4, "720p": 3, "480p": 2, "360p": 1, "n/a": 0}


# ══════════════════════════════════════════════════════════
#  AUTO DELETE  ← NEW
# ══════════════════════════════════════════════════════════

async def _delete_later(*msgs):
    await asyncio.sleep(AUTO_DELETE_SECS)
    for m in msgs:
        try:
            await m.delete()
        except Exception:
            pass


def auto_delete(*msgs):
    """Non-blocking. Schedules msgs for deletion after 300 s."""
    asyncio.create_task(_delete_later(*msgs))


# ══════════════════════════════════════════════════════════
#  DEDUPLICATION HELPERS  (unchanged logic)
# ══════════════════════════════════════════════════════════

def normalize_name(name: str) -> str:
    name = name.lower()
    name = re.sub(r'[\[\](){}@#$%^&*!.,;:\'"\\/-]', ' ', name)
    return re.sub(r'\s+', ' ', name).strip()


def detect_quality(fname: str) -> str:
    fl = fname.lower()
    for q in ["2160p", "4k", "1080p", "720p", "480p", "360p"]:
        if q in fl:
            return q
    return "n/a"


def detect_lang(fname: str) -> str:
    fl = fname.lower()
    if "multi" in fl:
        return "multi"
    for l in ["malayalam", "tamil", "hindi", "telugu", "kannada", "english"]:
        if l in fl:
            return l
    return "unknown"


def deduplicate(files):
    seen = {}
    for f in files:
        fname = f.file_name if hasattr(f, 'file_name') else f.get("file_name", "")
        if not fname:
            continue
        quality = detect_quality(fname)
        lang    = detect_lang(fname)
        clean   = re.sub(
            r'(19|20)\d{2}|2160p|1080p|720p|480p|360p|4k|hdrip|bluray|webrip|'
            r'hdtv|dvdrip|x264|x265|hevc|aac|hindi|tamil|malayalam|telugu|'
            r'kannada|english|multi|dubbed|web-dl|mkv|mp4|avi',
            ' ', fname.lower(), flags=re.IGNORECASE
        )
        clean = normalize_name(clean)
        key   = (clean, lang, quality)
        prio  = QUALITY_PRIORITY.get(quality, 0)
        if key not in seen or prio > seen[key][1]:
            seen[key] = (f, prio)
    return [item[0] for item in seen.values()]


# ══════════════════════════════════════════════════════════
#  FILE HELPERS
# ══════════════════════════════════════════════════════════

def get_fname(f):
    return (f.file_name if hasattr(f, 'file_name') else f.get("file_name", "")) or "Unknown"


def get_fsize(f):
    size = f.file_size if hasattr(f, 'file_size') else f.get("file_size", 0)
    return get_size(size) if size else "N/A"


def get_fid(f):
    return str(f.file_id if hasattr(f, 'file_id') else f.get("_id", ""))


def make_btn_label(fname):
    q     = detect_quality(fname).upper()
    short = fname[:38].strip()
    return f"📄 {short} [{q}]"


def apply_filters(files, lang="All", quality="All"):
    out = []
    for f in files:
        name = get_fname(f).lower()
        if lang != "All" and lang.lower() not in name:
            continue
        if quality != "All" and quality.lower() not in name:
            continue
        out.append(f)
    return out if out else files


# ══════════════════════════════════════════════════════════
#  MESSAGE FORMAT  ← NEW
# ══════════════════════════════════════════════════════════

def results_header(query, files, lang, quality):
    active = " | ".join(x for x in [lang, quality] if x != "All")
    text   = (
        f"🔍 <b>Results for:</b> <i>{query}</i>\n"
        f"📦 <b>Found:</b> {len(files)} unique file(s)"
    )
    if active:
        text += f"\n🎯 <b>Showing:</b> {active}"
    text += "\n\n<b>Select filters or tap Show Results:</b>"
    return text


# ══════════════════════════════════════════════════════════
#  KEYBOARD BUILDERS
# ══════════════════════════════════════════════════════════

def build_keyboard(state_id, sel_lang="All", sel_qual="All"):
    rows = []

    # Row 1 – Languages (3 per row)
    for i in range(0, len(LANGUAGES), 3):
        row = []
        for lang in LANGUAGES[i:i + 3]:
            tick = "✅ " if lang == sel_lang else ""
            row.append(InlineKeyboardButton(
                f"{tick}{lang}",
                callback_data=f"lang#{state_id}#{lang}#{sel_qual}"
            ))
        rows.append(row)

    # Row 2 – Qualities
    rows.append([
        InlineKeyboardButton(
            ("✅ " if q == sel_qual else "") + q,
            callback_data=f"qual#{state_id}#{sel_lang}#{q}"
        )
        for q in QUALITIES
    ])

    # Row 3 – Actions
    rows.append([
        InlineKeyboardButton("📥 How to Download", callback_data=f"how_to_dl#{state_id}"),
        InlineKeyboardButton("🎬 Show Results",     callback_data=f"show#{state_id}#{sel_lang}#{sel_qual}"),
        InlineKeyboardButton("✖ Close",             callback_data="close_filter"),
    ])
    return InlineKeyboardMarkup(rows)


def build_file_keyboard(state_id, filtered):
    btn = [
        [InlineKeyboardButton(make_btn_label(get_fname(f)), callback_data=f"filep#{get_fid(f)}")]
        for f in filtered[:10]
    ]
    btn.append([
        InlineKeyboardButton("🔄 Change Filters", callback_data=f"refilter#{state_id}"),
        InlineKeyboardButton("✖ Close",           callback_data="close_filter"),
    ])
    return InlineKeyboardMarkup(btn)


# ══════════════════════════════════════════════════════════
#  CACHE HELPER
# ══════════════════════════════════════════════════════════

def _cache_set(key, value):
    if len(_search_cache) >= 200:
        del _search_cache[next(iter(_search_cache))]
    _search_cache[key] = value


# ══════════════════════════════════════════════════════════
#  MAIN SEARCH HANDLER
# ══════════════════════════════════════════════════════════

@Client.on_message(filters.group & filters.text & filters.incoming)
async def give_filter(client, message):
    query_text = message.text.strip()
    if not query_text or query_text.startswith("/"):
        return

    # ── Cache lookup ──────────────────────────────────────
    cache_key = query_text.lower()
    if cache_key in _search_cache:
        files = _search_cache[cache_key]
    else:
        try:
            files, _, _ = await get_search_results(query_text, max_results=50, offset=0)
        except TypeError:
            try:
                files, _, _ = await get_search_results(query_text)
            except Exception as e:
                logger.exception(e)
                return
        except Exception as e:
            logger.exception(e)
            return

        if not files:
            return

        files = deduplicate(files)
        _cache_set(cache_key, files)

    if not files:
        return

    state_id = str(message.id)
    filter_state[state_id] = {
        "query":   query_text,
        "files":   files,
        "total":   len(files),
        "chat":    message.chat.id,
        "lang":    "All",
        "quality": "All",
    }

    sent = await message.reply(
        results_header(query_text, files, "All", "All"),
        reply_markup=build_keyboard(state_id),
        quote=True,
        parse_mode="html"
    )
    auto_delete(message, sent)   # ← delete both in 300 s


# ══════════════════════════════════════════════════════════
#  CALLBACKS
# ══════════════════════════════════════════════════════════

@Client.on_callback_query(filters.regex(r"^how_to_dl#"))
async def how_to_download_cb(client, query):
    await query.answer()
    sent = await query.message.reply(HOW_TO_DL_TEXT, quote=True, parse_mode="html")
    auto_delete(sent)


@Client.on_callback_query(filters.regex(r"^lang#"))
async def lang_cb(client, query):
    _, state_id, lang, qual = query.data.split("#", 3)
    if state_id not in filter_state:
        return await query.answer("Session expired. Search again.", show_alert=True)
    filter_state[state_id]["lang"] = lang
    state = filter_state[state_id]
    try:
        await query.message.edit_text(
            results_header(state["query"], state["files"], lang, qual),
            reply_markup=build_keyboard(state_id, sel_lang=lang, sel_qual=qual),
            parse_mode="html"
        )
    except Exception:
        pass
    await query.answer(f"Language: {lang}")


@Client.on_callback_query(filters.regex(r"^qual#"))
async def qual_cb(client, query):
    _, state_id, lang, qual = query.data.split("#", 3)
    if state_id not in filter_state:
        return await query.answer("Session expired. Search again.", show_alert=True)
    filter_state[state_id]["quality"] = qual
    state = filter_state[state_id]
    try:
        await query.message.edit_text(
            results_header(state["query"], state["files"], lang, qual),
            reply_markup=build_keyboard(state_id, sel_lang=lang, sel_qual=qual),
            parse_mode="html"
        )
    except Exception:
        pass
    await query.answer(f"Quality: {qual}")


@Client.on_callback_query(filters.regex(r"^show#"))
async def show_cb(client, query):
    _, state_id, lang, qual = query.data.split("#", 3)
    if state_id not in filter_state:
        return await query.answer("Session expired. Search again.", show_alert=True)

    state    = filter_state[state_id]
    filtered = apply_filters(state["files"], lang=lang, quality=qual)
    active   = " | ".join(x for x in [lang, qual] if x != "All")

    text = (
        f"🎬 <b>{state['query']}</b>\n"
        f"📦 <b>Showing:</b> {len(filtered)} of {state['total']} files"
        + (f"\n🎯 <b>Filter:</b> {active}" if active else "")
    )

    sent = await query.message.reply(
        text,
        reply_markup=build_file_keyboard(state_id, filtered),
        quote=True,
        parse_mode="html"
    )
    auto_delete(sent)
    await query.answer(f"Showing {len(filtered)} result(s)")


@Client.on_callback_query(filters.regex(r"^refilter#"))
async def refilter_cb(client, query):
    _, state_id = query.data.split("#", 1)
    if state_id not in filter_state:
        return await query.answer("Session expired.", show_alert=True)
    state = filter_state[state_id]
    sent = await query.message.reply(
        results_header(state["query"], state["files"], state["lang"], state["quality"]),
        reply_markup=build_keyboard(state_id, sel_lang=state["lang"], sel_qual=state["quality"]),
        quote=True,
        parse_mode="html"
    )
    auto_delete(sent)
    await query.answer()


@Client.on_callback_query(filters.regex(r"^close_filter$"))
async def close_filter_cb(client, query):
    try:
        await query.message.delete()
    except Exception:
        pass
    await query.answer("Closed")


@Client.on_callback_query(filters.regex(r"^filep#"))
async def file_pm_cb(client, query):
    _, file_id = query.data.split("#", 1)
    await query.answer("Sending to your PM...", show_alert=False)
    try:
        sent = await query.message.reply(
            "✅ File is being sent to your PM!\n"
            "If nothing arrives, start the bot in PM first.",
            quote=True
        )
        auto_delete(sent)
    except Exception as e:
        logger.exception(e)
