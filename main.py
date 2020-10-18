from whatsapp import Whatsapp,Message
from time import sleep
from configparser import ConfigParser
from typing import NoReturn,List,Callable,Dict,Any,Optional
from telegram.ext import Updater, CommandHandler, MessageHandler
from telegram.ext.dispatcher import Dispatcher
from telegram.ext.callbackcontext import CallbackContext
from telegram.update import Update
from os.path import join,exists
from telegram.bot import Bot
from io import BytesIO
from json import dump,load
from telegram.ext.filters import Filters

DATA_DIR:str='data'
DATA_FILE:str=join(DATA_DIR,'data.json')

USERNAME='username'
DEFAULT_CHAT_ID='default_chat_id'
ASSOCIATIONS='associations'
DEFAULT_CHAT='default_chat'

AUTH_FILE='auth.ini'
TELEGRAM_SECTION='telegram'
TELEGRAM_TOKEN='token'

USERS='users'

users:List['User']=[]
current_mode:Optional[Callable[[Update,'User'],NoReturn]]=None

class User:
    def __init__(self,bot:Bot,username:str,default_chat_id:int,associations:Dict[str,int]=None,default_chat:str=None):
        self.bot:Bot=bot
        self.username:str=username
        self.default_chat_id:int=default_chat_id
        self._default_chat:Optional[str]=default_chat
        self.associations:Dict[str,int]={} if associations is None else associations
        self.whatsapp=Whatsapp(join(DATA_DIR, username))
        self.whatsapp.qr_callback = self._create_callback()

    def _set_default_chat(self,default_chat:str)->NoReturn:
        if not self.whatsapp.user_exists(default_chat):
            raise WhatsappUserNotFoundError(default_chat)
        self._default_chat=default_chat

    default_chat:Optional[str]=property(lambda self:self._default_chat,_set_default_chat)

    def _create_callback(self)->Callable[[bytes],NoReturn]:
        def method(image:bytes):
            self.bot.send_photo(self.default_chat_id,BytesIO(image))
        return method

    def add_association(self,who:str,chat:int)->NoReturn:
        if not self.whatsapp.user_exists(who):
            raise WhatsappUserNotFoundError(who)
        self.associations[who]=chat

    def receive_messages(self):
        if not self.whatsapp.logged_in:
            return
        messages:List[Message]=self.whatsapp.get_unread_messages()
        for message in messages:
            text:str=''
            chat_id:int=self.default_chat_id
            if message.sender not in self.associations:
                text=f'{message.sender}: '
            else:
                chat_id=self.associations[message.sender]
            self.bot.send_message(chat_id,text+message.message)
        if len(messages)>0 and self.default_chat is not None:
            self.whatsapp.select_chat(self.default_chat)

    def send_message(self,chat_id:int,message:str):
        who:Optional[str]=None
        for key in self.associations.keys():
            if self.associations[key]==chat_id:
                who=key
        if who is None:
            who=message.split(' ')[0]
            message=message[len(who)+1:]
        self.whatsapp.send_message(who,message)
        if self.default_chat is not None:
            self.whatsapp.select_chat(self.default_chat)

    def as_dict(self)->Dict[str,Any]:
        return {USERNAME:self.username,DEFAULT_CHAT_ID:self.default_chat_id,ASSOCIATIONS:self.associations,DEFAULT_CHAT:self.default_chat}

    def log(self,log:str):
        self.bot.send_message(self.default_chat_id,log)


def main()->NoReturn:
    config=ConfigParser()
    config.read(AUTH_FILE)
    if TELEGRAM_SECTION not in config:
        raise Exception('Missing or malformed auth.ini')
    updater:Updater=Updater(config[TELEGRAM_SECTION][TELEGRAM_TOKEN],use_context=True)
    restore_all(updater.bot)
    dispatcher:Dispatcher=updater.dispatcher
    dispatcher.add_handler(CommandHandler('start',start))
    dispatcher.add_handler(CommandHandler('stop',stop))
    dispatcher.add_handler(CommandHandler('associate',create_set_mode(associate)))
    dispatcher.add_handler(CommandHandler('set_default_chat',create_set_mode(set_default_chat)))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command,on_message))
    updater.start_polling()
    try:
        print('Started')
        notify_all('The bot is online')
        while True:
            for user in users:
                user.receive_messages()
            sleep(3)
    finally:
        print('Shutting down')
        notify_all('The bot is shutting down')
        updater.stop()
        save_all()

def start(update:Update,context:CallbackContext)->NoReturn:
    username:str=update.message.from_user.username
    update.message.reply_text(f'Your username is {username}')
    user:User=User(context.bot,username,update.message.chat_id)

    def logged_in():
        user.log('Log in successful')

    user.whatsapp.logged_in_callback=logged_in
    users.append(user)

def associate(update:Update,user:User):
    try:
        who:str=update.message.text
        user.add_association(who,update.message.chat_id)
        update.message.reply_text('The association was successful, you can now send messages over Whatsapp with this chat')
    except WhatsappUserNotFoundError as e:
        e.log_error(update)

def stop(update:Update,context:CallbackContext):
    try:
        user:User=find_user(update.message.from_user.username)
        user.whatsapp.close()
        users.remove(user)
        update.message.reply_text('Stopped')
    except NoSuchUserError as e:
        e.log_error(update)

def set_default_chat(update:Update,user:User):
    try:
        user.default_chat=update.message.text
        update.message.reply_text('Default chat successfully changed')
    except NoSuchUserError as e:
        e.log_error(update)

def on_message(update:Update,context:CallbackContext)->NoReturn:
    global current_mode
    try:
        user:User=find_user(update.message.from_user.username)
        if current_mode is not None:
            current_mode(update,user)
            current_mode=None
        else:
            user.send_message(update.message.chat_id,update.message.text)
    except NoSuchUserError as e:
        e.log_error(update)

def save_all():
    with open(DATA_FILE,'w') as f:
        dump({USERS:[user.as_dict() for user in users]},f)

def restore_all(bot:Bot):
    if not exists(DATA_FILE):
        return
    with open(DATA_FILE,'r') as f:
        data:Dict[str,Any]=load(f)
        for user in data[USERS]:
            users.append(User(bot,user[USERNAME],user[DEFAULT_CHAT_ID],user[ASSOCIATIONS],user[DEFAULT_CHAT]))

def notify_all(log:str):
    for user in users:
        user.log(log)

def create_set_mode(mode:Callable[[Update,User],NoReturn])->Callable[[Update,CallbackContext],NoReturn]:
    def method(update:Update,context:CallbackContext):
        global current_mode
        current_mode=mode
    return method

def find_user(username:str)->User:
    for user in users:
        if user.username==username:
            return user
    raise NoSuchUserError(username)

class NoSuchUserError(Exception):
    def __init__(self,username:str):
        self.username:str=username
        super(NoSuchUserError, self).__init__(f'User {username} not found')

    def log_error(self,update:Update):
        update.message.reply_text(f'User {self.username} not found, have you logged in with /start?')

class WhatsappUserNotFoundError(Exception):
    def __init__(self,username:str):
        self.username:str=username
        super(WhatsappUserNotFoundError, self).__init__(f'Whatsapp user {username} not found')

    def log_error(self,update:Update):
        update.message.reply_text(f'Whatsapp user {self.username} not found, is it right?')

if __name__ == '__main__':
    main()
