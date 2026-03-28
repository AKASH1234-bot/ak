# -*- coding: utf-8 -*-
import re
import logging
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database.ia_filterdb import get_search_results
from utils import get_size

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════
#  STATE
# ══════════════════════════════════════════════════════════

filter_state = {}

LANGUAGES = ["Malayalam", "Tamil", "Hindi", "English", "All"]
QUALITIES  = ["480p", "720p", "1080p", "All"]

HOW_TO_DL_TEXT = (
    "How to Download\n\n"
    "Step 1: Type the movie name in the group.\n"
    "Step 2: Bot shows results with filter buttons.\n"
    "Step 3: Pick Language and Quality.\n"
    "Step 4: Tap Show Results.\n"
    "Step 5: Click a file — bot sends it to your PM.\n\n"
    "Tips:\n"
    "- Use short movie names\n"
    "- Try different spellings\n"
    "- Select language first then quality\n\n"
    "Powered by Eva Maria Bot"
)

# Quality priority for deduplication (higher = better)
QUALITY_PRIORITY = {"2160p": 5, "4k": 5, "1080p": 4, "720p": 3, "480p": 2, "360p": 1, "n/a": 0}


# ══════════════════════════════════════════════════════════
#  DEDUPLICATION HELPERS
# ══════════════════════════════════════════════════════════

def normalize_name(name: str) -> str:
    """Lowercase, remove symbols, collapse spaces."""
    name = name.lower()
    name = re.sub(r'[\[\](){}@#$%^&*!.,;:\'"\\/-]', ' ', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def detect_quality(fname: str) -> str:
    fname_lower = fname.lower()
    for q in ["2160p", "4k", "1080p", "720p", "480p", "360p"]:
        if q in fname_lower:
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
    """
    Remove duplicate files.
    Key = (normalized_name, language, quality)
    If duplicate exists, keep the one with higher quality priority.
    """
    seen = {}  # key -> (file, quality_priority)

    for f in files:
        fname = f.file_name if hasattr(f, 'file_name') else f.get("file_name", "")
        if not fname:
            continue

        quality = detect_quality(fname)
        lang    = detect_lang(fname)

        # Strip quality/lang/year tags to get clean movie name
        clean = re.sub(
            r'(19|20)\d{2}|2160p|1080p|720p|480p|360p|4k|hdrip|bluray|webrip|'
            r'hdtv|dvdrip|x264|x265|hevc|aac|hindi|tamil|malayalam|telugu|'
            r'kannada|english|multi|dubbed|web-dl|mkv|mp4|avi',
            ' ', fname.lower(), flags=re.IGNORECASE
        )
        clean = normalize_name(clean)

        key = (clean, lang, quality)
        prio = QUALITY_PRIORITY.get(quality, 0)

        if key not in seen:
            seen[key] = (f, prio)
        else:
            # Keep higher quality version
            if prio > seen[key][1]:
                seen[key] = (f, prio)

    return [item[0] for item in seen.values()]


# ══════════════════════════════════════════════════════════
#  KEYBOARD BUILDER
# ══════════════════════════════════════════════════════════

def build_keyboard(state_id, sel_lang="All", sel_qual="All"):
    rows = []
    for i in range(0, len(LANGUAGES), 3):
        row = []
        for lang in LANGUAGES[i:i+3]:
            tick = "[OK] " if lang == sel_lang else ""
            row.append(InlineKeyboardButton(
                f"{tick}{lang}",
                callback_data=f"lang#{state_id}#{lang}#{sel_qual}"
            ))
        rows.append(row)

    qual_row = []
    for qual in QUALITIES:
        tick = "[OK] " if qual == sel_qual else ""
        qual_row.append(InlineKeyboardButton(
            f"{tick}{qual}",
            callback_data=f"qual#{state_id}#{sel_lang}#{qual}"
        ))
    rows.append(qual_row)

    rows.append([
        InlineKeyboardButton("Show Results", callback_data=f"show#{state_id}#{sel_lang}#{sel_qual}"),
        InlineKeyboardButton("Close",        callback_data="close_filter")
    ])
    return InlineKeyboardMarkup(rows)


# ══════════════════════════════════════════════════════════
#  FILTER HELPERS
# ══════════════════════════════════════════════════════════

def apply_filters(files, lang="All", quality="All"):
    out = []
    for f in files:
        name = f.file_name.lower() if hasattr(f, 'file_name') else f.get("file_name", "").lower()
        if lang != "All" and lang.lower() not in name:
            continue
        if quality != "All" and quality.lower() not in name:
            continue
        out.append(f)
    return out or files


def get_fname(f):
    if hasattr(f, 'file_name'):
        return f.file_name or "Unknown"
    return f.get("file_name", "Unknown")


def get_fid(f):
    if hasattr(f, 'file_id'):
        return str(f.file_id)
    return str(f.get("_id", ""))


def make_btn_label(fname):
    q = detect_quality(fname)
    short = fname[:40].strip()
    return f"{short} [{q.upper()}]"


# ══════════════════════════════════════════════════════════
#  MAIN SEARCH HANDLER
# ══════════════════════════════════════════════════════════

@Client.on_message(filters.group & filters.text & filters.incoming)
async def give_filter(client, message):
    query_text = message.text.strip()
    if not query_text or query_text.startswith("/"):
        return

    try:
        files, next_offset, total = await get_search_results(
            query_text, max_results=50, offset=0
        )
    except TypeError:
        try:
            files, next_offset, total = await get_search_results(query_text)
        except Exception as e:
            logger.exception(e)
            return
    except Exception as e:
        logger.exception(e)
        return

    if not files:
        return

    # ✅ Deduplicate before storing
    files = deduplicate(files)
    total = len(files)

    state_id = str(message.id)
    filter_state[state_id] = {
        "query":   query_text,
        "files":   files,
        "total":   total,
        "chat":    message.chat.id,
        "lang":    "All",
        "quality": "All",
    }

    header = (
        f"Search: {query_text}\n"
        f"Found: {total} unique file(s)\n\n"
        f"Select Language and Quality to filter:"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("How to Download", callback_data=f"how_to_dl#{state_id}")],
        *build_keyboard(state_id).inline_keyboard
    ])

    await message.reply(header, reply_markup=keyboard, quote=True)


# ══════════════════════════════════════════════════════════
#  CALLBACKS
# ══════════════════════════════════════════════════════════

@Client.on_callback_query(filters.regex(r"^how_to_dl#"))
async def how_to_download_cb(client, query):
    await query.answer()
    await query.message.reply(HOW_TO_DL_TEXT, quote=True)


@Client.on_callback_query(filters.regex(r"^lang#"))
async def lang_cb(client, query):
    _, state_id, lang, qual = query.data.split("#", 3)
    if state_id not in filter_state:
        return await query.answer("Session expired. Search again.", show_alert=True)
    filter_state[state_id]["lang"] = lang
    try:
        await query.message.edit_reply_markup(
            build_keyboard(state_id, sel_lang=lang, sel_qual=qual)
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
    try:
        await query.message.edit_reply_markup(
            build_keyboard(state_id, sel_lang=lang, sel_qual=qual)
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

    await query.answer(f"Showing {len(filtered)} result(s)")

    btn = []
    for f in filtered[:10]:
        fname = get_fname(f)
        fid   = get_fid(f)
        btn.append([InlineKeyboardButton(
            make_btn_label(fname),
            callback_data=f"filep#{fid}"
        )])

    btn.append([
        InlineKeyboardButton("Change Filters", callback_data=f"refilter#{state_id}"),
        InlineKeyboardButton("Close",          callback_data="close_filter"),
    ])

    text = (
        f"Results\n"
        f"Language: {lang} | Quality: {qual}\n"
        f"Showing {len(filtered)} of {state['total']} files"
    )
    await query.message.reply(
        text,
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
        [InlineKeyboardButton("How to Download", callback_data=f"how_to_dl#{state_id}")],
        *build_keyboard(
            state_id,
            sel_lang=state["lang"],
            sel_qual=state["quality"]
        ).inline_keyboard
    ])
    await query.message.reply(
        f"Refilter: {state['query']}\nChoose Language and Quality:",
        reply_markup=keyboard,
        quote=True
    )
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
        await query.message.reply(
            "File is being sent to your PM!\n"
            "If nothing arrives, start the bot in PM first.",
            quote=True
        )
    except Exception as e:
        logger.exception(e)
