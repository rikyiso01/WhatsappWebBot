from aiogram import Bot  # type: ignore
from aiogram.types import InputFile  # type: ignore
from typing import BinaryIO, Optional
from whatsapp import Chat as WhatsappChat

TelegramChatId = int

SerializedChat = tuple[TelegramChatId, WhatsappChat]

# Utility to manage a telegram chat
class TelegramChat:
    def __init__(self, bot: Bot, id: TelegramChatId):
        self.bot = bot
        self.id = id

    async def send_image(self, photo: BinaryIO, caption: str = "") -> None:
        await self.bot.send_photo(
            self.id, InputFile(photo), caption=None if caption == "" else caption
        )

    async def send_text(self, text: str) -> None:
        await self.bot.send_message(self.id, text)


# Represents an association between a telegram chat and a whatsapp chat
class Chat:
    @classmethod
    def load(cls, bot: Bot, data: SerializedChat) -> "Chat":
        return Chat(TelegramChat(bot, data[0]), data[1])

    def __init__(self, telegram_chat: TelegramChat, whatsapp_chat: WhatsappChat):
        self.telegram_chat = telegram_chat
        self.whatsapp_chat = whatsapp_chat

    def save(self) -> SerializedChat:
        return (self.telegram_chat.id, self.whatsapp_chat)
