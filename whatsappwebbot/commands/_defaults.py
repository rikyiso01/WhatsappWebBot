from typing import Callable,NoReturn
from whatsappwebbot.user import User
from telegram.message import Message

Command=Callable[[User],NoReturn]

def create_set_mode(mode:Callable[[User,Message],NoReturn])->Command:
    def method(user:User):
        user.current_mode = mode
    return method
