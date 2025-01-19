import time
from functools import wraps
from aiogram import types
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from utils import translated
import utils
import db
import config

GLOBAL_THROTTLE: dict[int] = {}


def user_registered(handler):
    @wraps(handler)
    async def wrapper(*args, **kwargs):
        user_id = None

        if isinstance(args[0], CallbackQuery):
            user_id = args[0].from_user.id
        elif isinstance(args[0], Message):
            user_id = args[0].from_user.id

        if user_id is not None and db.get_user_stage(user_id):
            return await handler(*args, **kwargs)
        else:
            keyboard = InlineKeyboardMarkup(
                       inline_keyboard=[
                           [InlineKeyboardButton(text="English", callback_data="lang_en")],
                           [InlineKeyboardButton(text="Russian", callback_data="lang_ru")],
                       ])
            if isinstance(args[0], CallbackQuery):
                await args[0].message.answer("Добро пожаловать! Выберите язык\n\nWelcome! Select your language.", reply_markup=keyboard)
            elif isinstance(args[0], Message):
                await args[0].answer("Добро пожаловать! Выберите язык\n\nWelcome! Select your language.", reply_markup=keyboard)
            return

    return wrapper

def is_private(handler):
    @wraps(handler)
    async def wrapper(entity: types.Message | types.CallbackQuery, *args, **kwargs):
        message = None
        if isinstance(entity, types.CallbackQuery):
            message = entity.message
        elif isinstance(entity, types.Message):
            message = entity
        if message.chat.type == 'private':
            return await handler(entity, *args, **kwargs)
        else:
            # await message.answer("Bot only responds to private messages.")
            pass
    return wrapper

def is_user_subscribe(handler):
    @wraps(handler)
    async def wrapper(*args, **kwargs):
        user_id = None
        if isinstance(args[0], CallbackQuery):
            user_id = args[0].from_user.id
        elif isinstance(args[0], Message):
            user_id = args[0].from_user.id

        if await utils.check_subscriptions(user_id):
            return await handler(*args, **kwargs)
        else:
            message = None
            if isinstance(args[0], CallbackQuery):
                message = args[0].message
            if isinstance(args[0], Message):
                message = args[0]
            await message.answer(utils.translated("subscribe_to_channel", user_id), parse_mode='Markdown',
                                 reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(text=translated("channel", user_id), url=config.CHANNEL_LINK),
                        InlineKeyboardButton(text=translated("chat", user_id), url=config.CHAT_LINK)
                    ],
                    [InlineKeyboardButton(text=translated("check_subscriptions", user_id),
                                          callback_data="check_subscriptions")]]))

    return wrapper


def delete_message_after(handler):
    @wraps(handler)
    async def wrapper(query: CallbackQuery, *args, **kwargs):
        response = await handler(query, *args, **kwargs)
        if isinstance(query, CallbackQuery):
            await query.message.delete()
        elif isinstance(query, Message):
            await query.delete()
        return response

    return wrapper


def throttle(limit: float):
    """
    Декоратор для ограничения частоты запросов.

    :param limit: Ограничение на время между запросами в секундах.
    """
    def decorator(func, show_message=False):
        @wraps(func)
        async def wrapper(message: types.Message, *args, **kwargs):
            user_id = message.from_user.id
            current_time = time.time()
            last_request_time = GLOBAL_THROTTLE.get(user_id, 0)
            if current_time - last_request_time < limit:
                remaining_time = int(limit - (current_time - last_request_time))
                if show_message:
                    await message.answer(f"Слишком много запросов. Подождите {remaining_time} сек.")
                return
            GLOBAL_THROTTLE[user_id] = current_time
            return await func(message, *args, **kwargs)

        return wrapper

    return decorator