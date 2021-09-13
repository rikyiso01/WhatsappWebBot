from aiogram import Bot  # type: ignore
from whatsapp import Whatsapp, Message, Chat as WhatsappChat
from typing import Callable, BinaryIO, Optional
from pathlib import Path
from collections import Awaitable
from functools import partial
from ._chat import TelegramChatId, TelegramChat, SerializedChat, Chat
from ._consts import DATA_DIR
import whatsappwebbot._global as GLOBAL

# Typedef for better annotations
TelegramUserId = int

# Used for saving the user to the yaml file
SerializedUser = tuple[
    TelegramUserId, TelegramChatId, Optional[WhatsappChat], list[SerializedChat]
]

# Error for a non existent association
class NoSuchChatError(Exception):
    ...


# Each user is an utilizer of the bot, it has an associated Whatsapp instance to control
# its web session
class User:
    # Loads the user from a tuple
    @classmethod
    def load(
        cls,
        bot: Bot,
        qr_callback: Callable[["User", BinaryIO], Awaitable[None]],
        login_callback: Callable[["User"], Awaitable[None]],
        message_callback: Callable[["User", Message], Awaitable[None]],
        exception_callback: Callable[["User"], Awaitable[None]],
        data: SerializedUser,
    ) -> "User":
        return User(
            bot,
            data[0],
            data[1],
            qr_callback,
            login_callback,
            message_callback,
            exception_callback,
            data[2],
            [Chat.load(bot, chat) for chat in data[3]],
        )

    def __init__(
        self,
        bot: Bot,
        telegram_id: TelegramUserId,
        telegram_user_chat_id: TelegramChatId,
        qr_callback: Callable[["User", BinaryIO], Awaitable[None]],
        login_callback: Callable[["User"], Awaitable[None]],
        message_callback: Callable[["User", Message], Awaitable[None]],
        exception_callback: Callable[["User"], Awaitable[None]],
        whatsapp_default_chat: Optional[WhatsappChat] = None,
        chats: list[Chat] = [],
    ):
        self.telegram_id = telegram_id
        self.telegram_user_chat = TelegramChat(bot, telegram_user_chat_id)
        self._whatsapp = Whatsapp(
            self.profile_dir,
            whatsapp_default_chat,
            GLOBAL.SHOW,
            GLOBAL.DEBUG,
            partial(qr_callback, self),
            partial(login_callback, self),
            partial(message_callback, self),
            partial(exception_callback, self),
        )
        self.chats = chats
        self.current_command: Optional[str] = None
        self.current_args: list[str] = []

    @property
    def profile_dir(self) -> Path:
        return DATA_DIR.joinpath(str(self.telegram_id))

    @property
    def whatsapp_default_chat(self) -> Optional[WhatsappChat]:
        return self._whatsapp.default_chat

    @whatsapp_default_chat.setter
    def whatsapp_default_chat(self, value: Optional[WhatsappChat]) -> None:
        self._whatsapp.default_chat = value

    async def start(self):
        await self._whatsapp.start()

    async def close(self):
        await self._whatsapp.close()

    # Converts the user into a tuple
    def save(self) -> SerializedUser:
        return (
            self.telegram_id,
            self.telegram_user_chat.id,
            self.whatsapp_default_chat,
            [chat.save() for chat in self.chats],
        )

    # Add a whatsapp message to the message queue
    def send_whatsapp_message(self, message: Message) -> None:
        self._whatsapp.send_message(message)

    # Finds a chat association from a telegram chat id
    def get_chat(self, id: TelegramChatId) -> Chat:
        current_chat: Optional[Chat] = None
        for chat in self.chats:
            if chat.telegram_chat.id == id:
                current_chat = chat
        if current_chat is None:
            raise NoSuchChatError(str(id))
        return current_chat

    @property
    def command_mode(self) -> bool:
        return self.current_command is not None
