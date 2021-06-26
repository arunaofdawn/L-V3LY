import importlib
import time
import re
from sys import argv
from typing import Optional

from MashaRoBot import (
    ALLOW_EXCL,
    CERT_PATH,
    DONATION_LINK,
    LOGGER,
    OWNER_ID,
    PORT,
    SUPPORT_CHAT,
    TOKEN,
    URL,
    WEBHOOK,
    SUPPORT_CHAT,
    dispatcher,
    StartTime,
    telethn,
    pbot,
    updater,
)

# needed to dynamically load modules
# NOTE: Module order is not guaranteed, specify that in the config file!
from MashaRoBot.modules import ALL_MODULES
from MashaRoBot.modules.helper_funcs.chat_status import is_user_admin
from MashaRoBot.modules.helper_funcs.misc import paginate_modules
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, Update
from telegram.error import (
    BadRequest,
    ChatMigrated,
    NetworkError,
    TelegramError,
    TimedOut,
    Unauthorized,
)
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    Filters,
    MessageHandler,
)
from telegram.ext.dispatcher import DispatcherHandlerStop, run_async
from telegram.utils.helpers import escape_markdown


def get_readable_time(seconds: int) -> str:
    count = 0
    ping_time = ""
    time_list = []
    time_suffix_list = ["s", "m", "h", "days"]

    while count < 4:
        count += 1
        remainder, result = divmod(seconds, 60) if count < 3 else divmod(seconds, 24)
        if seconds == 0 and remainder == 0:
            break
        time_list.append(int(result))
        seconds = int(remainder)

    for x in range(len(time_list)):
        time_list[x] = str(time_list[x]) + time_suffix_list[x]
    if len(time_list) == 4:
        ping_time += time_list.pop() + ", "

    time_list.reverse()
    ping_time += ":".join(time_list)

    return ping_time


PM_START_TEXT = """
Hai yang disana! 
[Grup Manajer](https://t.me/GrupManajerBot) adalah Bot *yang paling lengkap* dan *gratis* untuk membantumu *mengelola* grup anda dengan lebih mudah dan *aman*! 
 
👉🏻 *Tambahkan saya ke Supergrup* dan atur saya sebagai Admin agar saya dapat bertindak!
 
❓ *APA PERINTAHNYA?* ❓
Tekan /help untuk *melihat semua perintah* dan bagaimana mereka bekerja! 
"""

buttons = [
    [   InlineKeyboardButton(text="➕ Tambahkan ke grup ➕", url="t.me/GrupManajerBot?startgroup=start"),
    ],
    [   InlineKeyboardButton(text="👥 Grup", url="https://t.me/nothingspecialonhere/10"),
        InlineKeyboardButton(text="Channel 📢", url="https://t.me/nothingspecialonhere/10"),
    ],
    [
        InlineKeyboardButton(text="🔧 Bantuan",callback_data="help_back"),
        InlineKeyboardButton(text="Informasi 💬",callback_data="aboutmanu_"),   
    ],
    [    
        InlineKeyboardButton(text="🇮🇩 Bahasa 🇮🇩",callback_data="help_back"
        ),
    ],
]

HELP_STRINGS = f"""
*PENGATURAN GRUP*

_Pilih salah satu pengaturan yang ingin anda ubah._
""".format(
    dispatcher.bot.first_name,
    "" if not ALLOW_EXCL else "\nAll commands can either be used with / or !.\n",
)


DONATE_STRING = """Heya, glad to hear you want to donate!
You can donate to the original writer's of the Base code,
Support them  [Inuka](t.me/InukaASiTH),[Jason](t.me/imjanindu),"""

IMPORTED = {}
MIGRATEABLE = []
HELPABLE = {}
STATS = []
USER_INFO = []
USER_BOOK = []
DATA_IMPORT = []
DATA_EXPORT = []

CHAT_SETTINGS = {}
USER_SETTINGS = {}

GDPR = []

for module_name in ALL_MODULES:
    imported_module = importlib.import_module("MashaRoBot.modules." + module_name)
    if not hasattr(imported_module, "__mod_name__"):
        imported_module.__mod_name__ = imported_module.__name__

    if not imported_module.__mod_name__.lower() in IMPORTED:
        IMPORTED[imported_module.__mod_name__.lower()] = imported_module
    else:
        raise Exception("Can't have two modules with the same name! Please change one")

    if hasattr(imported_module, "__help__") and imported_module.__help__:
        HELPABLE[imported_module.__mod_name__.lower()] = imported_module

    # Chats to migrate on chat_migrated events
    if hasattr(imported_module, "__migrate__"):
        MIGRATEABLE.append(imported_module)

    if hasattr(imported_module, "__stats__"):
        STATS.append(imported_module)

    if hasattr(imported_module, "__gdpr__"):
        GDPR.append(imported_module)

    if hasattr(imported_module, "__user_info__"):
        USER_INFO.append(imported_module)

    if hasattr(imported_module, "__user_book__"):
        USER_BOOK.append(imported_module)

    if hasattr(imported_module, "__import_data__"):
        DATA_IMPORT.append(imported_module)

    if hasattr(imported_module, "__export_data__"):
        DATA_EXPORT.append(imported_module)

    if hasattr(imported_module, "__chat_settings__"):
        CHAT_SETTINGS[imported_module.__mod_name__.lower()] = imported_module

    if hasattr(imported_module, "__user_settings__"):
        USER_SETTINGS[imported_module.__mod_name__.lower()] = imported_module


# do not async
def send_help(chat_id, text, keyboard=None):
    if not keyboard:
        keyboard = InlineKeyboardMarkup(paginate_modules(0, HELPABLE, "help"))
    dispatcher.bot.send_message(
        chat_id=chat_id, text=text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard
    )


@run_async
def test(update, context):
    try:
        print(update)
    except:
        pass
    update.effective_message.reply_text(
        "Hola tester! _I_ *have* `markdown`", parse_mode=ParseMode.MARKDOWN
    )
    update.effective_message.reply_text("This person edited a message")
    print(update.effective_message)


@run_async
def start(update: Update, context: CallbackContext):
    args = context.args
    uptime = get_readable_time((time.time() - StartTime))
    if update.effective_chat.type == "private":
        if len(args) >= 1:
            if args[0].lower() == "help":
                send_help(update.effective_chat.id, HELP_STRINGS)
            elif args[0].lower().startswith("ghelp_"):
                mod = args[0].lower().split("_", 1)[1]
                if not HELPABLE.get(mod, False):
                    return
                send_help(
                    update.effective_chat.id,
                    HELPABLE[mod].__help__,
                    InlineKeyboardMarkup(
                        [[InlineKeyboardButton(text="Back", callback_data="help_back")]]
                    ),
                )

            elif args[0].lower().startswith("stngs_"):
                match = re.match("stngs_(.*)", args[0].lower())
                chat = dispatcher.bot.getChat(match.group(1))

                if is_user_admin(chat, update.effective_user.id):
                    send_settings(match.group(1), update.effective_user.id, False)
                else:
                    send_settings(match.group(1), update.effective_user.id, True)

            elif args[0][1:].isdigit() and "rules" in IMPORTED:
                IMPORTED["rules"].send_rules(update, args[0], from_pm=True)

        else:
            update.effective_message.reply_text(
                PM_START_TEXT,
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=ParseMode.MARKDOWN,
                timeout=60,
            )
    else:
        update.effective_message.reply_text(
            "Saya sedang online!\n<b>Online sejak:</b> <code>{}</code>".format(
                uptime
            ),
            parse_mode=ParseMode.HTML,
        )


def error_handler(update, context):
    """Log the error and send a telegram message to notify the developer."""
    # Log the error before we do anything else, so we can see it even if something breaks.
    LOGGER.error(msg="Exception while handling an update:", exc_info=context.error)

    # traceback.format_exception returns the usual python message about an exception, but as a
    # list of strings rather than a single string, so we have to join them together.
    tb_list = traceback.format_exception(
        None, context.error, context.error.__traceback__
    )
    tb = "".join(tb_list)

    # Build the message with some markup and additional information about what happened.
    message = (
        "An exception was raised while handling an update\n"
        "<pre>update = {}</pre>\n\n"
        "<pre>{}</pre>"
    ).format(
        html.escape(json.dumps(update.to_dict(), indent=2, ensure_ascii=False)),
        html.escape(tb),
    )

    if len(message) >= 4096:
        message = message[:4096]
    # Finally, send the message
    context.bot.send_message(chat_id=OWNER_ID, text=message, parse_mode=ParseMode.HTML)


# for test purposes
def error_callback(update: Update, context: CallbackContext):
    error = context.error
    try:
        raise error
    except Unauthorized:
        print("no nono1")
        print(error)
        # remove update.message.chat_id from conversation list
    except BadRequest:
        print("no nono2")
        print("BadRequest caught")
        print(error)

        # handle malformed requests - read more below!
    except TimedOut:
        print("no nono3")
        # handle slow connection problems
    except NetworkError:
        print("no nono4")
        # handle other connection problems
    except ChatMigrated as err:
        print("no nono5")
        print(err)
        # the chat_id of a group has changed, use e.new_chat_id instead
    except TelegramError:
        print(error)
        # handle all other telegram related errors


@run_async
def help_button(update, context):
    query = update.callback_query
    mod_match = re.match(r"help_module\((.+?)\)", query.data)
    prev_match = re.match(r"help_prev\((.+?)\)", query.data)
    next_match = re.match(r"help_next\((.+?)\)", query.data)
    back_match = re.match(r"help_back", query.data)
    try:
        if mod_match:
            module = mod_match.group(1)
            text = (
                "*｢  Help  for  {}  module 」*\n".format(
                    HELPABLE[module].__mod_name__
                )
                + HELPABLE[module].__help__
            )
            query.message.edit_text(
                text=text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton(text="Back", callback_data="help_back")]]
                ),
            )

        elif prev_match:
            curr_page = int(prev_match.group(1))
            query.message.edit_text(
                HELP_STRINGS,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(curr_page - 1, HELPABLE, "help")
                ),
            )

        elif next_match:
            next_page = int(next_match.group(1))
            query.message.edit_text(
                HELP_STRINGS,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(next_page + 1, HELPABLE, "help")
                ),
            )

        elif back_match:
            query.message.edit_text(
                text=HELP_STRINGS,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(0, HELPABLE, "help")
                ),
            )

        # ensure no spinny white circle
        context.bot.answer_callback_query(query.id)
        # query.message.delete()
    except Exception as excp:
        if excp.message == "Message is not modified":
            pass
        elif excp.message == "Query_id_invalid":
            pass
        elif excp.message == "Message can't be deleted":
            pass
        else:
            query.message.edit_text(excp.message)
            LOGGER.exception("Exception in help buttons. %s", str(query.data))


@run_async
def DaisyX_about_callback(update, context):
    query = update.callback_query
    if query.data == "aboutmanu_":
        query.message.edit_text(
            text=f"*Grup Manager* adalah Bot yang copas penampilan dari Grup Help dan hasil cloning dari beberapa repo manager yang ada, daring sejak 23 april 2020 dan terus diperbarui!"
            f"\n\n*Versi Bot:* _2.0_"
            f"\n\nTerima kasih kepada *SaitamaRobot*, *Masha* dan semua manajer peladen lainnya, semua admin bot, semua *pendukung*, dan semua pengguna yang membantu kami dalam mengelola, *donatur*, dan semua pengguna yang melaporkan kesalahan atau fitur baru kepada kami."
            f"\n\nJuga terima kasih kepada *semua grup* yang menggunakan bot kami, kami terus belajar agar tidak copas doang!"
            f"\n💡 [Terms & Conditions](https://telegra.ph/Terms-and-Conditions-06-23)",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(text="Bantuan untuk bot", callback_data="aboutmanu_tac")
                    ],
                    [
                        InlineKeyboardButton(text="🔆 Perintah bot", callback_data="aboutmanu_howto")
                    ],
                    [   
                        InlineKeyboardButton(text="🔙Kembali", callback_data="aboutmanu_back")],
                ]
            ),
        )
    elif query.data == "aboutmanu_back":
        query.message.edit_text(
            PM_START_TEXT,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode=ParseMode.MARKDOWN,
            timeout=60,
        )

    elif query.data == "aboutmanu_howto":
        query.message.edit_text(
            text=f"Selamat datang di menu bantuan"
            f"",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(text="Basic", callback_data="aboutmanu_permis"),
                        InlineKeyboardButton(text="Advanced", url="https://t.me/nothingspecialonhere/10"),
                    ],
                    [
                        InlineKeyboardButton(text="Fun", url="https://t.me/nothingspecialonhere/10"),
                        InlineKeyboardButton(text="Tools", url="https://t.me/nothingspecialonhere/10"),   
                    ],
                    [
                        InlineKeyboardButton(text="➕Bantuan Lengkap➕",callback_data="help_back")
                    ],
                    [   
                        InlineKeyboardButton(text="🔙Kembali", callback_data="aboutmanu_back")],
                ]
            ),
        )
    elif query.data == "aboutmanu_permis":
        query.message.edit_text(
            text=f"*Basic Commands*"
            f"",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(text="Admin", callback_data="aboutmanu_admin"),
                        InlineKeyboardButton(text="AntiFlood", callback_data="aboutmanu_antiflood"),
                        InlineKeyboardButton(text="Banned", callback_data="aboutmanu_banned"),
                    ],
                    [
                        InlineKeyboardButton(text="Blacklist", callback_data="aboutmanu_blacklist"),
                        InlineKeyboardButton(text="Bl Stiker", callback_data="aboutmanu_blstiker"),   
                        InlineKeyboardButton(text="B Teks", callback_data="aboutmanu_bteks"),
                    ],
                    [
                        InlineKeyboardButton(text="Delete", callback_data="aboutmanu_hapus"),
                        InlineKeyboardButton(text="Mute", callback_data="aboutmanu_bisu"),
                        InlineKeyboardButton(text="Rules",callback_data="aboutmanu_rules")
                    ],
                    [
                        InlineKeyboardButton(text="Tag", callback_data="aboutmanu_tag"),
                        InlineKeyboardButton(text="Warns", callback_data="aboutmanu_warns"),
                        InlineKeyboardButton(text="Welcome",callback_data="aboutmanu_welcome")
                    ],
                    [   
                        InlineKeyboardButton(text="🔙Kembali", callback_data="aboutmanu_back")],
                ]
            ),
        )    
    elif query.data == "aboutmanu_admin":
        query.message.edit_text(
            text=f"*{dispatcher.bot.first_name} Is the redisigned version of Daisy and Naruto for the best performance.*"
            f"\n\nBased on [Daisy](https://github.com/inukaasith/daisy) + [Naruto](https://github.com/imjanindu/narutorobot)."
            f"\n\n{dispatcher.bot.first_name}'s source code was written by InukaASiTH and Imjanindu"
            f"\n\nIf Any Question About {dispatcher.bot.first_name}, \nLet Us Know At @{SUPPORT_CHAT}.",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="Kembali ke bantuan", callback_data="aboutmanu_permis")]]
            ),
        )

    elif query.data == "aboutmanu_antiflood":
        query.message.edit_text(
            text=f"*Perintah Dasar*"
            f"\n\n👮🏻Tersedia untuk Admin"
            f"\n🕵🏻Tersedia untuk Semua Anggota"
            f"\n\n👮🏻 `/admincache` memperbarui daftar Admin dan hak istimewanya"
            f"\n\n🕵🏻  `/help` anda dapat melihat atau mengelola semua pengaturan Bot di pm"
            f"\n\n👮🏻  `/ban` anda dapat memblokir pengguna dari grup tanpa memberinya kemungkinan untuk bergabung kembali menggunakan tautan grup"
            f"\n\n👮🏻  `/mute` menempatkan pengguna dalam mode hanya-membaca. Dia bisa membaca tetapi tidak bisa mengirim pesan apapun"
            f"\n\n👮🏻  `/kick` menendang pengguna dari grup, memberinya kemungkinan untuk bergabung kembali menggunakan tautan grup"
            f"\n\n👮🏻  `/unban` menghapus blokiran pengguna dari grup dalam daftar blokiran, memberinya kemungkinan untuk bergabung kembali dengan tautan grup"
            f"\n\n👮🏻  `/info` memberikan informasi tentang pengguna"
            f"\n👮🏻  `/whois` mirip dengan `/info` tetapi lebih simpel"
            f"\n\n◽️ `/admins` memberikan Daftar lengkap admin grup",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="Kembali ke bantuan", callback_data="aboutmanu_permis")]]
            ),
        )
    elif query.data == "aboutmanu_banned":
        query.message.edit_text(
            text="*Perintah Lanjutan*"
            "\n\n🔘Tersedia untuk Admin"
            "\n\n*MANAJEMEN PERINGATAN*"
            "\n👮🏻  `/warn` memberikan peringatan ke pengguna"
            "\n👮🏻  `/resetwarn` balas ke pengguna untuk menghapus warn"
            "\n👮🏻  `/warns` memungkinkan anda melihat dan mengelola peringatan pengguna"
            "\n👮🏻  `/addwarn [kata kunci]` balas ke pesan untuk mengatur filter peringatan pada kata kunci tertentu."
            "\n\n🛃 `/del` menghapus pesan yang dipilih"
            "\n🛃 `/purge` menghapus antara pesan yang dipilih sampai pesan saat ini"
            "\n\n◽️  `/reports [on/off]` mengubah pengaturan laporan, atau melihat status saat ini."
            "\n\n👮🏻 `/antispam [on/off]` Mengatur keamanan antispam di grup. Ini akan membantu melindungi Anda dan grup Anda dengan menghapus pembanjir spam secepat mungkin",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="Kembali ke bantuan", callback_data="aboutmanu_permis")]]
            ),
        )  
    elif query.data == "aboutmanu_blacklist":
        query.message.edit_text(
            text=f"*Perintah Dasar*"
            f"\n\n👮🏻Tersedia untuk Admin"
            f"\n🕵🏻Tersedia untuk Semua Anggota"
            f"\n\n👮🏻 `/admincache` memperbarui daftar Admin dan hak istimewanya"
            f"\n<Code>You must be this chat administrator to perform this action!</code>"
            f"\nThis has nothing to do with {dispatcher.bot.first_name}'s rights; this is all about YOUR permissions as an admin. {dispatcher.bot.first_name} respects admin permissions; if you do not have the Ban Users permission as a telegram admin, you won't be able to ban users with {dispatcher.bot.first_name}. Similarly, to change {dispatcher.bot.first_name} settings, you need to have the Change group info permission."
            f"\n\nThe message very clearly says that you need these rights - <i>not {dispatcher.bot.first_name}.</i>",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="Back", callback_data="aboutmanu_permis")]]
            ),
        )
    elif query.data == "aboutmanu_blstiker":
        query.message.edit_text(
            text=f"*Perintah Dasar*"
            f"\n\n👮🏻Tersedia untuk Admin"
            f"\n🕵🏻Tersedia untuk Semua Anggota"
            f"\n\nIf you are getting a message saying:"
            f"\n<Code>You must be this chat administrator to perform this action!</code>"
            f"\nThis has nothing to do with {dispatcher.bot.first_name}'s rights; this is all about YOUR permissions as an admin. {dispatcher.bot.first_name} respects admin permissions; if you do not have the Ban Users permission as a telegram admin, you won't be able to ban users with {dispatcher.bot.first_name}. Similarly, to change {dispatcher.bot.first_name} settings, you need to have the Change group info permission."
            f"\n\nThe message very clearly says that you need these rights - <i>not {dispatcher.bot.first_name}.</i>",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="Back", callback_data="aboutmanu_permis")]]
            ),
        ) 
    elif query.data == "aboutmanu_bteks":
        query.message.edit_text(
            text=f"*Perintah Dasar*"
            f"\n\n👮🏻Tersedia untuk Admin"
            f"\n🕵🏻Tersedia untuk Semua Anggota"
            f"\n\n👮🏻 `/admincache` memperbarui daftar Admin dan hak istimewanya"
            f"\n<Code>You must be this chat administrator to perform this action!</code>"
            f"\nThis has nothing to do with {dispatcher.bot.first_name}'s rights; this is all about YOUR permissions as an admin. {dispatcher.bot.first_name} respects admin permissions; if you do not have the Ban Users permission as a telegram admin, you won't be able to ban users with {dispatcher.bot.first_name}. Similarly, to change {dispatcher.bot.first_name} settings, you need to have the Change group info permission."
            f"\n\nThe message very clearly says that you need these rights - <i>not {dispatcher.bot.first_name}.</i>",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="Back", callback_data="aboutmanu_permis")]]
            ),
        )
    elif query.data == "aboutmanu_hapus":
        query.message.edit_text(
            text=f"*Perintah Dasar*"
            f"\n\n👮🏻Tersedia untuk Admin"
            f"\n🕵🏻Tersedia untuk Semua Anggota"
            f"\n\nIf you are getting a message saying:"
            f"\n<Code>You must be this chat administrator to perform this action!</code>"
            f"\nThis has nothing to do with {dispatcher.bot.first_name}'s rights; this is all about YOUR permissions as an admin. {dispatcher.bot.first_name} respects admin permissions; if you do not have the Ban Users permission as a telegram admin, you won't be able to ban users with {dispatcher.bot.first_name}. Similarly, to change {dispatcher.bot.first_name} settings, you need to have the Change group info permission."
            f"\n\nThe message very clearly says that you need these rights - <i>not {dispatcher.bot.first_name}.</i>",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="Back", callback_data="aboutmanu_permis")]]
            ),
        )
    elif query.data == "aboutmanu_bisu":
        query.message.edit_text(
            text=f"*Perintah Dasar*"
            f"\n\n👮🏻Tersedia untuk Admin"
            f"\n🕵🏻Tersedia untuk Semua Anggota"
            f"\n\n👮🏻 `/admincache` memperbarui daftar Admin dan hak istimewanya"
            f"\n<Code>You must be this chat administrator to perform this action!</code>"
            f"\nThis has nothing to do with {dispatcher.bot.first_name}'s rights; this is all about YOUR permissions as an admin. {dispatcher.bot.first_name} respects admin permissions; if you do not have the Ban Users permission as a telegram admin, you won't be able to ban users with {dispatcher.bot.first_name}. Similarly, to change {dispatcher.bot.first_name} settings, you need to have the Change group info permission."
            f"\n\nThe message very clearly says that you need these rights - <i>not {dispatcher.bot.first_name}.</i>",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="Back", callback_data="aboutmanu_permis")]]
            ),
        )
    elif query.data == "aboutmanu_rules":
        query.message.edit_text(
            text=f"*Perintah Dasar*"
            f"\n\n👮🏻Tersedia untuk Admin"
            f"\n🕵🏻Tersedia untuk Semua Anggota"
            f"\n\nIf you are getting a message saying:"
            f"\n<Code>You must be this chat administrator to perform this action!</code>"
            f"\nThis has nothing to do with {dispatcher.bot.first_name}'s rights; this is all about YOUR permissions as an admin. {dispatcher.bot.first_name} respects admin permissions; if you do not have the Ban Users permission as a telegram admin, you won't be able to ban users with {dispatcher.bot.first_name}. Similarly, to change {dispatcher.bot.first_name} settings, you need to have the Change group info permission."
            f"\n\nThe message very clearly says that you need these rights - <i>not {dispatcher.bot.first_name}.</i>",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="Back", callback_data="aboutmanu_permis")]]
            ),
        )
    elif query.data == "aboutmanu_tag":
        query.message.edit_text(
            text=f"*Perintah Dasar*"
            f"\n\n👮🏻Tersedia untuk Admin"
            f"\n🕵🏻Tersedia untuk Semua Anggota"
            f"\n\nIf you are getting a message saying:"
            f"\n<Code>You must be this chat administrator to perform this action!</code>"
            f"\nThis has nothing to do with {dispatcher.bot.first_name}'s rights; this is all about YOUR permissions as an admin. {dispatcher.bot.first_name} respects admin permissions; if you do not have the Ban Users permission as a telegram admin, you won't be able to ban users with {dispatcher.bot.first_name}. Similarly, to change {dispatcher.bot.first_name} settings, you need to have the Change group info permission."
            f"\n\nThe message very clearly says that you need these rights - <i>not {dispatcher.bot.first_name}.</i>",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="Back", callback_data="aboutmanu_permis")]]
            ),
       )
    elif query.data == "aboutmanu_warns":
        query.message.edit_text(
            text=f"*Perintah Dasar*"
            f"\n\n👮🏻Tersedia untuk Admin"
            f"\n🕵🏻Tersedia untuk Semua Anggota"
            f"\n\n👮🏻 `/admincache` memperbarui daftar Admin dan hak istimewanya"
            f"\n<Code>You must be this chat administrator to perform this action!</code>"
            f"\nThis has nothing to do with {dispatcher.bot.first_name}'s rights; this is all about YOUR permissions as an admin. {dispatcher.bot.first_name} respects admin permissions; if you do not have the Ban Users permission as a telegram admin, you won't be able to ban users with {dispatcher.bot.first_name}. Similarly, to change {dispatcher.bot.first_name} settings, you need to have the Change group info permission."
            f"\n\nThe message very clearly says that you need these rights - <i>not {dispatcher.bot.first_name}.</i>",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="Back", callback_data="aboutmanu_permis")]]
            ),
        )
    elif query.data == "aboutmanu_welcome":
        query.message.edit_text(
            text=f"*Perintah Dasar*"
            f"\n\n👮🏻Tersedia untuk Admin"
            f"\n🕵🏻Tersedia untuk Semua Anggota"
            f"\n\nIf you are getting a message saying:"
            f"\n<Code>You must be this chat administrator to perform this action!</code>"
            f"\nThis has nothing to do with {dispatcher.bot.first_name}'s rights; this is all about YOUR permissions as an admin. {dispatcher.bot.first_name} respects admin permissions; if you do not have the Ban Users permission as a telegram admin, you won't be able to ban users with {dispatcher.bot.first_name}. Similarly, to change {dispatcher.bot.first_name} settings, you need to have the Change group info permission."
            f"\n\nThe message very clearly says that you need these rights - <i>not {dispatcher.bot.first_name}.</i>",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="Back", callback_data="aboutmanu_permis")]]
            ),
        )      
    elif query.data == "aboutmanu_tac":
        query.message.edit_text(
            text=f"<b> ｢ Terms and Conditions 」</b>\n"
            f"\n<i>To Use This Bot, You Need To Read Terms and Conditions Carefully.</i>\n"
            f"\n✪ We always respect your privacy \n  We never log into bot's api and spying on you \n  We use a encripted database \n  Bot will automatically stops if someone logged in with api."
            f"\n✪ Always try to keep credits, so \n  This hardwork is done by Infinity_Bots team spending many sleepless nights.. So, Respect it."
            f"\n✪ Some modules in this bot is owned by different authors, So, \n  All credits goes to them \n  Also for <b>Paul Larson for Marie</b>."
            f"\n✪ If you need to ask anything about \n  this bot, Go @{SUPPORT_CHAT}."
            f"\n✪ If you asking nonsense in Support \n  Chat, you will get warned/banned."
            f"\n✪ All api's we used owned by originnal authors \n  Some api's we use Free version \n  Please don't overuse AI Chat."
            f"\n✪ We don't Provide any support to forks,\n  So these terms and conditions not applied to forks \n  If you are using a fork of DaisyXBot we are not resposible for anything."
            f"\n\nFor any kind of help, related to this bot, Join @{SUPPORT_CHAT}."
            f"\n\n<i>Terms & Conditions will be changed anytime</i>\n",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(text="Kembali", callback_data="aboutmanu_"),
                    ]
                ]
            ),
        )


@run_async
def get_help(update, context):
    chat = update.effective_chat  # type: Optional[Chat]
    args = update.effective_message.text.split(None, 1)

    # ONLY send help in PM
    if chat.type != chat.PRIVATE:
        if len(args) >= 2 and any(args[1].lower() == x for x in HELPABLE):
            module = args[1].lower()
            update.effective_message.reply_text(
                f"Contact me in PM to get help of {module.capitalize()}",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text="Help",
                                url="t.me/{}?start=ghelp_{}".format(
                                    context.bot.username, module
                                ),
                            )
                        ]
                    ]
                ),
            )
            return
        update.effective_message.reply_text(
            "Penjelasan Perintah",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text="Tekan disini",
                            url="t.me/{}?start=help".format(context.bot.username),
                        )
                    ],
                ]
            ),
        )
        return

    elif len(args) >= 2 and any(args[1].lower() == x for x in HELPABLE):
        module = args[1].lower()
        text = (
            "Here is the available help for the *{}* module:\n".format(
                HELPABLE[module].__mod_name__
            )
            + HELPABLE[module].__help__
        )
        send_help(
            chat.id,
            text,
            InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="Back", callback_data="aboutmanu_howto")]]
            ),
        )

    else:
        send_help(chat.id, HELP_STRINGS)


def send_settings(chat_id, user_id, user=False):
    if user:
        if USER_SETTINGS:
            settings = "\n\n".join(
                "*{}*:\n{}".format(mod.__mod_name__, mod.__user_settings__(user_id))
                for mod in USER_SETTINGS.values()
            )
            dispatcher.bot.send_message(
                user_id,
                "These are your current settings:" + "\n\n" + settings,
                parse_mode=ParseMode.MARKDOWN,
            )

        else:
            dispatcher.bot.send_message(
                user_id,
                "Seems like there aren't any user specific settings available :'(",
                parse_mode=ParseMode.MARKDOWN,
            )

    else:
        if CHAT_SETTINGS:
            chat_name = dispatcher.bot.getChat(chat_id).title
            dispatcher.bot.send_message(
                user_id,
                text="Which module would you like to check {}'s settings for?".format(
                    chat_name
                ),
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(0, CHAT_SETTINGS, "stngs", chat=chat_id)
                ),
            )
        else:
            dispatcher.bot.send_message(
                user_id,
                "Seems like there aren't any chat settings available :'(\nSend this "
                "in a group chat you're admin in to find its current settings!",
                parse_mode=ParseMode.MARKDOWN,
            )


@run_async
def settings_button(update, context):
    query = update.callback_query
    user = update.effective_user
    mod_match = re.match(r"stngs_module\((.+?),(.+?)\)", query.data)
    prev_match = re.match(r"stngs_prev\((.+?),(.+?)\)", query.data)
    next_match = re.match(r"stngs_next\((.+?),(.+?)\)", query.data)
    back_match = re.match(r"stngs_back\((.+?)\)", query.data)
    try:
        if mod_match:
            chat_id = mod_match.group(1)
            module = mod_match.group(2)
            chat = context.bot.get_chat(chat_id)
            text = "*{}* has the following settings for the *{}* module:\n\n".format(
                escape_markdown(chat.title), CHAT_SETTINGS[module].__mod_name__
            ) + CHAT_SETTINGS[module].__chat_settings__(chat_id, user.id)
            query.message.edit_text(
                text=text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text="Back",
                                callback_data="stngs_back({})".format(chat_id),
                            )
                        ]
                    ]
                ),
            )

        elif prev_match:
            chat_id = prev_match.group(1)
            curr_page = int(prev_match.group(2))
            chat = context.bot.get_chat(chat_id)
            query.message.edit_text(
                "Hi there! There are quite a few settings for *{}* - go ahead and pick what "
                "you're interested in.".format(chat.title),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(
                        curr_page - 1, CHAT_SETTINGS, "stngs", chat=chat_id
                    )
                ),
            )

        elif next_match:
            chat_id = next_match.group(1)
            next_page = int(next_match.group(2))
            chat = context.bot.get_chat(chat_id)
            query.message.edit_text(
                "Hi there! There are quite a few settings for *{}* - go ahead and pick what "
                "you're interested in.".format(chat.title),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(
                        next_page + 1, CHAT_SETTINGS, "stngs", chat=chat_id
                    )
                ),
            )

        elif back_match:
            chat_id = back_match.group(1)
            chat = context.bot.get_chat(chat_id)
            query.message.edit_text(
                text="Hi there! There are quite a few settings for *{}* - go ahead and pick what "
                "you're interested in.".format(escape_markdown(chat.title)),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(0, CHAT_SETTINGS, "stngs", chat=chat_id)
                ),
            )

        # ensure no spinny white circle
        context.bot.answer_callback_query(query.id)
        # query.message.delete()
    except Exception as excp:
        if excp.message == "Message is not modified":
            pass
        elif excp.message == "Query_id_invalid":
            pass
        elif excp.message == "Message can't be deleted":
            pass
        else:
            query.message.edit_text(excp.message)
            LOGGER.exception("Exception in settings buttons. %s", str(query.data))


@run_async
def get_settings(update: Update, context: CallbackContext):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]

    # ONLY send settings in PM
    if chat.type != chat.PRIVATE:
        if is_user_admin(chat, user.id):
            text = "Dimana anda ingin membuka menu pengaturan"
            msg.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text="👤 Buka di pesan pribadi",
                                url="t.me/{}?start=help".format(context.bot.username),
                            )
                        ],
                        [   
                            InlineKeyboardButton(text="👥 Buka Disini",callback_data="help_back")],   
                    ]
                ),
            )
        else:
            text = "Click here to check your settings."

    else:
        send_settings(chat.id, user.id, True)


def migrate_chats(update, context):
    msg = update.effective_message  # type: Optional[Message]
    if msg.migrate_to_chat_id:
        old_chat = update.effective_chat.id
        new_chat = msg.migrate_to_chat_id
    elif msg.migrate_from_chat_id:
        old_chat = msg.migrate_from_chat_id
        new_chat = update.effective_chat.id
    else:
        return

    LOGGER.info("Migrating from %s, to %s", str(old_chat), str(new_chat))
    for mod in MIGRATEABLE:
        mod.__migrate__(old_chat, new_chat)

    LOGGER.info("Successfully migrated!")
    raise DispatcherHandlerStop


def is_chat_allowed(update, context):
    if len(WHITELIST_CHATS) != 0:
        chat_id = update.effective_message.chat_id
        if chat_id not in WHITELIST_CHATS:
            context.bot.send_message(
                chat_id=update.message.chat_id, text="Unallowed chat! Leaving..."
            )
            try:
                context.bot.leave_chat(chat_id)
            finally:
                raise DispatcherHandlerStop
    if len(BL_CHATS) != 0:
        chat_id = update.effective_message.chat_id
        if chat_id in BL_CHATS:
            context.bot.send_message(
                chat_id=update.message.chat_id, text="Unallowed chat! Leaving..."
            )
            try:
                context.bot.leave_chat(chat_id)
            finally:
                raise DispatcherHandlerStop
    if len(WHITELIST_CHATS) != 0 and len(BL_CHATS) != 0:
        chat_id = update.effective_message.chat_id
        if chat_id in BL_CHATS:
            context.bot.send_message(
                chat_id=update.message.chat_id, text="Unallowed chat, leaving"
            )
            try:
                context.bot.leave_chat(chat_id)
            finally:
                raise DispatcherHandlerStop
    else:
        pass


@run_async
def donate(update: Update, context: CallbackContext):
    update.effective_message.from_user
    chat = update.effective_chat  # type: Optional[Chat]
    context.bot
    if chat.type == "private":
        update.effective_message.reply_text(
            DONATE_STRING, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True
        )
        update.effective_message.reply_text(
            "You can also donate to the person currently running me "
            "[here]({})".format(DONATION_LINK),
            parse_mode=ParseMode.MARKDOWN,
        )

    else:
        pass


def main():

    if SUPPORT_CHAT is not None and isinstance(SUPPORT_CHAT, str):
        try:
            dispatcher.bot.sendMessage(f"@{SUPPORT_CHAT}", "I am now online!")
        except Unauthorized:
            LOGGER.warning(
                "Bot isnt able to send message to support_chat, go and check!"
            )
        except BadRequest as e:
            LOGGER.warning(e.message)

    # test_handler = CommandHandler("test", test)
    start_handler = CommandHandler("start", start, pass_args=True)

    help_handler = CommandHandler("help", get_help)
    help_callback_handler = CallbackQueryHandler(help_button, pattern=r"help_")

    settings_handler = CommandHandler("settings", get_settings)
    settings_callback_handler = CallbackQueryHandler(settings_button, pattern=r"stngs_")

    about_callback_handler = CallbackQueryHandler(
        DaisyX_about_callback, pattern=r"aboutmanu_"
    )

    donate_handler = CommandHandler("donate", donate)

    migrate_handler = MessageHandler(Filters.status_update.migrate, migrate_chats)
    is_chat_allowed_handler = MessageHandler(Filters.group, is_chat_allowed)

    # dispatcher.add_handler(test_handler)
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(about_callback_handler)
    dispatcher.add_handler(help_handler)
    dispatcher.add_handler(settings_handler)
    dispatcher.add_handler(help_callback_handler)
    dispatcher.add_handler(settings_callback_handler)
    dispatcher.add_handler(migrate_handler)
    dispatcher.add_handler(is_chat_allowed_handler)
    dispatcher.add_handler(donate_handler)

    dispatcher.add_error_handler(error_handler)

    if WEBHOOK:
        LOGGER.info("Using webhooks.")
        updater.start_webhook(listen="0.0.0.0", port=PORT, url_path=TOKEN)

        if CERT_PATH:
            updater.bot.set_webhook(url=URL + TOKEN, certificate=open(CERT_PATH, "rb"))
        else:
            updater.bot.set_webhook(url=URL + TOKEN)
            client.run_until_disconnected()

    else:
        LOGGER.info("Using long polling.")
        updater.start_polling(timeout=15, read_latency=4, clean=True)

    if len(argv) not in (1, 3, 4):
        telethn.disconnect()
    else:
        telethn.run_until_disconnected()

    updater.idle()


if __name__ == "__main__":
    LOGGER.info("Successfully loaded modules: " + str(ALL_MODULES))
    telethn.start(bot_token=TOKEN)
    pbot.start()
    main()
