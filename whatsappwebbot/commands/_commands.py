from telegram.message import Message
from typing import List,Dict
from whatsappwebbot.user import User
from whatsappwebbot.error import WhatsappUserNotFoundError
from io import BytesIO
from whatsappwebbot.commands._defaults import create_set_mode,Command

def associate(user:User,message:Message):
    try:
        who:str=message.text
        chat_id:int=message.chat_id
        user.add_association(who,chat_id)
        user.reply('The association was successful',message)
    except WhatsappUserNotFoundError as e:
        user.log_error(e)

def associate_with_list(user:User,message:Message):
    try:
        for line in message.text.split('\n'):
            pieces:List[str]=line.split(': ')
            user.add_association(pieces[0],int(pieces[1]))
        user.reply('The association was successful',message)
    except WhatsappUserNotFoundError as e:
        user.log_error(e)

def stop(user:User):
    user.delete_user()
    user.log('Stopped')

def show_logs(user:User):
    if user.username == user.whatsappwebbot.admin:
        user.log(user.whatsappwebbot.logs.getvalue())
    else:
        user.log(f'User {user.username} is not authorized for this command')

def list_associations(user:User):
    message: str = ''
    for association in user.associations.keys():
        message += association + ': ' + str(user.associations[association])
    if len(message) == 0:
        message = 'None'
    user.log(message)

def show_default_chat(user:User):
    user.log(user.default_chat)

def take_screenshot(user:User):
    user.log_photo(BytesIO(user.whatsapp.driver.get_screenshot_as_png()))

def set_default_chat(user:User,message:Message):
    default_chat: str = message.text
    user.default_chat = default_chat
    user.reply('Default chat successfully changed', message)

COMMANDS:Dict[str,Command]={'stop':stop,
                            'logs':show_logs,
                            'screenshot':take_screenshot,
                            'associate':create_set_mode(associate),
                            'associate_with_list':create_set_mode(associate_with_list),
                            'set_default_chat':create_set_mode(set_default_chat),
                            'associations':list_associations,
                            'show_default_chat':show_default_chat}
