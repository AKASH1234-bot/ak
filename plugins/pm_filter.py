# -*- coding: utf-8 -*-
import logging
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from info import LOG_CHANNEL
from utils import get_size, get_settings

logger = logging.getLogger(__name__)


def get_quality(file_name: str) -> str:
    for q in ["2160p", "1080p", "720p", "480p", "360p", "4K"]:
        if q.lower() in file_name.lower():
            return q
    return "N/A"


def get_lang(file_name: str) -> str:
    for l in ["Malayalam", "Tamil", "Hindi", "Telugu", "Kannada", "English"]:
        if l.lower() in file_name.lower():
            if "dubbed" in file_name.lower():
                return f"{l} Dubbed"
            return l
    if "multi" in file_name.lower():
        return "Multi Audio"
    return "N/A"


@Client.on_callback_query(filters.regex(r"^fileid#"))
async def pm_filter_cb(client, query):
    _, file_id, chat_id = query.data.split("#", 2)
    await get_settings(int(chat_id))

    try:
        file_msg = await client.get_messages(int(chat_id), int(file_id))
    except Exception as e:
        logger.exception(e)
        return await query.answer("File not found!", show_alert=True)

    fname = file_msg.document.file_name if file_msg.document else "Unknown"
    fsize = file_msg.document.file_size if file_msg.document else 0
    quality = get_quality(fname)
    lang = get_lang(fname)
    size_str = get_size(fsize)

    caption = (
        f"{fname}\n"
        f"Language : {lang}\n"
        f"Quality  : {quality}\n"
        f"File Size: {size_str}\n"
        f"Sent by Eva Maria Bot"
    )

    await query.answer("Sending file...")

    try:
        await client.send_document(
            query.from_user.id,
            document=file_msg.document.file_id,
            caption=caption,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Share", switch_inline_query=fname[:30])]
            ])
        )
        await query.message.reply(
            "File sent to your PM!\nCheck your messages.",
            quote=True
        )
    except Exception as e:
        logger.exception(e)
        await query.message.reply(
            "Start the bot in PM first!",
            quote=True
        )
