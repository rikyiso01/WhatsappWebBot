from whatsapp import Message as WhatsappMessage, TextMessage, AudioMessage, ImageMessage
from typing import Callable, Any, TypeVar
from collections import Awaitable
from ._chat import TelegramChat
from io import BytesIO
from inspect import getfullargspec
from aiogram.types import InputFile  # type: ignore

# Contains handlers for different types of whatsapp message
# The first argument is the message
# The second argument is the telegram chat in which the message should be send
# The third argument is the message prefix, in case of groups or chat not associated,
# the message should have an heading indicating who has sent the message

# The dict uses the type of the handled message to find the corresponding callback
WHATSAPP_HANDLERS: dict[Any, Callable[[Any, TelegramChat, str], Awaitable[None]]] = {}

T = TypeVar("T", bound=WhatsappMessage)


# Decorator to simplify the insertion of the callback into the dictionary
def handler(
    function: Callable[[T, TelegramChat, str], Awaitable[None]]
) -> Callable[[T, TelegramChat, str], Awaitable[None]]:
    specs = getfullargspec(function)
    # Deducts the supported message type by using the annotation of the first argument
    type = specs.annotations[specs.args[0]]
    WHATSAPP_HANDLERS[type] = function
    return function


@handler
async def text_callback(message: TextMessage, chat: TelegramChat, prefix: str) -> None:
    await chat.send_text(prefix + message.text)


@handler
async def image_callback(
    message: ImageMessage, chat: TelegramChat, prefix: str
) -> None:
    await chat.send_image(BytesIO(message.image), prefix + message.caption)


@handler
async def audio_callback(
    message: AudioMessage, chat: TelegramChat, prefix: str
) -> None:
    await chat.bot.send_audio(
        chat.id,
        InputFile(BytesIO(message.audio)),
        caption=prefix if prefix != "" else None,
    )
