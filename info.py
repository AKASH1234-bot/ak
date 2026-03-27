import re
from os import environ

id_pattern = re.compile(r'^.\d+$')


def is_enabled(value, default):
    if str(value).lower() in ["true", "yes", "1", "enable", "y"]:
        return True
    elif str(value).lower() in ["false", "no", "0", "disable", "n"]:
        return False
    else:
        return default


# ================= BOT INFO ================= #

SESSION = environ.get('SESSION', 'Media_search')
API_ID = int(environ.get('API_ID', '4052973'))
API_HASH = environ.get('API_HASH', '3238bd8ae26df065d11c4054fe8a231c')
BOT_TOKEN = environ.get('BOT_TOKEN', '')


# ================= SETTINGS ================= #

CACHE_TIME = int(environ.get('CACHE_TIME', 300))
USE_CAPTION_FILTER = is_enabled(environ.get('USE_CAPTION_FILTER', "False"), False)

PICS = environ.get(
    'PICS',
    'https://te.legra.ph/file/aa5e35b86c0018c346ca6.jpg'
).split()


# ================= ADMINS ================= #

ADMINS = [
    int(admin) if id_pattern.search(admin) else admin
    for admin in environ.get('ADMINS', '707282066 1746132193').split()
]

CHANNELS = [
    int(ch) if id_pattern.search(ch) else ch
    for ch in environ.get(
        'CHANNELS',
        '-1001642260702 -1001591302937 -1001699721730 -1001663686263'
    ).split()
]

auth_users = [
    int(user) if id_pattern.search(user) else user
    for user in environ.get('AUTH_USERS', '').split()
]

AUTH_USERS = (auth_users + ADMINS) if auth_users else []

auth_channel = environ.get('AUTH_CHANNEL', '-1002059503298')
AUTH_CHANNEL = int(auth_channel) if auth_channel and id_pattern.search(auth_channel) else None

auth_grp = environ.get('AUTH_GROUP')
AUTH_GROUPS = [int(ch) for ch in auth_grp.split()] if auth_grp else None


# ================= REQUIRED CHANNELS ================= #

REQ_CHANNEL_1 = environ.get("REQ_CHANNEL_1", "-1002012736737")
REQ_CHANNEL_1 = int(REQ_CHANNEL_1) if id_pattern.search(str(REQ_CHANNEL_1)) else None

REQ_CHANNEL_2 = environ.get("REQ_CHANNEL_2", "-1002067561371")
REQ_CHANNEL_2 = int(REQ_CHANNEL_2) if id_pattern.search(str(REQ_CHANNEL_2)) else None


# ================= PORT ================= #

PORT = int(environ.get("PORT", 8080))


# ================= DATABASE ================= #

DATABASE_URI = environ.get('DATABASE_URI', 'mongodb+srv://plotlinethe:24DqkVSpG3ibzcC4@cluster0.048lbou.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
DATABASE_NAME = environ.get('DATABASE_NAME', 'AkBot')
COLLECTION_NAME = environ.get('COLLECTION_NAME', 'Telegram_Files')

JOIN_REQS_DB = environ.get("JOIN_REQS_DB", DATABASE_URI)
FILES_DATABASE = environ.get('FILES_DATABASE', DATABASE_URI)

MAX_BTN = int(environ.get('MAX_BTN', 10))


# ================= OTHER SETTINGS ================= #

SPELL_LNK = environ.get('SPELL_LNK', 'https://t.me/+PBf0P-7hMh4yZmM1')
LOG_CHANNEL = int(environ.get('LOG_CHANNEL', '-1001716429576'))
SUPPORT_CHAT = environ.get('SUPPORT_CHAT', 'TeamEvamaria')

P_TTI_SHOW_OFF = is_enabled(environ.get('P_TTI_SHOW_OFF', "False"), False)
IMDB = is_enabled(environ.get('IMDB', "False"), False)
SINGLE_BUTTON = is_enabled(environ.get('SINGLE_BUTTON', "True"), True)

CUSTOM_FILE_CAPTION = environ.get(
    "CUSTOM_FILE_CAPTION",
    "FILE : <code>{file_name}</code>"
)

BATCH_FILE_CAPTION = environ.get("BATCH_FILE_CAPTION", "")

IMDB_TEMPLATE = environ.get(
    "IMDB_TEMPLATE",
    "<b>{title}</b> ({year}) ⭐ {rating}"
)

LONG_IMDB_DESCRIPTION = is_enabled(environ.get("LONG_IMDB_DESCRIPTION", "False"), False)
SPELL_CHECK_REPLY = is_enabled(environ.get("SPELL_CHECK_REPLY", "True"), True)

MAX_LIST_ELM = environ.get("MAX_LIST_ELM", None)

INDEX_REQ_CHANNEL = int(environ.get('INDEX_REQ_CHANNEL', LOG_CHANNEL))

FILE_STORE_CHANNEL = [
    int(ch) for ch in environ.get('FILE_STORE_CHANNEL', '-1001642260702').split()
]

MELCOW_NEW_USERS = is_enabled(environ.get('MELCOW_NEW_USERS', "False"), False)
PROTECT_CONTENT = is_enabled(environ.get('PROTECT_CONTENT', "False"), False)
PUBLIC_FILE_STORE = is_enabled(environ.get('PUBLIC_FILE_STORE', "True"), True)


# ================= URL SHORTENER ================= #

URL_SHORTENR_WEBSITE = environ.get('URL_SHORTENR_WEBSITE', 'ccshort.site')
URL_SHORTNER_WEBSITE_API = environ.get('URL_SHORTNER_WEBSITE_API', 'your_api_key')


# ================= LOG ================= #

LOGO_PATH = environ.get('LOGO_PATH', 'logo.jpg')

LOG_STR = "Bot started successfully with current configuration"
