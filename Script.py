class script(object):

    START_TXT = """
Hello {},
I am an Auto Filter Bot. I will give you movies and series.
Add me to your group and index your channel to get started.
"""

    HELP_TXT = """
**Available Commands:**
/start - Start the bot
/help - Get this help message
/about - About this bot
/filter - Add manual filter
/filters - View all filters
/del - Delete a filter
/delall - Delete all filters
/stats - Get database stats
/id - Get Telegram IDs
/info - Get user info
/imdb - Search IMDB
/index - Index a channel
/delete - Delete a file
/deleteall - Delete all indexed files
"""

    ABOUT_TXT = """
**About This Bot**
Bot: {}
Developer: Eva Maria
Language: Python
Library: Pyrogram
"""

    IMDB_TEMPLATE = """
**{title}** ({year})
Rating: {rating}/10
Genres: {genres}
Language: {languages}
"""

    FILE_CAPTION = """**{file_name}**
Size: {file_size}
"""

    BUTTON_LOCK_TXT = """
You need to join our channel to use this bot.
"""

    NO_RESULTS = """
No results found for **{}**
Try a different search term.
"""

    LOG_TEXT_G = """
#NewGroup
Group: {}
ID: {}
Members: {}
By: {}
"""

    LOG_TEXT_P = """
#NewUser
ID: {}
User: {}
"""

    BATCH_FILES_BTN = "Get Files"

    FILE_STORE_LINK = "Here is your file link:\n{}"

    MELCOW_NEW_USERS = """
Welcome {} to {}!
"""

    SPELL_CHECK_TXT = """
Did you mean: **{}** ?
"""

    IMDB_TEMPLATE_TXT = """
**{title}** ({year})
Rating: {rating}
Genres: {genres}
"""

    HOW_TO_DL = """
How to Download

Step 1: Type the movie name in the group.
Step 2: Bot shows results with filter buttons.
Step 3: Pick Language and Quality.
Step 4: Tap Show Results.
Step 5: Click a file — bot sends it to your PM.

Tips:
- Use short movie names
- Try different spellings
- Select language first then quality

Powered by Eva Maria Bot
"""

    FILTER_HEADER = """
Search Results for: {query}
Found: {total} files

Select Language and Quality to filter:
"""

    NO_RESULTS_MSG = """
No Results Found

Movie: {query}

Try:
- Shorter name
- Different spelling
- Remove year from name
"""
