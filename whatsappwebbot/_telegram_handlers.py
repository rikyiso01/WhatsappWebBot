from aiogram.types import Message as TelegramMessage  # type: ignore
from aiogram.types.message import ContentType  # type: ignore
from ._user import User
from whatsapp import Chat as WhatsappChat, TextMessage, ImageMessage, AudioMessage
from typing import Callable
from collections import Awaitable
from tempfile import NamedTemporaryFile


# Contains handlers for different types of telegram message
# The first argument is the message
# The second argument is the user
# The third argument is the WhatsappChat to send the message to

FunctionType = Callable[[TelegramMessage, User, WhatsappChat], Awaitable[None]]

TELEGRAM_HANDLERS: dict[ContentType, FunctionType] = {}


# Decorator to simply the insertion of a new callback into the handlers list,
# must indicate the content type of the supported message
def handler(content_type: ContentType) -> Callable[[FunctionType], FunctionType]:
    def decorator(function: FunctionType) -> FunctionType:
        TELEGRAM_HANDLERS[content_type] = function
        return function

    return decorator


@handler(ContentType.TEXT)
async def text_handler(
    message: TelegramMessage, user: User, chat: WhatsappChat
) -> None:
    user.send_whatsapp_message(TextMessage(chat, message.text))


@handler(ContentType.PHOTO)
async def image_handler(
    message: TelegramMessage, user: User, chat: WhatsappChat
) -> None:
    with NamedTemporaryFile("rb") as file:
        await message.photo[-1].download(file.name)
        user.send_whatsapp_message(ImageMessage(chat, message.caption, file.read()))


@handler(ContentType.AUDIO)
async def audio_handler(
    message: TelegramMessage, user: User, chat: WhatsappChat
) -> None:
    print(message.audio)
