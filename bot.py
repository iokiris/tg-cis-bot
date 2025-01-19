import asyncio
from aiogram import Dispatcher, types, F, Router
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import config
import tables
from config import bot
from utils import translated
import time
import db
import handlers
import messages
import utils

GLOBAL_THROTTLE: dict[int, float] = {}

dp = Dispatcher()
router = Router()
dp.include_router(router)

tables_throttle: dict[int, float] = {}  #id, time

with open("media/title.jpg", "rb") as file:
    title_photo = BufferedInputFile(file.read(), filename="photo.jpg")

captcha_answers: dict[int, list[time.time()]] = {}  # id, last-time
unsaved_referrals: dict[int, int] = {}  # referral, referred_by


class UserStates(StatesGroup):
    waiting_for_captcha = State()
    waiting_for_wallet = State()


@dp.message(Command(commands=['start']))
@handlers.throttle(5)
@handlers.is_private
async def start(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state:
        await message.answer(translated("already_processing", message.from_user.id))
        return

    command_with_args = message.text
    args = command_with_args.split(maxsplit=1)[1] if len(command_with_args.split()) > 1 else ""
    referrer_id = None
    if args.startswith("ref_"):
        referrer_id = int(args.split("_")[1])
    user_id = message.from_user.id
    stage = db.get_user_stage(user_id)
    if not stage:
        if referrer_id != message.from_user.id:
            unsaved_referrals[user_id] = referrer_id
        await message.answer("Добро пожаловать! Выберите язык\n\nWelcome! Select your language.",
                             reply_markup=InlineKeyboardMarkup(
                                 inline_keyboard=[
                                     [InlineKeyboardButton(text="English", callback_data="lang_en")],
                                     [InlineKeyboardButton(text="Russian", callback_data="lang_ru")],
                                 ]))
        await message.delete()


@dp.callback_query(F.data.startswith("lang_"))
@handlers.throttle(1)
@handlers.is_private
async def lang(query: types.CallbackQuery):
    language = query.data.split("_")[1]
    utils.users_language[query.from_user.id] = language
    await query.message.edit_text(translated("ask_to_captcha", query.from_user.id),
                                  reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(
                                      callback_data="run_captcha",
                                      text=translated("run_captcha", query.from_user.id))]]))


@dp.callback_query(F.data == "run_captcha")
@handlers.throttle(1)
@handlers.is_private
async def go_captcha(query: types.CallbackQuery, state: FSMContext):
    if await state.get_state() == UserStates.waiting_for_captcha.state:
        await bot.answer_callback_query(callback_query_id=query.id,
                                        text=translated("captcha_already_active", query.from_user.id), show_alert=True)
        return

    captcha_created = await utils.send_captcha(query, True)
    if not captcha_created:
        await bot.answer_callback_query(callback_query_id=query.id,
                                        text=translated("captcha_throttle", query.from_user.id),
                                        show_alert=True)
        return
    await state.set_state(UserStates.waiting_for_captcha.state)
    await utils.send_captcha(query, True)


@dp.callback_query(F.data.split("_")[0] == "cpt")
@handlers.throttle(1)
@handlers.is_private
async def captcha_handler(query: types.CallbackQuery, state: FSMContext):
    uid = query.from_user.id
    if utils.compare_captcha(uid, query.data.split("_")[-1]):
        # await state.clear()
        await query.message.answer(translated("subscribe_to_channel", uid), reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text=translated("channel", uid), url=config.CHANNEL_LINK),
                    InlineKeyboardButton(text=translated("chat", uid), url=config.CHAT_LINK)
                ],
                [InlineKeyboardButton(text=translated("check_subscriptions", uid),
                                      callback_data="check_subscriptions")]]))
        await query.message.delete()
    else:
        await state.clear()
        await query.message.edit_caption(caption=translated("captcha_solved_incorrectly", uid), caption_entities=None,
                                         reply_markup=InlineKeyboardMarkup(
                                             inline_keyboard=[
                                                 [InlineKeyboardButton(
                                                     text=translated("captcha_retry", uid),
                                                     callback_data="run_captcha")]
                                             ]))


@dp.callback_query(F.data == "check_subscriptions")
@handlers.throttle(1)
@handlers.is_private
async def check_subscriptions(query: types.CallbackQuery, state: FSMContext):
    if await utils.check_subscriptions(query.from_user.id):
        await query.message.delete()
        await send_wallet_form(query, state)
    else:
        await query.answer(translated("subscriptions_error", query.from_user.id), show_alert=True)


async def send_wallet_form(query: types.CallbackQuery, state: FSMContext):
    await query.message.answer(translated("wallet_require", query.from_user.id))
    await state.set_state(UserStates.waiting_for_wallet.state)


@dp.message(UserStates.waiting_for_wallet)
@handlers.is_private
async def wallet_form(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    wallet_address = message.text.strip()
    await state.clear()
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=translated("confirm_wallet", uid), callback_data=f"w-save_{wallet_address}")],
            [InlineKeyboardButton(text=translated("edit_wallet", uid), callback_data=f"w-edit_{wallet_address}")]
        ]
    )
    prefix = ""
    if not utils.validate_address(wallet_address):
                                                                                prefix = f"*{translated('wallet_invalid', uid)}*\n\n"
    await message.answer(f"{prefix}{translated('wallet_confirm', uid)}: {wallet_address}\n", reply_markup=keyboard,
                          parse_mode='Markdown')


@dp.callback_query(F.data.startswith("w-save_"))
@handlers.throttle(1)
@handlers.is_private
async def save_user(query: types.CallbackQuery):
    wallet = query.data.split("_")[-1]
    uid = query.from_user.id
    referred_by = None
    if query.from_user.id in unsaved_referrals:
        referred_by = unsaved_referrals[uid]
    db.register_user(uid, query.from_user.first_name, referred_by, wallet, utils.users_language[uid])
    if referred_by:
        await bot.send_message(chat_id=referred_by, text=f"*{translated('new_referral', query.from_user.id)}*",
                               parse_mode='Markdown')
    await query.message.edit_text(translated("registration_success", query.from_user.id), )


@dp.callback_query(F.data.startswith("w-edit"))
@handlers.throttle(1)
@handlers.is_private
async def edit_wallet(query: types.CallbackQuery, state: FSMContext):
    await send_wallet_form(query, state)


@dp.callback_query(F.data == "get_ref")
@handlers.throttle(1)
@handlers.is_private
async def get_ref(query: types.CallbackQuery):
    buttons = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=translated("more_info", query.from_user.id),
            callback_data="info")],
        [InlineKeyboardButton(text=translated(
            "rate", query.from_user.id), callback_data="rate")]
    ])
    try:
        await query.message.edit_caption(
            caption=messages.get_ref_message(query.from_user.id), parse_mode='HTML',
            reply_markup=buttons)
    except:
        # await query.message.answer_photo(
        #     photo=title_photo,
        #     caption=messages.get_ref_message(query.from_user.id), parse_mode='HTML',
        #     reply_markup=buttons)
        # await query.message.delete()
        ...


@dp.callback_query(F.data == "info")
@handlers.throttle(1)
@handlers.is_private
async def info(query: types.CallbackQuery):
    uid = query.from_user.id
    buttons = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=translated("increase_chances", uid), callback_data="get_ref")],
        [InlineKeyboardButton(text=translated("rate", uid), callback_data="rate")]
    ])
    try:
        await query.message.edit_caption(
            caption=messages.get_subscribed_text(query.from_user.id), parse_mode='Markdown',
            reply_markup=buttons,
        )
    except Exception as e:
        # print(e)
        # await query.message.answer_photo(
        #     photo=title_photo,
        #     caption=messages.get_subscribed_text(query.from_user.id), parse_mode='Markdown',
        #     reply_markup=buttons)
        # await query.message.delete()
        ...


@dp.callback_query(F.data == "rate")
@handlers.throttle(1)
@handlers.is_private
async def rate(query: types.CallbackQuery):
    user_id = query.from_user.id
    user_position, surrounding_users = db.get_user_position_and_surroundings(user_id)


    max_position_length = 3 * len(str(surrounding_users[-1]['position']))
    max_name_length = 8  
    max_ref_counter_length = 5
    message = f"<b>{translated('rating', user_id)}</b>\n\n"

    if user_position is not None:
        for user in surrounding_users:
            position = str(user['position']).rjust(
                max_position_length - len(str(user['position'])))
            wrapped_name = user['name'][:max_name_length - 3] + "..." if len(user['name']) >= max_name_length else user[
                'name']
            name = wrapped_name.ljust(max_name_length)
            ref_count = str(user['ref_counter']).rjust(max_ref_counter_length)
            if user['id'] == user_id:
                message += f"<b>{position}. {name} - {ref_count} {translated('referrals', query.from_user.id)}</b>\n"
            else:
                message += f"{position}. {name} - {ref_count} {translated('referrals', query.from_user.id)}\n"
    else:
        message += f"\n{translated('rate_position_error', user_id)}\n"

    buttons = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=translated("more_info", user_id), callback_data="info")],
        [InlineKeyboardButton(text=translated("increase_chances", user_id), callback_data="get_ref")]
    ])


    try:
        await query.message.edit_caption(caption=message, reply_markup=buttons, parse_mode='HTML')
    except Exception as e:
        # print("cannot edit to rate: ", e)
        # await query.message.answer(message, reply_markup=buttons, parse_mode='HTML')
        # await query.message.delete()
        ...


@dp.message(Command(commands=['get_tables']))
@handlers.throttle(1)
@handlers.is_private
async def get_tables(message: types.Message):
    t = time.time() - tables_throttle.get(message.from_user.id, 0)
    if t < 30:
        await message.answer(f"Это будет доступно вам через {int(30 - t)}с.")
        return
    tables.save_top_100('top_100.csv', db.get_top_100())
    tables.save_all_users('all_users.csv', db.get_all_users())

    try:
        tables_throttle[message.from_user.id] = time.time()
        await message.answer("Отправляю таблицы...")
        await message.answer_document(FSInputFile("top_100.csv"), caption="ТОП-100 Пользователей")
        await message.answer_document(FSInputFile("all_users.csv"), caption="Общая таблица")
    except:
        await message.answer("Таблица пустая.")

@dp.message()
@handlers.is_private
@handlers.throttle(10)
@handlers.user_registered
@handlers.is_user_subscribe
async def title_with_check_subscriptions(message: types.Message):
    buttons = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=translated("increase_chances", message.from_user.id), callback_data="get_ref")],
        [InlineKeyboardButton(text=translated("rate", message.from_user.id), callback_data="rate")]
    ])

    await message.answer_photo(
        photo=title_photo,
        caption=messages.get_subscribed_text(message.from_user.id), parse_mode='Markdown',
        reply_markup=buttons)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(dp.start_polling(bot, skip_updates=True))
