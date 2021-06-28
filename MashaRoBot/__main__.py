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
NAMA SAYA ROSO..


➪COMING SOON..
"""

buttons = [
    [
        InlineKeyboardButton(
            text="Tambahkan ke Grup", url="t.me/RosoManage_bot?startgroup=true"),
    ],
    [
        InlineKeyboardButton(
            text="About", callback_data="masha_"),
        InlineKeyboardButton(
            text="Plugins", callback_data="help_back"),
    ],
    [  
        InlineKeyboardButton(text="Bantuan", callback_data="aboutmanu_howto"
    ),
    ],
]



HELP_STRINGS = """
*Pengaturan Grup*
"""


DONATE_STRING = """No need.. I'm rich"""

IMPORTED = {}
MIGRATEABLE = []
HELPABLE = {}
STATS = []
USER_INFO = []
DATA_IMPORT = []
DATA_EXPORT = []
CHAT_SETTINGS = {}
USER_SETTINGS = {}

for module_name in ALL_MODULES:
    imported_module = importlib.import_module("MashaRoBot.modules." + module_name)
    if not hasattr(imported_module, "__mod_name__"):
        imported_module.__mod_name__ = imported_module.__name__

    if imported_module.__mod_name__.lower() not in IMPORTED:
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

    if hasattr(imported_module, "__user_info__"):
        USER_INFO.append(imported_module)

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
        chat_id=chat_id,
        text=text,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True,
        reply_markup=keyboard,
    )


@run_async
def test(update: Update, context: CallbackContext):
    # pprint(eval(str(update)))
    # update.effective_message.reply_text("Hola tester! _I_ *have* `markdown`", parse_mode=ParseMode.MARKDOWN)
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
                        [[InlineKeyboardButton(text="⬅️ BACK", callback_data="help_back")]]
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
            "I'm awake already!\n<b>Haven't slept since:</b> <code>{}</code>".format(
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

    print(query.message.chat.id)

    try:
        if mod_match:
            module = mod_match.group(1)
            text = (
                "「 *HELP FOR* *{}* 」:\n".format(
                    HELPABLE[module].__mod_name__
                )
                + HELPABLE[module].__help__
            )
            query.message.edit_text(
                text=text,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True,
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton(text="「 GO BACK 」", callback_data="help_back")]]
                ),
            )

        elif prev_match:
            curr_page = int(prev_match.group(1))
            query.message.edit_text(
                text=HELP_STRINGS,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(curr_page - 1, HELPABLE, "help")
                ),
            )

        elif next_match:
            next_page = int(next_match.group(1))
            query.message.edit_text(
                text=HELP_STRINGS,
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

    except BadRequest:
        pass


@run_async
def Masha_about_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    if query.data == "masha_":
        query.message.edit_text(
            text=""" ℹ️ I'm *SOULMATE*, a powerful group management bot built to help you manage your group easily.
                 ❍ I can restrict users.
                 ❍ I can greet users with customizable welcome messages and even set a group's rules.
                 ❍ I have an advanced anti-flood system.
                 ❍ I can warn users until they reach max warns, with each predefined actions such as ban, mute, kick, etc.
                 ❍ I have a note keeping system, blacklists, and even predetermined replies on certain keywords.
                 ❍ I check for admins' permissions before executing any command and more stuffs
                 \n_LOVELY's licensed under the GNU General Public License v3.0_
                 Here is the [Dev](https://t.me/tushar204).
                 If you have any question about Soulmate, let us know at @SOULMAT3SUPPORTS.""",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [
                 [
                    InlineKeyboardButton(text="Back", callback_data="masha_back")
                 ]
                ]
            ),
        )
    elif query.data == "masha_back":
        query.message.edit_text(
                PM_START_TEXT,
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=ParseMode.MARKDOWN,
                timeout=60,
                disable_web_page_preview=False,
        )


@run_async
def Source_about_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    if query.data == "source_":
        query.message.edit_text(
            text=""" Hi..🤗 I'm *Rosi*
                 \nHere is the [Source Code](https://t.me/arunasupportbot) .""",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=False,
            reply_markup=InlineKeyboardMarkup(
                [
                 [
                    InlineKeyboardButton(text="Go Back", callback_data="source_back")
                 ]
                ]
            ),
        )
    elif query.data == "source_back":
        query.message.edit_text(
                PM_START_TEXT,
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=ParseMode.MARKDOWN,
                timeout=60,
                disable_web_page_preview=False,
        )


    elif query.data == "aboutmanu_permis":
        query.message.edit_text(
            text=f"Selamat datang di menu bantuan"
            f"",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(text="Basic📕", callback_data="aboutmanu_permis"),
                        InlineKeyboardButton(text="Advanced📗", callback_data="aboutmanu_advanced"),
                    ],
                    [
                        InlineKeyboardButton(text="Fun📘", callback_data="aboutmanu_fun"),
                        InlineKeyboardButton(text="Tools📙", callback_data="aboutmanu_alat"),
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
                        InlineKeyboardButton(text="Filters", callback_data="aboutmanu_filters"),
                        InlineKeyboardButton(text="Mute",callback_data="aboutmanu_bisu"),
                    ],
                    [
                        InlineKeyboardButton(text="Rules", callback_data="aboutmanu_rules"),
                        InlineKeyboardButton(text="Tag", callback_data="aboutmanu_tag"),
                        InlineKeyboardButton(text="Warns", callback_data="aboutmanu_ingat"),
                        InlineKeyboardButton(text="Welcome",callback_data="aboutmanu_welcome")
                    ],
                    [   
                        InlineKeyboardButton(text="🔙Kembali", callback_data="aboutmanu_howto")],
                ]
            ),
        )
    elif query.data == "aboutmanu_advanced":
        query.message.edit_text(
            text=f"*Advanced Commands*"
            f"",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(text="Approve", callback_data="aboutmanu_approve"),
                        InlineKeyboardButton(text="Backups", callback_data="aboutmanu_backups"),
                        InlineKeyboardButton(text="Channel", callback_data="aboutmanu_channel"),
                    ],
                    [
                        InlineKeyboardButton(text="Disable", callback_data="aboutmanu_disable"),
                        InlineKeyboardButton(text="Federasi", callback_data="aboutmanu_federasi"),
                        InlineKeyboardButton(text="F-Subs", callback_data="aboutmanu_fsubs"),   
                    ],
                    [
                        InlineKeyboardButton(text="Info", callback_data="aboutmanu_infoo"),
                        InlineKeyboardButton(text="Koneksi", callback_data="aboutmanu_koneksi"),
                        InlineKeyboardButton(text="Blok",callback_data="aboutmanu_blok"),
                    ],
                    [
                        InlineKeyboardButton(text="Md Malam", callback_data="aboutmanu_malam"),
                        InlineKeyboardButton(text="Poll", callback_data="aboutmanu_poll"),
                        InlineKeyboardButton(text="Notes",callback_data="aboutmanu_notes"),
                        InlineKeyboardButton(text="Shield",callback_data="aboutmanu_shield")
                    ],
                    [   
                        InlineKeyboardButton(text="🔙Kembali", callback_data="aboutmanu_howto")],
                ]
            ),
        )
    elif query.data == "aboutmanu_fun":
        query.message.edit_text(
            text=f"*Fun Commands*"
            f"",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(text="Animasi", callback_data="aboutmanu_animasi"),
                        InlineKeyboardButton(text="Anime", callback_data="aboutmanu_anime"),
                    ],
                    [
                        InlineKeyboardButton(text="Cricket", callback_data="aboutmanu_kriket"),
                        InlineKeyboardButton(text="Chatbot", callback_data="aboutmanu_chatbot"),   
                        InlineKeyboardButton(text="Film", callback_data="aboutmanu_film"),
                    ],
                    [
                        InlineKeyboardButton(text="Font", callback_data="aboutmanu_font"),
                        InlineKeyboardButton(text="Logo", callback_data="aboutmanu_logo"),
                        InlineKeyboardButton(text="Musik",callback_data="aboutmanu_musik"),
                    ],
                    [
                        InlineKeyboardButton(text="Random", callback_data="aboutmanu_random"),
                        InlineKeyboardButton(text="Stiker", callback_data="aboutmanu_stiker"),
                        InlineKeyboardButton(text="Youtube", callback_data="aboutmanu_youtube")
                    ],
                    [   
                        InlineKeyboardButton(text="🔙Kembali", callback_data="aboutmanu_howto")],
                ]
            ),
        )
    elif query.data == "aboutmanu_alat":
        query.message.edit_text(
            text=f"*Fun Commands*"
            f"",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(text="Country", callback_data="aboutmanu_negara"),
                        InlineKeyboardButton(text="Extras", callback_data="aboutmanu_ekstra"),
                        InlineKeyboardButton(text="English", callback_data="aboutmanu_english"),
                    ],
                    [
                        InlineKeyboardButton(text="Github", callback_data="aboutmanu_github"),
                        InlineKeyboardButton(text="Google", callback_data="aboutmanu_google"),   
                        InlineKeyboardButton(text="Gps", callback_data="aboutmanu_gps"),
                    ],
                    [
                        InlineKeyboardButton(text="Grammar", callback_data="aboutmanu_grammar"),
                        InlineKeyboardButton(text="G-Trans", callback_data="aboutmanu_gtrans"),
                        InlineKeyboardButton(text="Json",callback_data="aboutmanu_json"),
                    ],
                    [
                        InlineKeyboardButton(text="Math", callback_data="aboutmanu_math"),
                        InlineKeyboardButton(text="Report", callback_data="aboutmanu_report"),
                        InlineKeyboardButton(text="Secure", callback_data="aboutmanu_secure"),
                    ],
                    [
                        InlineKeyboardButton(text="Time", callback_data="aboutmanu_time"),
                        InlineKeyboardButton(text="Tts", callback_data="aboutmanu_tts"),
                        InlineKeyboardButton(text="Weather", callback_data="aboutmanu_cuaca"),
                        InlineKeyboardButton(text="Zipper", callback_data="aboutmanu_zipper")
                    ],
                    [   
                        InlineKeyboardButton(text="🔙Kembali", callback_data="aboutmanu_howto")],
                ]
            ),
        )                
    elif query.data == "aboutmanu_admin":
        query.message.edit_text(
            text=f"*Bantuan untuk ️modul Admin:*"
            f"\n\n*Admin rights:*"
            f"\n❍ /pin: reply pesan untuk disematkan, tambahkan 'loud' atau 'notify' untuk memberikan pemberitahuan kepada anggota."
            f"\n❍ /unpin: melepas pin pesan yang saat ini disematkan."
            f"\n❍ /invitelink: mendapat tautan grup."
            f"\n❍ /promote: mempromosikan pengguna"
            f"\n❍ /demote: menurunkan pengguna."
            f"\n❍ /title (title): menetapkan judul khusus untuk admin yang dipromosikan bot.",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(text="Manage", callback_data="aboutmanu_amanage"),
                        InlineKeyboardButton(text="Cleaner", callback_data="aboutmanu_cleaner"),
                    ],
                    [   
                        InlineKeyboardButton(text="🔙Kembali", callback_data="aboutmanu_permis")],
                ]
            ),
        )
    elif query.data == "aboutmanu_amanage":
        query.message.edit_text(
            text=f"*Bantuan untuk ️modul Admin:*"
            f"\n\n*Manage:*"
            f"\n❍ /admincache: refresh daftar admin."
            f"\n❍ /antispam (on/off): Akan mengaktifkan teknologi antispam kami atau mengembalikan pengaturan Anda saat ini."
            f"\n❍ /setgtitle [new title]: Mengatur judul obrolan baru di grup Anda."
            f"\n❍ /setgpic: Sebagai balasan ke file atau foto untuk mengatur gambar profil grup!"
            f"\n❍ /delgpic: Sama seperti di atas tetapi untuk menghapus foto profil grup."
            f"\n❍ /setsticker: Sebagai balasan untuk beberapa stiker untuk ditetapkan sebagai set stiker grup!"
            f"\n❍ /setdescription (deskripsi): Mengatur deskripsi obrolan baru di grup.",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="Back", callback_data="aboutmanu_admin")]]
            ),
        )
    elif query.data == "aboutmanu_cleaner":
        query.message.edit_text(
            text=f"*Bantuan untuk ️modul Admin:*"
            f"\n\n*Cleaner:*"
            f"\n❍ /zombies: Temukan semua akun yang dihapus di grup Anda."
            f"\n❍ /zombies clean: Hapus semua akun yang dihapus dari grup Anda.",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="Back", callback_data="aboutmanu_admin")]]
            ),
        )
    elif query.data == "aboutmanu_antiflood":
        query.message.edit_text(
            text=f"*Bantuan untuk modul AntiFlood*"
            f"\n\n*Commands*"
            f"\n❍ /flood: Dapatkan pengaturan pengendalian pesan banjir saat ini"
            f"\n❍ /setflood (int/no/off'): mengaktifkan atau menonaktifkan pengendalian pesan banjir"
            f"\n❍ /setfloodmode [ban/kick/mute/tban/tmute] [nilai]: Tindakan yang harus dilakukan ketika pengguna telah melampaui batas pesan banjir. ban/tendangan/bisu/tmute/tban",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(text="About", callback_data="aboutmanu_flood"),
                    ],
                    [   
                        InlineKeyboardButton(text="🔙Kembali", callback_data="aboutmanu_permis")],
                ]
            ),
        )
    elif query.data == "aboutmanu_flood":
        query.message.edit_text(
            text=f"*Bantuan untuk ️modul AntiFlood*"
            f"\n\n*About:*"
            f"\nAntiflood memungkinkan Anda untuk mengambil tindakan pada pengguna yang mengirim lebih dari x pesan berturut-turut. Melebihi banjir yang ditetapkan akan mengakibatkan pembatasan pengguna itu. Ini akan membisukan pengguna jika mereka mengirim lebih dari 10 pesan berturut-turut, bot diabaikan."
            f"\n\n*Catatan:*"
            f"\n • Nilai harus diisi untuk tban dan tmute!!"
            f"\n Ini bisa berupa:"
            f"\n 5m = 5 menit"
            f"\n 6h = 6 jam"
            f"\n 3d = 3 hari"
            f"\n 1w = 1 minggu"
            f"\n\nContoh:"
            f"\n❍ /setflood 5"
            f"\n /setfloodmode tmute 2h:"
            f"\nini akan membisukan pengguna selama 2 jam jika mengirim 5 pesan sekaligus."
            f"\n\n❍ /setflood off: menonaktifkan pengendalian banjir",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="Kembali", callback_data="aboutmanu_antiflood")]]
            ),
        )
    elif query.data == "aboutmanu_banned":
        query.message.edit_text(
            text="*Bantuan untuk moduk Banned:*"
            f"\n\n*Commands:*"
            f"\n❍ /punchme: meninju pengguna yang menggunakan perintah ini"
            f"\n\n*Khusus Admin:*"
            f"\n❍ /ban (userhandle): melarang pengguna.(melalui tag atau balasan)"
            f"\n❍ /sban (userhandle): Diam-diam melarang pengguna. Menghapus perintah, Membalas pesan dan tidak membalas.(melalui tag atau balasan)"
            f"\n❍ /tban (userhandle) x(m/h/d): melarang pengguna untuk x waktu yang ditentukan(melalui tag atau balasan)."
            f"\n❍ /unban (userhandle): membatalkan pemblokiran pengguna(melalui tag atau balasan)"
            f"\n❍ /punch (userhandle): Mengeluarkan pengguna dari grup(melalui tag atau reply).",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(text="About", callback_data="aboutmanu_larang"),
                    ],
                    [   
                        InlineKeyboardButton(text="🔙Kembali", callback_data="aboutmanu_permis")],
                ]
            ),
        )
    elif query.data == "aboutmanu_larang":
        query.message.edit_text(
            text=f"*Bantuan untuk ️modul Banned:*"
            f"\n\n*About:*"
            f"\nm = menit"
            f"\nh = jam"
            f"\nd = hari"
            f"\n\n*Contoh:*"
            f"\n❍ /tban `@username` 1d: ini akan melarang `@username` selama 1 hari.",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="Back", callback_data="aboutmanu_banned")]]
            ),
        )  
    elif query.data == "aboutmanu_blacklist":
        query.message.edit_text(
            text=f"*Bantuan untuk modul Blacklist:*"
            f"\n\n*Commands*"
            f"\n❍ /blacklist: Melihat kata-kata yang masuk daftar hitam saat ini."
            f"\n\n*Khusus Admin:*"
            f"\n❍ /addblacklist (pemicu): Menambahkan pemicu ke daftar hitam."
            f"\n❍ /unblacklist (pemicu): Hapus pemicu dari daftar hitam." 
            f"\n❍ /blacklistmode (off/del/warn/ban/kick/mute/tban/tmute): Tindakan yang dilakukan ketika seseorang mengirim kata-kata yang masuk daftar hitam.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(text="About", callback_data="aboutmanu_listkata"),
                    ],
                    [   
                        InlineKeyboardButton(text="🔙Kembali", callback_data="aboutmanu_permis")],
                ]
            ),
        )
    elif query.data == "aboutmanu_listkata":
        query.message.edit_text(
            text=f"*Bantuan untuk modul Blacklist:*"
            f"\n\n*About*"
            f"\nBlacklist digunakan untuk menghentikan pemicu tertentu agar tidak diucapkan dalam grup. Setiap kali pemicu disebutkan, pesan akan segera dihapus. Kombo yang bagus terkadang memasangkan ini dengan filter Warns(peringatan)!"
            f"\n\nCATATAN: Daftar hitam tidak memengaruhi admin grup"
            f"\n- /blacklist: Setiap baris dianggap sebagai satu pemicu, jadi menggunakan baris yang berbeda akan memungkinkan Anda untuk menambahkan beberapa pemicu."
            f"\n- /unblacklist: Logika baris baru yang sama berlaku di sini, sehingga Anda dapat menghapus beberapa pemicu sekaligus.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="Back", callback_data="aboutmanu_blacklist")]]
            ),
        )
    elif query.data == "aboutmanu_blstiker":
        query.message.edit_text(
            text=f"*Bantuan untuk modul Blacklist Stiker:*"
            f"\n\n*Commands:*"
            f"\n❍ /blsticker: Lihat stiker yang masuk daftar hitam saat ini."
            f"\n\n*Khusus Admin:*"
            f"\n❍ /addblsticker (tautan stiker): Tambahkan pemicu stiker ke daftar hitam. Dapat dilakukan dengan cara reply stiker."
            f"\n❍ /unblsticker (tautan stiker): Hapus pemicu dari daftar hitam. Logika baris baru yang sama berlaku di sini, sehingga Anda dapat menghapus beberapa pemicu sekaligus."
            f"\n❍ /rmblsticker (tautan stiker): Sama seperti di atas."
            f"\n❍ /blstickermode (ban/tban/mute/tmute): mengatur tindakan default tentang apa yang harus dilakukan jika pengguna menggunakan stiker yang masuk daftar hitam.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(text="About", callback_data="aboutmanu_tikell"),
                    ],
                    [   
                        InlineKeyboardButton(text="🔙Kembali", callback_data="aboutmanu_permis")],
                ]
            ),
        )
    elif query.data == "aboutmanu_tikell":
        query.message.edit_text(
            text=f"*Bantuan untuk modul Blacklist Stiker:*"
            f"\n\n*About:*"
            f"\nBlacklist Stiker digunakan untuk menghentikan stiker tertentu. Setiap kali stiker dikirim, pesan akan segera dihapus."
            f"\n\nCATATAN: Daftar hitam tidak memengaruhi admin grup"
            f"\n- Blacklist Stiker tidak memengaruhi admin grup"
            f"\n- Link stiker bisa `https://t.me/addstickers/(nama_stiker)` atau cukup (`@sticker`) atau balas pesan stiker.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="Back", callback_data="aboutmanu_blstiker")]]
            ),
        ) 
    elif query.data == "aboutmanu_bteks":
        query.message.edit_text(
            text=f"*Bantuan untuk modul Blue text:*"
            f"\n\n*About:*"
            f"\nPembersih teks biru menghapus semua perintah yang dibuat-buat dan dikirim orang dalam obrolan Anda."
            f"\n\n*Commands:*"
            f"\n❍ /cleanblue (on/off): bersihkan perintah setelah mengirim."
            f"\n❍ /ignoreblue (kata): mencegah pembersihan otomatis dari perintah itu."
            f"\n❍ /unignoreblue (kata): hapus cegah pembersihan otomatis dari perintah itu."
            f"\n❍ /listblue: daftar perintah yang saat ini masuk daftar putih.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="Back", callback_data="aboutmanu_permis")]]
            ),
        )
    elif query.data == "aboutmanu_hapus":
        query.message.edit_text(
            text=f"*Bantuan untuk modul Delete:*"
            f"\n*Commands:*"
            f"\n❍ /del: menghapus pesan yang Anda balas."
            f"\n❍ /purge: menghapus semua pesan antara ini dan pesan yang dibalas."
            f"\n❍ /purge (nilai x): menghapus pesan yang dibalas, dan nilai x pesan yang mengikutinya jika membalas pesan.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="Back", callback_data="aboutmanu_permis")]]
            ),
        )
    elif query.data == "aboutmanu_filters":
        query.message.edit_text(
            text=f"<b>Bantuan untuk modul Filters:</b>"
            f"\n\n<b>Commands:</b>"
            f"\n❍ /filters: Melihat daftar semua filter aktif yang disimpan dalam obrolan."
            f"\n\n<b>Khusus Admin:</b>"
            f"\n❍ /filter (kata kunci × reply pesan): Tambahkan filter ke obrolan ini. Bot sekarang akan membalas pesan itu setiap kali (kata kunci) disebutkan. Jika Anda membalas ke stiker dengan kata kunci, bot akan membalas dengan stiker itu."
            f"\n❍ /stop (kata kunci): Hentikan filter itu."
            f"\n\n<b>Khusus Owner:</b>"
            f"\n❍ /removeallfilters: Hapus semua filter obrolan sekaligus.",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(text="About", callback_data="aboutmanu_pilter"),
                        InlineKeyboardButton(text="Markdown", callback_data="aboutmanu_fmark"),
                    ],
                    [   
                        InlineKeyboardButton(text="🔙Kembali", callback_data="aboutmanu_permis")],
                ]
            ),
        )
    elif query.data == "aboutmanu_pilter":
        query.message.edit_text(
            text=f"<b>Bantuan untuk modul Filters:</b>"
            f"\n\n<b>About</b>"
            f"\n- Semua kata kunci filter dalam huruf kecil. Jika Anda ingin kata kunci Anda menjadi kalimat, gunakan tanda kutip. misalnya: /filter ”hai yang disana” Bagaimana kabarmu?"
            f"\n- Jika ingin membuat filter dengan balasan yang berbeda, gunakan %%% untuk mendapatkan balasan acak dari setiap filter yang disebutkan."
            f"\n*Contoh:*"
            f"\n /filter ”nama filter”"
            f"\n kata 1"
            f"\n %%%"
            f"\n kata 2"
            f"\n %%%"
            f"\n kata 3"
            f"\n- Filter juga mendukung pemformatan Markdown seperti: {first}, {last} dll. dan tombol. Cek Markdown untuk tahu lebih banyak!",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="Back", callback_data="aboutmanu_filters")]]
            ),
        )
    elif query.data == "aboutmanu_fmark":
        query.message.edit_text(
            text=f"<b>Bantuan untuk modul Filters:</b>"
            f"\n\n<b>Markdownhelp:</b>*"
            f"\nMarkdown adalah alat pemformatan yang sangat kuat yang didukung oleh telegram."
            f"\nRosi memiliki beberapa peningkatan, untuk memastikan bahwa pesan yang disimpan diurai dengan benar, dan juga memungkinkan Anda membuat tombol(button)."
            f"\n\n• _italic_: membungkus teks dengan tanda _ akan menghasilkan teks miring."
            f"\n• *bold*: membungkus teks dengan tanda * akan menghasilkan teks tebal."
            f"\n• code: membungkus teks dengan tanda ` akan menghasilkan teks monospace, atau juga dikenal sebagai 'code'."
            f"\n• [teks](url/link): ini akan membuat tautan - pesan hanya akan menampilkan teks, dan mengetuknya akan membuka halaman di url/link."
            f"\n*Contoh:* [test](example.com)"
            f"\n\n• [buttontext](buttonurl:someURL)"
            f"\nini adalah peningkatan khusus untuk memungkinkan pengguna memiliki tombol telegram dalam Markdown mereka. Buttontext akan menjadi apa yang ditampilkan pada tombol, dan someurl akan menjadi link yang dibuka."
            f"\n*Contoh*: [Ini adalah tombol](buttonurl:example.com)"
            f"\n\nJika Anda ingin beberapa tombol pada baris yang sama, gunakan:(same), seperti:"
            f"\n[satu](buttonurl://example.com)"
            f"\n[dua](buttonurl://google.com:same)"
            f"\nIni akan membuat dua tombol dalam satu baris, bukan satu tombol per baris."
            f"\n\nIngatlah bahwa pesan Anda HARUS berisi beberapa teks selain hanya sebuah tombol!",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="Back", callback_data="aboutmanu_filters")]]
            ),
        )
    elif query.data == "aboutmanu_bisu":
        query.message.edit_text(
            text=f"*Bantuan untuk modul Mute:*"
            f"\n\n*Commands:*"
            f"\n*Khusus Admin:*"
            f"\n❍ /mute (userhandle): membungkam pengguna. Dapat juga digunakan sebagai balasan, menonaktifkan pengguna yang dibalas."
            f"\n❍ /tmute (userhandle) x(m/h/d): membisukan pengguna selama x waktu.(melalui tag atau balasan)."
            f"\n❍ /unmute (userhandle): mengaktifkan suara pengguna. Dapat juga digunakan sebagai balasan, menonaktifkan pengguna yang dibalas.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(text="About", callback_data="aboutmanu_muting"),
                    ],
                    [   
                        InlineKeyboardButton(text="🔙Kembali", callback_data="aboutmanu_permis")],
                ]
            ),
        )
    elif query.data == "aboutmanu_muting":
        query.message.edit_text(
            text=f"*Bantuan untuk modul Mute:*"
            f"\n\n*About:*"
            f"\nm = menit"
            f"\nh = jam"
            f"\nd = hari"
            f"\n\n*Contoh:*"
            f"\n/tmute 10m: ini akan membisukan pengguna selama 10 menit",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="Back", callback_data="aboutmanu_bisu")]]
            ),
        )
    elif query.data == "aboutmanu_rules":
        query.message.edit_text(
            text=f"*Bantuan untuk modul Rules:*"
            f"\n\n*Commands:*"
            f"\n❍ /rules: dapatkan aturan untuk obrolan ini."
            f"\n\n*Khusus Admin:*"
            f"\n❍ /setrules (rules): tetapkan aturan untuk obrolan ini."
            f"\n❍ /clearrules: hapus aturan untuk obrolan ini.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="Back", callback_data="aboutmanu_permis")]]
            ),
        )
    elif query.data == "aboutmanu_tag":
        query.message.edit_text(
            text=f"*Bantuan untuk modul Tag:*"
            f"\n\n*Commands:*"
            f"\n❍ /tagme: mendaftar ke daftar tag obrolan."
            f"\n❍ /untagme: berhenti berlangganan dari daftar tag obrolan."
            f"\n\n*Khusus Admin:*"
            f"\n❍ /tagall: mention semua member yang subscribe."
            f"\n❍ /untagall: menghapus semua anggota yang berlangganan."
            f"\n❍ /addtag ​(userhandle): menambahkan pengguna ke daftar tag obrolan(melalui tag atau balasan)."
            f"\n❍ /removetag (userhandle): menghapus pengguna ke daftar tag obrolan(melalui tag atau balasan).",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(text="About", callback_data="aboutmanu_taging"),
                    ],
                    [   
                        InlineKeyboardButton(text="🔙Kembali", callback_data="aboutmanu_permis")],
                ]
            ),
        )
    elif query.data == "aboutmanu_taging":
        query.message.edit_text(
            text=f"*Bantuan untuk modul Rules:*"
            f"\n\n*About:*"
            f"\nTag adalah fitur penting untuk menyebutkan semua anggota yang berlangganan di grup. Setiap anggota obrolan dapat berlangganan tagger sendiri dengan cara `/tagme` atau anda dapat menambahkan orang lain menggunakan `/addtag @usernamenya`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="Back", callback_data="aboutmanu_tag")]]
            ),
        )
    elif query.data == "aboutmanu_ingat":
        query.message.edit_text(
            text=f"Bantuan untuk modul Warns:"
            f"\n\nCommands:"
            f"\n❍ /warns (userhandle): melihat jumlah warn pengguna, dan alasan dari warn."
            f"\n❍ /warnlist: daftar semua filter peringatan saat ini."
            f"\n\nKhusus Admin:"
            f"\n❍ /warn (userhandle): memperingatkan pengguna. Setelah 3 kali peringatan, pengguna akan diblokir dari grup."
            f"\n❍ /dwarn (userhandle): memperingatkan pengguna dan menghapus pesan. Setelah 3 kali peringatan, pengguna akan diblokir dari grup."
            f"\n❍ /resetwarn (userhandle): mengatur ulang peringatan untuk pengguna. Bisa juga digunakan sebagai balasan."
            f"\n❍ /addwarn (kata kunci x repy pesan): mengatur filter peringatan pada kata kunci tertentu."
            f"\n❍ /nowarn (kata kunci): menghentikan filter peringatan."
            f"\n❍ /warnlimit (jumlah): mengatur batas peringatan."
            f"\n❍ /strongwarn (on/yes): Jika disetel ke on, pengguna yang melebihi batas peringatan akan mengakibatkan banned, yang lainnya hanya akan dikick.",
            disable_web_page_preview=True,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="Kembali", callback_data="aboutmanu_permis")]]
            ),
        )
    elif query.data == "aboutmanu_welcome":
        query.message.edit_text(
            text=f"<b>Bantuan untuk modul Welcome:</b>"
            f"\n\n<b>Khusus Admin:*"
            f"\n\n<b>Welcome:</b>"
            f"\n❍ /welcome (on/off): mengaktifkan/menonaktifkan pesan selamat datang."
            f"\n❍ /welcome: menunjukkan pengaturan selamat datang saat ini."
            f"\n❍ /welcome noformat: menunjukkan pengaturan selamat datang saat ini, tanpa pemformatan - berguna untuk mendaur ulang pesan selamat datang Anda!"
            f"\n\n❍ /setwelcome (teks): mengatur pesan selamat datang khusus. Jika digunakan untuk membalas media, gunakan media tersebut."
            f"\n❍ /resetwelcome: reset ke pesan selamat datang default."
            f"\n❍ /cleanwelcome (on/off): menghapus pesan selamat datang sebelumnya untuk menghindari spam chat."
            f"\n\n❍ /welcomemutehelp: memberikan informasi tentang penyambutan bisu.",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(text="Goodbye", callback_data="aboutmanu_gudbay"),
                        InlineKeyboardButton(text="About", callback_data="aboutmanu_datang"),
                    ],
                    [   
                        InlineKeyboardButton(text="🔙Kembali", callback_data="aboutmanu_permis")],
                ]
            ),
        )
    elif query.data == "aboutmanu_gudbay":
        query.message.edit_text(
            text=f"<b>Bantuan untuk modul Welcome:</b>"
            f"\n\n<b>Goodbye:</b>"
            f"\n❍ /setgoodbye: mengatur pesan selamat tinggal secara default untuk anggota yang keluar."
            f"\n❍ /setgoodbye (teks): mengatur pesan selamat tinggal khusus. Jika digunakan untuk membalas media, maka media tersebut akan diatur sebagai pesan selamat tinggal."
            f"\n❍ /resetgoodbye: reset ke pesan selamat tinggal default."
            f"\n❍ /cleanservice (on/off): menghapus pesan layanan/tanda anggota baru yang bergabung dan keluar.",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="Back", callback_data="aboutmanu_welcome")]]
            ),
        )
    elif query.data == "aboutmanu_approve":
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
    elif query.data == "aboutmanu_backups":
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
    elif query.data == "aboutmanu_channel":
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
    elif query.data == "aboutmanu_disable":
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
    elif query.data == "aboutmanu_federasi":
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
    elif query.data == "aboutmanu_fsubs":
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
    elif query.data == "aboutmanu_infoo":
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
    elif query.data == "aboutmanu_koneksi":
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
    elif query.data == "aboutmanu_blok":
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
    elif query.data == "aboutmanu_malam":
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
    elif query.data == "aboutmanu_poll":
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
    elif query.data == "aboutmanu_notes":
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
    elif query.data == "aboutmanu_animasi":
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
    elif query.data == "aboutmanu_anime":
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
    elif query.data == "aboutmanu_kriket":
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
    elif query.data == "aboutmanu_chatbot":
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
    elif query.data == "aboutmanu_film":
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
    elif query.data == "aboutmanu_font":
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
    elif query.data == "aboutmanu_logo":
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
    elif query.data == "aboutmanu_musik":
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
    elif query.data == "aboutmanu_random":
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
    elif query.data == "aboutmanu_stiker":
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
    elif query.data == "aboutmanu_youtube":
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
    elif query.data == "aboutmanu_negara":
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
    elif query.data == "aboutmanu_ekstra":
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
    elif query.data == "aboutmanu_english":
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
    elif query.data == "aboutmanu_github":
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
    elif query.data == "aboutmanu_google":
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
    elif query.data == "aboutmanu_gps":
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
    elif query.data == "aboutmanu_grammar":
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
    elif query.data == "aboutmanu_gtrans":
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
    elif query.data == "aboutmanu_json":
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
    elif query.data == "aboutmanu_math":
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
    elif query.data == "aboutmanu_report":
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
    elif query.data == "aboutmanu_secure":
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
    elif query.data == "aboutmanu_time":
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
    elif query.data == "aboutmanu_tts":
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
    elif query.data == "aboutmanu_cuaca":
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
    elif query.data == "aboutmanu_zipper":
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

@run_async
def get_help(update: Update, context: CallbackContext):
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
            "Contact me in PM to get the list of possible commands.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text="Help",
                            url="t.me/{}?start=help".format(context.bot.username),
                        )
                    ]
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
                [[InlineKeyboardButton(text="Back", callback_data="help_back")]]
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
def settings_button(update: Update, context: CallbackContext):
    query = update.callback_query
    user = update.effective_user
    bot = context.bot
    mod_match = re.match(r"stngs_module\((.+?),(.+?)\)", query.data)
    prev_match = re.match(r"stngs_prev\((.+?),(.+?)\)", query.data)
    next_match = re.match(r"stngs_next\((.+?),(.+?)\)", query.data)
    back_match = re.match(r"stngs_back\((.+?)\)", query.data)
    try:
        if mod_match:
            chat_id = mod_match.group(1)
            module = mod_match.group(2)
            chat = bot.get_chat(chat_id)
            text = "*{}* has the following settings for the *{}* module:\n\n".format(
                escape_markdown(chat.title), CHAT_SETTINGS[module].__mod_name__
            ) + CHAT_SETTINGS[module].__chat_settings__(chat_id, user.id)
            query.message.reply_text(
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
            chat = bot.get_chat(chat_id)
            query.message.reply_text(
                "Hi there! There are quite a few settings for {} - go ahead and pick what "
                "you're interested in.".format(chat.title),
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(
                        curr_page - 1, CHAT_SETTINGS, "stngs", chat=chat_id
                    )
                ),
            )

        elif next_match:
            chat_id = next_match.group(1)
            next_page = int(next_match.group(2))
            chat = bot.get_chat(chat_id)
            query.message.reply_text(
                "Hi there! There are quite a few settings for {} - go ahead and pick what "
                "you're interested in.".format(chat.title),
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(
                        next_page + 1, CHAT_SETTINGS, "stngs", chat=chat_id
                    )
                ),
            )

        elif back_match:
            chat_id = back_match.group(1)
            chat = bot.get_chat(chat_id)
            query.message.reply_text(
                text="Hi there! There are quite a few settings for {} - go ahead and pick what "
                "you're interested in.".format(escape_markdown(chat.title)),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(0, CHAT_SETTINGS, "stngs", chat=chat_id)
                ),
            )

        # ensure no spinny white circle
        bot.answer_callback_query(query.id)
        query.message.delete()
    except BadRequest as excp:
        if excp.message not in [
            "Message is not modified",
            "Query_id_invalid",
            "Message can't be deleted",
        ]:
            LOGGER.exception("Exception in settings buttons. %s", str(query.data))


@run_async
def get_settings(update: Update, context: CallbackContext):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]

    # ONLY send settings in PM
    if chat.type != chat.PRIVATE:
        if is_user_admin(chat, user.id):
            text = "Click here to get this chat's settings, as well as yours."
            msg.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text="Settings",
                                url="t.me/{}?start=stngs_{}".format(
                                    context.bot.username, chat.id
                                ),
                            )
                        ]
                    ]
                ),
            )
        else:
            text = "Click here to check your settings."

    else:
        send_settings(chat.id, user.id, True)


@run_async
def donate(update: Update, context: CallbackContext):
    user = update.effective_message.from_user
    chat = update.effective_chat  # type: Optional[Chat]
    bot = context.bot
    if chat.type == "private":
        update.effective_message.reply_text(
            DONATE_STRING, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True
        )

        if OWNER_ID != 1677365574 and DONATION_LINK:
            update.effective_message.reply_text(
                "You can also donate to the person currently running me "
                "[here]({})".format(DONATION_LINK),
                parse_mode=ParseMode.MARKDOWN,
            )

    else:
        try:
            bot.send_message(
                user.id,
                DONATE_STRING,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True,
            )

            update.effective_message.reply_text(
                "I've PM'ed you about donating to my creator!"
            )
        except Unauthorized:
            update.effective_message.reply_text(
                "Contact me in PM first to get donation information."
            )


def migrate_chats(update: Update, context: CallbackContext):
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


def main():

    if SUPPORT_CHAT is not None and isinstance(SUPPORT_CHAT, str):
        try:
            dispatcher.bot.sendMessage(f"@{SUPPORT_CHAT}", "Lovely is back with explosive features.✨")
        except Unauthorized:
            LOGGER.warning(
                "Bot isnt able to send message to support_chat, go and check!"
            )
        except BadRequest as e:
            LOGGER.warning(e.message)

    test_handler = CommandHandler("test", test)
    start_handler = CommandHandler("start", start)

    help_handler = CommandHandler("help", get_help)
    help_callback_handler = CallbackQueryHandler(help_button, pattern=r"help_.*")

    settings_handler = CommandHandler("settings", get_settings)
    settings_callback_handler = CallbackQueryHandler(settings_button, pattern=r"stngs_")

    about_callback_handler = CallbackQueryHandler(Masha_about_callback, pattern=r"masha_")
    source_callback_handler = CallbackQueryHandler(Source_about_callback, pattern=r"source_")

    donate_handler = CommandHandler("donate", donate)
    migrate_handler = MessageHandler(Filters.status_update.migrate, migrate_chats)

    # dispatcher.add_handler(test_handler)
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(help_handler)
    dispatcher.add_handler(about_callback_handler)
    dispatcher.add_handler(source_callback_handler)
    dispatcher.add_handler(settings_handler)
    dispatcher.add_handler(help_callback_handler)
    dispatcher.add_handler(settings_callback_handler)
    dispatcher.add_handler(migrate_handler)
    dispatcher.add_handler(donate_handler)

    dispatcher.add_error_handler(error_callback)

    if WEBHOOK:
        LOGGER.info("Using webhooks.")
        updater.start_webhook(listen="0.0.0.0", port=PORT, url_path=TOKEN)

        if CERT_PATH:
            updater.bot.set_webhook(url=URL + TOKEN, certificate=open(CERT_PATH, "rb"))
        else:
            updater.bot.set_webhook(url=URL + TOKEN)

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
