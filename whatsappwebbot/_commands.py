from typing import Callable, Union
from ._user import User
from ._chat import TelegramChat, Chat
from inspect import getfullargspec

# Contains handlers for different commands
# The first argument is the user requesting the command
# The second argument is the chat in which the command is being executed
# The other arguments are the arguments of the command

FunctionType = Union[
    Callable[[User, TelegramChat], None],
    Callable[[User, TelegramChat, str], None],
]

# The dict uses the command name to find the corresponding callback and
# the number of arguments
COMMANDS: dict[str, tuple[int, FunctionType]] = {}

# Gets the number of arguments of a command from its name
def get_command_args(command: str) -> int:
    return COMMANDS[command][0]


# Gets the command callback from its name
def get_command(command: str) -> FunctionType:
    return COMMANDS[command][1]


# Decorator to simply the process of adding the handler to the handlers dict
def command(function: FunctionType) -> FunctionType:
    # Finds out the command name from the function name, and the number of arguments
    # from the function signature
    COMMANDS[function.__name__] = (
        len(getfullargspec(function).args) - 2,
        function,
    )
    return function


@command
def set_default_whatsapp_chat(
    user: User, chat: TelegramChat, whatsapp_default_chat: str
) -> None:
    """Whatsapp chat that will not receive any message to use to simplify the process of gathering messages"""
    user.whatsapp_default_chat = whatsapp_default_chat


@command
def associate(user: User, chat: TelegramChat, whatsapp_chat: str) -> None:
    """Associate the current Telegram chat with the given Whatsapp chat"""
    user.chats.append(Chat(chat, whatsapp_chat))
