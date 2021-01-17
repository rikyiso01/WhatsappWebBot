from telegram.update import Update

class NoSuchUserError(Exception):
    def __init__(self,username:int):
        super(NoSuchUserError, self).__init__(f'User {username} not found, have you logged in with /start')

class WhatsappUserNotFoundError(Exception):
    def __init__(self,username:str):
        super(WhatsappUserNotFoundError, self).__init__(f'Whatsapp user {username} not found, is it right')
