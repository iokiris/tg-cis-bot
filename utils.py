import json
import random
import re
import string
import time
import urllib.parse

from aiogram.types import BufferedInputFile
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

import config
import db
import image_captcha
from config import bot

captcha_answers: dict[int, str] = {}
captcha_throttles: dict[int, float] = {}
users_language: dict[int, str] = {} # 1234566, "ru"

with open("translations.json") as f:
    translations = json.load(f)


def gen_captcha_key() -> str:
    captcha_text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    return captcha_text


def captcha_keyboard(captcha_key) -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(text=captcha_key, callback_data=f"cpt_{captcha_key}")]]
    for i in range(3):
        c = gen_captcha_key()
        buttons.append([InlineKeyboardButton(text=c, callback_data=f"cpt_{c}")])
    random.shuffle(buttons)
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def compare_captcha(uid: int, c: str) -> bool:
    if uid not in captcha_answers:
        return False
    if c == captcha_answers[uid]:
        return True
    return False


def generate_referral_link(user_id: int) -> str:
    base_url = f"https://t.me/{config.BOT_ID}?start="
    referral_code = f"ref_{user_id}"
    return base_url + urllib.parse.quote(referral_code)


def validate_address(address: str) -> bool:
    solana_address_pattern = re.compile(r"^([1-9A-HJ-NP-Za-km-z]{44})$")
    return bool(solana_address_pattern.match(address))


def translated(key: str, uid: int):
    if uid not in users_language:
        lang = db.get_user_language(uid)
        users_language[uid] = lang
    else:
        lang = users_language[uid]
    return translations[lang][key]


async def send_captcha(query: CallbackQuery, should_delete: bool = False) -> bool:
    if query.from_user.id in captcha_throttles:
        if time.time() - captcha_throttles[query.from_user.id] < 30:
            return False
    captcha_stream, answer = image_captcha.generate_captcha_image()
    captcha_answers[query.from_user.id] = answer

    await query.message.answer_photo(photo=BufferedInputFile(file=captcha_stream.getvalue(), filename="captcha.png"),
                                     caption=translated("captcha_buttons_text", query.from_user.id),
                                     reply_markup=captcha_keyboard(answer))
    captcha_throttles[query.from_user.id] = time.time()
    if should_delete:
        await query.message.delete()
    return True


async def check_subscriptions(uid: int):
    member_channel = await bot.get_chat_member(chat_id=config.CHANNEL_ID, user_id=uid)
    member_chat = await bot.get_chat_member(chat_id=config.CHAT_ID, user_id=uid)
    if member_channel.status != 'left' and member_chat.status != 'left':
        return True
    return False