from telegram.ext import Updater,Dispatcher,CommandHandler,MessageHandler,Filters
from .commands import COMMANDS
from typing import List,NoReturn,Any,Dict,TextIO,Optional
from .user import User,USERNAME,DEFAULT_CHAT_ID,ASSOCIATIONS,DEFAULT_CHAT
from logging import Logger,getLogger,StreamHandler,DEBUG,INFO
from time import sleep
from telegram.ext import CallbackContext
from telegram import Update
from .error import NoSuchUserError
from os.path import exists,join
from os import mkdir
from json import dump,load
from whatsapp import WhatsappOptions
from io import StringIO

USERS='users'

class WhatsappWebBot:
    def __init__(self,options:WhatsappOptions,token:str,data_dir:str,admin:int,stdout:Optional[TextIO],
                 silent_start:bool):
        self.updater: Updater = Updater(token, use_context=True)
        self.users:List[User]=[]
        self.silent_start:bool=silent_start
        self.logs:StringIO=StringIO()
        self.logger:Logger=getLogger('WhatsappWebBot')
        level:int=DEBUG if options.debug else INFO
        self.logger.setLevel(level)
        handler:StreamHandler=StreamHandler(self.logs)
        handler.setLevel(DEBUG)
        self.logger.addHandler(StreamHandler(self.logs))
        if stdout is not None:
            handler=StreamHandler(stdout)
            handler.setLevel(level)
            self.logger.addHandler(StreamHandler(stdout))
        self.data_dir:str=data_dir
        self.admin:int=admin
        self.options:WhatsappOptions=options
        dispatcher: Dispatcher = self.updater.dispatcher
        dispatcher.add_handler(CommandHandler('start',self.start_command))
        for command in COMMANDS.keys():
            dispatcher.add_handler(self.create_command_handler(command))
        dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, self.on_message))
        self.restore_all()

    def create_command_handler(self,command:str):
        def method(update:Update,_context:CallbackContext):
            try:
                user:User=self.find_user(update.message.from_user.id)
                self.log(command,username=update.message.from_user.username,user=user)
                COMMANDS[command](user)
            except NoSuchUserError as exception:
                self.log_error(exception,update.message.chat_id)
        return CommandHandler(command,method)

    def start(self):
        self.updater.start_polling()
        try:
            self.logger.info('Started')
            self.logger.debug('Debug Mode On')
            if not self.silent_start:
                self.notify_all('The bot is online')
            while True:
                for user in self.users:
                    user.receive_messages()
                sleep(3)
        except KeyboardInterrupt:
            pass
        finally:
            self.logger.info('Shutting down')
            if not self.silent_start:
                self.notify_all('The bot is shutting down')
            self.updater.stop()
            self.save_all()
            for user in self.users:
                user.close()

    def on_message(self,update: Update, _context: CallbackContext) -> NoReturn:
        try:
            user: User = self.find_user(update.message.from_user.id)
            if user.current_mode is not None:
                user.current_mode(user,update.message)
                user.current_mode = None
            else:
                user.send_message(update.message.chat_id, update.message.text)
        except NoSuchUserError as e:
            self.log_error(e,update.message.chat_id)

    def start_command(self,update: Update, _context: CallbackContext) -> NoReturn:
        username: int = update.message.from_user.id
        chat_id: int = update.message.chat_id
        self.log('start', username=username, chat_id=chat_id)
        user: User = User(self, username, chat_id)
        user.reply(f'Your username is {username} with chat id {chat_id}', update.message)

        def logged_in():
            user.log('Log in successful')

        user.whatsapp.logged_in_callback = logged_in
        self.users.append(user)

    def save_all(self):
        if not exists(self.data_dir):
            mkdir(self.data_dir)
        with open(self.data_file(), 'w') as f:
            dump({USERS: [user.as_dict() for user in self.users]}, f)

    def restore_all(self):
        if not exists(self.data_file()):
            return
        with open(self.data_file(), 'r') as f:
            data: Dict[str, Any] = load(f)
            for user in data[USERS]:
                self.users.append(User(self, user[USERNAME], user[DEFAULT_CHAT_ID], user[ASSOCIATIONS],
                                       user[DEFAULT_CHAT]))

    def notify_all(self,message: str):
        for user in self.users:
            user.log(message)

    def find_user(self,username: int) -> User:
        for user in self.users:
            if user.username == username:
                return user
        raise NoSuchUserError(username)

    def data_file(self)->str:
        return join(self.data_dir,'data.json')

    def log(self,command: str, **kwargs):
        message: str = f'/{command}'
        for key in kwargs.keys():
            message += f' {key}={kwargs[key]}'
        self.logger.info(message)

    def log_error(self,exception:Exception,chat_id:int):
        self.logger.error(str(exception), exc_info=True)
        self.updater.bot.send_message(chat_id,str(exception))
