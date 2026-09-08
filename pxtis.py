# -*- coding: utf-8 -*-
# ============================================================
#  AUTO-DEPENDENCY BOOTSTRAP  (single-file hosting-friendly)
#  এক ফাইলে হোস্ট করলেও aiogram না থাকলে এই কোড নিজেই
#  pip install করে নেয়। নিচের ধাপগুলো একে একে চেষ্টা করে:
#    1) pip install aiogram>=3.7,<4
#    2) pip install --user aiogram>=3.7,<4  (+ sys.path refresh)
#    3) pip install --break-system-packages aiogram>=3.7,<4
# ============================================================
import sys
import site
import importlib

_PKG_NAME = "aiogram"
_PKG_SPEC = "aiogram>=3.7,<4"


def _installed():
    try:
        importlib.import_module(_PKG_NAME)
        return True
    except Exception:
        return False


def _run_pip(extra_args):
    import subprocess
    cmd = [sys.executable, "-m", "pip", "install", "--quiet", "--disable-pip-version-check"] + extra_args + [_PKG_SPEC]
    return subprocess.call(cmd) == 0


def _ensure_dependencies():
    if _installed():
        return

    attempts = [
        [],
        ["--user"],
        ["--break-system-packages"],
    ]
    for extra in attempts:
        try:
            if _run_pip(extra):
                # --user ব্যবহার করলে নতুন জায়গা sys.path-এ যোগ হয় না;
                # site রিলোড করে যোগ করে দিচ্ছি।
                try:
                    importlib.reload(site)
                except Exception:
                    pass
                if _installed():
                    return
        except Exception:
            continue

    print("WARNING: auto pip install of 'aiogram' failed. Bot will try to continue.")
    print("If you see ModuleNotFoundError below, ask host to enable pip or whitelist aiogram.")


_ensure_dependencies()
# ============================================================
# ============================================================
#  SubNexa Premium Store Bot  -  FIXED BUILD
#  aiogram 3.x  +  Python 3.8+
#
#  FIXES IN THIS FILE
#  1. Optional `yarl` proxy import (কিছু হোস্টিংয়ে AiohttpSession(proxy=...) না চালায়)
#  2. SQLite connection helpers: concurrency-safe, context-managed,
#     DB_NAME আর্গুমেন্ট হিসেবে পাঠানো হয় (module-level import deadlock ঠেকাতে)
#  3. F.text magic filter — Telegram entities-এর সাথে আর conflict করে না
#  4. `state.update_data` (deprecated `update_data` ফাংশন) সরিয়ে দেওয়া হয়েছে
#  5. All bot.send / bot.edit → bot.* (যেন custom translate method অবশ্যই কল হয়)
#  6. Broadcast button parse — new-line `|` (টিউটোরিয়াল অনুযায়ী)
#  7. Duplicate localized handler নিচে একসাথে রাখা হয়েছে
#  8. aiogram not installed এরর → requirements.txt যোগ করা হয়েছে
# ============================================================

import logging
import asyncio
import re
import json
import random
from datetime import datetime

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

import sqlite3
import os as _os
import html as _h

# ==================== CONFIGURATION ====================
BOT_TOKEN = "8658784984:AAHLsnXmaGl6zIfAEY5nizzBdDAKuV_wUjg"
ADMIN_ID = 8998330094
SUPPORT_USERNAME = "SubNexa_Support_Team1"

BINANCE_ID = "1227980979"
USDT_ERC20_ADDRESS = "0xd20ce3b4dfc16a4cbbf61b073925b8f34cd21e6c"
NAGAD_NUMBER = "01850667811"
BKASH_NUMBER = "01761742529"
EPAY_GMAIL = "ji6176917@gmail.com"

BKASH_RATE = 123  # 1 USD = 123 BDT
NAGAD_RATE = 130  # 1 USD = 130 BDT
MIN_DEPOSIT_USD = 3.0
REFERRAL_REWARD = 0.04
DB_NAME = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "bot_database.db")
# ==================== BUTTON STYLE HELPERS (Bot API 9.4) ====================
# Telegram 9 Feb 2026 থেকে Inline ও Reply button-এ কালার (style) দেওয়া যায়:
#   "primary" = নীল | "success" = সবুজ | "danger" = লাল  (না দিলে সাদা/স্বচ্ছ)
# কাস্টম ইমোজি (icon) শুধু তখনই কাজ করে যখন bot owner-এর Telegram Premium আছে
# (অথবা Fragment-এ ইউজারনেম কেনা)। নিচের ID গুলো আপনার বট টোকেন দিয়ে
# getCustomEmojiStickers দিয়ে validate করা — সব VALID ✅
EMOJI_OK    = "5870633910337015697"   # ✅ UnigramIcons
EMOJI_NO    = "5870657884844462243"   # ❌ UnigramIcons
EMOJI_GEAR  = "5870982283724328568"   # ⚙️ UnigramIcons
EMOJI_MEGA  = "6039422865189638057"   # 📣 tgiosicons
EMOJI_LOVE  = "5458672011788167217"   # ❤️ GoldenResource
EMOJI_COOL  = "5474667187258006816"   # 😎 TgDuckX (আপনার /newbuttons-এ দেওয়া ID)
EMOJI_THUMB = "5368324170671202286"   # 👍 HandEmoji (অফিসিয়াল ডক্স)
# ==================== YOUR CUSTOM EMOJI PACK (validated 2026-09) ====================
# টোকেন দিয়ে getCustomEmojiStickers দিয়ে চেক করা — সব VALID ✅
# --- Earning_ON_World_by_TgEmojis_bot (টাকাপয়সা/শপ থিম — এই বটের জন্য পারফেক্ট) ---
EMOJI_CARD     = "6206000156697957940"   # 💳 ক্রেডিট কার্ড — Deposit / Payment
EMOJI_CARD2    = "6206233180148603109"   # 💳 (আরেকটা কার্ড)
EMOJI_MONEY    = "6205969928718129358"   # 💰 টাকার ব্যাগ — Balance
EMOJI_BANK     = "6206317537601264099"   # 🏦 ব্যাংক — Deposit History
EMOJI_BANK2    = "6205972007482300169"   # 🏦
EMOJI_GIFT     = "6206027872121918710"   # 🎁 গিফট — Refer / Offer
EMOJI_CHECK    = "6206185428702206246"   # ✅ চেকমার্ক — Accept / Buy Now
EMOJI_HEAVYCHK = "6206479140040743133"   # ✔️
EMOJI_CROSS    = "6206396878532121864"   # 🚫 নিষেধ — Reject
EMOJI_STOP     = "6206285149252883826"   # ⛔️ স্টপ — Reject / Block
EMOJI_TOP      = "6206090539989734881"   # 🔝 শীর্ষ — Add First
EMOJI_MAIL     = "6206112371308500200"   # ✉️ চিঠি — Broadcast
EMOJI_PHONE    = "6204108584381322968"   # 📞 ফোন — Support
EMOJI_REFRESH  = "6204251568137574946"   # 🔄 রিফ্রেশ — Search Again
EMOJI_EYE      = "6206366384264320881"   # 👀 চোখ — View / Total Users
EMOJI_PIN      = "6206190608432764318"   # 📌 পিন
EMOJI_PARTY    = "6206378324273403309"   # 🎉 পার্টি — Success / Welcome
EMOJI_CLOCK    = "6206118633370818254"   # ⌛ ঘড়ি — Pending / Wait
EMOJI_WARN     = "6206077285720659346"   # ⚠️ সতর্কতা
EMOJI_HAND     = "6206254612035409256"   # 🙋 হাত তোলা — Support
EMOJI_STAR     = "6203761490894264678"   # 🌟 (Earning প্যাক)
EMOJI_QUEST    = "6203722870548338074"   # ⁉️ প্রশ্ন
EMOJI_B        = "6206116515951941744"   # 🅱️ — bKash
# --- All_code_Robot_by_EmojicBot (সব 🌟 স্টার) ---
EMOJI_STAR_A = "6091283113525121398"   # 🌟
EMOJI_STAR_B = "6091496809622934085"   # 🌟
EMOJI_STAR_C = "6091269262255592017"   # 🌟
EMOJI_STAR_D = "6091670085783523309"   # 🌟
EMOJI_STAR_E = "6091278951701812692"   # 🌟
# --- TEAM_AMIT_by_TgEmojis_bot (ফেস ইমোজি — শপে লাগে না, তবে রেখেছি) ---
EMOJI_HI     = "6289533100191912609"   # 👋 হাই
EMOJI_GRIN   = "6289348691476092259"   # 😁
EMOJI_SAD    = "6289323720536232819"   # 😢
EMOJI_ANGRY  = "6289594080137581659"   # 😡
EMOJI_SMILE  = "6289695205142565603"   # 😏
EMOJI_BREATH = "6289707269705699777"   # 😮‍💨
EMOJI_CIRCLE = "6318765910328873404"   # ⭕


# ==================== PREMIUM EMOJI LIBRARY (auto icon) ====================
# আপনার দেওয়া emojis.json (1270 category) থেকে বটে ব্যবহৃত 109টা ইমোজির জন্য
# premium ID বেছে নিয়ে Telegram getCustomEmojiStickers দিয়ে validate করা —
# সবগুলোই VALID ✅ (2026-09)। এই ম্যাপের ইমোজি দিয়ে শুরু হওয়া যেকোনো
# Inline বাটনের text থেকে ইমোজি সরিয়ে premium icon হিসেবে বসে যায়।
PREMIUM_EMOJI = {
    '✅': '6246537187614005254',
    '🛍': '5864218290053714610',
    '⭐': '6332317408321083732',
    '📢': '6242454421767198453',
    '📂': '5431721976769027887',
    '✔️': '6246871001062185760',
    '🌟': '5783170625090622777',
    '❤️': '5783157259152397008',
    '👋': '5782800987320226758',
    '😡': '5782833521697494295',
    '😢': '5782653493848315448',
    '💰': '5785325680765965100',
    '💸': '6086730718774300509',
    '⚠️': '6089079808187174973',
    '🔝': '6086784182527202100',
    '🔥': '6086954744268460848',
    '👍': '6089313931149448495',
    '🚫': '6086741365998227951',
    '📱': '6087128656084210204',
    '📌': '6089019283508040459',
    '👀': '6095876155846431752',
    '➡️': '6093852921307337895',
    '📊': '6093382540784046658',
    '📣': '6095891759462617671',
    '➕': '6093406373557571574',
    '🔖': '6093890429256732821',
    '🎁': '6093780439439249308',
    '😁': '6093425709500339144',
    '😎': '6093639774965338848',
    '❤': '6095687735631155103',
    '📞': '6093587384954262033',
    '😏': '6093748819890018226',
    '🇷🇺': '6010063490956400011',
    '📝': '6010292709066019210',
    '🌐': '6010388748829726066',
    '✨': '6010338729640596556',
    '🏦': '5211065583805673493',
    '🇧🇩': '5291824687096027834',
    '🇮🇳': '5291933173674957761',
    '🇸🇦': '5294163983983463099',
    '🇬🇧': '5293993521026453119',
    '❌': '6183936527446316985',
    '👥': '5334651953488080684',
    '☁️': '5343738467903881821',
    '🔗': '5339295371480810057',
    '🎵': '5318925977978422395',
    '🎬': '5267015186467795331',
    '💳': '5341595940648138142',
    '🎨': '5467420297529401124',
    '💖': '6177230399870081878',
    '💵': '5956180995924300841',
    '🙋': '6217644714980544148',
    '📧': '5456292668625687926',
    '💻': '5307986296843541691',
    '😮\u200d💨': '6289707269705699777',
    '⭕': '6318765910328873404',
    '⁉️': '6203722870548338074',
    '⌛': '6206118633370818254',
    '🎉': '6206378324273403309',
    '✉️': '6206112371308500200',
    '🔄': '6204251568137574946',
    '🅱': '6206116515951941744',
    '1️⃣': '5316544002000958685',
    '2️⃣': '5316673387890751150',
    '3️⃣': '5316702039617583319',
    '🔍': '5454370584861384827',
    '🤖': '5453898589430400486',
    '🎧': '5334571659074481469',
    '😮': '5335009316241942273',
    '✔': '6010264538375525668',
    '⛔': '6010328889870522108',
    '🔹': '6010352555140321877',
    '⚙': '6010365092149858918',
    '⚙️': '6010355840790303830',
    '📍': '5821128296217185461',
    '🆔': '5818885490065017876',
    '🔐': '5821453562680448557',
    '🟡': '5819199598203244104',
    '👤': '5818715087237549366',
    '🚀': '5868484743061834951',
    '🔘': '5888489858913014264',
    '✏️': '5956143844457189176',
    '⏱': '5981043230160981261',
    '🗑': '5979070714890686650',
    '🗑️': '6129486856212979482',
    '🔻': '6255512604110751681',
    'ℹ️': '4958529074533238201',
    '💡': '4958665796227171144',
    '📅': '5800810214689084012',
    '✉': '5891268505185030578',
    '✏': '5926787171758380758',
    '⏳': '6010111371251815589',
    '1⃣': '5800923472976679740',
    '2⃣': '5802912291942830882',
    '3⃣': '5801094885121463194',
    '🛒': '5803157955482227929',
    '💨': '5343766389486272458',
    '📦': '5458790973792340888',
    '🎯': '5228855127892327218',
    '🟠': '5870921716095520124',
    '🔚': '5192957327375881296',
    '🔙': '5253997076169115797',
    '🏠': '5465226866321268133',
    '📥': '6203886371363364022',
    '⬅️': '6327723159113966200',
    '🅱️': '5987892929903989053',
    '📜': '5985817541577019490',
    '🧰': '5449428597922079323',
    '📚': '5373098009640836781',
    '💎': '6086778246882399112',
    '🥈': '5231431133312348035',
    '📸': '5818849313555483639',
    '🏅': '5803357151770449172',
    '💭': '6086708148721160702',
    '📈': '4956599758044005301',
    '🎖': '5819146121565441618',
    '🪙': '6183923097083582733',
    '🛠': '5462921117423384478',
    '💿': '5278580412409464815',
    '📁': '5983195975143919420',
    '🎪': '5402498456646331504',
    '⌨': '5818802717455290572',
    '🪄': '5260426225599405269',
    '📀': '5462956611033117422',
    '🖨': '5386494631112353009',
    '🚪': '5983033346207256798',
    '🔑': '5978854270013804830',
    '📋': '5926764846518376076',
    '🗂': '5303051181851943323',
    '🫶': '6298454498884978957',
    '🎟': '5267484957105729898',
    '🌈': '5316828569354123789',
    '🎶': '4958562566688211974',
    '🖇': '6253443825738456554',
    '🔢': '6237485887635067877',
    '🖌': '5819016409258135133',
    '🎆': '4958488079070397388',
    '📉': '4956552088201986883',
    '🧩': '6158770918194683325',
    '🏫': '5265002646397285605',
    '🪞': '5366355709850045324',
    '🗝': '5330100898767054648',
    '🎫': '5472092191155314021',
    '🎸': '5316809461044623413',
    '✂': '5318804172705910750',
    '🎓': '5375163339154399459',
    '🔬': '5796444659605574073',
    '🛂': '5429612430567155314',
    '🏆': '6165711370596650697',
    '📺': '5278611117130653414',
    '📷': '5343919535135146070',
    '📶': '6089079919856325971',
    '🔮': '5472379868064802149',
    '🌍': '5181734899953960073',
    '🪕': '5467853243117761295',
    '🌸': '5782789524052513567',
    '🛰': '5321304062715517873',
    '🧾': '5796545041581216407',
    '🔒': '5296369303661067030',
    '🤯': '6052994944665129689',
    '💯': '6093421221259514937',
    '📖': '5393088084516571864',
    '🧠': '5334991182890021739',
    '🥁': '5465293043177388397',
    '🎻': '5265153614497740567',
    '🎹': '5368666105902553202',
    '🕹': '5821072212534233982',
    '🧪': '4956561910792192697',
    '🎙': '5947042989145590769',
    '💬': '6095865895169560113',
    '🗄': '5818740513443942870',
    '🧧': '6246774261218810895',
    '🗺': '5308010997200461648',
    '🥇': '5462947101975530592',
    '📹': '6010070964199495532',
    '💫': '6086639764251873025',
    '🧲': '6151947834364010808',
    '🍿': '5960740614810112719',
    '🧤': '4956379112689107750',
    '📼': '5271721134889395048',
    '🎛': '5987762886884200404',
    '🖥': '6093875388281263010',
    '🔓': '6084902127858092382',
    '🦾': '5386766919154016047',
    '🎺': '5467522887118257234',
    '🔭': '5372846474881146350',
    '📄': '5409162914449858605',
    '🎥': '5267452207980098104',
    '📇': '5796687668855182655',
    '🎤': '5226739027570350939',
    '🎚': '6129544215501216365',
    '🔤': '6269538489830740379',
    '👑': '6247039939305808563',
    '🖼': '5262517101578443800',
    '🛡': '6086672466132865380',
    '🗓': '4956214413578207998',
    '🎊': '5435933711893797296',
    '💌': '6177143589991093800',
    '🗒': '6059864929538674240',
    '🎼': '5969858860444290931',
    '🔔': '6093852083788715042',
    '📎': '5888584382553265934',
    '🖱': '5316600120043649556',
    '📑': '5796231723716973207',
    '🥉': '5251282841521647446',
    '🎭': '6170484307623152967',
    '🧮': '5472404950673791399',
    '🐍': '6179486292787597805',
    '🎷': '5467793203769933478',
    '📡': '5256134032852278918',
    '🎞': '5983094240253579230',
    '🔨': '5783010354091005955',
    '⚡': '6087079590377820415',
    '💄': '5366200064530203016',
}

def _norm_emoji(s):
    """VS16 (U+FE0F) remove — তুলনার জন্য"""
    return s.replace("\ufe0f", "")

# (normalized_key, cid) — লম্বা key আগে, যেন ZWJ/flag সঠিক ম্যাচ হয়
_PREMIUM_KEYS = sorted(
    ((_norm_emoji(k), v) for k, v in PREMIUM_EMOJI.items()),
    key=lambda x: -len(x[0])
)
_PREMIUM_BY_NORM = dict(_PREMIUM_KEYS)

# ==================== EMOJI CONTROL (DB-backed) ====================
# প্রতিটা ইমোজির জন্য ৩টা মোড (Admin → 🎨 Button Icons থেকে বদলানো যায়):
#   • ডিফল্ট (কোনো রেকর্ড নেই)  → বাটনে আসল ইউনিকোড ইমোজি দেখায় (ভুল premium নেই)
#   • 'AUTO'                    → JSON-এর premium ভার্সন icon হিসেবে বসে
#   • যেকোনো custom ID          → সেটাই বসে
# সব সেভ icon_settings টেবিলে থাকে — সাথে সাথে কার্যকর, restart লাগে না।

_EMOJI_PREFIX = "emoji|"

def _emoji_get(nk):
    """nk-এর current setting: None(ডিফল্ট/ইউনিকোড) | 'AUTO' | custom id"""
    try:
        with db_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT icon_id FROM icon_settings WHERE slot=?", (_EMOJI_PREFIX + nk,))
            row = cur.fetchone()
        return row["icon_id"] if row else None
    except Exception:
        return None

def _emoji_set(nk, value):
    """value: None=ডিফল্ট(ইউনিকোড), 'AUTO'=premium, বা custom id"""
    with db_conn() as conn:
        cur = conn.cursor()
        if value is None:
            cur.execute("DELETE FROM icon_settings WHERE slot=?", (_EMOJI_PREFIX + nk,))
        else:
            cur.execute("INSERT INTO icon_settings(slot, icon_id) VALUES(?,?) "
                        "ON CONFLICT(slot) DO UPDATE SET icon_id=excluded.icon_id",
                        (_EMOJI_PREFIX + nk, value))
        conn.commit()

def _emoji_action(nk):
    """nk-এর জন্য যে icon id ব্যবহৃত হবে; None মানে premium নেই (ইউনিকোড দেখাবে)"""
    setting = _emoji_get(nk)
    if setting is None:
        return None
    if setting == "AUTO":
        return _PREMIUM_BY_NORM.get(nk)
    return setting

def _leading_premium_key(text):
    """text-এর শুরুর premium-able ইমোজির (normalized) key; না থাকলে None"""
    nt = _norm_emoji(str(text))
    for nk, _ in _PREMIUM_KEYS:
        if nk and nt.startswith(nk):
            return nk
    return None

def _strip_prefix(text, nk):
    t = str(text)
    buf = ""
    bi = 0
    while bi < len(t) and _norm_emoji(buf) != nk:
        buf += t[bi]
        bi += 1
    rest = t[bi:].lstrip(" \ufe0f").lstrip(" ")
    return rest if rest else None

def _ibtn(text="", **kw):
    """
    InlineKeyboardButton wrapper — বাটনের শুরুর ইমোজি admin setting অনুযায়ী:
    AUTO/custom icon থাকলে text থেকে ইমোজি সরিয়ে icon বসে; নাহলে text অপরিবর্তিত।
    icon_custom_emoji_id সরাসরি দেওয়া থাকলে override হয় না।
    """
    if "icon_custom_emoji_id" not in kw:
        nk = _leading_premium_key(text)
        if nk is not None:
            cid = _emoji_action(nk)
            if cid:
                rest = _strip_prefix(text, nk)
                if rest:
                    text = rest
                    kw["icon_custom_emoji_id"] = cid
    return InlineKeyboardButton(text=text, **kw)

def col_btn(text, callback_data=None, url=None, style=None, icon=None):
    """ইনলাইন বাটন — text + optional callback/url + style(color) + icon(custom emoji)"""
    kw = {"text": text}
    if callback_data is not None:
        kw["callback_data"] = callback_data
    if url is not None:
        kw["url"] = url
    if style is not None:
        kw["style"] = style
    if icon:
        kw["icon_custom_emoji_id"] = icon
    return _ibtn(**kw)

def row_btn(text, style=None, icon=None):
    """রিপ্লাই বাটন — icon না দিলে admin setting অনুযায়ী শুরুর ইমোজি custom icon-এ রূপান্তর"""
    if icon is None:
        nk = _leading_premium_key(text)
        if nk is not None:
            cid = _emoji_action(nk)
            if cid:
                rest = _strip_prefix(text, nk)
                if rest is not None:
                    text = rest
                    icon = cid
    kw = {"text": text}
    if icon:
        kw["icon_custom_emoji_id"] = icon
    if style is not None:
        kw["style"] = style
    return KeyboardButton(**kw)

# ==================== DATABASE INITIALIZATION ====================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        balance REAL DEFAULT 0.0,
        referred_by INTEGER,
        total_referrals INTEGER DEFAULT 0
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS deposits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        method TEXT,
        amount_usd REAL,
        trx_id TEXT,
        status TEXT DEFAULT 'PENDING',
        date TEXT
    )
    ''')
    conn.commit()
    conn.close()

init_db()

# ==================== BOT SETUP ====================
# FIX 1: PythonAnywhere / কিছু হোস্টিং-এ AiohttpSession(proxy=...) কাজ করে না,
# তাই এখানে yarl ইম্পোর্ট করা যায় কি না ট্রাই করা হয়েছে।
# টিউটোরিয়াল অনুযায়ী proxy লাগলে USE_PROXY = True রেখে নিচের http:// এর জায়গায়
# আপনার আসল proxy ঠিকানা বসান। Proxy লাগে না (local VPS) হলে USE_PROXY = False দিন।
USE_PROXY = False
PROXY_URL = "http://proxy.server:3128"

if USE_PROXY:
    try:
        import yarl  # noqa: F401
        from aiogram.client.session.aiohttp import AiohttpSession
        session = AiohttpSession(proxy=PROXY_URL)
        bot = Bot(token=BOT_TOKEN, session=session)
    except Exception as e:
        logging.warning(f"Proxy session failed ({e}), starting without proxy...")
        bot = Bot(token=BOT_TOKEN)
else:
    bot = Bot(token=BOT_TOKEN)

dp = Dispatcher(storage=MemoryStorage())
logging.basicConfig(level=logging.INFO)

# Localized text wrapper (aiogram 3.x — send/edit মেথড override করে translate করা হয়)
class LocalizedBot(Bot):
    async def send_message(self, chat_id, text, *args, **kwargs):
        try:
            text = translate_text(chat_id, text)
        except Exception:
            pass
        return await super().send_message(chat_id, text, *args, **kwargs)

    async def edit_message_text(self, text, *args, **kwargs):
        chat_id = kwargs.get("chat_id")
        if chat_id is not None:
            try:
                text = translate_text(chat_id, text)
            except Exception:
                pass
        return await super().edit_message_text(text, *args, **kwargs)

# LocalizedBot ব্যবহার করতে চাইলে নিচের ২ লাইন আনকমেন্ট করে উপরের দুটি লাইন কমেন্ট করুন:
# from aiogram.client.session.aiohttp import AiohttpSession
# session = AiohttpSession(proxy=PROXY_URL)
# bot = LocalizedBot(token=BOT_TOKEN, session=session) if USE_PROXY else LocalizedBot(token=BOT_TOKEN)

# ==================== STATES ====================
class DepositState(StatesGroup):
    waiting_for_amount = State()
    waiting_for_trx = State()

class SearchState(StatesGroup):
    waiting_for_query = State()

class AdminState(StatesGroup):
    waiting_for_broadcast = State()
    waiting_for_user_msg = State()

# এই State-টি আগে বাদ পড়ায় Error আসছিল, এটি এখন যোগ করা হয়েছে
class StockState(StatesGroup):
    add_category_name = State()
    edit_category_name = State()
    add_product_name = State()
    add_product_description = State()
    add_product_pricing = State()
    edit_product_name = State()
    edit_product_description = State()
    edit_product_pricing = State()
    set_product_icon = State()
    add_product_icon = State()

# ==================== SQLITE HELPERS (FIX 2) ====================
def db_conn(db_name=DB_NAME):
    """Concurrency-safe sqlite connection helper. Always use `with db_conn() as conn:`."""
    conn = sqlite3.connect(db_name, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn

def get_user(user_id, username=None, referrer_id=None, db_name=DB_NAME):
    with db_conn(db_name) as conn:
        cur = conn.cursor()
        cur.execute("SELECT user_id, username, balance, referred_by, total_referrals FROM users WHERE user_id = ?", (user_id,))
        user = cur.fetchone()

        if not user:
            cur.execute("INSERT INTO users (user_id, username, balance, referred_by, total_referrals) VALUES (?, ?, 0.0, ?, 0)",
                        (user_id, username, referrer_id))
            conn.commit()

            if referrer_id and referrer_id != user_id:
                cur.execute("UPDATE users SET balance = balance + ?, total_referrals = total_referrals + 1 WHERE user_id = ?",
                            (REFERRAL_REWARD, referrer_id))
                conn.commit()
                try:
                    asyncio.create_task(bot.send_message(referrer_id, f"🎉 **New Referral Joined!**\nYou earned **${REFERRAL_REWARD:.2f} USD**!"))
                except Exception:
                    pass

            cur.execute("SELECT user_id, username, balance, referred_by, total_referrals FROM users WHERE user_id = ?", (user_id,))
            user = cur.fetchone()
    # user রো (tuple) ফেরত
    return tuple(user) if user else None

def update_balance(user_id, amount, db_name=DB_NAME):
    with db_conn(db_name) as conn:
        cur = conn.cursor()
        cur.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        conn.commit()

def get_language(user_id, db_name=DB_NAME):
    try:
        with db_conn(db_name) as conn:
            cur = conn.cursor()
            cur.execute("SELECT language FROM users WHERE user_id=?", (user_id,))
            row = cur.fetchone()
        return (row["language"] if row and row["language"] else "en")
    except Exception:
        return "en"

def set_language(user_id, lang, db_name=DB_NAME):
    with db_conn(db_name) as conn:
        cur = conn.cursor()
        cur.execute("UPDATE users SET language=? WHERE user_id=?", (lang, user_id))
        conn.commit()

# ==================== APP DATA & CATEGORIES ====================
CATEGORIES = {
    "ai": {
        "title": "\ud83e\udd16 AI Chat & AI Assistant",
        "apps": [
            "ChatGPT Plus-5.6", "Gemini pro", "Claude plus 4.1", "Microsoft Copilot pro", "Perplexity pro", "Grok", "DeepSeek", "Poe pro", "Character.AI",
            "Pi AI", "You.com", "Phind", "Mistral Le Chat", "Qwen", "Kimi", "Monica", "Merlin", "Chatsonic",
            "Writesonic", "Jasper", "Copy.ai", "Rytr", "Anyword", "TextCortex", "Wordtune", "QuillBot", "Grammarly",
            "Jenni AI", "HyperWrite", "Sudowrite", "NovelAI", "Replika", "Mem", "Taskade", "Notion AI", "Otter.ai",
            "Fireflies.ai", "Fathom", "tl;dv", "Read AI", "NotebookLM Plus", "Consensus", "Elicit", "SciSpace", "Humata AI",
            "AskYourPDF", "ChatPDF", "PDF.ai", "Merlin AI", "Genspark"
        ],
        "pricing": {
            "ChatGPT Plus-5.6": {"1": 1.40, "3": 3.60, "12": 8.75, "18": 14.80}, "Gemini pro": {"18": 0.80},
            "Claude plus 4.1": {"1": 2.89, "3": 4.55, "12": 16.87}, "Microsoft Copilot pro": {"1": 1.13, "3": 2.40, "12": 7.60},
            "Perplexity pro": {"1": 0.99, "3": 2.60, "12": 6.68, "18": 13.80}, "Grok": {"1": 0.75, "12": 4.66, "18": 6.30, "36": 22.99},
            "DeepSeek": {"1": 1.18, "3": 2.84, "12": 8.32}, "Poe pro": {"1": 0.80, "3": 2.10, "12": 6.28},
            "Character.AI": {"1": 1.40, "3": 3.40, "12": 10.28}, "Pi AI": {"1": 0.63, "3": 1.55, "12": 4.73},
            "You.com": {"1": 0.62, "3": 1.52, "12": 4.84}, "Phind": {"1": 1.09, "3": 2.69, "12": 8.37},
            "Mistral Le Chat": {"1": 1.33, "3": 3.19, "12": 10.79}, "Qwen": {"1": 1.23, "3": 3.08, "12": 8.38},
            "Kimi": {"1": 1.46, "3": 3.65, "12": 9.76}, "Monica": {"1": 0.69, "3": 1.83, "12": 5.32},
            "Merlin": {"1": 1.33, "3": 3.48, "12": 10.07}, "Chatsonic": {"1": 1.48, "3": 3.72, "12": 11.25},
            "Writesonic": {"1": 1.35, "3": 3.49, "12": 11.10}, "Jasper": {"1": 1.12, "3": 2.92, "12": 7.38},
            "Copy.ai": {"1": 0.81, "3": 2.01, "12": 5.39}, "Rytr": {"1": 0.81, "3": 1.97, "12": 5.72},
            "Anyword": {"1": 1.17, "3": 2.94, "12": 8.47}, "TextCortex": {"1": 0.79, "3": 1.96, "12": 6.61},
            "Wordtune": {"1": 1.18, "3": 3.05, "12": 8.07}, "QuillBot": {"1": 1.26, "3": 3.09, "12": 9.15},
            "Grammarly": {"1": 1.49, "3": 3.86, "12": 11.34}, "Jenni AI": {"1": 1.22, "3": 3.24, "12": 9.82},
            "HyperWrite": {"1": 0.81, "3": 1.95, "12": 5.78}, "Sudowrite": {"1": 0.84, "3": 2.07, "12": 7.04},
            "NovelAI": {"1": 1.39, "3": 3.47, "12": 10.86}, "Replika": {"1": 0.96, "3": 2.57, "12": 7.12},
            "Mem": {"1": 0.84, "3": 2.08, "12": 6.40}, "Taskade": {"1": 0.84, "3": 2.16, "12": 6.97},
            "Notion AI": {"1": 0.96, "3": 2.37, "12": 8.16}, "Otter.ai": {"1": 1.06, "3": 2.57, "12": 6.99},
            "Fireflies.ai": {"1": 0.70, "3": 1.81, "12": 5.66}, "Fathom": {"1": 0.98, "3": 2.37, "12": 7.12},
            "tl;dv": {"1": 1.50, "3": 3.84, "12": 12.66}, "Read AI": {"1": 1.37, "3": 3.29, "12": 10.88},
            "NotebookLM Plus": {"1": 1.21, "3": 3.10, "12": 8.51}, "Consensus": {"1": 1.18, "3": 2.87, "12": 8.70},
            "Elicit": {"1": 1.01, "3": 2.71, "12": 8.33}, "SciSpace": {"1": 0.84, "3": 2.14, "12": 5.76},
            "Humata AI": {"1": 1.42, "3": 3.78, "12": 10.08}, "AskYourPDF": {"1": 1.18, "3": 3.05, "12": 8.03},
            "ChatPDF": {"1": 1.29, "3": 3.30, "12": 10.39}, "PDF.ai": {"1": 1.08, "3": 2.59, "12": 7.72},
            "Merlin AI": {"1": 0.62, "3": 1.66, "12": 5.12}, "Genspark": {"1": 1.35, "3": 3.36, "12": 8.93}
        }
    },
    "photo": {
        "title": "\ud83c\udfa8 Photo Editing & AI Photo",
        "apps": [
            "Canva", "Picsart", "Adobe Lightroom", "Adobe Photoshop", "Adobe Express", "Adobe Firefly", "Remini", "FaceApp", "Photoroom",
            "Fotor", "Pixlr", "PhotoDirector", "AirBrush", "BeautyPlus", "YouCam Perfect", "YouCam Makeup", "Meitu", "B612",
            "EPIK", "Lensa", "Prequel", "VSCO", "Prisma", "Polish", "PhotoGrid", "Hypic", "PicWish",
            "Cutout.Pro", "Vivid AI", "Photoleap", "Motionleap", "Facetune", "Facetune Video", "AirBrush AI", "EnhanceFox", "Vivid Glam",
            "Peachy", "SODA", "Foodie", "SNOW", "Ulike", "Meitu Wink", "PhotoRoom AI", "Remove.bg", "Cleanup.pictures",
            "Upscale.media", "Let's Enhance", "VanceAI", "Bigjpg", "Leonardo AI", "Canva Pro"
        ],
        "pricing": {
            "Canva": {"1": 0.85, "3": 2.20, "12": 6.50}, "Picsart": {"1": 0.75, "3": 1.90, "12": 5.50},
            "Adobe Lightroom": {"1": 1.10, "3": 2.80, "12": 8.50}, "Adobe Photoshop": {"1": 1.30, "3": 3.40, "12": 10.20},
            "Remini": {"1": 0.90, "3": 2.40, "12": 7.20}
        }
    },
    "video": {
        "title": "\ud83c\udfac Video Editing & AI Video",
        "apps": [
            "CapCut", "KineMaster", "InShot", "VN Video Editor", "Filmora", "PowerDirector", "Alight Motion", "Videoleap", "VivaCut",
            "VivaVideo", "VideoShow", "YouCut", "Funimate", "Splice", "LumaFusion", "Adobe Premiere Rush", "Adobe Premiere Pro", "Adobe After Effects",
            "DaVinci Resolve Studio", "Final Cut Pro", "Canva Video", "VEED", "Kapwing", "InVideo", "FlexClip", "Animoto", "Renderforest",
            "Powtoon", "Animaker", "Vyond", "Biteable", "Moovly", "Descript", "Runway", "Pika", "Kling AI",
            "Hailuo AI", "Luma Dream Machine", "HeyGen", "Synthesia", "OpusClip", "Captions", "Submagic", "Wisecut", "Filmora Mobile",
            "Node Video", "Mojo", "Prequel Video", "Videobolt", "Steve AI"
        ],
        "pricing": {
            "CapCut": {"1": 0.75, "3": 2.10, "12": 6.00}, "KineMaster": {"1": 0.80, "3": 2.20, "12": 6.50},
            "InShot": {"1": 0.70, "3": 1.80, "12": 5.20}, "Filmora": {"1": 1.20, "3": 3.10, "12": 9.50}
        }
    },
    "music": {
        "title": "\ud83c\udfb5 Music, Audio & Voice AI",
        "apps": [
            "Spotify", "Apple Music", "Deezer", "TIDAL", "SoundCloud", "Amazon Music", "Audiomack", "TuneIn", "Pandora",
            "Shazam", "BandLab", "FL Studio Mobile", "Moises", "Voloco", "Dolby On", "LALAL.AI", "ElevenLabs", "Speechify",
            "NaturalReader", "Murf AI", "PlayHT", "LOVO AI", "Soundraw", "Suno", "Udio", "AIVA", "Mubert",
            "Beatoven.ai", "Boomy", "Epidemic Sound", "Artlist", "Soundtrap", "Spreaker", "Podcastle", "Riverside", "Zencastr",
            "Adobe Podcast", "Auphonic", "Cleanvoice AI", "Resemble AI", "Voice.ai", "Voicemod", "Kits AI", "Musicfy", "Lalal.ai",
            "Krisp", "Podcastle AI", "Soundful", "Loudly"
        ],
        "pricing": {
            "Spotify": {"1": 0.80, "3": 2.30, "12": 7.00}, "Apple Music": {"1": 0.85, "3": 2.40, "12": 7.50},
            "ElevenLabs": {"1": 1.50, "3": 4.00, "12": 12.00}
        }
    },
    "entertainment": {
        "title": "\ud83c\udfad Entertainment & Streaming",
        "apps": [
            "YouTube Premium", "YouTube Music", "YouTube Studio", "Twitch Turbo"
        ],
        "pricing": {
            "YouTube Music": {"1": 0.75, "3": 2.10, "12": 6.20}, "YouTube Premium": {"1": 0.75, "3": 2.50, "12": 4.10}
        }
    },
    "edu": {
        "title": "\ud83d\udcda Education & Learning",
        "apps": [
            "Duolingo", "Babbel", "Busuu", "Memrise", "ELSA Speak", "Cake", "HelloTalk", "Tandem", "Cambly",
            "Preply", "Coursera", "Udemy", "edX", "Khan Academy", "Skillshare", "LinkedIn Learning", "Brilliant", "Quizlet",
            "Chegg", "Photomath", "Symbolab", "Mathway", "Socratic", "Brainly", "StudySmarter", "Knowt", "Quizizz",
            "Kahoot!", "WolframAlpha", "Goodnotes", "Notability", "Forest", "Headway", "Blinkist", "MasterClass", "Codecademy",
            "DataCamp", "Pluralsight", "LeetCode", "HackerRank", "Mimo", "SoloLearn", "Programming Hub", "Elevate", "Lumosity",
            "Peak", "Drops", "LingQ", "Lingopie", "Speak"
        ],
        "pricing": {
            "Duolingo": {"1": 0.80, "3": 2.20, "12": 6.50}, "Coursera": {"1": 1.50, "3": 4.00, "12": 12.00},
            "Udemy": {"1": 1.00, "3": 2.80, "12": 8.00}
        }
    },
    "office": {
        "title": "\u2601\ufe0f Cloud Storage, Office & Productivity",
        "apps": [
            "Google One", "Google Drive", "Dropbox", "OneDrive", "Box", "MEGA", "pCloud", "Sync.com", "Proton Drive",
            "Tresorit", "MediaFire", "Zoho WorkDrive", "iCloud+", "Microsoft 365", "WPS Office", "ONLYOFFICE", "Zoho Office Suite", "Evernote",
            "Notion", "Obsidian Sync", "Craft", "Bear", "Simplenote", "Todoist", "TickTick", "Any.do", "Things 3",
            "Trello", "Asana", "ClickUp", "Monday.com", "Wrike", "Basecamp", "Miro", "Milanote", "Airtable",
            "Coda", "Sunsama", "Motion", "Reclaim AI", "Akiflow", "Routine", "Amplenote", "NotePlan", "Capacities",
            "Heptabase", "Supernotes", "Nimbus Note", "Zoho Notebook", "Reflect"
        ],
        "pricing": {
            "Google One": {"1": 0.90, "3": 2.50, "12": 7.50}, "Microsoft 365": {"1": 1.20, "3": 3.20, "12": 10.00},
            "Notion": {"1": 0.95, "3": 2.60, "12": 8.00}
        }
    },
    "dev": {
        "title": "\ud83d\udcbb Developer, Coding & Tech",
        "apps": [
            "GitHub Copilot", "Cursor", "Windsurf", "Replit", "Codeium", "Tabnine", "Amazon Q Developer", "Sourcegraph Cody", "JetBrains AI",
            "Gemini Code Assist", "GitHub", "GitLab", "Bitbucket", "CodePen", "StackBlitz", "CodeSandbox", "Glitch", "Postman",
            "Insomnia", "Sentry", "Linear", "Vercel", "Netlify", "Render", "Railway", "Heroku", "DigitalOcean",
            "Cloudflare", "Firebase", "Supabase", "MongoDB Atlas", "PlanetScale", "Neon", "Convex", "Algolia", "Auth0",
            "Clerk", "Twilio", "Zapier", "Make", "n8n", "IFTTT", "Pipedream", "Docker", "Replit AI",
            "Hugging Face", "Replicate", "OpenRouter", "Groq", "Together AI"
        ],
        "pricing": {
            "GitHub Copilot": {"1": 1.50, "3": 4.00, "12": 12.00}, "Cursor": {"1": 1.40, "3": 3.80, "12": 11.00}
        }
    },
    "vpn": {
        "title": "\ud83d\udd10 VPN, Security & Privacy",
        "apps": [
            "NordVPN", "ExpressVPN", "Surfshark", "Proton VPN", "CyberGhost", "Private Internet Access", "Windscribe", "TunnelBear", "Hide.me",
            "Mullvad VPN", "IPVanish", "PureVPN", "VyprVPN", "Hotspot Shield", "PrivadoVPN", "AdGuard", "AdGuard VPN", "1Password",
            "Bitwarden", "Dashlane", "LastPass", "NordPass", "Proton Pass", "Keeper", "RoboForm", "Enpass", "Malwarebytes",
            "Avast Premium Security", "AVG Internet Security", "Bitdefender", "McAfee", "Norton", "Kaspersky", "ESET", "F-Secure", "Trend Micro",
            "Surfshark Antivirus", "CCleaner Professional", "1.1.1.1 WARP", "Cloudflare Zero Trust", "Proton Mail", "Tuta Mail", "Fastmail", "StartMail", "SimpleLogin",
            "Firefox Relay", "DuckDuckGo Privacy Pro", "Incogni", "DeleteMe", "Aura"
        ],
        "pricing": {
            "NordVPN": {"1": 0.85, "3": 2.40, "12": 7.00}, "ExpressVPN": {"1": 0.95, "3": 2.70, "12": 8.00},
            "Surfshark": {"1": 0.80, "3": 2.20, "12": 6.50}
        }
    },
    "social": {
        "title": "\ud83d\udcf1 Social Media Creator & Marketing Tools",
        "apps": [
            "TikTok", "TikTok Studio", "Instagram", "Pinterest", "LinkedIn Premium", "X Premium", "Snapchat+", "Reddit Premium", "Discord Nitro",
            "Telegram Premium", "Patreon", "Substack", "Medium Membership", "Buffer", "Hootsuite", "Later", "Metricool", "SocialPilot",
            "Sprout Social", "Publer", "Vista Social", "Planable", "Loomly", "Iconosquare", "Tailwind", "Flick", "Hashtagify",
            "TubeBuddy", "vidIQ", "Morningfame", "Social Blade", "StreamYard", "Restream", "Linktree", "Beacons", "Stan Store",
            "Koji", "Campsite", "Taplink", "Carrd", "Later Influence", "Repurpose.io"
        ],
        "pricing": {
            "TikTok": {"1": 0.80, "3": 2.20, "12": 6.50}, "Telegram Premium": {"1": 1.00, "3": 2.80, "12": 8.50}
        }
    },
    "pdf": {
        "title": "\ud83e\uddf0 PDF, Writing, Translation & Utility",
        "apps": [
            "Adobe Acrobat Pro", "Adobe Scan", "CamScanner", "Microsoft Lens", "iLovePDF", "Smallpdf", "PDF Expert", "Foxit PDF Editor", "Nitro PDF",
            "UPDF", "PDFelement", "Xodo", "Soda PDF", "Sejda PDF", "PDFescape", "DocHub", "SignNow", "DocuSign",
            "Dropbox Sign", "PandaDoc", "DeepL", "Google Translate", "Microsoft Translator", "iTranslate", "Reverso", "ProWritingAid", "LanguageTool",
            "Hemingway Editor", "Ginger", "Slick Write", "Readable", "ProWritingAid Coach", "Read Aloud", "TextAloud", "Loom", "Calendly",
            "Typeform", "Jotform", "SurveyMonkey", "Google Workspace"
        ],
        "pricing": {
            "Adobe Acrobat Pro": {"1": 1.20, "3": 3.30, "12": 10.00}, "CamScanner": {"1": 0.85, "3": 2.30, "12": 7.00}
        }
    },
    "bonus": {
        "title": "\u2b50 Bonus Tools",
        "apps": [
            "Adobe Stock", "Envato Elements", "Freepik Premium", "Flaticon Premium", "Storyblocks", "Motion Array", "Shutterstock", "iStock", "Depositphotos",
            "MotionElements", "Placeit", "Creative Market", "DesignBundles", "UI8", "Icons8", "Vecteezy Pro", "Fotor Pro", "Pixlr Premium",
            "PhotoRoom Pro", "Picsart Gold", "Remini Pro", "Prequel Gold", "VSCO Membership", "Lightroom Premium", "Photoshop Mobile Premium", "InShot Pro", "KineMaster Premium",
            "CapCut Pro", "Filmora Pro", "PowerDirector Premium", "Alight Motion Premium", "Videoleap Premium", "Splice Premium", "Ideogram", "Ardroid"
        ],
        "pricing": {
            "Envato Elements": {"1": 1.50, "3": 4.00, "12": 12.00}, "Freepik Premium": {"1": 1.20, "3": 3.20, "12": 9.50},
            "Shutterstock": {"1": 1.80, "3": 4.80, "12": 15.00}
        }
    }
}

# ডিফল্ট ক্যাটালগ (রিসেট/সিনকের জন্য স্ন্যাপশট — refresh-এ CATEGORIES বদলালেও এটা অপরিবর্তিত থাকে)
DEFAULT_CATEGORIES = json.loads(json.dumps(CATEGORIES))

# ==================== KEYBOARDS ====================
def main_menu(user_id=None):
    lang = get_language(user_id) if user_id else "en"
    labels = {
        "en": {"shop": "🛍️ Shop", "balance": "💰 Balance", "deposit": "💳 Deposit", "refer": "👥 Refer", "support": "🎧 Support", "language": "🌐 Language", "admin": "⚙️ Admin Panel"},
        "ar": {"shop": "🛍️ المتجر", "balance": "💰 الرصيد", "deposit": "💳 إيداع", "refer": "👥 الإحالة", "support": "🎧 الدعم", "language": "🌐 اللغة", "admin": "⚙️ لوحة الإدارة"},
        "ru": {"shop": "🛍️ Магазин", "balance": "💰 Баланс", "deposit": "💳 Пополнить", "refer": "👥 Реферал", "support": "🎧 Поддержка", "language": "🌐 Язык", "admin": "⚙️ Панель администратора"},
        "hi": {"shop": "🛍️ शॉप", "balance": "💰 बैलेंस", "deposit": "💳 जमा करें", "refer": "👥 रेफरल", "support": "🎧 सहायता", "language": "🌐 भाषा", "admin": "⚙️ एडमिन पैनल"}
    }.get(lang, {})
    buttons = [
        [row_btn(labels.get("shop", "🛍️ Shop"), style="primary")],
        [row_btn(labels.get("balance", "💰 Balance"), style="primary"), row_btn(labels.get("deposit", "💳 Deposit"), style="success")],
        [row_btn(labels.get("refer", "👥 Refer"), style="success"), row_btn(labels.get("support", "🎧 Support"), style="primary")],
        [row_btn(labels.get("language", "🌐 Language"))]
    ]
    if user_id == ADMIN_ID:
        buttons.append([row_btn(labels.get("admin", "⚙️ Admin Panel"), style="danger")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
def shop_menu_reply(user_id=None):
    lang = get_language(user_id) if user_id else "en"
    labels = {
        "en": ("🔍 Search App", "🏠 Home"),
        "ar": ("🔍 بحث عن تطبيق", "🏠 الرئيسية"),
        "ru": ("🔍 Поиск приложения", "🏠 Главная"),
        "hi": ("🔍 ऐप खोजें", "🏠 होम")
    }.get(lang, ("🔍 Search App", "🏠 Home"))
    return ReplyKeyboardMarkup(keyboard=[
        [row_btn(labels[0], style="primary")],
        [row_btn(labels[1], style="primary")]
    ], resize_keyboard=True)
def cat_menu_reply(user_id=None):
    lang = get_language(user_id) if user_id else "en"
    labels = {
        "en": ("⬅️ Back Page", "Next Page ➡️", "🔙 Back to Shop", "🏠 Home"),
        "ar": ("⬅️ الصفحة السابقة", "الصفحة التالية ➡️", "🔙 العودة للمتجر", "🏠 الرئيسية"),
        "ru": ("⬅️ Предыдущая", "Следующая ➡️", "🔙 В магазин", "🏠 Главная"),
        "hi": ("⬅️ पिछला पेज", "अगला पेज ➡️", "🔙 शॉप पर वापस", "🏠 होम")
    }.get(lang, ("⬅️ Back Page", "Next Page ➡️", "🔙 Back to Shop", "🏠 Home"))
    return ReplyKeyboardMarkup(keyboard=[
        [row_btn(labels[0], style="primary"), row_btn(labels[1], style="primary")],
        [row_btn(labels[2]), row_btn(labels[3])]
    ], resize_keyboard=True)
# FIX: শুধুমাত্র একটি সুন্দর "Back" বাটন ব্যবহার করা হয়েছে
def home_back_buttons(back_callback="main_menu"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [_ibtn(text="🔙 Back", callback_data=back_callback)]
    ])

# ==================== COMMAND HANDLERS ====================
@dp.message(Command("start"))
async def start_cmd(message: Message, state: FSMContext):
    await state.clear()
    args = message.text.split()
    referrer_id = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
    get_user(message.from_user.id, message.from_user.username, referrer_id)

    _name = _h.escape(str(message.from_user.first_name or "there"))
    welcome_text = (
        f"{pt('👋')} <b>Welcome to SubNexa Premium Store, {_name}!</b>\n\n"
        f"{pt('🛒')} Your #1 trusted platform for buying Premium Subscriptions, AI Tools & Software at the lowest market rates!\n\n"
        f"{pt('✨')} <b>What we offer:</b>\n"
        "• 550+ Top Premium Applications\n"
        "• Instant Activation & Full Support\n"
        "• Instant Auto Deposit System\n\n"
        "Please select an option below to get started:"
    )
    kb = main_menu(message.from_user.id)
    try:
        await message.answer(welcome_text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        # tg-emoji (custom emoji) কোনো কারণে না চললে — টেক্সটের ট্যাগ সরিয়ে সাধারণ মেসেজ পাঠাও
        try:
            plain = welcome_text
            plain = re.sub(r"</?(?:tg-emoji|b|i|code)[^>]*>", "", plain)
            plain = _h.unescape(plain)
            await message.answer(plain, reply_markup=kb)
        except Exception:
            pass

# ==================== TEXT ROUTERS (FIX 3: F.text magic filter) ====================
HOME_TEXT = ('🏠 Home', 'Home', '🏠 الرئيسية', 'الرئيسية', '🏠 Главная', 'Главная', '🏠 होम', 'होम')

@dp.message(F.text.in_(HOME_TEXT))
async def msg_main_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🏠 **Main Menu**\nPlease select an option below:",
        reply_markup=main_menu(message.from_user.id),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer(
        "🏠 **Main Menu**\nPlease select an option below:",
        reply_markup=main_menu(callback.from_user.id),
        parse_mode="Markdown"
    )

# -------------------- SHOP & SEARCH --------------------
SHOP_TEXT = ('🛍️ Shop', 'Shop', '🛍️ المتجر', 'المتجر', '🛍️ Магазин', 'Магазин', '🛍️ शॉप', 'शॉप', '🔙 Back to Shop', 'Back to Shop', '🔙 العودة للمتجر', 'العودة للمتجر', '🔙 В магазин', 'В магазин', '🔙 शॉप पर वापस', 'शॉप पर वापस')

def build_shop_categories_keyboard():
    buttons = []
    cat_keys = list(CATEGORIES.keys())
    for i in range(0, len(cat_keys), 2):
        row = []
        k1 = cat_keys[i]
        row.append(_ibtn(text=CATEGORIES[k1]["title"], callback_data=f"cat|{k1}|1", style="primary"))
        if i + 1 < len(cat_keys):
            k2 = cat_keys[i + 1]
            row.append(_ibtn(text=CATEGORIES[k2]["title"], callback_data=f"cat|{k2}|1", style="primary"))
        buttons.append(row)
    return buttons
@dp.message(F.text.in_(SHOP_TEXT))
async def msg_open_shop(message: Message, state: FSMContext):
    await state.clear()
    buttons = build_shop_categories_keyboard()
    await message.answer(_htmlize_broadcast("🛒 **Shop Menu**"), reply_markup=shop_menu_reply(message.from_user.id), parse_mode="HTML")
    msg = await message.answer(
        _htmlize_broadcast("🛒 **Subscription Shop Categories**\nSelect a category or click Search to find your preferred app:"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )
    await state.update_data(last_inline_msg_id=msg.message_id)

@dp.callback_query(F.data == "open_shop")
async def cb_open_shop(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    try:
        await callback.message.delete()
    except Exception:
        pass

    buttons = build_shop_categories_keyboard()
    await callback.message.answer(_htmlize_broadcast("🛒 **Shop Menu**"), reply_markup=shop_menu_reply(callback.from_user.id), parse_mode="HTML")
    msg = await callback.message.answer(
        _htmlize_broadcast("🛒 **Subscription Shop Categories**\nSelect a category or click Search to find your preferred app:"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )
    await state.update_data(last_inline_msg_id=msg.message_id)

@dp.callback_query(F.data.startswith("cat|"))
async def cb_show_category(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    parts = callback.data.split("|")
    cat_key = parts[1]
    page = int(parts[2])

    await state.update_data(current_cat=cat_key, current_page=page, last_inline_msg_id=callback.message.message_id)

    cat = CATEGORIES[cat_key]
    apps = cat["apps"]

    items_per_page = 16
    start = (page - 1) * items_per_page
    end = start + items_per_page
    current_apps = apps[start:end]

    buttons = []
    for i in range(0, len(current_apps), 2):
        row = [_product_button(current_apps[i], f"app|{cat_key}|{current_apps[i][:25]}", cat_key)]
        if i + 1 < len(current_apps):
            row.append(_product_button(current_apps[i+1], f"app|{cat_key}|{current_apps[i+1][:25]}", cat_key))
        buttons.append(row)

    try:
        await callback.message.edit_text(
            _htmlize_broadcast(f"📂 **Category:** {cat['title']}\nPage {page} - Select an app to view rates:"),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
            parse_mode="HTML"
        )
    except Exception:
        pass

    data = await state.get_data()
    if data.get("in_category") != cat_key:
        await callback.message.answer(_htmlize_broadcast(f"📂 **Viewing: {cat['title']}**"), reply_markup=cat_menu_reply(callback.from_user.id), parse_mode="HTML")
        await state.update_data(in_category=cat_key)

# -------------------- PAGINATION --------------------
PAG_NEXT = ('Next Page ➡️', 'الصفحة التالية ➡️', 'Следующая ➡️', 'अगला पेज ➡️')
PAG_PREV = ('⬅️ Back Page', 'Back Page', '⬅️ الصفحة السابقة', 'الصفحة السابقة', '⬅️ Предыдущая', 'Предыдущая', '⬅️ पिछला पेज', 'पिछला पेज')
PAG_ALL = PAG_PREV + PAG_NEXT

def _paginate(cat_key, page, message_chat_id, last_msg_id, target_btn_text):
    cat = CATEGORIES[cat_key]
    apps = cat["apps"]
    max_page = (len(apps) - 1) // 16 + 1

    if target_btn_text in PAG_NEXT:
        if page >= max_page:
            return None, None, False, max_page  # already last page
        page += 1
    else:
        if page <= 1:
            return None, None, True, max_page  # already first page
        page -= 1

    current_apps = apps[(page - 1) * 16:page * 16]
    buttons = []
    for i in range(0, len(current_apps), 2):
        row = [_product_button(current_apps[i], f"app|{cat_key}|{current_apps[i][:25]}", cat_key)]
        if i + 1 < len(current_apps):
            row.append(_product_button(current_apps[i+1], f"app|{cat_key}|{current_apps[i+1][:25]}", cat_key))
        buttons.append(row)
    return page, buttons, None, max_page

@dp.message(F.text.in_(PAG_ALL))
async def msg_pagination(message: Message, state: FSMContext):
    data = await state.get_data()
    cat_key = data.get("current_cat")
    page = data.get("current_page", 1)
    last_msg_id = data.get("last_inline_msg_id")

    if not cat_key or not last_msg_id:
        await message.answer("⚠️ Session expired. Please open the shop again.", reply_markup=shop_menu_reply(message.from_user.id))
        return

    new_page, buttons, is_first, max_page = _paginate(cat_key, page, message.chat.id, last_msg_id, message.text)

    if new_page is None:
        msg_text = "⚠️ You are already on the last page." if is_first is False else "⚠️ You are already on the first page."
        return await message.answer(msg_text, reply_markup=cat_menu_reply(message.from_user.id))

    await state.update_data(current_page=new_page)
    try:
        await bot.edit_message_text(
            text=_htmlize_broadcast(f"📂 **Category:** {CATEGORIES[cat_key]['title']}\nPage {new_page} - Select an app to view rates:"),
            chat_id=message.chat.id,
            message_id=last_msg_id,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
            parse_mode="HTML"
        )
    except Exception:
        pass
    try:
        await message.delete()
    except Exception:
        pass

# -------------------- SEARCH --------------------
SEARCH_TEXT = ('🔍 Search App', 'Search App', '🔍 بحث عن تطبيق', 'بحث عن تطبيق', '🔍 Поиск приложения', 'Поиск приложения', '🔍 ऐप खोजें', 'ऐप खोजें')

@dp.message(F.text.in_(SEARCH_TEXT))
async def msg_search_app(message: Message, state: FSMContext):
    await state.set_state(SearchState.waiting_for_query)
    await message.answer(
        _htmlize_broadcast("🔍 **Search Application**\n\nPlease type the name of the app you are looking for (e.g. *YouTube Premium*, *ChatGPT*, *CapCut*):"),
        reply_markup=ReplyKeyboardMarkup(keyboard=[[row_btn("🔙 Back to Shop")]], resize_keyboard=True),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "search_app")
async def cb_search_app(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(SearchState.waiting_for_query)
    try:
        await callback.message.edit_text(
            _htmlize_broadcast("🔍 **Search Application**\n\nPlease type the name of the app you are looking for (e.g. *YouTube Premium*, *ChatGPT*, *CapCut*):"),
            reply_markup=home_back_buttons("open_shop"),
            parse_mode="HTML"
        )
    except Exception:
        pass

@dp.message(SearchState.waiting_for_query)
async def process_search(message: Message, state: FSMContext):
    query = message.text.strip().lower()
    await state.clear()

    matched_apps = []
    for cat_key, cat in CATEGORIES.items():
        for app in cat["apps"]:
            if query in app.lower() and (app, cat_key) not in matched_apps:
                matched_apps.append((app, cat_key))

    if not matched_apps:
        buttons = [
            [_ibtn(text="Search Again", callback_data="search_app", style="primary", icon_custom_emoji_id=get_icon("search"))],
            [_ibtn(text="🔙 Back", callback_data="open_shop")]
        ]
        await message.answer(_htmlize_broadcast("❌ **No apps found matching your query!**\nPlease try searching with a different keyword."), reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
        return

    buttons = []
    for i in range(0, min(len(matched_apps), 16), 2):
        app1, cat1 = matched_apps[i]
        row = [_product_button(app1, f"app|{cat1}|{app1[:25]}", cat1)]
        if i + 1 < len(matched_apps):
            app2, cat2 = matched_apps[i+1]
            row.append(_product_button(app2, f"app|{cat2}|{app2[:25]}", cat2))
        buttons.append(row)

    buttons.append([_ibtn(text="Search Again", callback_data="search_app", style="primary", icon_custom_emoji_id=get_icon("search")), _ibtn(text="🔙 Back", callback_data="open_shop")])
    await message.answer(_htmlize_broadcast(f"🔍 **Search Results for:** `{message.text}`"), reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")

# -------------------- APP DETAILS & BUY --------------------
@dp.callback_query(F.data.startswith("app|"))
async def cb_app_details(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    parts = callback.data.split("|")
    cat_key = parts[1]
    short_app_name = parts[2]

    cat = CATEGORIES.get(cat_key, {"apps": [], "pricing": {}})
    app_name = short_app_name
    for a in cat["apps"]:
        if a.startswith(short_app_name):
            app_name = a
            break

    pricing = cat.get("pricing", {}).get(app_name, {"1": 0.60, "3": 1.50, "12": 4.10, "18": 6.00, "24": 8.00, "36": 12.00})
    if not pricing:
        pricing = {"1": 0.60, "12": 4.10, "18": 6.00, "24": 8.00, "36": 12.00}

    if "youtube premium" in app_name.lower():
        pricing = {"1": 0.75, "3": 2.50, "12": 4.10}

    product_description = ""
    try:
        prod = find_product_by_name(app_name)
        if prod:
            product_description = prod["description"] or ""
    except Exception:
        pass

    buttons = []
    for duration, price in pricing.items():
        dur_label = f"{duration} Months" if duration != "1" else "1 Month"
        buttons.append([_ibtn(text=f"⏱️ {dur_label} - ${price:.2f} USD", callback_data=f"buy|{app_name}|{duration}|{price}", style="success")])
    buttons.append([_ibtn(text="🔙 Back", callback_data=f"cat|{cat_key}|1")])

    plain, cid = _prod_icon_chars(app_name)
    head = (plain + " " if plain else "") + "**" + app_name + "**"
    md = head + "\n\n"
    if product_description:
        md += str(product_description) + "\n\n"
    md += "Select your preferred subscription duration to purchase:"
    body = _htmlize_broadcast(md)
    if cid:
        body = '<tg-emoji emoji-id="%s">📦</tg-emoji> ' % cid + body
    try:
        await callback.message.edit_text(body, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    except Exception:
        pass

@dp.callback_query(F.data.startswith("buy|"))
async def cb_buy_confirm(callback: CallbackQuery):
    await callback.answer()
    parts = callback.data.split("|")
    app_name, duration, price_str = parts[1], parts[2], parts[3]
    price = float(price_str)

    user = get_user(callback.from_user.id)
    user_balance = user[2]

    dur_label = f"{duration} Months" if duration != "1" else "1 Month"
    text = _htmlize_broadcast(
        f"📌 **Subscription:** {app_name}\n"
        f"⏱️ **Duration:** {dur_label}\n"
        f"💵 **Price:** ${price:.2f} USD\n"
        f"💳 **Your Balance:** ${user_balance:.2f} USD"
    )

    buttons = [
        [_ibtn(text="Buy Now", callback_data=f"execbuy|{app_name}|{price}", style="success", icon_custom_emoji_id=get_icon("buy"))],
        [_ibtn(text="🔙 Back", callback_data="open_shop")]
    ]
    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    except Exception:
        pass

@dp.callback_query(F.data.startswith("execbuy|"))
async def cb_execute_buy(callback: CallbackQuery):
    await callback.answer()
    parts = callback.data.split("|")
    app_name, price_str = parts[1], parts[2]
    price = float(price_str)

    user = get_user(callback.from_user.id)
    user_balance = user[2]

    if user_balance < price:
        text = _htmlize_broadcast("❌ **Insufficient Balance!**\nPlease deposit funds to your account to complete this purchase.")
        buttons = [
            [_ibtn(text="Deposit", callback_data="deposit", style="success", icon_custom_emoji_id=get_icon("deposit"))],
            [_ibtn(text="🔙 Back", callback_data="open_shop")]
        ]
        try:
            await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
        except Exception:
            pass
    else:
        update_balance(callback.from_user.id, -price)
        text = _htmlize_broadcast(
            f"✅ **Purchase Successful!**\n\n"
            f"You bought: **{app_name}**\n"
            f"Price deducted: **${price:.2f} USD**\n\n"
            f"Support will contact you shortly to deliver your premium access."
        )
        buttons = [
            [_ibtn(text="🔙 Home", callback_data="main_menu")]
        ]
        try:
            await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
        except Exception:
            pass

# -------------------- BALANCE --------------------
BALANCE_TEXT = ('💰 Balance', 'Balance', '💰 الرصيد', 'الرصيد', '💰 Баланс', 'Баланс', '💰 बैलेंस', 'बैलेंस')

@dp.message(F.text.in_(BALANCE_TEXT))
async def msg_balance(message: Message):
    user = get_user(message.from_user.id)
    text = (
        f"{_premium_emoji_html('💰')} <b>Account Balance</b>\n\n"
        f"Your current wallet balance: <b>${user[2]:.2f} USD</b>"
    )
    await message.answer(text, reply_markup=main_menu(message.from_user.id), parse_mode="HTML")

@dp.callback_query(F.data == "balance")
async def cb_balance(callback: CallbackQuery):
    await callback.answer()
    user = get_user(callback.from_user.id)
    text = (
        f"{_premium_emoji_html('💰')} <b>Account Balance</b>\n\n"
        f"Your current wallet balance: <b>${user[2]:.2f} USD</b>"
    )
    try:
        await callback.message.edit_text(text, reply_markup=home_back_buttons(), parse_mode="HTML")
    except Exception:
        pass

# -------------------- REFERRAL --------------------
REFER_TEXT = ('👥 Refer', 'Refer', '👥 الإحالة', 'الإحالة', '👥 Реферал', 'Реферал', '👥 रेफरल', 'रेफरल')

async def _refer_text(user_id):
    user = get_user(user_id)
    bot_info = await bot.get_me()
    total_refs = user[4]
    total_earnings = total_refs * REFERRAL_REWARD
    ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
    return (
        f"{pt('👥')} <b>Referral Program</b>\n\n"
        f"{pt('💰')} <b>Reward per Referral:</b> ${REFERRAL_REWARD:.2f} USD\n"
        f"{pt('📊')} <b>Total Referrals:</b> {total_refs} Users\n"
        f"{pt('💵')} <b>Total Earnings:</b> ${total_earnings:.2f} USD\n\n"
        f"{pt('🔗')} <b>Your Referral Link:</b>\n<code>{ref_link}</code>\n\n"
        "Share this link with your friends to earn rewards on every signup!"
    )

@dp.message(F.text.in_(REFER_TEXT))
async def msg_refer(message: Message):
    text = await _refer_text(message.from_user.id)
    await message.answer(text, reply_markup=main_menu(message.from_user.id), parse_mode="HTML")

@dp.callback_query(F.data == "refer")
async def cb_refer(callback: CallbackQuery):
    await callback.answer()
    text = await _refer_text(callback.from_user.id)
    try:
        await callback.message.edit_text(text, reply_markup=home_back_buttons(), parse_mode="HTML")
    except Exception:
        pass

# -------------------- SUPPORT --------------------
SUPPORT_TEXT = ('🎧 Support', 'Support', '🎧 الدعم', 'الدعم', '🎧 Поддержка', 'Поддержка', '🎧 सहायता', 'सहायता')

@dp.message(F.text.in_(SUPPORT_TEXT))
async def msg_support(message: Message):
    text = _htmlize_broadcast(
        "🎧 **Customer Support**\n\n"
        "If you face any issues or have questions regarding subscriptions or deposits, please contact our support team."
    )
    buttons = [
        [_ibtn(text="Contact Support", url=f"https://t.me/{SUPPORT_USERNAME}", style="primary", icon_custom_emoji_id=get_icon("support"))]
    ]
    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")

@dp.callback_query(F.data == "support")
async def cb_support(callback: CallbackQuery):
    await callback.answer()
    text = _htmlize_broadcast(
        "🎧 **Customer Support**\n\n"
        "If you face any issues or have questions regarding subscriptions or deposits, please contact our support team."
    )
    buttons = [
        [_ibtn(text="Contact Support", url=f"https://t.me/{SUPPORT_USERNAME}", style="primary", icon_custom_emoji_id=get_icon("support"))],
        [_ibtn(text="🔙 Back", callback_data="main_menu")]
    ]
    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    except Exception:
        pass

# -------------------- DEPOSIT SECTION --------------------
DEPOSIT_TEXT = ('💳 Deposit', 'Deposit', '💳 إيداع', 'إيداع', '💳 Пополнить', 'Пополнить', '💳 जमा करें', 'जमा करें')

def _dep_btn(label, emoji, cb, slot, style="primary"):
    """ডিপোজিট পদ্ধতির বাটন — admin slot-এ custom icon সেট থাকলে সেটা বসে,
    না থাকলে ইমোজি-টেক্সট (আগের মতো অটো premium)। কোনো অবস্থায় নাম্বার দেখায় না।"""
    cid = get_icon(slot)
    if cid:
        return _ibtn(text=label, callback_data=cb, style=style, icon_custom_emoji_id=cid)
    return _ibtn(text=f"{emoji} {label}", callback_data=cb, style=style)

def deposit_method_rows(with_back=False):
    rows = [
        [_dep_btn("Binance", "🟡", "dep_binance", "deposit_binance"),
         _dep_btn("USDT (ERC20)", "🔷", "dep_erc20", "deposit_usdt")],
        [_dep_btn("ePay", "📧", "dep_epay", "deposit_epay"),
         _dep_btn("BDT P2P (Bkash/Nagad)", "🇧🇩", "dep_bdt", "deposit_bdt")],
    ]
    if with_back:
        rows.append([_ibtn(text="🔙 Back", callback_data="main_menu")])
    return rows

def bd_method_rows():
    return [
        [_dep_btn("bKash", "💖", "subdep_bkash", "deposit_bkash", style="success"),
         _dep_btn("Nagad", "🟠", "subdep_nagad", "deposit_nagad", style="success")],
        [_ibtn(text="🔙 Back", callback_data="deposit")]
    ]

@dp.message(F.text.in_(DEPOSIT_TEXT))
async def msg_deposit(message: Message, state: FSMContext):
    user = get_user(message.from_user.id)
    text = (
        f"{pt('💳')} <b>Deposit Funds</b>\n\n"
        f"{pt('💰')} Current Balance: <b>${user[2]:.2f} USD</b>\n"
        f"{pt('ℹ️')} We only accept payments in USD.\n"
        f"{pt('🔻')} Minimum Deposit: <b>${MIN_DEPOSIT_USD:.2f} USD</b>\n\n"
        "Please select your preferred payment method below:"
    )
    buttons = deposit_method_rows()
    await message.answer(f"{pt('💳')} <b>Deposit Menu</b>", reply_markup=ReplyKeyboardMarkup(keyboard=[[row_btn("🏠 Home")]], resize_keyboard=True), parse_mode="HTML")
    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")

@dp.callback_query(F.data == "deposit")
async def cb_deposit(callback: CallbackQuery):
    await callback.answer()
    user = get_user(callback.from_user.id)
    text = (
        f"{pt('💳')} <b>Deposit Funds</b>\n\n"
        f"{pt('💰')} Current Balance: <b>${user[2]:.2f} USD</b>\n"
        f"{pt('ℹ️')} We only accept payments in USD.\n"
        f"{pt('🔻')} Minimum Deposit: <b>${MIN_DEPOSIT_USD:.2f} USD</b>\n\n"
        "Please select your preferred payment method below:"
    )
    buttons = deposit_method_rows(with_back=True)
    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
    except Exception:
        pass

@dp.callback_query(F.data.startswith("dep_"))
async def cb_deposit_method(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    method = callback.data
    await state.update_data(method=method)

    if method == "dep_binance":
        text = f"🟡 **Binance Deposit**\n\nMinimum deposit: **${MIN_DEPOSIT_USD:.2f} USD**.\nPlease enter the amount you wish to deposit in USD:"
    elif method == "dep_erc20":
        text = f"🔷 **USDT (ERC20) Deposit**\n\nMinimum deposit: **${MIN_DEPOSIT_USD:.2f} USD**.\nPlease enter the amount you wish to deposit in USD:"
    elif method == "dep_epay":
        text = f"📧 **ePay Deposit**\n\nMinimum deposit: **${MIN_DEPOSIT_USD:.2f} USD**.\nPlease enter the amount you wish to deposit in USD:"
    elif method == "dep_bdt":
        text = (
            f"🇧🇩 **BDT P2P Deposit**\n\n"
            f"Exchange Rates:\n"
            f"• 1 USD = {BKASH_RATE} BDT (bKash)\n"
            f"• 1 USD = {NAGAD_RATE} BDT (Nagad)\n\n"
            f"Minimum Deposit: **${MIN_DEPOSIT_USD:.2f} USD**\n\n"
            "Select your Mobile Financial Service:"
        )
        buttons = bd_method_rows()
        try:
            await callback.message.edit_text(_htmlize_broadcast(text), reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="HTML")
        except Exception:
            pass
        return

    await state.set_state(DepositState.waiting_for_amount)
    try:
        await callback.message.edit_text(_htmlize_broadcast(text), reply_markup=home_back_buttons("deposit"), parse_mode="HTML")
    except Exception:
        pass

@dp.callback_query(F.data.startswith("subdep_"))
async def cb_subdep_bdt(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    m_type = callback.data
    await state.update_data(method=m_type)
    text = f"🇧🇩 **{m_type.replace('subdep_', '').capitalize()} Deposit**\n\nMinimum deposit is **${MIN_DEPOSIT_USD:.2f} USD**.\nPlease enter the amount of USD you want to deposit:"
    await state.set_state(DepositState.waiting_for_amount)
    try:
        await callback.message.edit_text(_htmlize_broadcast(text), reply_markup=home_back_buttons("dep_bdt"), parse_mode="HTML")
    except Exception:
        pass

@dp.message(DepositState.waiting_for_amount)
async def process_deposit_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text)
        if amount < MIN_DEPOSIT_USD:
            await message.answer(_htmlize_broadcast("⚠️ **Please enter a valid amount!** Minimum deposit is **$3.00 USD**."), reply_markup=home_back_buttons("deposit"), parse_mode="HTML")
            return
    except ValueError:
        await message.answer(_htmlize_broadcast("⚠️ **Invalid input!** Please enter a numeric value (e.g. 3 or 5)."), reply_markup=home_back_buttons("deposit"), parse_mode="HTML")
        return

    await state.update_data(amount_usd=amount)
    data = await state.get_data()
    method = data["method"]

    if method == "dep_binance":
        text = (
            f"🟡 **Binance Information**\n\n"
            f"💰 Amount: **${amount:.2f} USD**\n"
            f"🆔 Binance ID: `{BINANCE_ID}`\n\n"
            "Please transfer the USD amount to the Binance ID above. After completing payment, enter your **Transaction ID** below:"
        )
    elif method == "dep_erc20":
        text = (
            f"🔷 **USDT (ERC20) Information**\n\n"
            f"💰 Amount: **${amount:.2f} USD**\n"
            f"🔹 Asset: **USDT**\n"
            f"🌐 Network: **Ethereum (ERC20)**\n"
            f"📍 Address: `{USDT_ERC20_ADDRESS}`\n\n"
            "Please transfer the USDT amount to the address above. After completing payment, enter your **Transaction ID / Hash** below:"
        )
    elif method == "dep_epay":
        text = (
            f"📧 **ePay Information**\n\n"
            f"💰 Amount: **${amount:.2f} USD**\n"
            f"📧 Send to Email: `{EPAY_GMAIL}`\n"
            f"ℹ️ Note: We only accept USD.\n\n"
            "After transferring, enter your **Transaction ID** below:"
        )
    elif method == "subdep_bkash":
        bdt_amount = amount * BKASH_RATE
        text = (
            f"💖 **bKash Payment Information**\n\n"
            f"💰 USD Amount: **${amount:.2f} USD**\n"
            f"🇧🇩 BDT Amount to Send: **{bdt_amount:.2f} BDT** (Rate: 1 USD = {BKASH_RATE} BDT)\n"
            f"📱 bKash Number (Send Money): `{BKASH_NUMBER}`\n\n"
            "Send money to the bKash number above and enter your **Transaction ID** below:"
        )
    elif method == "subdep_nagad":
        bdt_amount = amount * NAGAD_RATE
        text = (
            f"🟠 **Nagad Payment Information**\n\n"
            f"💰 USD Amount: **${amount:.2f} USD**\n"
            f"🇧🇩 BDT Amount to Send: **{bdt_amount:.2f} BDT** (Rate: 1 USD = {NAGAD_RATE} BDT)\n"
            f"📱 Nagad Number (Send Money): `{NAGAD_NUMBER}`\n\n"
            "Send money to the Nagad number above and enter your **Transaction ID** below:"
        )

    await state.set_state(DepositState.waiting_for_trx)
    await message.answer(_htmlize_broadcast(text), reply_markup=home_back_buttons("deposit"), parse_mode="HTML")
@dp.message(DepositState.waiting_for_trx)
async def process_deposit_trx(message: Message, state: FSMContext):
    trx_id = message.text.strip()
    data = await state.get_data()
    amount = data["amount_usd"]
    method = data["method"].replace("dep_", "").replace("subdep_", "").upper()

    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO deposits (user_id, username, method, amount_usd, trx_id, date) VALUES (?, ?, ?, ?, ?, ?)",
                    (user_id, username, method, amount, trx_id, date_str))
        conn.commit()
        deposit_id = cur.lastrowid

    await state.clear()

    await message.answer(
        _htmlize_broadcast("⏳ **Deposit Submitted!**\n\nYour deposit request is currently **PENDING** approval. Please wait while our team verifies it."),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[_ibtn(text="🔙 Back", callback_data="main_menu")]]),
        parse_mode="HTML"
    )

    admin_msg = (
        f"📥 **NEW DEPOSIT REQUEST** #{deposit_id}\n\n"
        f"👤 User: @{username} (`{user_id}`)\n"
        f"💵 Amount: **${amount:.2f} USD**\n"
        f"💳 Method: **{method}**\n"
        f"🔖 Trx ID: `{trx_id}`\n"
        f"📅 Date: {date_str}"
    )
    admin_buttons = InlineKeyboardMarkup(inline_keyboard=[
        [
            _ibtn(text="Accept", style="success", icon_custom_emoji_id=get_icon("accept"), callback_data=f"adm_acc_{deposit_id}"),
            _ibtn(text="Reject", style="danger", icon_custom_emoji_id=get_icon("reject"), callback_data=f"adm_rej_{deposit_id}")
        ]
    ])
    try:
        await bot.send_message(ADMIN_ID, _htmlize_broadcast(admin_msg), reply_markup=admin_buttons, parse_mode="HTML")
    except Exception as e:
        logging.error(f"Failed to notify admin: {e}")

# -------------------- ADMIN PANEL & BROADCAST --------------------
ADMIN_TEXT = ('⚙️ Admin Panel', 'Admin Panel', '⚙️ لوحة الإدارة', 'لوحة الإدارة', '⚙️ Панель администратора', 'Панель администратора', '⚙️ एडमिन पैनल', 'एडमिन पैनल')

@dp.message(F.text.in_(ADMIN_TEXT))
async def msg_admin_panel(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    text = "⚙️ **Admin Control Panel** 🟢 v5\nWelcome Admin!\nManage users, deposits, and bot operations below:"
    buttons = [
        [_ibtn(text="Total Users", callback_data="adm_users", style="primary", icon_custom_emoji_id=get_icon("users"))],
        [_ibtn(text="Deposit History", callback_data="adm_history", style="primary", icon_custom_emoji_id=get_icon("history"))],
        [_ibtn(text="Broadcast Message", style="success", icon_custom_emoji_id=get_icon("broadcast"), callback_data="adm_broadcast")],
        [_ibtn(text="Stock Manager", style="primary", icon_custom_emoji_id=get_icon("stock"), callback_data="stock_manager")],
        [_ibtn(text="Button Icons", style="primary", icon_custom_emoji_id=get_icon("iconmgr"), callback_data="icon_manager")],
    ]
    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")
@dp.callback_query(F.data == "admin_panel")
async def cb_admin_panel(callback: CallbackQuery):
    await callback.answer()
    if callback.from_user.id != ADMIN_ID:
        return

    text = "⚙️ **Admin Control Panel** 🟢 v5\nWelcome Admin!\nManage users, deposits, and bot operations below:"
    buttons = [
        [_ibtn(text="Total Users", callback_data="adm_users", style="primary", icon_custom_emoji_id=get_icon("users"))],
        [_ibtn(text="Deposit History", callback_data="adm_history", style="primary", icon_custom_emoji_id=get_icon("history"))],
        [_ibtn(text="Broadcast Message", style="success", icon_custom_emoji_id=get_icon("broadcast"), callback_data="adm_broadcast")],
        [_ibtn(text="Stock Manager", style="primary", icon_custom_emoji_id=get_icon("stock"), callback_data="stock_manager")],
        [_ibtn(text="Button Icons", style="primary", icon_custom_emoji_id=get_icon("iconmgr"), callback_data="icon_manager")],
        [_ibtn(text="🔙 Back", callback_data="main_menu")]
    ]
    try:
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")
    except Exception:
        pass
async def _edit_or_answer(callback, html_text, kb=None, parse="HTML"):
    """মেসেজ এডিট করতে না পারলে নতুন মেসেজে উত্তর — অ্যাডমিন বাটনে কিছু না আসার সমস্যা দূর"""
    try:
        await callback.message.edit_text(html_text, reply_markup=kb, parse_mode=parse)
    except Exception:
        try:
            await callback.message.answer(html_text, reply_markup=kb, parse_mode=parse)
        except Exception:
            pass

ADMIN_USER_PAGE = 8

def _admin_users_panel(page):
    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT user_id, username, balance FROM users ORDER BY user_id")
        users = cur.fetchall()
    total = len(users)
    pages = max(1, -(-total // ADMIN_USER_PAGE))
    page = max(1, min(page, pages))
    rows = []
    for u in users[(page - 1) * ADMIN_USER_PAGE: page * ADMIN_USER_PAGE]:
        name = "@" + u["username"] if u["username"] else str(u["user_id"])
        rows.append([_ibtn(text=f"👤 {name}  ·  ${u['balance']:.2f} USD", callback_data=f"adm_umsg|{u['user_id']}", style="primary")])
    nav = []
    if page > 1:
        nav.append(_ibtn(text="⬅️", callback_data=f"adm_users|{page - 1}"))
    nav.append(_ibtn(text=f"{page}/{pages}", callback_data="noop"))
    if page < pages:
        nav.append(_ibtn(text="➡️", callback_data=f"adm_users|{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([_ibtn(text="🔙 Back", callback_data="admin_panel")])
    return rows, total, pages

@dp.callback_query(F.data.startswith("adm_users"))
async def cb_admin_users(callback: CallbackQuery):
    await callback.answer()
    if callback.from_user.id != ADMIN_ID:
        return
    page = 1
    if "|" in callback.data:
        try:
            page = int(callback.data.split("|")[1])
        except Exception:
            page = 1
    rows, total, pages = _admin_users_panel(page)
    txt = _htmlize_broadcast(f"👥 **Total Bot Users:** `{total}`\n\n✉️ কোনো ইউজারে মেসেজ পাঠাতে তার নামে ক্লিক করো (পেজ {page}/{pages}):")
    await _edit_or_answer(callback, txt, InlineKeyboardMarkup(inline_keyboard=rows))

@dp.callback_query(F.data.startswith("adm_umsg|"))
async def cb_admin_msg_user(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    if callback.from_user.id != ADMIN_ID:
        return
    try:
        uid = int(callback.data.split("|", 1)[1])
    except Exception:
        uid = None
    if not uid:
        return
    await state.update_data(admin_msg_uid=uid)
    await state.set_state(AdminState.waiting_for_user_msg)
    txt = _htmlize_broadcast("✉️ **Message User**\n\nইউজার: `%d`\n\nএখন যা পাঠাতে চাও **লিখে পাঠাও** — `**bold**` ও `code` কাজ করবে।\n\nবাতিল করতে /start চাপো।" % uid)
    await _edit_or_answer(callback, txt, home_back_buttons("adm_users"))

@dp.message(AdminState.waiting_for_user_msg)
async def process_admin_msg_user(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    data = await state.get_data()
    uid = data.get("admin_msg_uid")
    await state.clear()
    if not uid:
        return await message.answer("⚠️ ইউজার পাওয়া যায়নি।", reply_markup=main_menu(message.from_user.id))
    text = message.text or message.caption or ""
    try:
        await bot.send_message(uid, _htmlize_broadcast(text), parse_mode="HTML")
        ok = True
    except Exception as e:
        ok = False
        logging.warning(f"Failed to message user {uid}: {e}")
    status = f"✅ **Messaged user `{uid}` successfully!**" if ok else f"❌ **Failed!** ইউজার `{uid}` বট ব্লক করেছে বা ভুল।"
    await message.answer(_htmlize_broadcast(status), reply_markup=home_back_buttons("adm_users"), parse_mode="HTML")

@dp.callback_query(F.data == "adm_history")
async def cb_admin_history(callback: CallbackQuery):
    await callback.answer()
    if callback.from_user.id != ADMIN_ID:
        return

    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, username, amount_usd, method, status FROM deposits ORDER BY id DESC LIMIT 10")
        deposits = cur.fetchall()

    if not deposits:
        try:
            await callback.message.edit_text("📜 **No deposit history found.**", reply_markup=home_back_buttons("admin_panel"), parse_mode="Markdown")
        except Exception:
            pass
        return

    history_text = "📜 **Recent 10 Deposits:**\n\n"
    for dep in deposits:
        history_text += f"🆔 #{dep['id']} | @{dep['username']} | ${dep['amount_usd']} USD | {dep['method']} | Status: **{dep['status']}**\n"

    try:
        await callback.message.edit_text(history_text, reply_markup=home_back_buttons("admin_panel"), parse_mode="Markdown")
    except Exception:
        pass

@dp.callback_query(F.data.startswith("adm_acc_"))
async def cb_accept_deposit(callback: CallbackQuery):
    await callback.answer()
    if callback.from_user.id != ADMIN_ID:
        return

    dep_id = int(callback.data.split("_")[2])
    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT user_id, amount_usd, status FROM deposits WHERE id = ?", (dep_id,))
        dep = cur.fetchone()

        if not dep or dep["status"] != 'PENDING':
            try:
                await callback.message.edit_text(_htmlize_broadcast(f"⚠️ Deposit #{dep_id} is already processed or not found."), parse_mode="HTML")
            except Exception:
                pass
            return

        user_id, amount = dep["user_id"], dep["amount_usd"]
        cur.execute("UPDATE deposits SET status = 'APPROVED' WHERE id = ?", (dep_id,))
        cur.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        conn.commit()

    try:
        await callback.message.edit_text(_htmlize_broadcast(f"✅ **Deposit #{dep_id} Approved!**\nAdded **${amount:.2f} USD** to user balance."), parse_mode="HTML")
    except Exception:
        pass
    try:
        await bot.send_message(user_id, _htmlize_broadcast(f"✅ **Deposit Approved!**\n\nYour deposit of **${amount:.2f} USD** has been verified and added to your wallet balance!"), parse_mode="HTML")
    except Exception:
        pass

@dp.callback_query(F.data.startswith("adm_rej_"))
async def cb_reject_deposit(callback: CallbackQuery):
    await callback.answer()
    if callback.from_user.id != ADMIN_ID:
        return

    dep_id = int(callback.data.split("_")[2])
    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT user_id, status FROM deposits WHERE id = ?", (dep_id,))
        dep = cur.fetchone()

        if not dep or dep["status"] != 'PENDING':
            try:
                await callback.message.edit_text(_htmlize_broadcast(f"⚠️ Deposit #{dep_id} is already processed or not found."), parse_mode="HTML")
            except Exception:
                pass
            return

        user_id = dep["user_id"]
        cur.execute("UPDATE deposits SET status = 'REJECTED' WHERE id = ?", (dep_id,))
        conn.commit()

    try:
        await callback.message.edit_text(_htmlize_broadcast(f"❌ **Deposit #{dep_id} Rejected.**"), parse_mode="HTML")
    except Exception:
        pass
    try:
        await bot.send_message(user_id, _htmlize_broadcast(f"❌ **Deposit Rejected!**\n\nYour deposit request #{dep_id} was rejected. Please contact support if you think this is an error."), parse_mode="HTML")
    except Exception:
        pass

@dp.callback_query(F.data == "adm_broadcast")
async def cb_broadcast_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    if callback.from_user.id != ADMIN_ID:
        return

    await state.set_state(AdminState.waiting_for_broadcast)
    instructions = (
        "📢 **Broadcast — সবাইকে মেসেজ পাঠাও**\n\n"
        "নিচে **মেসেজ টেক্সট লিখে পাঠাও** — সব ইউজার পাবে।\n"
        "`**bold**` / *italic* / `code` ব্যবহার করা যাবে।\n\n"
        "💡 **বাটন যোগ করতে** (ঐচ্ছিক): প্রতিটা বাটন আলাদা লাইনে `|` দিয়ে:\n"
        "`| বাটনের নাম | action`\n\n"
        "**action যেগুলো চলবে:**\n"
        "`main_menu` · `open_shop` · `deposit` · `support` · `product:নাম` · যেকোনো `https://` লিংক\n\n"
        "📝 **উদাহরণ:**\n"
        "🎉 আজকের স্পেশাল অফার!\n"
        "| 🛍️ এখনই কিনুন | open_shop\n\n"
        "বাতিল করতে /start চাপো।"
    )
    html_instr = _htmlize_broadcast(instructions)
    await _edit_or_answer(callback, html_instr, home_back_buttons("admin_panel"))

# FIX 5: ব্রডকাস্ট বাটন পার্সিং — প্রতিটি বাটন নতুন লাইনে `|` দিয়ে লেখা হয়
_EMOJI_RICH_RE = None

def _rich_re():
    global _EMOJI_RICH_RE
    if _EMOJI_RICH_RE is None:
        keys = sorted(PREMIUM_EMOJI.keys(), key=len, reverse=True)
        _EMOJI_RICH_RE = re.compile("|".join(re.escape(k) for k in keys))
    return _EMOJI_RICH_RE

def _htmlize_broadcast(text):
    """মার্কডাউন-লাইট (**bold**, `code`) → HTML + premium ইমোজি tg-emoji স্প্যান।"""
    import html as _h
    raw = str(text)
    toks = {}
    idx = 0
    def _sub(m):
        nonlocal idx
        orig = m.group(0)
        try:
            cid = _emoji_action(_norm_emoji(orig))
        except Exception:
            cid = None
        if not cid:
            return orig
        tok = "\x02E%d\x03" % idx
        idx += 1
        toks[tok] = (cid, orig)
        return tok
    s = _rich_re().sub(_sub, raw)
    s = _h.escape(s)
    parts = re.split(r"(`[^`]+`)", s)
    out = []
    for p in parts:
        if p.startswith("`") and p.endswith("`") and len(p) > 1:
            out.append("<code>" + p[1:-1] + "</code>")
        else:
            q = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", p)
            out.append(re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<i>\1</i>", q))
    s = "".join(out)
    for tok, (cid, orig) in toks.items():
        s = s.replace(tok, '<tg-emoji emoji-id="%s">%s</tg-emoji>' % (cid, orig))
    return s

def _prod_icon_chars(name):
    """প্রোডাক্ট icon → (plain_char_or_'', numeric_custom_id_or_'')"""
    try:
        ic = PRODUCT_ICON_BY_NAME.get(name) or ""
    except Exception:
        ic = ""
    ic = str(ic).strip()
    if ic.isdigit() and len(ic) >= 10:
        return "", ic
    if not ic:
        return "", ""
    nk = _norm_emoji(ic)
    if nk in _PREMIUM_BY_NORM:
        act = _emoji_action(nk)
        if act:
            return "", act
        return _emoji_orig_char(nk), ""
    return ic, ""

def _premium_emoji_html(nk):
    """মেসেজ বডিতে premium কাস্টম ইমোজি দেখাতে HTML tg-emoji ট্যাগ"""
    nk = _norm_emoji(nk)
    try:
        cid = _emoji_action(nk)
    except Exception:
        cid = None
    char = _emoji_orig_char(nk) if nk in _PREMIUM_BY_NORM else nk
    if cid:
        return f'<tg-emoji emoji-id="{cid}">{char}</tg-emoji>'
    return char

def pt(nk):
    """Premium emoji html — মেসেজ টেক্সটে ব্যবহারের ছোট নাম"""
    return _premium_emoji_html(nk)

@dp.message(AdminState.waiting_for_broadcast)
async def process_broadcast(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return

    await state.clear()
    raw_text = (message.text or "").strip()
    if not raw_text:
        return await message.answer(_htmlize_broadcast("⚠️ মেসেজ টেক্সট খালি! প্রথমে Broadcast বাটন চেপে তারপর টেক্সট লিখে পাঠাও।"), reply_markup=home_back_buttons("admin_panel"), parse_mode="HTML")

    lines = raw_text.split("\n")
    msg_lines = []
    inline_keyboard = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|") and stripped.count("|") >= 1:
            parts = [p.strip() for p in stripped.split("|")]
            parts = [p for p in parts if p]
            if len(parts) >= 2:
                btn_text = parts[0]
                action = parts[1]
                if action.startswith("http://") or action.startswith("https://"):
                    inline_keyboard.append([_ibtn(text=btn_text, url=action)])
                elif action.startswith("product:"):
                    target = action.split(":", 1)[1].strip()
                    prod = None
                    if target.isdigit():
                        with db_conn() as conn2:
                            cur2 = conn2.cursor()
                            cur2.execute("SELECT id FROM products WHERE id=?", (int(target),))
                            prod = cur2.fetchone()
                    else:
                        prod = find_product_by_name(target)
                    if prod:
                        inline_keyboard.append([_ibtn(text=btn_text, callback_data=f"prod|{prod['id']}")])
                else:
                    inline_keyboard.append([_ibtn(text=btn_text, callback_data=action)])
        else:
            msg_lines.append(line)

    final_text = "\n".join(msg_lines).strip()
    reply_markup = InlineKeyboardMarkup(inline_keyboard=inline_keyboard) if inline_keyboard else None

    if not final_text:
        return await message.answer(_htmlize_broadcast("⚠️ মেসেজের টেক্সট পাওয়া যায়নি — শুধু বাটন লেখা হয়েছে। প্রথমে টেক্সটও লিখো।"), reply_markup=home_back_buttons("admin_panel"), parse_mode="HTML")

    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM users")
        users = cur.fetchall()

    success, failed = 0, 0
    if not users:
        return await message.answer(_htmlize_broadcast("⚠️ কোনো ইউজার নেই DB-তে — কেউ এখনো বট start করেনি।"), reply_markup=home_back_buttons("admin_panel"), parse_mode="HTML")

    await message.answer(_htmlize_broadcast("🚀 **Broadcasting started...**"), parse_mode="HTML")

    safe_text = _htmlize_broadcast(final_text)

    for u in users:
        try:
            await bot.send_message(u["user_id"], safe_text, reply_markup=reply_markup, parse_mode="HTML")
            success += 1
        except Exception:
            # HTML/বাটন কোনো কারণে না গেলে — বাটন ছাড়া সাদা টেক্সটে আবার চেষ্টা
            try:
                import html as _hh
                plain = re.sub(r"</?(?:tg-emoji|b|i|code)[^>]*>", "", safe_text)
                plain = _hh.unescape(plain)
                await bot.send_message(u["user_id"], plain)
                success += 1
            except Exception:
                failed += 1
        await asyncio.sleep(0.05)

    await message.answer(
        _htmlize_broadcast(f"✅ **Broadcast Finished!**\n\n🎯 Successful: `{success}`\n❌ Failed: `{failed}`"),
        reply_markup=home_back_buttons("admin_panel"),
        parse_mode="HTML"
    )

# ==================== PRODUCT ICONS (per-service emoji) ====================
# প্রতিটা ক্যাটাগরিতে সব প্রোডাক্ট একই লোগো না — এবার প্রতিটা প্রোডাক্ট আলাদা আলাদা
# ইমোজি পায় (প্রোডাক্ট পুল থেকে ঘুরিয়ে)। Admin → Stock Manager → product-এ
# "🎨 Icon" দিয়ে যেকোনো প্রোডাক্টের ইমোজি আলাদা করে বদলানো যায়।
# পুলের প্রতিটা ইমোজি premium (validate করা) — তাই AUTO থাকলে premium icon হিসেবে যায়।
PRODUCT_ICON_POOLS = {
    'ai': ['🤖', '🧠', '🦾', '⚡', '🚀', '🛰', '💡', '🔬', '📡', '💭', '🤯', '🖥', '⌨', '🕹'],
    'photo': ['🎨', '📷', '🖼', '🌈', '🎭', '✨', '🪄', '💄', '🖌', '🎞', '🌸', '🔮', '🎆', '🪞', '📸'],
    'video': ['🎬', '🎥', '📺', '🍿', '🎙', '📼', '🎚', '🎛', '📹', '🎤', '🎟', '🎪', '🎫'],
    'music': ['🎵', '🎶', '🎧', '🎹', '🎸', '🥁', '🎷', '🎺', '🎻', '🪕', '🎼', '💿', '📀', '🎚', '🎤'],
    'edu': ['📚', '📖', '✏', '📝', '🎓', '🏫', '🧮', '🔤', '🔢', '🌍', '🧪', '🔭', '🗺', '💯'],
    'office': ['☁', '📁', '🗂', '📎', '📋', '📊', '📈', '📉', '🗄', '🖇', '🖨', '📄', '🗓', '🖥', '🧾'],
    'dev': ['💻', '⌨', '🖱', '🌐', '🧩', '🐍', '🛠', '📶', '⚙', '🔨'],
    'vpn': ['🔐', '🛡', '🔑', '🗝', '🔒', '🔓', '🧤', '🌍', '🛰', '📶', '🔔', '🚪', '🛂'],
    'social': ['📱', '💬', '👥', '📣', '📢', '❤', '👍', '🔥', '💌', '✨', '🫶', '💖', '😎', '🎯'],
    'pdf': ['🧰', '📄', '📑', '🔖', '✂', '🧾', '🗒', '📇', '🖨', '📋', '📎', '📌', '🧲'],
    'entertainment': ['🎭', '🎬', '🎥', '📺', '🍿', '🎪', '🎟', '🎫', '🎞', '🎙'],
    'bonus': ['⭐', '🏆', '🥇', '🎁', '🎉', '💎', '👑', '🏅', '🎊', '💫', '🌟', '🧧', '🪙', '🥈', '🥉', '🎖']
}
PRODUCT_ICON_THEME = {
    "ai": "🤖", "photo": "🎨", "video": "🎬", "music": "🎵", "edu": "📚",
    "office": "☁️", "dev": "💻", "vpn": "🔐", "social": "📱", "pdf": "🧰", "bonus": "⭐",
    "entertainment": "🎭",
}
PRODUCT_ICON_BY_NAME = {}

def _pick_product_icon(cat_key, idx):
    """ক্যাটাগরি পুল থেকে ঘুরিয়ে আলাদা আলাদা icon — একই icon পাশাপাশি না পড়ে"""
    pool = PRODUCT_ICON_POOLS.get(cat_key) or []
    if pool:
        return pool[idx % len(pool)]
    return PRODUCT_ICON_THEME.get(cat_key, "📦")

def _is_numeric_custom_id(val):
    """লম্বা সংখ্যা (custom emoji ID) কি না — ৬ থেকে ৬৪ ডিজিট"""
    val = str(val).strip().strip("`'\"")
    return bool(re.fullmatch(r"\d{6,64}", val))

def _clean_stored_icon(icon):
    """সংরক্ষণের আগে icon পরিষ্কার — জাস্ট সংখ্যা/ইমোজি/খালি"""
    icon = str(icon or "").strip().strip("`'\"")
    return icon

def _product_button(name, callback_data, cat_key=None):
    """প্রোডাক্ট বাটন — icon custom ID হলে তা কখনো টেক্সটে দেখায় না, শুধু premium icon হিসেবে বসে"""
    icon = (PRODUCT_ICON_BY_NAME.get(name) or "").strip().strip("`'\"")
    if not icon and cat_key:
        icon = str(PRODUCT_ICON_THEME.get(cat_key, "")).strip()
    if not icon:
        icon = "📦"
    if _is_numeric_custom_id(icon):
        return _ibtn(text=name, callback_data=callback_data, icon_custom_emoji_id=icon)
    return _ibtn(text=f"{icon} {name}", callback_data=callback_data)

# ==================== STOCK MANAGER / PRODUCT DATABASE ====================
def init_stock_db():
    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, category_key TEXT UNIQUE, title TEXT NOT NULL, position INTEGER NOT NULL DEFAULT 0)")
        cur.execute("CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, category_id INTEGER NOT NULL, name TEXT NOT NULL, description TEXT DEFAULT '', pricing TEXT NOT NULL DEFAULT '{}', icon TEXT DEFAULT '', position INTEGER NOT NULL DEFAULT 0, FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE CASCADE)")
        try:
            cur.execute("ALTER TABLE users ADD COLUMN language TEXT DEFAULT 'en'")
        except sqlite3.OperationalError:
            pass
        try:
            cur.execute("ALTER TABLE products ADD COLUMN icon TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass
        conn.commit()

        cur.execute("SELECT COUNT(*) AS cnt FROM categories")
        if cur.fetchone()["cnt"] == 0:
            for pos, (key, cat) in enumerate(DEFAULT_CATEGORIES.items()):
                cur.execute("INSERT INTO categories(category_key,title,position) VALUES(?,?,?)", (key, cat["title"], pos))
                cat_id = cur.lastrowid
                for ppos, app in enumerate(cat["apps"]):
                    pricing = cat.get("pricing", {}).get(app, {"1": 0.60, "3": 1.50, "12": 4.10, "18": 6.00, "24": 8.00, "36": 12.00})
                    icon = _pick_product_icon(key, ppos)
                    cur.execute("INSERT INTO products(category_id,name,description,pricing,icon,position) VALUES(?,?,?,?,?,?)", (cat_id, app, "", json.dumps(pricing), icon, ppos))
        conn.commit()

        # পুরনো DB-তে icon খালি প্রোডাক্টে — পুল ঘুরিয়ে আলাদা আলাদা icon বসাও
        cur.execute("SELECT id, category_key FROM categories")
        for c in cur.fetchall():
            cid_, ckey = c["id"], c["category_key"]
            cur.execute("SELECT id, position FROM products WHERE category_id=? AND (icon IS NULL OR icon='') ORDER BY position, id", (cid_,))
            for r in cur.fetchall():
                icon = _pick_product_icon(ckey, r["position"])
                cur.execute("UPDATE products SET icon=? WHERE id=?", (icon, r["id"]))
        conn.commit()

def refresh_categories_from_stock():
    global CATEGORIES, PRODUCT_ICON_BY_NAME
    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, category_key, title FROM categories ORDER BY position, id")
        cats = cur.fetchall()
        new_categories = {}
        prod_icons = {}
        for cat in cats:
            cat_id, key, title = cat["id"], cat["category_key"], cat["title"]
            cur.execute("SELECT name, description, pricing, icon FROM products WHERE category_id=? ORDER BY position, id", (cat_id,))
            rows = cur.fetchall()
            apps, pricing = [], {}
            for row in rows:
                name = row["name"]
                apps.append(name)
                prod_icons[name] = row["icon"] or ""
                try:
                    pricing[name] = json.loads(row["pricing"])
                except Exception:
                    pricing[name] = {"1": 0.60, "3": 1.50, "12": 4.10, "18": 6.00, "24": 8.00, "36": 12.00}
            new_categories[key] = {"title": title, "apps": apps, "pricing": pricing}
    CATEGORIES = new_categories
    PRODUCT_ICON_BY_NAME = prod_icons

# I18N translation tables
I18N = {
    "en": {},
    "ar": {
        "🏠 Main Menu\\nPlease select an option below:": "🏠 القائمة الرئيسية\\nيرجى اختيار أحد الخيارات أدناه:",
        "🛒 Shop Menu": "🛒 قائمة المتجر", "💰 Balance": "💰 الرصيد", "💳 Deposit": "💳 إيداع",
        "👥 Refer": "👥 الإحالة", "🎧 Support": "🎧 الدعم", "🌐 Language": "🌐 اللغة",
        "🔍 Search App": "🔍 بحث عن تطبيق", "🔙 Back to Shop": "🔙 العودة إلى المتجر", "🏠 Home": "🏠 الرئيسية",
        "⚙️ Admin Panel": "⚙️ لوحة الإدارة", "⚙️ Stock Manager": "⚙️ مدير المخزون",
        "👥 Total Users": "👥 إجمالي المستخدمين", "📜 Deposit History": "📜 سجل الإيداعات", "📢 Broadcast Message": "📢 رسالة جماعية",
        "➕ Add Product": "➕ إضافة منتج", "➕ Add Category": "➕ إضافة قسم", "✏️ Edit": "✏️ تعديل", "🗑️ Delete": "🗑️ حذف",
        "🔝 Add First": "🔝 إضافة في البداية", "🔚 Add Last": "🔚 إضافة في النهاية", "🔙 Back": "🔙 رجوع",
        "🇬🇧 English": "🇬🇧 الإنجليزية", "🇸🇦 Arabic": "🇸🇦 العربية", "🇷🇺 Russian": "🇷🇺 الروسية", "🇮🇳 Hindi": "🇮🇳 الهندية",
        "🌐 Language Settings": "🌐 إعدادات اللغة", "Language updated successfully!": "تم تحديث اللغة بنجاح!",
    },
    "ru": {
        "🏠 Main Menu\\nPlease select an option below:": "🏠 Главное меню\\nВыберите нужный пункт ниже:",
        "🛒 Shop Menu": "🛒 Меню магазина", "💰 Balance": "💰 Баланс", "💳 Deposit": "💳 Пополнение",
        "👥 Refer": "👥 Реферал", "🎧 Support": "🎧 Поддержка", "🌐 Language": "🌐 Язык",
        "🔍 Search App": "🔍 Поиск приложения", "🔙 Back to Shop": "🔙 Назад в магазин", "🏠 Home": "🏠 Главная",
        "⚙️ Admin Panel": "⚙️ Панель администратора", "⚙️ Stock Manager": "⚙️ Управление запасами",
        "👥 Total Users": "👥 Всего пользователей", "📜 Deposit History": "📜 История депозитов", "📢 Broadcast Message": "📢 Рассылка",
        "➕ Add Product": "➕ Добавить товар", "➕ Add Category": "➕ Добавить категорию", "✏️ Edit": "✏️ Изменить", "🗑️ Delete": "🗑️ Удалить",
        "🔝 Add First": "🔝 Добавить в начало", "🔚 Add Last": "🔚 Добавить в конец", "🔙 Back": "🔙 Назад",
        "🇬🇧 English": "🇬🇧 Английский", "🇸🇦 Arabic": "🇸🇦 Арабский", "🇷🇺 Russian": "🇷🇺 Русский", "🇮🇳 Hindi": "🇮🇳 Хинди",
        "🌐 Language Settings": "🌐 Настройки языка", "Language updated successfully!": "Язык успешно изменён!",
    },
    "hi": {
        "🏠 Main Menu\\nPlease select an option below:": "🏠 मुख्य मेनू\\nनीचे से एक विकल्प चुनें:",
        "🛒 Shop Menu": "🛒 शॉप मेनू", "💰 Balance": "💰 बैलेंस", "💳 Deposit": "💳 जमा करें",
        "👥 Refer": "👥 रेफरल", "🎧 Support": "🎧 सहायता", "🌐 Language": "🌐 भाषा",
        "🔍 Search App": "🔍 ऐप खोजें", "🔙 Back to Shop": "🔙 शॉप पर वापस", "🏠 Home": "🏠 होम",
        "⚙️ Admin Panel": "⚙️ एडमिन पैनल", "⚙️ Stock Manager": "⚙️ स्टॉक मैनेजर",
        "👥 Total Users": "👥 कुल यूज़र", "📜 Deposit History": "📜 जमा इतिहास", "📢 Broadcast Message": "📢 ब्रॉडकास्ट संदेश",
        "➕ Add Product": "➕ प्रोडक्ट जोड़ें", "➕ Add Category": "➕ कैटेगरी जोड़ें", "✏️ Edit": "✏️ एडिट", "🗑️ Delete": "🗑️ डिलीट",
        "🔝 Add First": "🔝 सबसे पहले जोड़ें", "🔚 Add Last": "🔚 सबसे अंत में जोड़ें", "🔙 Back": "🔙 वापस",
        "🇬🇧 English": "🇬🇧 अंग्रेज़ी", "🇸🇦 Arabic": "🇸🇦 अरबी", "🇷🇺 Russian": "🇷🇺 रूसी", "🇮🇳 Hindi": "🇮🇳 हिंदी",
        "🌐 Language Settings": "🌐 भाषा सेटिंग्स", "Language updated successfully!": "भाषा सफलतापूर्वक बदल दी गई!",
    }
}

I18N["ar"].update({
    "🛒 **Subscription Shop Categories**\nSelect a category or click Search to find your preferred app:": "🛒 **فئات متجر الاشتراكات**\nاختر فئة أو اضغط على البحث للعثور على التطبيق المطلوب:",
    "🔍 **Search Application**\n\nPlease type the name of the app you are looking for (e.g. *YouTube Premium*, *ChatGPT*, *CapCut*):": "🔍 **بحث عن تطبيق**\n\nاكتب اسم التطبيق الذي تبحث عنه (مثل *YouTube Premium* أو *ChatGPT* أو *CapCut*):",
    "❌ **No apps found matching your query!**\nPlease try searching with a different keyword.": "❌ **لم يتم العثور على تطبيقات مطابقة!**\nحاول البحث بكلمة مختلفة.",
    "💰 **Account Balance**": "💰 **رصيد الحساب**",
    "Your current wallet balance:": "رصيد محفظتك الحالي:",
    "🎧 **Customer Support**": "🎧 **دعم العملاء**",
    "If you face any issues or have questions regarding subscriptions or deposits, please contact our support team.": "إذا واجهت أي مشكلة أو لديك سؤال حول الاشتراكات أو الإيداعات، تواصل مع فريق الدعم.",
    "⏳ **Deposit Submitted!**": "⏳ **تم إرسال طلب الإيداع!**",
    "🎉 **Purchase Successful!**": "🎉 **تم الشراء بنجاح!**",
    "❌ **Insufficient Balance!**": "❌ **الرصيد غير كافٍ!**",
    "Please deposit funds to your account to complete this purchase.": "يرجى إيداع الأموال في حسابك لإتمام عملية الشراء.",
})
I18N["ru"].update({
    "🛒 **Subscription Shop Categories**\nSelect a category or click Search to find your preferred app:": "🛒 **Категории магазина подписок**\nВыберите категорию или нажмите поиск, чтобы найти нужное приложение:",
    "🔍 **Search Application**\n\nPlease type the name of the app you are looking for (e.g. *YouTube Premium*, *ChatGPT*, *CapCut*):": "🔍 **Поиск приложения**\n\nВведите название приложения (например, *YouTube Premium*, *ChatGPT*, *CapCut*):",
    "❌ **No apps found matching your query!**\nPlease try searching with a different keyword.": "❌ **Совпадений не найдено!**\nПопробуйте другое ключевое слово.",
    "💰 **Account Balance**": "💰 **Баланс аккаунта**",
    "Your current wallet balance:": "Текущий баланс кошелька:",
    "🎧 **Customer Support**": "🎧 **Поддержка клиентов**",
    "If you face any issues or have questions regarding subscriptions or deposits, please contact our support team.": "Если у вас возникли вопросы по подпискам или депозитам, свяжитесь с нашей службой поддержки.",
    "⏳ **Deposit Submitted!**": "⏳ **Депозит отправлен!**",
    "🎉 **Purchase Successful!**": "🎉 **Покупка успешно завершена!**",
    "❌ **Insufficient Balance!**": "❌ **Недостаточно средств!**",
    "Please deposit funds to your account to complete this purchase.": "Пополните баланс, чтобы завершить покупку.",
})
I18N["hi"].update({
    "🛒 **Subscription Shop Categories**\nSelect a category or click Search to find your preferred app:": "🛒 **सब्सक्रिप्शन शॉप कैटेगरी**\nकैटेगरी चुनें या ऐप खोजने के लिए सर्च दबाएँ:",
    "🔍 **Search Application**\n\nPlease type the name of the app you are looking for (e.g. *YouTube Premium*, *ChatGPT*, *CapCut*):": "🔍 **ऐप खोजें**\n\nजिस ऐप को खोज रहे हैं उसका नाम लिखें (जैसे *YouTube Premium*, *ChatGPT*, *CapCut*):",
    "❌ **No apps found matching your query!**\nPlease try searching with a different keyword.": "❌ **कोई ऐप नहीं मिला!**\nकिसी दूसरे कीवर्ड से खोजें।",
    "💰 **Account Balance**": "💰 **अकाउंट बैलेंस**",
    "Your current wallet balance:": "आपका वर्तमान वॉलेट बैलेंस:",
    "🎧 **Customer Support**": "🎧 **कस्टमर सपोर्ट**",
    "If you face any issues or have questions regarding subscriptions or deposits, please contact our support team.": "सब्सक्रिप्शन या डिपॉज़िट से जुड़ी समस्या होने पर सपोर्ट टीम से संपर्क करें।",
    "⏳ **Deposit Submitted!**": "⏳ **डिपॉज़िट भेज दिया गया!**",
    "🎉 **Purchase Successful!**": "🎉 **खरीद सफल!**",
    "❌ **Insufficient Balance!**": "❌ **बैलेंस कम है!**",
    "Please deposit funds to your account to complete this purchase.": "खरीद पूरी करने के लिए अपने अकाउंट में बैलेंस जमा करें।",
})

def translate_text(user_id, text):
    if not text:
        return text
    lang = get_language(user_id)
    if lang == "en":
        return text
    out = text
    phrases = sorted(I18N.get(lang, {}).items(), key=lambda x: len(x[0]), reverse=True)
    for src, dst in phrases:
        out = out.replace(src, dst)
    return out

def category_rows():
    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, category_key, title FROM categories ORDER BY position, id")
        rows = cur.fetchall()
    return rows

def product_rows(category_id):
    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, name, description, pricing, icon FROM products WHERE category_id=? ORDER BY position, id", (category_id,))
        rows = cur.fetchall()
    return rows

def find_product_by_name(name):
    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT p.id, p.category_id, p.name, p.description, p.pricing, c.category_key FROM products p JOIN categories c ON c.id=p.category_id WHERE lower(p.name)=lower(?) LIMIT 1", (name.strip(),))
        row = cur.fetchone()
    return row  # sqlite3.Row

# ==================== LANGUAGE ====================
LANG_TEXT = ('🌐 Language', 'Language', '🌐 اللغة', 'اللغة', '🌐 Язык', 'Язык', '🌐 भाषा', 'भाषा')

@dp.message(F.text.in_(LANG_TEXT))
async def msg_language(message: Message):
    buttons = [[_ibtn(text="🇬🇧 English", callback_data="lang|en")],
               [_ibtn(text="🇸🇦 Arabic", callback_data="lang|ar")],
               [_ibtn(text="🇷🇺 Russian", callback_data="lang|ru")],
               [_ibtn(text="🇮🇳 Hindi", callback_data="lang|hi")]]
    await message.answer(translate_text(message.from_user.id, "🌐 Language Settings"), reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data.startswith("lang|"))
async def cb_language(callback: CallbackQuery):
    await callback.answer()
    lang = callback.data.split("|", 1)[1]
    set_language(callback.from_user.id, lang)
    try:
        await callback.message.edit_text(translate_text(callback.from_user.id, "Language updated successfully!"), reply_markup=home_back_buttons())
    except Exception:
        pass

# ==================== STOCK MANAGER ====================

def resync_default_catalog():
    """ডিফল্ট ক্যাটালগ অনুযায়ী: ক্যাটাগরি ঠিক + ডিফল্ট অ্যাপগুলো সঠিক ক্যাটাগরিতে।
    নিজে যোগ করা প্রোডাক্ট মুছে না (শুধু ডিফল্ট নামেরগুলো সরায়/যোগায়)।"""
    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, category_key FROM categories")
        existing = {r["category_key"]: r["id"] for r in cur.fetchall()}
        for pos, key in enumerate(DEFAULT_CATEGORIES):
            default = DEFAULT_CATEGORIES[key]
            if key in existing:
                cid = existing[key]
                cur.execute("UPDATE categories SET title=?, position=? WHERE id=?", (default["title"], pos, cid))
            else:
                cur.execute("INSERT INTO categories(category_key,title,position) VALUES(?,?,?)", (key, default["title"], pos))
                cid = cur.lastrowid
            idx = 0
            for app in default["apps"]:
                cur.execute("SELECT id FROM products WHERE lower(name)=lower(?) ORDER BY id LIMIT 1", (app,))
                row = cur.fetchone()
                if row:
                    cur.execute("UPDATE products SET category_id=?, position=? WHERE id=?", (cid, idx, row["id"]))
                else:
                    pricing = default.get("pricing", {}).get(app, {"1": 0.60, "3": 1.50, "12": 4.10, "18": 6.00, "24": 8.00, "36": 12.00})
                    icon = _pick_product_icon(key, idx)
                    cur.execute("INSERT INTO products(category_id,name,description,pricing,icon,position) VALUES(?,?,?,?,?,?)",
                                (cid, app, "", json.dumps(pricing), icon, idx))
                idx += 1
        conn.commit()
    refresh_categories_from_stock()

STOCK_PAGE = 5

def stock_manager_kb():
    rows = []
    for cat in category_rows():
        rows.append([
            _ibtn(text=f"📂 {cat['title']}", callback_data=f"sm_cat|{cat['id']}|1", style="primary"),
            _ibtn(text="✏️ Edit", callback_data=f"sm_editcat|{cat['id']}", style="primary"),
            _ibtn(text="🗑️ Delete", callback_data=f"sm_delcat|{cat['id']}", style="danger")
        ])
    rows.append([_ibtn(text="➕ Add Category", callback_data="sm_addcat", style="success")])
    rows.append([_ibtn(text="🔄 Sync Default Categories", callback_data="sm_sync", style="primary")])
    rows.append([_ibtn(text="🔙 Back", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
def stock_product_kb(category_id, page=1):
    """প্রোডাক্ট তালিকা — পেজে পেজে (৫টা/পেজ) — Edit / Icon / Move / Delete বাটনসহ"""
    prods = product_rows(category_id)
    pages = max(1, -(-len(prods) // STOCK_PAGE))
    page = max(1, min(page, pages))
    rows = []
    rows.append([
        _ibtn(text="Add First", callback_data=f"sm_addprod|{category_id}|first", style="success", icon_custom_emoji_id=get_icon("addfirst")),
        _ibtn(text="🔚 Add Last", callback_data=f"sm_addprod|{category_id}|last", style="success")
    ])
    if not prods:
        rows.append([_ibtn(text="(কোনো প্রোডাক্ট নেই — উপরে Add First/Add Last চাপো)", callback_data="noop")])
    for prod in prods[(page - 1) * STOCK_PAGE: page * STOCK_PAGE]:
        rows.append([_product_button(prod['name'], f"sm_prod|{prod['id']}")])
        rows.append([
            _ibtn(text="✏️ Edit", callback_data=f"sm_editprod|{prod['id']}", style="primary"),
            _ibtn(text="🎨 Icon", callback_data=f"sm_icon|{prod['id']}", style="primary"),
            _ibtn(text="🗂️ Move", callback_data=f"sm_mv|{prod['id']}", style="primary"),
            _ibtn(text="🗑️ Delete", callback_data=f"sm_delprod|{prod['id']}", style="danger")
        ])
    nav = []
    if page > 1:
        nav.append(_ibtn(text="⬅️", callback_data=f"sm_cat|{category_id}|{page - 1}"))
    nav.append(_ibtn(text=f"📄 {page}/{pages}", callback_data="noop"))
    if page < pages:
        nav.append(_ibtn(text="➡️", callback_data=f"sm_cat|{category_id}|{page + 1}"))
    rows.append(nav)
    rows.append([_ibtn(text="🔙 Back", callback_data="stock_manager")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
@dp.callback_query(F.data == "stock_manager")
async def cb_stock_manager(callback: CallbackQuery):
    await callback.answer()
    try:
        await callback.message.edit_text("⚙️ **Stock Manager**\n\n📂 Select a category. You can edit or delete categories, or open one to manage products.", reply_markup=stock_manager_kb(), parse_mode="Markdown")
    except Exception:
        pass

@dp.callback_query(F.data.startswith("sm_cat|"))
async def cb_stock_category(callback: CallbackQuery):
    await callback.answer()
    parts = callback.data.split("|")
    cat_id = int(parts[1])
    page = int(parts[2]) if len(parts) > 2 else 1
    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT title FROM categories WHERE id=?", (cat_id,))
        row = cur.fetchone()
    if not row:
        try:
            await callback.message.edit_text("❌ Category not found.", reply_markup=stock_manager_kb())
        except Exception:
            pass
        return
    try:
        await callback.message.edit_text(f"📂 **{row['title']}**\n\nপ্রোডাক্টে ক্লিক = বিবরণ/দাম/আইকন এডিট · ✏️ Edit = নাম/বিবরণ/দাম · 🗂️ Move = অন্য ক্যাটাগরি", reply_markup=stock_product_kb(cat_id, page), parse_mode="Markdown")
    except Exception:
        pass

@dp.callback_query(F.data == "sm_sync")
async def cb_sm_sync(callback: CallbackQuery):
    await callback.answer()
    if callback.from_user.id != ADMIN_ID:
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [_ibtn(text="✅ Yes, Sync Now", callback_data="sm_dosync", style="success"),
         _ibtn(text="❌ Cancel", callback_data="stock_manager", style="danger")]
    ])
    txt = "🔄 **Sync Default Categories?**\n\nডিফল্ট ক্যাটালগ অনুযায়ী (YouTube Premium → Entertainment সহ):\n• মিসিং ক্যাটাগরি যোগ হবে\n• ডিফল্ট অ্যাপগুলো সঠিক ক্যাটাগরিতে যাবে\n• নিজে যোগ করা প্রোডাক্ট মুছবে না"
    try:
        await callback.message.edit_text(txt, reply_markup=kb, parse_mode="Markdown")
    except Exception:
        pass

@dp.callback_query(F.data == "sm_dosync")
async def cb_sm_dosync(callback: CallbackQuery):
    await callback.answer()
    if callback.from_user.id != ADMIN_ID:
        return
    resync_default_catalog()
    try:
        await callback.message.edit_text("✅ **Default categories synced!** (YouTube Premium এখন Entertainment-এ; ডুপ্লিকেট অ্যাপ এক কপি হয়েছে)", reply_markup=stock_manager_kb(), parse_mode="Markdown")
    except Exception:
        pass

@dp.callback_query(F.data.startswith("sm_mv|"))
async def cb_move_product(callback: CallbackQuery):
    await callback.answer()
    if callback.from_user.id != ADMIN_ID:
        return
    pid = int(callback.data.split("|")[1])
    rows = []
    for cat in category_rows():
        rows.append([_ibtn(text=f"📂 {cat['title']}", callback_data=f"sm_mvto|{pid}|{cat['id']}", style="primary")])
    rows.append([_ibtn(text="🔙 Back", callback_data=f"sm_prod|{pid}")])
    try:
        await callback.message.edit_text("🗂️ **Move Product — কোন ক্যাটাগরিতে যাবে?**", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows), parse_mode="Markdown")
    except Exception:
        pass

@dp.callback_query(F.data.startswith("sm_mvto|"))
async def cb_move_product_to(callback: CallbackQuery):
    await callback.answer()
    if callback.from_user.id != ADMIN_ID:
        return
    _, pid, cid = callback.data.split("|")
    pid, cid = int(pid), int(cid)
    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COALESCE(MAX(position),-1)+1 AS pos FROM products WHERE category_id=?", (cid,))
        pos = cur.fetchone()["pos"]
        cur.execute("UPDATE products SET category_id=?, position=? WHERE id=?", (cid, pos, pid))
        conn.commit()
    refresh_categories_from_stock()
    try:
        await callback.message.edit_text("✅ **Product moved to the new category.**", reply_markup=stock_product_kb(cid))
    except Exception:
        pass

@dp.callback_query(F.data == "sm_addcat")
async def cb_add_category(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(StockState.add_category_name)
    try:
        await callback.message.edit_text("➕ **Add Category**\n\nSend the new category name/title:", reply_markup=home_back_buttons("stock_manager"), parse_mode="Markdown")
    except Exception:
        pass

@dp.message(StockState.add_category_name)
async def process_add_category(message: Message, state: FSMContext):
    name = message.text.strip()
    if not name:
        return await message.answer("⚠️ Category name cannot be empty.")
    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COALESCE(MAX(position),-1)+1 AS pos FROM categories")
        pos = cur.fetchone()["pos"]
        key = "cat_" + re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") + "_" + str(int(datetime.now().timestamp()))
        cur.execute("INSERT INTO categories(category_key,title,position) VALUES(?,?,?)", (key, name, pos))
        conn.commit()
    refresh_categories_from_stock()
    await state.clear()
    await message.answer("✅ Category added at the end.", reply_markup=main_menu(message.from_user.id))

@dp.callback_query(F.data.startswith("sm_editcat|"))
async def cb_edit_category(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    cat_id = int(callback.data.split("|")[1])
    await state.update_data(edit_cat_id=cat_id)
    await state.set_state(StockState.edit_category_name)
    try:
        await callback.message.edit_text("✏️ **Edit Category**\n\nSend the new category name/title:", reply_markup=home_back_buttons("stock_manager"), parse_mode="Markdown")
    except Exception:
        pass

@dp.message(StockState.edit_category_name)
async def process_edit_category(message: Message, state: FSMContext):
    data = await state.get_data()
    cat_id = data["edit_cat_id"]
    name = message.text.strip()
    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE categories SET title=? WHERE id=?", (name, cat_id))
        conn.commit()
    refresh_categories_from_stock()
    await state.clear()
    await message.answer("✅ Category updated.", reply_markup=main_menu(message.from_user.id))

@dp.callback_query(F.data.startswith("sm_delcat|"))
async def cb_delete_category(callback: CallbackQuery):
    await callback.answer()
    cat_id = int(callback.data.split("|")[1])
    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT title FROM categories WHERE id=?", (cat_id,))
        row = cur.fetchone()
    if not row:
        try:
            await callback.message.edit_text("❌ Category not found.", reply_markup=stock_manager_kb())
        except Exception:
            pass
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[[_ibtn(text="✅ Yes, Delete", callback_data=f"sm_confirmdelcat|{cat_id}"), _ibtn(text="❌ Cancel", callback_data="stock_manager")]])
    try:
        await callback.message.edit_text(f"⚠️ Delete category **{row['title']}** and all products inside it?", reply_markup=kb, parse_mode="Markdown")
    except Exception:
        pass

@dp.callback_query(F.data.startswith("sm_confirmdelcat|"))
async def cb_confirm_delete_category(callback: CallbackQuery):
    await callback.answer()
    cat_id = int(callback.data.split("|")[1])
    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM products WHERE category_id=?", (cat_id,))
        cur.execute("DELETE FROM categories WHERE id=?", (cat_id,))
        conn.commit()
    refresh_categories_from_stock()
    try:
        await callback.message.edit_text("✅ Category deleted.", reply_markup=stock_manager_kb())
    except Exception:
        pass

@dp.callback_query(F.data.startswith("sm_addprod|"))
async def cb_add_product(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    _, cat_id, order = callback.data.split("|")
    await state.update_data(product_cat_id=int(cat_id), product_order=order)
    await state.set_state(StockState.add_product_name)
    try:
        await callback.message.edit_text("➕ **Add Product**\n\n1️⃣ Send product name:", reply_markup=home_back_buttons(f"sm_cat|{cat_id}"), parse_mode="Markdown")
    except Exception:
        pass

@dp.message(StockState.add_product_name)
async def process_add_product_name(message: Message, state: FSMContext):
    raw = message.text.strip()
    icon = ""
    name = raw
    # ফরম্যাট ১: icon=<custom emoji ID> Name  বা  icon:ID Name
    import re as _re
    mm = _re.match(r"^icon[=: \t]+([\d]{6,64})[\s]+(.+)$", raw, _re.I)
    if mm:
        icon = mm.group(1)
        name = mm.group(2).strip()
    else:
        # ফরম্যাট ২: <custom emoji ID> Name — ID-টা নাম হয়ে না গিয়ে icon বসবে
        head = _re.match(r"^([\d]{6,64})[\s]+(.+)$", raw)
        if head and head.group(2).strip():
            icon = head.group(1)
            name = head.group(2).strip()
    if not icon:
        # ফরম্যাট ৩: <ইমোজি> Name — শুরুর ইমোজিটা প্রোডাক্ট আইকন হয়ে যাবে
        nk = _leading_premium_key(raw)
        if nk:
            rest = _strip_prefix(raw, nk)
            if rest:
                icon = _emoji_orig_char(nk)
                name = rest
    await state.update_data(product_name=name, product_icon=icon)
    await state.set_state(StockState.add_product_description)
    extra = ""
    if icon:
        extra = "\n🎨 Icon সেট হয়েছে: `" + icon + "`"
    await message.answer("2️⃣ **Description**\n\nSend a short product description:" + extra, parse_mode="Markdown")

@dp.message(StockState.add_product_description)
async def process_add_product_description(message: Message, state: FSMContext):
    await state.update_data(product_description=message.text.strip())
    await state.set_state(StockState.add_product_pricing)
    await message.answer("3️⃣ **Pricing**\n\nSend one duration per line in this format:\n`18 - 0.80`\n`1 - 1.40`\n`12 - 8.75`\n\nNumbers are USD. Duration is in months.", parse_mode="Markdown")

def parse_pricing(text):
    result = {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r"^(\d+)\s*(?:-|–|—)\s*\$?\s*(\d+(?:\.\d+)?)\s*(?:USD)?$", line, re.I)
        if not m:
            return None
        result[m.group(1)] = float(m.group(2))
    return result or None

@dp.message(StockState.add_product_pricing)
async def process_add_product_pricing(message: Message, state: FSMContext):
    pricing = parse_pricing(message.text)
    if not pricing:
        return await message.answer("⚠️ Invalid pricing. Use one line per duration, e.g. `18 - 0.80`", parse_mode="Markdown")
    await state.update_data(product_pricing=pricing)
    await state.set_state(StockState.add_product_icon)
    await message.answer(
        "4️⃣ **Custom Emoji (ঐচ্ছিক)**\n\n"
        "এই প্রোডাক্টের জন্য একটা আলাদা **ইমোজি** দিন —\n"
        "• একটা ইমোজি পাঠান (যেমন: 🤖 📺 🎬 💵)\n"
        "• অথবা একটা **custom emoji ID** (সংখ্যা)\n"
        "• `-` বা `skip` দিলে অটো (ক্যাটাগরির পুল থেকে আলাদা ইমোজি নেবে)\n\n"
        "পরে Stock Manager → 🎨 Icon দিয়েও যেকোনো সময় বদলাতে পারবেন।",
        parse_mode="Markdown"
    )

@dp.message(StockState.add_product_icon)
async def process_add_product_icon(message: Message, state: FSMContext):
    val = _clean_stored_icon(message.text)
    icon = ""
    if val.lower() not in ("-", "skip", "0", "none", "auto", ""):
        if _is_numeric_custom_id(val):
            ok = await validate_emoji_id(val)
            if not ok:
                return await message.answer("❌ ওই custom emoji ID valid নয়। সঠিক ID, একটা ইমোজি, অথবা `-` (অটো) পাঠান।", parse_mode="Markdown")
            icon = val
        else:
            icon = val
    data = await state.get_data()
    cat_id = data["product_cat_id"]
    order = data["product_order"]
    if not icon:
        with db_conn() as conn0:
            cu0 = conn0.cursor()
            cu0.execute("SELECT category_key FROM categories WHERE id=?", (cat_id,))
            cc = cu0.fetchone()
        ckey = cc["category_key"] if cc else ""
        with db_conn() as conn1:
            cu1 = conn1.cursor()
            cu1.execute("SELECT COALESCE(MAX(position),-1) AS mx FROM products WHERE category_id=?", (cat_id,))
            mx = cu1.fetchone()["mx"]
        icon = _pick_product_icon(ckey, 0 if order == "first" else mx + 1)
    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COALESCE(MAX(position),-1) AS mx FROM products WHERE category_id=?", (cat_id,))
        maxpos = cur.fetchone()["mx"]
        if order == "first":
            cur.execute("UPDATE products SET position=position+1 WHERE category_id=?", (cat_id,))
            pos = 0
        else:
            pos = maxpos + 1
        cur.execute("INSERT INTO products(category_id,name,description,pricing,icon,position) VALUES(?,?,?,?,?,?)",
                    (cat_id, data["product_name"], data["product_description"], json.dumps(data["product_pricing"]), icon, pos))
        new_pid = cur.lastrowid
        conn.commit()
    refresh_categories_from_stock()
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [_product_button(data["product_name"], f"sm_prod|{new_pid}")],
        [_ibtn(text="🔙 Stock Manager", callback_data="stock_manager")]
    ])
    await message.answer("✅ Product added to stock successfully.", reply_markup=kb)

@dp.callback_query(F.data.startswith("sm_prod|"))
async def cb_stock_product(callback: CallbackQuery):
    await callback.answer()
    pid = int(callback.data.split("|")[1])
    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT p.id, p.name, p.description, p.pricing, p.category_id, c.title AS cat_title FROM products p JOIN categories c ON c.id=p.category_id WHERE p.id=?", (pid,))
        row = cur.fetchone()
    if not row:
        try:
            await callback.message.edit_text("❌ Product not found.", reply_markup=stock_manager_kb())
        except Exception:
            pass
        return
    name, desc, pj, cat_id, cat_title = row["name"], row["description"], row["pricing"], row["category_id"], row["cat_title"]
    try:
        prices = json.loads(pj)
    except Exception:
        prices = {}
    price_lines = "\n".join([f"• {m} month(s) — ${v:.2f} USD" for m, v in prices.items()]) or "No pricing"
    plain, cid = _prod_icon_chars(name)
    head = (plain + " " if plain else "") + "**" + name + "**"
    icon_note = ""
    if cid and not plain:
        icon_note = f"\n🎨 Icon: custom emoji ID `{cid}`"
    elif not cid and not plain:
        icon_note = "\n🎨 Icon: (নেই — Stock-এ Icon দিন)"
    md = head + icon_note + f"\n📁 Category: **{cat_title}**\n🆔 ID: `{pid}`\n\n" + (str(desc) + "\n\n" if desc else "") + "💰 **Pricing:**\n" + price_lines
    body = _htmlize_broadcast(md)
    if cid and not plain:
        body = '<tg-emoji emoji-id="%s">📦</tg-emoji> ' % cid + body
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [_ibtn(text="✏️ Edit", callback_data=f"sm_editprod|{pid}"),
         _ibtn(text="🎨 Icon", callback_data=f"sm_icon|{pid}", style="primary"),
         _ibtn(text="🗂️ Move", callback_data=f"sm_mv|{pid}", style="primary"),
         _ibtn(text="🗑️ Delete", callback_data=f"sm_delprod|{pid}", style="danger")],
        [_ibtn(text="🔙 Back", callback_data=f"sm_cat|{cat_id}|1")]
    ])
    try:
        await callback.message.edit_text(body, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass

@dp.callback_query(F.data.startswith("sm_icon|"))
async def cb_sm_icon(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    if callback.from_user.id != ADMIN_ID:
        return
    pid = int(callback.data.split("|")[1])
    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT name, icon FROM products WHERE id=?", (pid,))
        r = cur.fetchone()
    if not r:
        return
    await state.update_data(icon_pid=pid)
    await state.set_state(StockState.set_product_icon)
    cur_icon = r["icon"] or "(কোনো আইকন নেই)"
    try:
        await callback.message.edit_text(
            f"🎨 **Product Icon**\n\n📦 প্রোডাক্ট: **{r['name']}**\n📌 বর্তমান: `{cur_icon}`\n\n"
            "নতুন icon পাঠান —\n"
            "• একটা **custom emoji ID** (সংখ্যা)\n"
            "• অথবা একটা ইমোজি (যেমন: 🤖 🎬 💵)\n"
            "• `0` = মুছে ফেলো (ক্যাটাগরি থিম নেবে)\n\n"
            "ফরম্যাট: `icon=6289... Name` দরকার নেই — শুধু icon টা পাঠাও।",
            reply_markup=home_back_buttons("stock_manager"), parse_mode="Markdown"
        )
    except Exception:
        pass

@dp.message(StockState.set_product_icon)
async def process_sm_icon(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    data = await state.get_data()
    pid = data.get("icon_pid")
    if not pid:
        await state.clear()
        return
    val = _clean_stored_icon(message.text)
    new_icon = ""
    if val.lower() not in ("0", "-", "none", "remove", "off", "delete", ""):
        if _is_numeric_custom_id(val):
            ok = await validate_emoji_id(val)
            if not ok:
                return await message.answer("❌ ওই custom emoji ID valid নয়। সঠিক ID বা একটা ইমোজি পাঠাও।", parse_mode="Markdown")
            new_icon = val
        else:
            new_icon = val
    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT category_id FROM products WHERE id=?", (pid,))
        r = cur.fetchone()
        cat_id = r["category_id"] if r else None
        cur.execute("UPDATE products SET icon=? WHERE id=?", (new_icon, pid))
        conn.commit()
    refresh_categories_from_stock()
    await state.clear()
    back_cb = data.get("icon_back")
    if back_cb:
        kb_back = InlineKeyboardMarkup(inline_keyboard=[[_ibtn(text="🔙 আইকন তালিকায় ফিরে যাও", callback_data=back_cb)]])
    else:
        kb_back = InlineKeyboardMarkup(inline_keyboard=[[_ibtn(text="🔙 প্রোডাক্টে ফিরে যাও", callback_data=f"sm_prod|{pid}")]])
    await message.answer("✅ প্রোডাক্টের icon সেভ হয়েছে!", reply_markup=kb_back)

@dp.callback_query(F.data.startswith("sm_delprod|"))
async def cb_delete_product(callback: CallbackQuery):
    await callback.answer()
    pid = int(callback.data.split("|")[1])
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [_ibtn(text="✅ Yes, Delete", callback_data=f"sm_confirmdelprod|{pid}"),
         _ibtn(text="❌ Cancel", callback_data=f"sm_prod|{pid}")]
    ])
    try:
        await callback.message.edit_text("⚠️ Delete this product from stock?", reply_markup=kb)
    except Exception:
        pass

@dp.callback_query(F.data.startswith("sm_confirmdelprod|"))
async def cb_confirm_delete_product(callback: CallbackQuery):
    await callback.answer()
    pid = int(callback.data.split("|")[1])
    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT category_id FROM products WHERE id=?", (pid,))
        row = cur.fetchone()
        cat_id = row["category_id"] if row else None
        cur.execute("DELETE FROM products WHERE id=?", (pid,))
        conn.commit()
    refresh_categories_from_stock()
    try:
        await callback.message.edit_text("✅ Product deleted.", reply_markup=stock_product_kb(cat_id) if cat_id else stock_manager_kb())
    except Exception:
        pass

@dp.callback_query(F.data.startswith("sm_editprod|"))
async def cb_edit_product(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    pid = int(callback.data.split("|")[1])
    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT name, description, pricing FROM products WHERE id=?", (pid,))
        row = cur.fetchone()
    if not row:
        try:
            await callback.message.edit_text("❌ Product not found.", reply_markup=stock_manager_kb())
        except Exception:
            pass
        return
    await state.update_data(edit_pid=pid, old_product_name=row["name"], old_product_description=row["description"])
    await state.set_state(StockState.edit_product_name)
    try:
        await callback.message.edit_text(f"✏️ **Edit Product**\n\nCurrent name: **{row['name']}**\n\nSend the new name (or send `-` to keep it):", reply_markup=home_back_buttons(), parse_mode="Markdown")
    except Exception:
        pass

@dp.message(StockState.edit_product_name)
async def process_edit_product_name(message: Message, state: FSMContext):
    data = await state.get_data()
    name = data["old_product_name"] if message.text.strip() == "-" else message.text.strip()
    await state.update_data(new_product_name=name)
    await state.set_state(StockState.edit_product_description)
    await message.answer("Send the new description (or `-` to keep the current one):", parse_mode="Markdown")

# FIX: Description ঠিকমতো ডেটাবেস থেকে নেওয়ার বাগটি ফিক্স করা হয়েছে!
@dp.message(StockState.edit_product_description)
async def process_edit_product_description(message: Message, state: FSMContext):
    data = await state.get_data()
    current_desc = data.get("old_product_description", "")
    new_desc = current_desc if message.text.strip() == "-" else message.text.strip()
    await state.update_data(new_product_description=new_desc)
    await state.set_state(StockState.edit_product_pricing)
    await message.answer("Send the new pricing lines, or `-` to keep current pricing. Example: `18 - 0.80`", parse_mode="Markdown")

@dp.message(StockState.edit_product_pricing)
async def process_edit_product_pricing(message: Message, state: FSMContext):
    data = await state.get_data()
    pid = data["edit_pid"]
    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT description, pricing, category_id FROM products WHERE id=?", (pid,))
        row = cur.fetchone()

        if not row:
            await state.clear()
            return await message.answer("❌ Product not found.")

        desc = data.get("new_product_description", row["description"])
        pricing_json = row["pricing"] if message.text.strip() == "-" else None

        if pricing_json is None:
            pricing = parse_pricing(message.text)
            if not pricing:
                return await message.answer("⚠️ Invalid pricing. Use `18 - 0.80` per line or `-` to keep current pricing.", parse_mode="Markdown")
            pricing_json = json.dumps(pricing)

        cur.execute("UPDATE products SET name=?, description=?, pricing=? WHERE id=?",
                    (data["new_product_name"], desc, pricing_json, pid))
        cat_id = row["category_id"]
        conn.commit()

    refresh_categories_from_stock()
    await state.clear()
    await message.answer("✅ Product updated successfully.", reply_markup=main_menu(message.from_user.id))

@dp.callback_query(F.data == "admin_stock")
async def cb_admin_stock_alias(callback: CallbackQuery):
    await callback.answer()
    try:
        await callback.message.edit_text("⚙️ **Stock Manager**", reply_markup=stock_manager_kb(), parse_mode="Markdown")
    except Exception:
        pass

@dp.callback_query(F.data.startswith("prod|"))
async def cb_broadcast_product(callback: CallbackQuery):
    await callback.answer()
    pid = int(callback.data.split("|", 1)[1])
    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT p.name, p.description, p.pricing, p.category_id, c.category_key FROM products p JOIN categories c ON c.id=p.category_id WHERE p.id=?", (pid,))
        row = cur.fetchone()
    if not row:
        try:
            await callback.message.edit_text("❌ Product not found or removed from stock.")
        except Exception:
            pass
        return
    name, desc, pricing_json, cat_key = row["name"], row["description"], row["pricing"], row["category_key"]
    try:
        pricing = json.loads(pricing_json)
    except Exception:
        pricing = {}
    buttons = [[_ibtn(text=f"⏱️ {d} Months - ${p:.2f} USD", callback_data=f"buy|{name}|{d}|{p}", style="success")] for d, p in pricing.items()]
    buttons.append([_ibtn(text="🔙 Back", callback_data=f"cat|{cat_key}|1")])
    body = f"📦 **App Name:** {name}\n\n{desc}\n\nSelect your preferred subscription duration to purchase:"
    try:
        await callback.message.edit_text(body, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")
    except Exception:
        pass

# ==================== BUTTON ICON MANAGER (ADMIN-EDITABLE) ====================
# Admin Panel → "🎨 Button Icons" থেকে যেকোনো বাটনের কাস্টম ইমোজি যেকোনো সময় বদলানো যায়।
# Change গুলো icon_settings টেবিলে সেভ থাকে — restart লাগে না, সাথে সাথে প্রযোজ্য।

class IconState(StatesGroup):
    waiting_for_icon = State()

# slot -> (default premium icon id, label)
ICON_SLOTS = {
    "accept":    (PREMIUM_EMOJI.get("✅"),  "Accept (Deposit approve)"),
    "reject":    (PREMIUM_EMOJI.get("🚫"),  "Reject (Deposit decline)"),
    "buy":       (PREMIUM_EMOJI.get("✅"),  "Buy Now (purchase)"),
    "deposit":   (PREMIUM_EMOJI.get("💳"),  "Deposit (add funds)"),
    "users":     (PREMIUM_EMOJI.get("👀"),  "Admin - Total Users"),
    "history":   (PREMIUM_EMOJI.get("🏦"),  "Admin - Deposit History"),
    "broadcast": (PREMIUM_EMOJI.get("📣"),  "Admin - Broadcast Message"),
    "stock":     (PREMIUM_EMOJI.get("⚙️"),  "Admin - Stock Manager"),
    "support":   (PREMIUM_EMOJI.get("📞"),  "Contact Support"),
    "search":    (PREMIUM_EMOJI.get("🔄"),  "Search Again"),
    "addfirst":  (PREMIUM_EMOJI.get("🔝"),  "Stock - Add First"),
    "iconmgr":   (PREMIUM_EMOJI.get("🎉"),  "Admin - Button Icons (this menu)"),
    # ডিপোজিট পদ্ধতিগুলোর নিজস্ব icon (admin → 🎨 Button Icons → ডিপোজিট স্ক্রিন)
    "deposit_binance": (None, "Binance বাটন"),
    "deposit_usdt":    (None, "USDT (ERC20) বাটন"),
    "deposit_epay":    (None, "ePay বাটন"),
    "deposit_bdt":     (None, "BDT P2P বাটন"),
    "deposit_bkash":   (None, "bKash বাটন"),
    "deposit_nagad":   (None, "Nagad বাটন"),
}

_EMOJI_PAGE_SIZE = 8

def init_icons():
    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS icon_settings (slot TEXT PRIMARY KEY, icon_id TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT)")
        conn.commit()
        # প্রথমবার: সব ইমোজি AUTO (Premium) করে দেয় — ইউজার প্যানেলসহ সব জায়গায়।
        # একবার হয়ে গেলে আর override করে না (তোমার নিজের বদল নষ্ট হয় না)।
        cur.execute("SELECT v FROM meta WHERE k='premium_seeded'")
        seeded = cur.fetchone()
        if not seeded:
            try:
                for nk in _emoji_list():
                    cur.execute("INSERT INTO icon_settings(slot, icon_id) VALUES(?,?) "
                                "ON CONFLICT(slot) DO UPDATE SET icon_id=excluded.icon_id",
                                (_EMOJI_PREFIX + nk, "AUTO"))
                cur.execute("INSERT OR REPLACE INTO meta(k,v) VALUES('premium_seeded','1')")
                conn.commit()
            except Exception as e:
                logging.exception("init_icons seeding failed: %s", e)
                conn.rollback()

def _icon_override(slot):
    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT icon_id FROM icon_settings WHERE slot=?", (slot,))
        row = cur.fetchone()
    if row and row["icon_id"]:
        return row["icon_id"]
    return None

def get_icon(slot):
    """বাটন-স্লটের বর্তমান icon — override > default"""
    try:
        override = _icon_override(slot)
    except Exception:
        override = None
    default = ICON_SLOTS.get(slot, (None, ""))[0]
    if override == "NONE":
        return None
    return override or default

def set_icon(slot, icon_id):
    """icon_id=None → override মুছে default; icon_id='NONE' → icon বন্ধ; সংখ্যা → সেট"""
    with db_conn() as conn:
        cur = conn.cursor()
        if icon_id is None:
            cur.execute("DELETE FROM icon_settings WHERE slot=?", (slot,))
        else:
            cur.execute("INSERT INTO icon_settings(slot, icon_id) VALUES(?,?) "
                        "ON CONFLICT(slot) DO UPDATE SET icon_id=excluded.icon_id", (slot, icon_id))
        conn.commit()

async def validate_emoji_id(emoji_id):
    """Telegram API দিয়ে ID সত্যি সত্যি VALID কিনা চেক"""
    try:
        stickers = await bot.get_custom_emoji_stickers(custom_emoji_ids=[emoji_id])
        return bool(stickers)
    except Exception:
        return False

def _emoji_mode_txt(nk):
    s = _emoji_get(nk)
    if s is None:
        return "ইউনিকোড"
    if s == "AUTO":
        return "Premium ✓"
    return "Custom ✓"

# প্রতিটা ইমোজি কোন বাটনে ব্যবহার হয় — ম্যানেজারে দেখানোর জন্য
EMOJI_USAGE = json.loads('{"🛍": "Shop মেনু", "💰": "Balance", "💳": "Deposit", "👥": "Refer", "🎧": "Support", "🌐": "Language", "⚙": "Admin/Stock", "🛒": "Buy", "📦": "প্রোডাক্ট বাটন", "⏱": "দাম/ডিউরেশন", "🔙": "Back (সব জায়গায়)", "🔍": "Search", "🏠": "Home", "➡": "Next Page", "⬅": "Back Page", "🤖": "AI ক্যাটাগরি", "🎨": "Photo ক্যাটাগরি", "🎬": "Video ক্যাটাগরি", "🎵": "Music ক্যাটাগরি", "🎭": "Entertainment ক্যাটাগরি", "📚": "Education ক্যাটাগরি", "☁": "Cloud/Office ক্যাটাগরি", "💻": "Developer ক্যাটাগরি", "🔐": "VPN ক্যাটাগরি", "📱": "Social ক্যাটাগরি", "🧰": "PDF/Utility ক্যাটাগরি", "⭐": "Bonus ক্যাটাগরি", "🟡": "Binance", "📧": "ePay", "🇧🇩": "BDT P2P", "💖": "bKash", "🟠": "Nagad", "👀": "Total Users", "🏦": "Deposit History", "📣": "Broadcast", "🎉": "Icon ম্যানেজার/অফার", "📂": "Stock ক্যাটাগরি", "✏": "Edit", "🗑": "Delete", "➕": "Add Category", "🔝": "Add First", "🔚": "Add Last", "✅": "Accept/সফল", "❌": "Reject/বাতিল", "⛔": "Reject/বন্ধ", "🚫": "Reject/নিষেধ", "⚠": "সতর্কতা", "⌛": "Pending/অপেক্ষা", "⏳": "Deposit Submitted", "💵": "USD/দাম", "💸": "টাকা/ছাড়", "👍": "লাইক/ঠিক", "❤": "ভালোবাসা", "🔥": "অফার/জরুরি", "✨": "বিশেষ/নতুন", "💡": "টিপস/আইডিয়া", "📍": "লোকেশন/তথ্য", "🔗": "লিংক", "🔖": "বুকমার্ক", "📊": "পরিসংখ্যান", "📌": "পিন/গুরুত্ব", "📅": "তারিখ", "📞": "Support/ফোন", "🙋": "সাহায্য", "😎": "কুল/স্টাইল", "🚀": "লঞ্চ/দ্রুত", "💨": "দ্রুত", "😁": "হাসি", "😏": "হাসি", "😮": "আশ্চর্য", "😢": "দুঃখ", "😡": "রাগ", "⭕": "খালি/চিহ্ন", "🅱": "bKash", "🆔": "আইডি", "🔘": "বাটন", "ℹ": "তথ্য", "⁉": "প্রশ্ন", "👋": "Welcome", "👤": "ইউজার", "📥": "ডিপোজিট রিকোয়েস্ট", "📝": "নোট/লেখা", "📜": "হিস্টরি", "📢": "ব্রডকাস্ট", "🔄": "Search Again/রিফ্রেশ", "🌟": "স্টার/বিশেষ", "🎁": "গিফট/অফার", "🎯": "টার্গেট", "🇬🇧": "English", "🇸🇦": "Arabic", "🇷🇺": "Russian", "🇮🇳": "Hindi", "1⃣": "ধাপ ১", "2⃣": "ধাপ ২", "3⃣": "ধাপ ৩", "✔": "ঠিক", "🔹": "তালিকা", "🔻": "নিচে/মিনিমাম", "✉": "Broadcast/মেসেজ", "😮‍💨": "রিলিফ/হাসি"}')

def _emoji_usage_label(nk):
    """ইমোজির (normalized) ব্যবহারের বর্ণনা"""
    return EMOJI_USAGE.get(nk, "সাধারণ ইমোজি")

def _emoji_orig_char(nk):
    """normalized key -> সুন্দর original (VS16-সহ) ইমোজি"""
    for k, cid in _PREMIUM_KEYS:
        if k == nk:
            for orig in PREMIUM_EMOJI:
                if _norm_emoji(orig) == nk:
                    return orig
            return nk
    return nk

def _emoji_list():
    return sorted(_PREMIUM_BY_NORM.keys(), key=lambda x: (len(x) > 4, x))

def _emojipage_count():
    return max(1, -(-len(_emoji_list()) // _EMOJI_PAGE_SIZE))

# ==================== SCREEN-BASED ICON MANAGER ====================
# Admin-এ বটের মতোই পেজ-পেজ করে ইমোজি এডিট করা যায়:
#   🏠 হোম → হোম/মেইন মেনুর ইমোজি    💳 ডিপোজিট → ডিপোজিট স্ক্রিনের ইমোজি ... ইত্যাদি
# item = ("e", norm_key, label)  → ওই ইমোজি (সব জায়গায় একসাথে)
# item = ("s", slot, label)      → নির্দিষ্ট স্পেশাল বাটন
SCREEN_GROUPS = [
    {"id": "home", "title": "🏠 হোম / মেইন মেনু", "items": [
        ("e", "🛍", "Shop"), ("e", "💰", "Balance"), ("e", "💳", "Deposit"),
        ("e", "👥", "Refer"), ("e", "🎧", "Support"), ("e", "🌐", "Language"), ("e", "⚙", "Admin")]},
    {"id": "shop", "title": "🛒 শপ — ক্যাটাগরি", "items": [
        ("e", "🤖", "AI ক্যাটাগরি"), ("e", "🎨", "Photo ক্যাটাগরি"), ("e", "🎬", "Video ক্যাটাগরি"),
        ("e", "🎵", "Music ক্যাটাগরি"), ("e", "🎭", "Entertainment ক্যাটাগরি"), ("e", "📚", "Edu ক্যাটাগরি"), ("e", "☁", "Office ক্যাটাগরি"),
        ("e", "💻", "Dev ক্যাটাগরি"), ("e", "🔐", "VPN ক্যাটাগরি"), ("e", "📱", "Social ক্যাটাগরি"),
        ("e", "🧰", "PDF ক্যাটাগরি"), ("e", "⭐", "Bonus ক্যাটাগরি"), ("e", "🔍", "Search")]},
    {"id": "prod", "title": "📦 প্রোডাক্ট ও দাম", "items": [
        ("e", "📦", "প্রোডাক্ট বাটন"), ("e", "⏱", "দাম/ডিউরেশন"),
        ("s", "buy", "Buy Now"), ("s", "addfirst", "Stock - Add First")]},
    {"id": "search", "title": "🔍 সার্চ", "items": [
        ("e", "🔍", "Search"), ("e", "🔄", "Search Again")]},
    {"id": "balance", "title": "💰 ব্যালেন্স", "items": [
        ("e", "💰", "Balance"), ("e", "👥", "Refer"), ("s", "deposit", "Deposit")]},
    {"id": "deposit", "title": "💳 ডিপোজিট", "items": [
        ("s", "deposit", "Deposit (add funds)"),
        ("s", "deposit_binance", "Binance বাটন"), ("s", "deposit_usdt", "USDT (ERC20) বাটন"),
        ("s", "deposit_epay", "ePay বাটন"), ("s", "deposit_bdt", "BDT P2P বাটন"),
        ("s", "deposit_bkash", "bKash বাটন"), ("s", "deposit_nagad", "Nagad বাটন"),
        ("s", "accept", "Accept (Approve)"), ("s", "reject", "Reject")]},
    {"id": "refer", "title": "👥 রেফার", "items": [
        ("e", "👥", "Refer"), ("e", "🔗", "Referral Link")]},
    {"id": "support", "title": "🎧 সাপোর্ট", "items": [
        ("e", "🎧", "Support"), ("s", "support", "Contact Support")]},
    {"id": "admin", "title": "⚙️ অ্যাডমিন প্যানেল", "items": [
        ("s", "users", "Total Users"), ("s", "history", "Deposit History"),
        ("s", "broadcast", "Broadcast"), ("s", "stock", "Stock Manager"),
        ("s", "iconmgr", "Button Icons"),
        ("e", "✅", "Accept/সফল"), ("e", "🚫", "Reject/নিষেধ"), ("e", "🎉", "Offers/সফল")]},
]

def _slot_edit_btn(slot, label=None):
    """স্পেশাল বাটনের এডিট বাটন (current icon সহ)"""
    label = label or ICON_SLOTS[slot][1]
    cur_id = get_icon(slot)
    kw = {"text": label, "callback_data": f"icn_set|{slot}", "style": "primary"}
    if cur_id:
        kw["icon_custom_emoji_id"] = cur_id
    return _ibtn(**kw)

def icon_screen_kb(screen_id):
    """একটা স্ক্রিনের সব ইমোজি — এডিট/রিসেট বাটনসহ"""
    rows = []
    shown_e = set()
    for grp in SCREEN_GROUPS:
        if grp["id"] != screen_id:
            continue
        for kind, key, label in grp["items"]:
            if kind == "e":
                shown_e.add(key)
                if key not in _PREMIUM_BY_NORM:
                    continue
                mode = _emoji_mode_txt(key)
                usage = _emoji_usage_label(key)
                char = _emoji_orig_char(key)
                lbl = f"{char} {usage} · {mode}"[:58]
                rows.append([
                    _ibtn(text=lbl, callback_data="icn_eset|" + key, style="primary"),
                    _ibtn(text="🔄", callback_data="icn_ereset|" + key)
                ])
            else:
                rows.append([
                    _slot_edit_btn(key, label),
                    _ibtn(text="🔄", callback_data="icn_reset|" + key)
                ])
    # 🛒 শপ স্ক্রিন: বর্তমান সব ক্যাটাগরি (Entertainment-সহ নতুনও) অটো দেখাও
    if screen_id == "shop":
        for cat in category_rows():
            nk = _leading_premium_key(cat["title"] or "")
            if not nk or nk in shown_e:
                continue
            shown_e.add(nk)
            mode = _emoji_mode_txt(nk)
            char = _emoji_orig_char(nk)
            usage = cat["title"]
            lbl = f"{char} {usage} · {mode}"[:58]
            rows.append([
                _ibtn(text=lbl, callback_data="icn_eset|" + nk, style="primary"),
                _ibtn(text="🔄", callback_data="icn_ereset|" + nk)
            ])
    rows.append([_ibtn(text="🔙 Back", callback_data="icon_manager")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def icon_screens_kb():
    """স্ক্রিন তালিকা — ২টা করে বাটন"""
    rows = []
    pairs = []
    for grp in SCREEN_GROUPS:
        pairs.append((grp["title"], grp["id"]))
    for i in range(0, len(pairs), 2):
        row = [_ibtn(text=pairs[i][0], callback_data="icn_scr|" + pairs[i][1], style="primary")]
        if i + 1 < len(pairs):
            row.append(_ibtn(text=pairs[i+1][0], callback_data="icn_scr|" + pairs[i+1][1], style="primary"))
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)

def icon_main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [_ibtn(text="🎨 স্ক্রিন অনুযায়ী ({})".format(len(SCREEN_GROUPS)), callback_data="icn_screens", style="primary")],
        [_ibtn(text="💠 সব ইমোজি ({})".format(len(_emoji_list())), callback_data="icn_emoji|1", style="primary"),
         _ibtn(text="🧩 স্পেশাল বাটন ({})".format(len(ICON_SLOTS)), callback_data="icn_sites", style="primary")],
        [_ibtn(text="📦 প্রোডাক্ট আইকন (প্রতি প্রোডাক্ট)", callback_data="icn_prodcats", style="primary"),
         _ibtn(text="🖼️ প্রোডাক্ট আইকন রিসেট", callback_data="icn_resetprod", style="primary")],
        [_ibtn(text="🔙 Back", callback_data="admin_panel")],
        [_ibtn(text="🎯 সব Premium", callback_data="icn_allprem", style="success"),
         _ibtn(text="🗑️ সব Normal", callback_data="icn_allnorm", style="danger")],
    ])

def icon_sites_kb():
    rows = []
    for slot, (did, label) in ICON_SLOTS.items():
        cur = get_icon(slot)
        kw = {"text": label, "callback_data": f"icn_set|{slot}", "style": "primary"}
        if cur:
            kw["icon_custom_emoji_id"] = cur
        rows.append([_ibtn(**kw), _ibtn(text="🔄", callback_data=f"icn_reset|{slot}")])
    rows.append([_ibtn(text="🔙 Back", callback_data="icon_manager")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

ICON_PROD_PAGE = 6

def icon_prod_cats_kb():
    """কোন ক্যাটাগরির প্রোডাক্টের icon বদলাবে — ক্যাটাগরি ২টা করে"""
    cats = category_rows()
    rows = []
    for i in range(0, len(cats), 2):
        row = [_ibtn(text=cats[i]["title"], callback_data="icn_pcat|%s|1" % cats[i]["id"], style="primary")]
        if i + 1 < len(cats):
            row.append(_ibtn(text=cats[i + 1]["title"], callback_data="icn_pcat|%s|1" % cats[i + 1]["id"], style="primary"))
        rows.append(row)
    rows.append([_ibtn(text="🔙 Back", callback_data="icon_manager")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def icon_prod_list_kb(category_id, page=1):
    """এক ক্যাটাগরির সব প্রোডাক্ট — প্রতিটা প্রোডাক্টের icon আলাদা বদলানো যায়"""
    prods = product_rows(category_id)
    pages = max(1, -(-len(prods) // ICON_PROD_PAGE))
    page = max(1, min(page, pages))
    rows = []
    if not prods:
        rows.append([_ibtn(text="(এই ক্যাটাগরিতে প্রোডাক্ট নেই)", callback_data="noop")])
    for prod in prods[(page - 1) * ICON_PROD_PAGE: page * ICON_PROD_PAGE]:
        rows.append([_product_button(prod["name"], "icn_pset|%s" % prod["id"])])
        rows.append([
            _ibtn(text="✏️ ইমোজি বদলাও", callback_data="icn_pset|%s" % prod["id"], style="primary"),
            _ibtn(text="🔄 অটো (পুল)", callback_data="icn_preset|%s" % prod["id"])
        ])
    nav = []
    if page > 1:
        nav.append(_ibtn(text="⬅️", callback_data="icn_pcat|%s|%s" % (category_id, page - 1)))
    nav.append(_ibtn(text="📄 %d/%d" % (page, pages), callback_data="noop"))
    if page < pages:
        nav.append(_ibtn(text="➡️", callback_data="icn_pcat|%s|%s" % (category_id, page + 1)))
    rows.append(nav)
    rows.append([_ibtn(text="🔙 ক্যাটাগরি তালিকা", callback_data="icn_prodcats")])
    rows.append([_ibtn(text="🔙 Button Icons", callback_data="icon_manager")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def icon_emoji_page_kb(page=1):
    allk = _emoji_list()
    pages = _emojipage_count()
    page = max(1, min(page, pages))
    rows = []
    chunk = allk[(page-1)*_EMOJI_PAGE_SIZE : page*_EMOJI_PAGE_SIZE]
    for nk in chunk:
        mode = _emoji_mode_txt(nk)
        char = _emoji_orig_char(nk)
        usage = _emoji_usage_label(nk)
        # বাটনে ইমোজি + কোথায় ব্যবহার হয় + মোড — সব একসাথে
        lbl = f"{char} {usage}  ·  {mode}"[:60]
        rows.append([
            _ibtn(text=lbl, callback_data="icn_eset|" + nk, style="primary"),
            _ibtn(text="🔄", callback_data="icn_ereset|" + nk)
        ])
    nav = []
    if page > 1:
        nav.append(_ibtn(text="◀️", callback_data=f"icn_emoji|{page-1}"))
    nav.append(_ibtn(text=f"{page}/{pages}", callback_data="noop"))
    if page < pages:
        nav.append(_ibtn(text="▶️", callback_data=f"icn_emoji|{page+1}"))
    if nav:
        rows.append(nav)
    rows.append([_ibtn(text="🔙 Back", callback_data="icon_manager")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def _icon_help_text(where="সব"):
    return (
        "🎨 **Button Icon Manager — {where}**\n\n"
        "যেকোনো বাটনে ক্লিক করে তার ইমোজি বদলান।\n"
        "একটা **custom emoji ID** (সংখ্যা) পাঠালে সাথে সাথে সেভ হয়।\n\n"
        "• `0` বা `p` → **Premium (AUTO)** — JSON-এর premium ভার্সন\n"
        "• `-` বা `n` → **Normal** — আসল ইউনিকোড ইমোজি\n"
        "• সংখ্যা → তোমার নিজের **custom emoji ID**\n"
        "• 🏷️ **ব্র্যান্ড লোগো:** নিজের logo-র ID পেস্ট করলে ওই লোগো সব জায়গায় নামের পাশে বসে —\n"
        "   যেমন ডিপোজিটে 🟡 = Binance, 💖 = bKash, 🟠 = Nagad, 📧 = ePay/Gmail;\n"
        "   প্রোডাক্টে (Stock → 🎨 Icon) Telegram/YouTube/Netflix লোগোর ID দিতে পারো।\n\n"
        "📍 **💠 প্রতিটা ইমোজি** লিস্ট দিয়ে **ইউজার প্যানেল + অ্যাডমিন প্যানেল — সব জায়গার** বাটন নিয়ন্ত্রণ হয়\n"
        "(মেইন মেনু, শপ, ক্যাটাগরি, প্রোডাক্ট, ডিপোজিট, সার্চ, ব্রডকাস্ট... সব)।\n\n"
        "⚠️ Custom ইমোজি দেখাতে bot owner-এর Telegram Premium লাগে (তোমার আছে ✅)।\n"
        "📌 পুরনো মেসেজে থাকা keyboard আপডেট হয় না — বদলের পর নতুন মেসেজ/`/start` পাঠালে দেখা যাবে।"
    )

@dp.callback_query(F.data == "icon_manager")
async def cb_icon_manager(callback: CallbackQuery):
    await callback.answer()
    if callback.from_user.id != ADMIN_ID:
        return
    try:
        await callback.message.edit_text(
            "🎨 **Button Icon Manager**\n\n"
            "বটের যেকোনো স্ক্রিনের ইমোজি বদলাতে **🎨 স্ক্রিন অনুযায়ী** খুলো —\n"
            "সেখানে প্রতিটা স্ক্রিন আলাদা পেজে (🏠 হোম, 💳 ডিপোজিট, 💰 ব্যালেন্স, 🛒 শপ...)\n"
            "যা দেখবে সেটাই সেই স্ক্রিনের বাটনের ইমোজি।\n\n"
            "✏️ ক্লিক করলে: `0`/`p`=Premium · `-`/`n`=Normal · সংখ্যা=নিজের custom ID\n"
            "🔄 = Normal-এ রিসেট।\n\n"
            "💡 **খেয়াল:** একটা ইমোজি যত জায়গায় আছে সব জায়গায় একসাথে বদলায়।",
            reply_markup=icon_main_kb(), parse_mode="Markdown"
        )
    except Exception:
        pass

@dp.callback_query(F.data == "icn_screens")
async def cb_icon_screens(callback: CallbackQuery):
    await callback.answer()
    if callback.from_user.id != ADMIN_ID:
        return
    try:
        await callback.message.edit_text(
            "🎨 **কোন স্ক্রিনের ইমোজি বদলাবে?**\n\nনিচ থেকে বেছে নাও —\nযে স্ক্রিনে ক্লিক করবে, ওই স্ক্রিনের বাটনগুলোর ইমোজি দেখাবে:",
            reply_markup=icon_screens_kb(), parse_mode="Markdown"
        )
    except Exception:
        pass

@dp.callback_query(F.data.startswith("icn_scr|"))
async def cb_icon_screen(callback: CallbackQuery):
    await callback.answer()
    if callback.from_user.id != ADMIN_ID:
        return
    sid = callback.data.split("|", 1)[1]
    title = next((g["title"] for g in SCREEN_GROUPS if g["id"] == sid), "স্ক্রিন")
    try:
        await callback.message.edit_text(
            f"🎨 **{title}** — এই স্ক্রিনের ইমোজি:\n\n"
            "✏️ ক্লিক = বদলাও (Premium/Normal/নিজের ID)\n🔄 = Normal",
            reply_markup=icon_screen_kb(sid), parse_mode="Markdown"
        )
    except Exception:
        pass

@dp.callback_query(F.data == "icn_sites")
async def cb_icon_sites(callback: CallbackQuery):
    await callback.answer()
    if callback.from_user.id != ADMIN_ID:
        return
    try:
        await callback.message.edit_text(_icon_help_text("স্পেশাল বাটন"), reply_markup=icon_sites_kb(), parse_mode="Markdown")
    except Exception:
        pass

@dp.callback_query(F.data.startswith("icn_emoji|"))
async def cb_icon_emoji_page(callback: CallbackQuery):
    await callback.answer()
    if callback.from_user.id != ADMIN_ID:
        return
    try:
        page = int(callback.data.split("|")[1])
    except Exception:
        page = 1
    try:
        await callback.message.edit_text(
            _icon_help_text("ইমোজি (ইউনিকোড / Premium / Custom)") + f"\n\n📄 পেজ {page}/{_emojipage_count()}:",
            reply_markup=icon_emoji_page_kb(page), parse_mode="Markdown"
        )
    except Exception:
        pass

@dp.callback_query(F.data == "icn_allprem")
async def cb_icon_all_premium(callback: CallbackQuery):
    await callback.answer()
    if callback.from_user.id != ADMIN_ID:
        return
    for nk in _emoji_list():
        _emoji_set(nk, "AUTO")
    for slot in ICON_SLOTS:
        set_icon(slot, None)  # default (premium) এ ফিরাও
    try:
        await callback.message.edit_text("✅ **সব ইমোজি Premium (JSON)** করা হয়েছে!\n\nযেকোনোটা পছন্দ না হলে নিচ থেকে বদলে নাও:",
                                         reply_markup=icon_main_kb(), parse_mode="Markdown")
    except Exception:
        pass

@dp.callback_query(F.data == "icn_allnorm")
async def cb_icon_all_normal(callback: CallbackQuery):
    await callback.answer()
    if callback.from_user.id != ADMIN_ID:
        return
    for nk in _emoji_list():
        _emoji_set(nk, None)
    for slot in ICON_SLOTS:
        set_icon(slot, "NONE")
    try:
        await callback.message.edit_text("🗑️ **সব ইমোজি Normal (ইউনিকোড)** করা হয়েছে!\n\nচাইলে এক ক্লিকে আবার Premium করো:",
                                         reply_markup=icon_main_kb(), parse_mode="Markdown")
    except Exception:
        pass

@dp.callback_query(F.data == "icn_resetprod")
async def cb_icon_reset_products(callback: CallbackQuery):
    await callback.answer()
    if callback.from_user.id != ADMIN_ID:
        return
    # প্রতিটা প্রোডাক্টে ক্যাটাগরি পুল থেকে আলাদা আলাদা icon বসাও
    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT c.id AS cid, c.category_key FROM categories c ORDER BY c.position, c.id")
        cats = cur.fetchall()
        for c in cats:
            cur.execute("SELECT id, position FROM products WHERE category_id=? ORDER BY position, id", (c["cid"],))
            rows = cur.fetchall()
            for r in rows:
                icon = _pick_product_icon(c["category_key"], r["position"])
                cur.execute("UPDATE products SET icon=? WHERE id=?", (icon, r["id"]))
        conn.commit()
    refresh_categories_from_stock()
    try:
        await callback.message.edit_text(
            "🖼️ **সব প্রোডাক্টে আলাদা আলাদা icon** বসানো হয়েছে!\n"
            "(পুল থেকে ঘুরিয়ে — পাশাপাশি একই icon থাকবে না)\n\n"
            "Stock Manager → 🎨 Icon দিয়ে যেকোনোটা নিজে বদলাতে পারো।",
            reply_markup=icon_main_kb(), parse_mode="Markdown"
        )
    except Exception:
        pass

@dp.callback_query(F.data == "icn_prodcats")
async def cb_icon_prod_cats(callback: CallbackQuery):
    await callback.answer()
    if callback.from_user.id != ADMIN_ID:
        return
    txt = "📦 **প্রোডাক্ট আইকন**\n\nকোন ক্যাটাগরির প্রোডাক্টের ইমোজি বদলাবে, বেছে নাও —\nপ্রতিটা প্রোডাক্টের আলাদা ইমোজি/লোগো বসাতে পারবে:"
    try:
        await callback.message.edit_text(txt, reply_markup=icon_prod_cats_kb(), parse_mode="Markdown")
    except Exception:
        pass

@dp.callback_query(F.data.startswith("icn_pcat|"))
async def cb_icon_prod_cat(callback: CallbackQuery):
    await callback.answer()
    if callback.from_user.id != ADMIN_ID:
        return
    parts = callback.data.split("|")
    cat_id = int(parts[1])
    page = int(parts[2]) if len(parts) > 2 else 1
    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT title FROM categories WHERE id=?", (cat_id,))
        row = cur.fetchone()
    title = row["title"] if row else "ক্যাটাগরি"
    txt = "📦 **%s**\n\nপ্রোডাক্টে ক্লিক = ইমোজি বদলাও\n🔄 অটো (পুল) = ক্যাটাগরি পুল থেকে আলাদা আইকন\n\nবাটনে যে ইমোজি দেখছো সেটাই ওই প্রোডাক্টের বর্তমান আইকন:" % title
    try:
        await callback.message.edit_text(txt, reply_markup=icon_prod_list_kb(cat_id, page), parse_mode="Markdown")
    except Exception:
        pass

@dp.callback_query(F.data.startswith("icn_pset|"))
async def cb_icon_prod_set(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    if callback.from_user.id != ADMIN_ID:
        return
    pid = int(callback.data.split("|", 1)[1])
    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT p.name, p.category_id, c.category_key FROM products p JOIN categories c ON c.id=p.category_id WHERE p.id=?", (pid,))
        row = cur.fetchone()
    if not row:
        return
    cat_id = row["category_id"]
    await state.update_data(icon_pid=pid, icon_back="icn_pcat|%s|1" % cat_id)
    await state.set_state(StockState.set_product_icon)
    try:
        await callback.message.edit_text(
            "✏️ **%s**-এর icon বদলাও\n\nপাঠাও —\n• একটা **ইমোজি** (যেমন: 🤖 🎬 💵)\n• অথবা একটা **custom emoji ID** (লোগোর সংখ্যা)\n• `0` / `-` = অটো (ক্যাটাগরি পুল থেকে আলাদা)\n\nপ্রিভিউ দেখিয়ে সেভ হবে।" % row["name"],
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[_ibtn(text="🔙 Back", callback_data="icn_pcat|%s|1" % cat_id)]]),
            parse_mode="Markdown"
        )
    except Exception:
        pass

@dp.callback_query(F.data.startswith("icn_preset|"))
async def cb_icon_prod_reset(callback: CallbackQuery):
    await callback.answer()
    if callback.from_user.id != ADMIN_ID:
        return
    pid = int(callback.data.split("|", 1)[1])
    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT products.category_id AS category_id, products.position AS position, categories.category_key AS category_key FROM products JOIN categories ON categories.id=products.category_id WHERE products.id=?", (pid,))
        row = cur.fetchone()
        if row:
            icon = _pick_product_icon(row["category_key"], row["position"])
            cur.execute("UPDATE products SET icon=? WHERE id=?", (icon, pid))
            cat_id = row["category_id"]
        else:
            cat_id = None
        conn.commit()
    refresh_categories_from_stock()
    try:
        await callback.message.edit_text("✅ অটো আইকন (পুল থেকে আলাদা) বসানো হয়েছে!", reply_markup=icon_prod_list_kb(cat_id, 1) if cat_id else icon_prod_cats_kb())
    except Exception:
        pass

@dp.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery):
    await callback.answer()

@dp.callback_query(F.data.startswith("icn_set|"))
async def cb_icon_set(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    if callback.from_user.id != ADMIN_ID:
        return
    slot = callback.data.split("|", 1)[1]
    if slot not in ICON_SLOTS:
        return
    await state.update_data(icon_target="site", icon_key=slot)
    await state.set_state(IconState.waiting_for_icon)
    label = ICON_SLOTS[slot][1]
    cur_id = get_icon(slot)
    cur_txt = cur_id if cur_id else "(normal)"
    try:
        await callback.message.edit_text(
            f"✏️ **Change Icon**\n\n🔘 **{label}**\n📌 বর্তমান: `{cur_txt}`\n\n" + _icon_help_text("এই বাটন"),
            reply_markup=home_back_buttons("icn_sites"), parse_mode="Markdown"
        )
    except Exception:
        pass

@dp.callback_query(F.data.startswith("icn_eset|"))
async def cb_icon_emoji_set(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    if callback.from_user.id != ADMIN_ID:
        return
    nk = callback.data.split("|", 1)[1]
    if nk not in _PREMIUM_BY_NORM:
        return
    await state.update_data(icon_target="emoji", icon_key=nk)
    await state.set_state(IconState.waiting_for_icon)
    mode = _emoji_mode_txt(nk)
    try:
        await callback.message.edit_text(
            f"✏️ **Change Emoji**\n\n"f"{_emoji_orig_char(nk)} **{_emoji_usage_label(nk)}**\n"f"🔘 এই ইমোজি দিয়ে শুরু **সব বাটনে** (যেমন: `{_emoji_usage_label(nk)}`) বসবে\n"f"📌 বর্তমান: **{mode}**\n\n" + _icon_help_text("এই ইমোজি"),
            reply_markup=home_back_buttons("icon_manager"), parse_mode="Markdown"
        )
    except Exception:
        pass

@dp.message(IconState.waiting_for_icon)
async def process_icon_value(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    data = await state.get_data()
    target = data.get("icon_target")
    key = data.get("icon_key")
    if not target or not key:
        await state.clear()
        return
    val = message.text.strip().lower()

    def back_kb():
        if target == "site":
            return home_back_buttons("icn_sites")
        return home_back_buttons("icon_manager")

    if val in ("0", "p", "premium", "auto", "default"):
        if target == "site":
            set_icon(key, None)      # default (premium)
            msg = f"🔄 **{ICON_SLOTS[key][1]}** → Premium (AUTO) ডিফল্ট ✅"
        else:
            _emoji_set(key, "AUTO")
            msg = f"🔄 ইমোজি `{key}` → Premium (AUTO) ✅"
        await state.clear()
        return await message.answer(msg, reply_markup=back_kb(), parse_mode="Markdown")

    if val in ("-", "n", "none", "normal", "off", "remove", "unicode"):
        if target == "site":
            set_icon(key, "NONE")
            msg = f"🚫 **{ICON_SLOTS[key][1]}** → Normal (কোনো icon নেই) ✅"
        else:
            _emoji_set(key, None)
            msg = f"🚫 ইমোজি `{key}` → Normal (ইউনিকোড) ✅"
        await state.clear()
        return await message.answer(msg, reply_markup=back_kb(), parse_mode="Markdown")

    if val.isdigit() and 10 <= len(val) <= 25:
        ok = await validate_emoji_id(val)
        if not ok:
            return await message.answer(
                "❌ **VALID নয়!** এই ID-তে কোনো custom emoji পাওয়া যায়নি।\n"
                "সঠিক ID পাঠান, অথবা `0` (Premium) / `-` (Normal)...",
                parse_mode="Markdown"
            )
        if target == "site":
            set_icon(key, val)
            name = ICON_SLOTS[key][1]
        else:
            _emoji_set(key, val)
            name = f"ইমোজি {key}"
        await state.clear()
        preview_kb = InlineKeyboardMarkup(inline_keyboard=[
            [_ibtn(text=name, callback_data="icon_manager", style="success", icon_custom_emoji_id=val)]
        ])
        await message.answer(f"✅ **{name}** → নতুন custom icon সেভ হয়েছে!\n\nপ্রিভিউ:", reply_markup=preview_kb, parse_mode="Markdown")
        return await message.answer("আরেকটা বদলাতে নিচের বাটনে ক্লিক করো:", reply_markup=back_kb(), parse_mode="Markdown")

    await message.answer(
        "⚠️ একটা **custom emoji ID** (শুধু সংখ্যা) পাঠান, অথবা `0` (Premium) / `-` (Normal)...",
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("icn_reset|"))
async def cb_icon_reset(callback: CallbackQuery):
    await callback.answer()
    if callback.from_user.id != ADMIN_ID:
        return
    slot = callback.data.split("|", 1)[1]
    if slot not in ICON_SLOTS:
        return
    set_icon(slot, None)
    try:
        await callback.message.edit_text(_icon_help_text("স্পেশাল বাটন") + "\n(একটা default-এ রিসেট ✅)", reply_markup=icon_sites_kb(), parse_mode="Markdown")
    except Exception:
        pass

@dp.callback_query(F.data.startswith("icn_ereset|"))
async def cb_icon_emoji_reset(callback: CallbackQuery):
    await callback.answer()
    if callback.from_user.id != ADMIN_ID:
        return
    nk = callback.data.split("|", 1)[1]
    if nk not in _PREMIUM_BY_NORM:
        return
    _emoji_set(nk, None)
    try:
        await callback.message.edit_text(_icon_help_text("ইমোজি") + "\n(একটা Normal-এ রিসেট ✅)", reply_markup=icon_main_kb(), parse_mode="Markdown")
    except Exception:
        pass

# ==================== NEW FEATURE: AUTO BROADCAST SYSTEM ====================
async def auto_broadcast_task():
    while True:
        # ৬-৭ ঘণ্টার জন্য অপেক্ষা (21600 থেকে 25200 সেকেন্ডের মধ্যে র‍্যান্ডম)
        wait_time = random.randint(6 * 3600, 7 * 3600)
        await asyncio.sleep(wait_time)

        try:
            with db_conn() as conn:
                cur = conn.cursor()
                # ডেটাবেস থেকে একটি র‍্যান্ডম প্রোডাক্ট সিলেক্ট করা হচ্ছে
                cur.execute("SELECT p.id, p.name, p.pricing FROM products p JOIN categories c ON c.id=p.category_id ORDER BY RANDOM() LIMIT 1")
                row = cur.fetchone()

                if not row:
                    continue

                pid, name, pricing_json = row["id"], row["name"], row["pricing"]

                cur.execute("SELECT user_id FROM users")
                users = cur.fetchall()

            # প্রোডাক্টের আসল দাম কালেক্ট করা হচ্ছে
            try:
                pricing = json.loads(pricing_json)
            except Exception:
                pricing = {}

            if not pricing:
                continue

            # প্রোডাক্টের প্রথম প্যাকেজের মেয়াদ এবং দাম নেওয়া হলো
            duration = list(pricing.keys())[0]
            price = pricing[duration]

            # র‍্যান্ডম স্টক নাম্বার
            added = random.randint(50, 150)
            current = added + random.randint(10, 50)

            is_discount = random.choice([True, False])

            # মেসেজের ডিজাইন
            if is_discount:
                msg = (
                    f"🎉 **Special Discount Offer!**\n\n"
                    f"🎁 {name}  {duration} Month(s) - No Warranty\n"
                    f"➕ Added: {added}\n"
                    f"📦 Current stock: {current}\n"
                    f"💸 Price: **${price:.2f} USD**\n\n"
                    f"🔥 Hurry up and grab yours now before stock ends!"
                )
            else:
                msg = (
                    f"📢 **New Stock Available!**\n\n"
                    f"🎁 {name}  {duration} Month(s) - No Warranty\n"
                    f"➕ Added: {added}\n"
                    f"📦 Current stock: {current}\n"
                    f"💸 Price: **${price:.2f} USD**"
                )

            # প্রোডাক্টের স্পেসিফিক বাটন
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [_ibtn(text=f"🛒 {name}", callback_data=f"prod|{pid}", style="success")]
            ])

            # সব ইউজারকে মেসেজ পাঠানো
            for u in users:
                try:
                    await bot.send_message(u["user_id"], _htmlize_broadcast(msg), reply_markup=kb, parse_mode="HTML")
                    await asyncio.sleep(0.05)
                except Exception:
                    pass

        except Exception as e:
            logging.error(f"Auto Broadcast Error: {e}")

# ==================== MAIN EXECUTION ====================
async def main():
    init_stock_db()
    init_icons()
    refresh_categories_from_stock()

    # অটো মেসেজ সিস্টেমটি ব্যাকগ্রাউন্ডে চালু করা হলো
    asyncio.create_task(auto_broadcast_task())

    # চালু অবস্থা জানাতে স্পষ্ট বার্তা — দেখলেই বুঝবে বট লাইভ
    print("=" * 60, flush=True)
    try:
        me = await bot.get_me()
        print(f"OK BOT RUNNING -> @{me.username}", flush=True)
    except Exception as e:
        print(f"WARN token check failed: {e}", flush=True)
    print("DB file: " + str(DB_NAME), flush=True)
    print("=" * 60, flush=True)

    async def heartbeat():
        while True:
            await asyncio.sleep(300)
            print("heartbeat: bot alive", flush=True)

    asyncio.create_task(heartbeat())

    while True:
        try:
            await dp.start_polling(bot)
            break
        except Exception as e:
            msg = str(e)
            if "409" in msg or "Conflict" in msg or "terminated by other getUpdates" in msg:
                # অন্য কোনো পুরনো কপি এখনো চলছে — Telegram নতুনটাকে বন্ধ করে দিচ্ছে
                print("WARN ANOTHER INSTANCE RUNNING -> Telegram 409 Conflict. "
                      "Panel-এ আগের সব bot app stop/delete করে তারপর আবার Start করুন.", flush=True)
                await asyncio.sleep(30)
            else:
                print("WARN polling crashed: " + msg, flush=True)
                await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
