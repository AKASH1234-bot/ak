# database/ia_filterdb_patch.py
# Add this to your existing ia_filterdb.py  — patch increment_request_count into Media class
# and call it from your auto_filter send logic.

from motor.motor_asyncio import AsyncIOMotorClient
import logging

logger = logging.getLogger(__name__)

# ── Paste this method inside your existing Media class in ia_filterdb.py ──────

"""
    @classmethod
    async def increment_request_count(cls, file_id: str):
        \"\"\"Track how many times a file has been requested (for trending).\"\"\"
        try:
            await cls.collection.update_one(
                {"file_id": file_id},
                {"$inc": {"request_count": 1}},
                upsert=False
            )
        except Exception as e:
            pass   # non-critical — don't break filter on error
"""

# ── Also add to ensure_indexes ────────────────────────────────────────────────
"""
    @classmethod
    async def ensure_indexes(cls):
        await cls.collection.create_index([('file_id', 1)])
        await cls.collection.create_index([('file_name', 'text')])
        await cls.collection.create_index([('request_count', -1)])   # ← ADD THIS LINE
"""

# ── In your filter send loop (wherever you send file results), add: ────────────
"""
    from database.ia_filterdb import Media
    await Media.increment_request_count(file.file_id)
"""
