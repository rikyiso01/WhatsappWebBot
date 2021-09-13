from aiogram import Bot, Dispatcher  # type: ignore
from aiogram.types import Message as TelegramMessage  # type: ignore
from aiogram.types.message import ContentType  # type: ignore
from argparse import ArgumentParser
from os.path import exists
from yaml import load, safe_load, dump, Loader
from dataclasses import dataclass, field, asdict
from asyncio import wait, FIRST_EXCEPTION, CancelledError, run, create_task
from ._user import User, SerializedUser, TelegramUserId
from ._chat import TelegramChat
from typing import BinaryIO, Optional
from collections import Awaitable
from ._consts import CONFIG_FILE, DATA_FILE
from whatsapp import Message as WhatsappMessage
from traceback import format_exc, print_exc
from contextlib import AbstractAsyncContextManager
from ._telegram_handlers import TELEGRAM_HANDLERS
from ._whatsapp_handlers import WHATSAPP_HANDLERS
from ._commands import COMMANDS, get_command, get_command_args
import whatsappwebbot._global as GLOBAL

# Exception for a user not found
class NoSuchUserError(Exception):
    ...


# Class to manager the config.yml file
@dataclass
class Config:
    token: str


# Class to manage the data.yml file
@dataclass
class Data:
    users: list[SerializedUser] = field(default_factory=list)


# Entry point
def main():
    parser = ArgumentParser()
    parser.add_argument(
        "--debug",
        default=False,
        action="store_true",
        help="Starts the program in debug mode",
    )
    parser.add_argument(
        "--show",
        default=False,
        action="store_true",
        help="Show every chrome window the bot create",
    )
    parser.add_argument(
        "--commands",
        action="store_true",
        default=False,
        help="Outputs the command list for the bot father, then exits",
    )
    args = parser.parse_args()

    # Print the commands list, then exits
    if args.commands:
        print_commands()
        return

    # Global variables to simplify usage
    GLOBAL.DEBUG = args.debug
    GLOBAL.SHOW = args.show

    with CONFIG_FILE.open("rt") as file:
        config = Config(**safe_load(file.read()))
    try:
        run(WhatsappWebBot(config).run())
    except KeyboardInterrupt:
        pass


# Print the command list to give to the BotFather
def print_commands() -> None:
    print("start - Starts the bot")
    for command in COMMANDS:
        print(f"{command} - {get_command(command).__doc__}")


# Utility function to simplify the management of concurrent functions
async def safe_wait(aws: list[Awaitable]) -> None:
    done, pendings = await wait(
        [create_task(elem) for elem in aws], return_when=FIRST_EXCEPTION
    )
    for pending in pendings:
        pending.cancel()
    # If a future has raised an exception, it is raised
    for future in done:
        exc = future.exception()
        if exc is not None and type(exc) != CancelledError:
            raise exc


# User can run commands with arguments by first sending the command and then by sending
# the arguments as distinct messages

# Set the user into command mode
async def set_current_command(
    user: User, current_chat: TelegramChat, value: str
) -> None:
    user.current_command = value
    user.current_args = []
    await process_command(user, current_chat)


# Add an argument to a user into command mode
async def add_command_arg(user: User, current_chat: TelegramChat, arg: str) -> None:
    assert user.command_mode
    user.current_args.append(arg)
    await process_command(user, current_chat)


# Check if the required number of arguments has been reached, if so run the command
async def process_command(user: User, chat: TelegramChat) -> None:
    assert user.current_command is not None
    if len(user.current_args) == get_command_args(user.current_command):
        get_command(user.current_command)(user, chat, *user.current_args)
        user.current_command = None
        await chat.send_text("Command successfully executed")


# Forward exceptions to the users for easier debug
class ExceptionHandlerContextManager(AbstractAsyncContextManager):
    def __init__(self, chat: TelegramChat):
        self.chat = chat

    async def __aenter__(self) -> None:
        pass

    async def __aexit__(self, exc_type, exc_value, traceback):
        if (
            exc_type is not None
            and exc_type != KeyboardInterrupt
            and exc_type != CancelledError
        ):
            await send_stack_trace(self.chat)


# Utility function to send the latest exception stack trace in a telegram chat
async def send_stack_trace(chat: TelegramChat) -> None:
    await chat.send_text(format_exc())


class WhatsappWebBot:
    def __init__(self, config: Config):
        self.bot = Bot(config.token)
        self.dispatcher = Dispatcher(bot=self.bot)
        self.dispatcher.register_message_handler(self.start_handler, commands=["start"])
        self.dispatcher.register_message_handler(
            self.command_handler, commands=COMMANDS.keys()
        )
        self.dispatcher.register_message_handler(
            self.message_handler, content_types=list(TELEGRAM_HANDLERS.keys())
        )
        # Users that are currently logging in
        self.login_users: list[User] = []
        # Users logged in
        self.users: list[User] = []
        # Avoid saving before loading the users
        self.shoud_save = False
        if not exists(DATA_FILE):
            self.data = Data()
        else:
            with DATA_FILE.open("rt") as file:
                self.data = Data(**load(file.read(), Loader=Loader))

    async def run(self):
        try:
            await safe_wait([self.dispatcher.start_polling(), self.pool_whatsapp()])
        except KeyboardInterrupt:
            pass
        finally:
            # Saves the users and then closes everything
            if self.shoud_save:
                with DATA_FILE.open("wt") as file:
                    dump(asdict(Data([user.save() for user in self.users])), file)
            if len(self.login_users) > 0:
                await safe_wait([user.close() for user in self.login_users])
            if len(self.users) > 0:
                await safe_wait([user.close() for user in self.users])

    async def pool_whatsapp(self):
        # Loads and starts the users
        self.users = [
            User.load(
                self.bot,
                self.qr_callback,
                self.login_callback,
                self.message_callback,
                self.exception_callback,
                user,
            )
            for user in self.data.users
        ]
        self.shoud_save = True
        if len(self.users) > 0:
            await safe_wait([user.start() for user in self.users])

    async def qr_callback(self, user: User, data: BinaryIO) -> None:
        # Forwards the qr code on telegram
        await user.telegram_user_chat.send_image(data)

    async def login_callback(self, user: User) -> None:
        # Updates the users tables and send a notification to the logged in user
        if user in self.login_users:
            self.login_users.remove(user)
        if user not in self.users:
            self.users.append(user)
        await user.telegram_user_chat.send_text("Logged in")

    async def message_callback(self, user: User, message: WhatsappMessage) -> None:
        # The message is forwarded to the associated chat if it exists
        # else the message is sent to the user chat with a different heading
        current_chat: TelegramChat = user.telegram_user_chat
        for chat in user.chats:
            if chat.whatsapp_chat == message.chat:
                current_chat = chat.telegram_chat
        if type(message) not in WHATSAPP_HANDLERS:
            raise NotImplementedError(type(message))
        prefix = ""
        if current_chat == user.telegram_user_chat:
            prefix = f"{message.chat}: "
        if message.is_in_group:
            prefix = f"{prefix}{message.group_sender}: "
        await WHATSAPP_HANDLERS[type(message)](message, current_chat, prefix)

    async def exception_callback(self, user: User) -> None:
        # Send the error to the user
        print_exc()
        await send_stack_trace(user.telegram_user_chat)

    async def start_handler(self, message: TelegramMessage) -> None:
        async with ExceptionHandlerContextManager(
            TelegramChat(self.bot, message.chat.id)
        ):
            # A new user started the bot
            user = User(
                self.bot,
                message.from_user.id,
                message.chat.id,
                self.qr_callback,
                self.login_callback,
                self.message_callback,
                self.exception_callback,
            )
            self.login_users.append(user)
            await user.start()

    async def command_handler(self, message: TelegramMessage) -> None:
        # Set the user into command mode
        chat = TelegramChat(self.bot, message.chat.id)
        async with ExceptionHandlerContextManager(chat):
            await set_current_command(
                self.get_user(message.from_user.id),
                chat,
                message.text[1:].split("@")[0],
            )

    async def message_handler(self, message: TelegramMessage) -> None:
        telegram_chat = TelegramChat(self.bot, message.chat.id)
        async with ExceptionHandlerContextManager(telegram_chat):
            # Ignore command messages
            if message.content_type == ContentType.TEXT and message.text.startswith(
                "/"
            ):
                return

            user = self.get_user(message.from_user.id)

            if user.command_mode:
                # Add the argument value to the current command arguments
                if message.content_type != ContentType.TEXT:
                    raise ValueError(message.content_type)
                await add_command_arg(user, telegram_chat, message.text)
                return

            if message.content_type not in TELEGRAM_HANDLERS:
                raise NotImplementedError(message.content_type)
            chat = user.get_chat(message.chat.id)
            await TELEGRAM_HANDLERS[message.content_type](
                message, user, chat.whatsapp_chat
            )

    def get_user(self, id: TelegramUserId) -> User:
        # Find a logged in user with the given id
        current_user: Optional[User] = None
        for user in self.users:
            if user.telegram_id == id:
                current_user = user
        if current_user is None:
            raise NoSuchUserError(str(id))
        return current_user
