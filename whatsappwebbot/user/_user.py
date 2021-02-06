from typing import Dict,Optional,Callable,NoReturn,List,Any
from io import BytesIO
from whatsapp import Whatsapp,Message,MessageType
from os.path import join
from whatsappwebbot.error import WhatsappUserNotFoundError
from telegram.error import Unauthorized
import telegram.message
from shutil import rmtree
from threading import Lock

USERNAME='username'
DEFAULT_CHAT_ID='default_chat_id'
ASSOCIATIONS='associations'
DEFAULT_CHAT='default_chat'

class User:
    def __init__(self,whatsappwebbot,username:int,default_chat_id:int,associations:Dict[str,int]=None,
                 default_chat:str=None):
        self.username:int=username
        self.default_chat_id:int=default_chat_id
        self.current_mode: Optional[Callable[['User',Message], NoReturn]] = None
        self.associations:Dict[str,int]={} if associations is None else associations
        from whatsappwebbot import WhatsappWebBot
        self.whatsappwebbot: WhatsappWebBot = whatsappwebbot
        self.whatsapp = Whatsapp(self.get_user_folder(), default_chat,whatsappwebbot.options)
        self.whatsapp.qr_callback = self._create_callback()
        self._lock:Lock=Lock()

    @property
    def default_chat(self)->str:
        return self.whatsapp.default_chat

    @default_chat.setter
    def default_chat(self,default_chat:str)->NoReturn:
        self.whatsapp.default_chat=default_chat

    def _create_callback(self)->Callable[[bytes],NoReturn]:
        def method(image:bytes):
            self.whatsappwebbot.updater.bot.send_photo(self.default_chat_id,BytesIO(image))
        return method

    def add_association(self,who:str,chat:int)->NoReturn:
        if not self.whatsapp.user_exists(who):
            raise WhatsappUserNotFoundError(who)
        self.associations[who]=chat

    def receive_messages(self):
        if not self.whatsapp.logged_in:
            return
        with self._lock:
            messages: List[Message] = self.whatsapp.get_unread_messages()
        if len(messages) > 0:
            self.whatsappwebbot.logger.debug(f'User {self.username} has received {len(messages)} message/es')
        for message in messages:
            text: str = ''
            chat_id: int = self.default_chat_id
            if message.sender not in self.associations:
                text = f'{message.sender}: '
            else:
                chat_id = self.associations[message.sender]
            if message.who is not None:
                text += f'{message.who}: '
            try:
                if message.message_type == MessageType.TEXT:
                    self.whatsappwebbot.updater.bot.send_message(chat_id, text + message.message)
                elif message.message_type == MessageType.AUDIO:
                    self.whatsappwebbot.updater.bot.send_audio(chat_id, BytesIO(message.message), caption=text)
                elif message.message_type == MessageType.IMAGE:
                    caption, data = message.message
                    self.whatsappwebbot.updater.bot.send_photo(chat_id, BytesIO(data), caption=text + caption)
                else:
                    raise NotImplementedError(f'Message type {message.message_type.name} not supported')
            except Unauthorized:
                self.delete_user()
            print(message)

    def send_message(self,chat_id:int,message:str):
        self._send_message(chat_id,message,MessageType.TEXT)

    def send_photo(self,chat_id:int,photo:bytes,caption:str):
        self._send_message(chat_id,caption,MessageType.IMAGE,photo)

    def _send_message(self,chat_id:int,text:str,message_type:MessageType,data:bytes=None):
        who: Optional[str] = None
        for key in self.associations.keys():
            if self.associations[key] == chat_id:
                who = key
        if who is None:
            who = text.split(' ')[0]
            text = text[len(who) + 1:]
        self.whatsappwebbot.logger.debug(f'User {self.username} sent {message_type.name} to {who}')
        with self._lock:
            if message_type == MessageType.TEXT:
                self.whatsapp.send_message(who, text)
            elif message_type == MessageType.IMAGE:
                self.whatsapp.send_photo(who, data, text)
            else:
                raise NotImplementedError(f'{message_type.name} not implemented yet')

    def as_dict(self)->Dict[str,Any]:
        return {USERNAME:self.username,DEFAULT_CHAT_ID:self.default_chat_id,
                ASSOCIATIONS:self.associations,DEFAULT_CHAT:self.whatsapp.default_chat}

    def __repr__(self)->str:
        data:Dict[str,Any]=self.as_dict()
        del data[DEFAULT_CHAT]
        del data[ASSOCIATIONS]
        return str(data)

    def log(self,message:str):
        try:
            self.whatsappwebbot.updater.bot.send_message(self.default_chat_id,message)
        except Unauthorized:
            self.delete_user()

    def log_error(self,exception:Exception):
        self.whatsappwebbot.log_error(exception,self.default_chat_id)

    def log_photo(self,io:BytesIO):
        self.whatsappwebbot.updater.bot.send_photo(self.default_chat_id,io)

    def reply(self,message:str,reply:telegram.message.Message):
        try:
            reply.reply_text(message)
        except Unauthorized:
            self.delete_user()

    def get_user_folder(self):
        return join(self.whatsappwebbot.data_dir, str(self.username))

    def delete_user(self):
        self.whatsappwebbot.logger.debug(f'Deleting user {self.username}')
        self.whatsapp.close()
        self.whatsappwebbot.users.remove(self)
        rmtree(self.get_user_folder(),ignore_errors=True)
        rmtree(self.get_user_folder(), ignore_errors=True)

    def close(self)->NoReturn:
        self.whatsapp.close()
