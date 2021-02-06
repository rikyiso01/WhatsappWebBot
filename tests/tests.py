from unittest import TestCase,main
from whatsapp import Whatsapp,WhatsappOptions
from telethon import TelegramClient
from telethon.events.newmessage import NewMessage
from telethon.tl.custom.message import Message
from typing import Any,Dict,Optional,NoReturn
from time import sleep
from yaml import safe_load
from whatsappwebbot import WhatsappWebBot
import asyncio

MESSAGE='test'
TIMEOUT=30

class TelegramCase(TestCase):
    bot:Optional[WhatsappWebBot]=None
    group:Optional[int]=None
    chat:Optional[int]=None
    contact_name:Optional[str]=None
    group_name:Optional[str]=None
    buffer:Optional[Message]=None
    telegram:Optional[TelegramClient]=None
    whatsapp:Optional[Whatsapp]=None

    def setUpClass(self=None) -> None:
        with open('auth.yml') as f:
            config: Dict[str, Any] = safe_load(f)
        opt = WhatsappOptions()
        opt.show = True
        opt.debug = True
        opt.interactive = True
        TelegramCase.bot = WhatsappWebBot(opt, config['test-token'], 'data', config['admin'], None, True)
        TelegramCase.bot.async_start()
        with open('tests/auth.yml', 'rt') as f:
            config: Dict[str, Any] = safe_load(f.read())
        TelegramCase.group= config['group']
        TelegramCase.chat = config['chat']
        TelegramCase.contact_name= config['contact-name']
        TelegramCase.group_name= config['group-name']
        TelegramCase.buffer= None

        TelegramCase.telegram= TelegramClient('telethon', config['api-id'], config['api-hash'])
        TelegramCase.telegram.add_event_handler(TelegramCase.on_text, NewMessage())
        TelegramCase.telegram.start(phone=config['phone'])
        TelegramCase.whatsapp= Whatsapp('tests/data','default',opt)
        TelegramCase.whatsapp.wait_for_login()

    def on_text(self):
        update:TelegramCase=self
        update:Message
        print('got message',update.message.text)
        while TelegramCase.buffer is not None:
            sleep(1)
        TelegramCase.buffer = update.message

    def get_message(self) -> Message:
        return self.telegram.loop.run_until_complete(self._get_message())

    async def _get_message(self)->Message:
        counter: int = 0
        while self.buffer is None:
            await asyncio.sleep(1)
            if counter == TIMEOUT:
                print('timeout')
                raise TimeoutError('Message receive timeout')
            counter += 1
        msg: Message = self.buffer
        self.buffer = None
        return msg

    def send_text(self,chat_id: int, text: str) -> NoReturn:
        self.telegram.loop.run_until_complete(self.telegram.send_message(chat_id, text))

    def get_whatsapp_message(self):
        counter: int = 0
        while True:
            counter += 1
            if counter == TIMEOUT:
                print('timeout')
                raise TimeoutError('Whatsapp message receive timeout')
            messages = self.whatsapp.get_unread_messages()
            print(messages)
            if len(messages) > 0:
                return messages[0]
            sleep(1)

    def test_receive_text(self):
        self.whatsapp.send_message(self.contact_name,MESSAGE)
        message:Message=self.get_message()
        self.assertEqual(message.chat_id,self.chat)
        self.assertEqual(message.text,MESSAGE)

    def test_send_text(self):
        self.send_text(self.chat,MESSAGE)
        message=self.get_whatsapp_message()
        self.assertEqual(message.message,MESSAGE)

    def tearDownClass(self=None) -> None:
        print('stopping bot')
        TelegramCase.bot.stop()
        print('stop whatsapp')
        TelegramCase.whatsapp.close()
        print('stopping telegram')
        TelegramCase.telegram.disconnect()
        print('done stopping')


if __name__ == '__main__':
    main()
