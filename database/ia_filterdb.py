import logging
from struct import pack
import re
import base64
from pyrogram.file_id import FileId
from pymongo.errors import DuplicateKeyError
from umongo import Instance, Document, fields
from motor.motor_asyncio import AsyncIOMotorClient
from marshmallow.exceptions import ValidationError
from info import DATABASE_URI, DATABASE_NAME, COLLECTION_NAME, MAX_BTN

client = AsyncIOMotorClient(DATABASE_URI)
mydb = client[DATABASE_NAME]
instance = Instance.from_db(mydb)


@instance.register
class Media(Document):
    file_id = fields.StrField(attribute='_id')
    file_ref = fields.StrField(allow_none=True)
    file_name = fields.StrField(required=True)
    file_size = fields.IntField(required=True)
    mime_type = fields.StrField(allow_none=True)
    caption = fields.StrField(allow_none=True)
    file_type = fields.StrField(allow_none=True)

    class Meta:
        indexes = ('$file_name', )
        collection_name = COLLECTION_NAME


async def get_files_db_size():
    return (await mydb.command("dbstats"))['dataSize']


async def save_file(media):
    """Save file in database"""
    file_id, file_ref = unpack_new_file_id(media.file_id)
    file_name = re.sub(r"(_|\-|\.|\+)", " ", str(media.file_name))
    try:
        file = Media(
            file_id=file_id,
            file_ref=file_ref,
            file_name=file_name,
            file_size=media.file_size,
            mime_type=media.mime_type,
            caption=media.caption.html if media.caption else None,
            file_type=media.mime_type.split('/')[0]
        )
    except ValidationError:
        print('Error occurred while saving file in database')
        return 'err'
    else:
        try:
            await file.commit()
        except DuplicateKeyError:
            print(f'{getattr(media, "file_name", "NO_FILE")} is already saved in database')
            return 'dup'
        else:
            print(f'{getattr(media, "file_name", "NO_FILE")} is saved to database')
            return 'suc'


# ✅ FIX 1: Added `filter=False` parameter to accept calls from pm_filter.py
# ✅ FIX 2: Renamed internal `filter` variable to `query_filter` to avoid
#           shadowing Python's built-in filter() function
async def get_search_results(query, max_results=MAX_BTN, offset=0, lang=None, quality=None, filter=False):
    """
    Search files from DB.
    lang     — filter by language keyword (e.g. 'Malayalam')
    quality  — filter by quality keyword  (e.g. '720p')
    filter   — accepted for compatibility, not used internally
    Both lang and quality can be combined with a query string.
    """
    query = query.strip()
    if not query:
        raw_pattern = '.'
    elif ' ' not in query:
        raw_pattern = r'(\b|[\.\+\-\_])' + query + r'(\b|[\.\+\-\_])'
    else:
        raw_pattern = query.replace(' ', r'.*[\s\.\+\-\_]')

    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except Exception:
        regex = query

    query_filter = {'file_name': regex}

    # quality filter
    if quality:
        cursor_all = Media.find(query_filter)
        cursor_all.sort('$natural', -1)
        quality_files = [
            f async for f in cursor_all
            if quality.lower() in f.file_name.lower()
        ]
        files = quality_files[offset:][:max_results]
        total_results = len(quality_files)
        next_offset = offset + max_results
        if next_offset >= total_results:
            next_offset = ''
        return files, next_offset, total_results

    cursor = Media.find(query_filter)
    cursor.sort('$natural', -1)

    # language filter
    if lang:
        lang_files = [
            file async for file in cursor
            if lang.lower() in file.file_name.lower()
        ]
        files = lang_files[offset:][:max_results]
        total_results = len(lang_files)
        next_offset = offset + max_results
        if next_offset >= total_results:
            next_offset = ''
        return files, next_offset, total_results

    cursor.skip(offset).limit(max_results)
    files = await cursor.to_list(length=max_results)
    total_results = await Media.count_documents(query_filter)
    next_offset = offset + max_results
    if next_offset >= total_results:
        next_offset = ''
    return files, next_offset, total_results


async def get_bad_files(query, file_type=None, offset=0, filter=False):
    query = query.strip()
    if not query:
        raw_pattern = '.'
    elif ' ' not in query:
        raw_pattern = r'(\b|[\.\+\-\_])' + query + r'(\b|[\.\+\-\_])'
    else:
        raw_pattern = query.replace(' ', r'.*[\s\.\+\-\_]')

    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except Exception:
        return []

    query_filter = {'file_name': regex}
    if file_type:
        query_filter['file_type'] = file_type

    total_results = await Media.count_documents(query_filter)
    cursor = Media.find(query_filter)
    cursor.sort('$natural', -1)
    files = await cursor.to_list(length=total_results)
    return files, total_results


async def get_file_details(query):
    query_filter = {'file_id': query}
    cursor = Media.find(query_filter)
    filedetails = await cursor.to_list(length=1)
    return filedetails


def encode_file_id(s: bytes) -> str:
    r = b""
    n = 0
    for i in s + bytes([22]) + bytes([4]):
        if i == 0:
            n += 1
        else:
            if n:
                r += b"\x00" + bytes([n])
                n = 0
            r += bytes([i])
    return base64.urlsafe_b64encode(r).decode().rstrip("=")


def encode_file_ref(file_ref: bytes) -> str:
    return base64.urlsafe_b64encode(file_ref).decode().rstrip("=")


def unpack_new_file_id(new_file_id):
    """Return file_id, file_ref"""
    decoded = FileId.decode(new_file_id)
    file_id = encode_file_id(
        pack(
            "<iiqq",
            int(decoded.file_type),
            decoded.dc_id,
            decoded.media_id,
            decoded.access_hash
        )
    )
    file_ref = encode_file_ref(decoded.file_reference)
    return file_id, file_ref
