from selenium.webdriver import Chrome,ChromeOptions
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import TimeoutException,NoSuchElementException
from selenium.webdriver.common.keys import Keys
from threading import Thread
from typing import Optional,NoReturn,Callable,List,Tuple,Union
from atexit import register,unregister
from time import sleep
from pyvirtualdisplay import Display
from logging import getLogger,INFO,DEBUG,Logger
from os.path import basename
from base64 import b64decode
from enum import Enum
from os.path import join,abspath

QR_CODE="//canvas[@aria-label='Scan me!']"
HOME_PAGE_IMAGE='//div[@data-asset-intro-image-light="true"][@style="transform: scale(1); opacity: 1;"]'
HOME_PAGE_IMAGE2='//div[@data-asset-intro-image-light="true"][@style="opacity: 1;"]'
SEARCH_BAR='//div[@contenteditable="true"][@data-tab="3"]'
CONTACT_BOX='//span[contains(@title,"{}")]'
INPUT_BOX='//div[@contenteditable="true"][@spellcheck="true"]'
UNREAD_MESSAGES='//span[contains(@aria-label,"unread message")]'
MESSAGES='//div[contains(@class,"message-in focusable-list-item")][@tabindex="-1"]'
TEXT_IN_MESSAGE='.//span[contains(@class,"selectable-text invisible-space copyable-text")]'
AUDIO_IN_MESSAGE='.//audio'
IMAGE_IN_MESSAGE='.//img[contains(@src,"blob:")]'
WHO_FROM_UNREAD='./../../../../../div[1]/div[1]'
SENDER_IN_MESSAGE='.{}/span'
DIV='/div[1]'
IMAGE_CAPTION='./div[1]/div[1]/div[1]/div[1]/div/div[1]/span/span'
ADD_FILE='//span[@data-testid="{0}"][@data-icon="{0}"]'
CLIP='clip'
ATTACH_IMAGE='attach-image'
SEND='send'

class WhatsappOptions:
    def __init__(self):
        self.interactive:bool=False
        self.show:bool=False
        self.debug:bool=False

class Whatsapp:
    def __init__(self,profile_dir:str,default_chat:Optional[str],options:WhatsappOptions=WhatsappOptions())->NoReturn:
        self.display:Optional[Display]=None
        if not options.interactive:
            self.display=Display(visible=options.show)
            self.display.start()
        self._logged_in:bool=False
        self._default_chat:Optional[str]=default_chat
        self.name: str = basename(profile_dir)
        self.logger:Logger=getLogger(self.name)
        self.logger.setLevel(DEBUG if options.debug else INFO)
        self.running:bool=True
        self.profile_dir:str=profile_dir
        self._qr_callback:Optional[Callable[[bytes],NoReturn]]=None
        self.logged_in_callback: Optional[Callable[[], NoReturn]] = None
        self._qr_code_png:Optional[bytes]=None
        options:ChromeOptions=ChromeOptions()
        options.add_argument(f'--user-data-dir={profile_dir}')
        self.driver:WebDriver = Chrome(options=options)
        self.driver.get("https://web.whatsapp.com")
        register(self.close)
        self._thread_name:str=f'{self.name}-qr-thread'
        self._qr_thread:Thread=Thread(target=self._qr_code_thread,name=self._thread_name)
        self._qr_thread.start()

    @property
    def default_chat(self)->str:
        return self._default_chat

    @default_chat.setter
    def default_chat(self,default_chat:str)->NoReturn:
        if not self.user_exists(default_chat):
            raise UserNotFoundError(default_chat)
        self._default_chat=default_chat

    def _set_qr_callback(self,qr_callback:Optional[Callable[[bytes],NoReturn]])->NoReturn:
        self._qr_callback=qr_callback
        if self._qr_code_png is not None:
            qr_callback(self._qr_code_png)

    qr_callback:Optional[Callable[[bytes],NoReturn]]=property(None,_set_qr_callback)
    logged_in:bool=property(lambda self:self._logged_in)

    def close(self)->NoReturn:
        unregister(self.close)
        self.running=False
        self.driver.quit()
        if self.display is not None:
            self.display.stop()
        self._qr_thread.join()

    def wait_for_login(self):
        self._qr_thread.join()

    def _qr_code_thread(self)->NoReturn:
        try:
            try:
                canvas:WebElement = WebDriverWait(self.driver, 20).until(self._get_element_in_thread(QR_CODE))
                while True:
                    self._qr_code_png=canvas.screenshot_as_png
                    if self._qr_callback is not None:
                        self._qr_callback(self._qr_code_png)
                    try:
                        WebDriverWait(self.driver, 20).until_not(self._get_element_in_thread(QR_CODE))
                        break
                    except TimeoutException:
                        continue
            except TimeoutException:
                self.logger.debug(f'The user {self.name} is already logged in')

            WebDriverWait(self.driver, 20).until(self._get_element_in_thread(HOME_PAGE_IMAGE,HOME_PAGE_IMAGE2))
            self.logger.debug(f'Main page for {self.name} loaded')
            self._logged_in = True
            if self.logged_in_callback is not None:
                self.logged_in_callback()
        except ThreadStopError:
            self.logger.debug(f'The thread {self._thread_name} was stopped by interrupt')
        self.logger.debug(f'The thread {self._thread_name} is stopping normally')

    def _get_element_in_thread(self,*x_paths:str)->Callable[[WebDriver],WebElement]:
        def method(driver:WebDriver)->WebElement:
            if not self.running:
                raise ThreadStopError()
            err:Exception=ValueError('No xpath provided')
            for xpath in x_paths:
                try:
                    return driver.find_element_by_xpath(xpath)
                except NoSuchElementException as e:
                    err=e
            raise err
        return method

    def _select_chat(self,who:Optional[str]):
        if who is None:
            return
        try:
            selected_contact:WebElement=self._search_user(who)
        except TimeoutException:
            raise UserNotFoundError(who)
        selected_contact.click()
        self._clear_search_bar(who)
        sleep(2)

    def _search_user(self,who:str)->WebElement:
        search_bar: WebElement = self.driver.find_element_by_xpath(SEARCH_BAR)
        search_bar.click()
        search_bar.send_keys(who)
        element=WebDriverWait(self.driver, 2).until(
            lambda driver: self.driver.find_element_by_xpath(CONTACT_BOX.format(who)))
        sleep(1)
        return element

    def _clear_search_bar(self,who:str)->NoReturn:
        search_bar: WebElement = self.driver.find_element_by_xpath(SEARCH_BAR)
        search_bar.click()
        search_bar.send_keys(Keys.RIGHT*len(who))
        search_bar.send_keys(Keys.BACKSPACE*len(who))

    def user_exists(self,who:str)->bool:
        result:bool
        try:
            self._search_user(who)
            result=True
        except TimeoutException:
            result=False
        self._clear_search_bar(who)
        return result

    def _is_group(self)->bool:
        pass

    def get_messages(self,who:str,how_many:int)->List['Message']:
        self._select_chat(who)
        messages: List[WebElement] = self.driver.find_elements_by_xpath(MESSAGES)
        result: List[Message] = []
        for i in range(len(messages) - 1, len(messages) - how_many - 1, -1):
            data=self._get_message(messages[i])
            if data is None:
                continue
            message,message_type,divs=data
            sender:Optional[str]
            try:
                sender = messages[i].find_element_by_xpath(SENDER_IN_MESSAGE.format(DIV * divs)).text
            except NoSuchElementException:
                self.logger.debug('Not in a group')
                sender=None
            result.append(Message(who, message, sender, message_type))
        return result

    def _get_message(self,div:WebElement)->Optional[Tuple[Union[str,bytes,Tuple[str,bytes]],'MessageType',int]]:
        try:
            image: WebElement = div.find_element_by_xpath(IMAGE_IN_MESSAGE)
            caption:str
            try:
                caption=div.find_element_by_xpath(IMAGE_CAPTION).text
            except NoSuchElementException:
                caption=''
            return (caption,self._download_blob(image.get_attribute('src'))), MessageType.IMAGE, 6
        except NoSuchElementException:
            pass
        try:
            text = div.find_element_by_xpath(TEXT_IN_MESSAGE)
            return text.text,MessageType.TEXT,4
        except NoSuchElementException:
            pass
        try:
            audio: WebElement = div.find_element_by_xpath(AUDIO_IN_MESSAGE)
            return self._download_blob(audio.get_attribute('src')),MessageType.AUDIO,5
        except NoSuchElementException:
            pass
        return None

    def get_unread_messages(self)->List['Message']:
        result:List[Message]=[]
        reset:bool=False
        for bubble in self.driver.find_elements_by_xpath(UNREAD_MESSAGES):
            how_many:int=int(bubble.text)
            who:str=bubble.find_element_by_xpath(WHO_FROM_UNREAD).text
            result.extend(self.get_messages(who,how_many))
            reset=True
        if reset:
            self._select_chat(self._default_chat)
        return result

    def send_message(self,who:str,message:str)->NoReturn:
        self._select_chat(who)

        input_box = self.driver.find_element_by_xpath(INPUT_BOX)
        input_box.send_keys(message + Keys.ENTER)

        self._select_chat(self.default_chat)

    def send_photo(self,who:str,photo:bytes,caption:str)->NoReturn:
        self._select_chat(who)

        self.driver.find_element_by_xpath(ADD_FILE.format(CLIP)).click()
        button:WebElement=WebDriverWait(self.driver,2)\
            .until(lambda driver:self.driver.find_element_by_xpath(ADD_FILE.format(ATTACH_IMAGE)))
        inp:WebElement=button.find_element_by_xpath('./../input')
        path:str=abspath(join(self.profile_dir,'.photo.png'))
        with open(path,'wb') as f:
            f.write(photo)
        inp.send_keys(path)
        WebDriverWait(self.driver, 2).until(lambda driver: self.driver.find_element_by_xpath(ADD_FILE.format(SEND)))
        caption_bar=self.driver.find_element_by_xpath(INPUT_BOX)
        caption_bar.send_keys(caption+Keys.ENTER)

        self._select_chat(self._default_chat)

    def _download_blob(self,url:str)->bytes:
        result = self.driver.execute_async_script(
            'var uri = arguments[0];'
            'var callback = arguments[1];'
            'var toBase64 = function(buffer){for(var r,n=new Uint8Array(buffer),'
            't=n.length,a=new Uint8Array(4*Math.ceil(t/3)),i=new Uint8Array(64),o=0,c=0;64>c;++c)'
            'i[c]="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/".charCodeAt(c);'
            'for(c=0;t-t%3>c;c+=3,o+=4)r=n[c]<<16|n[c+1]<<8|n[c+2],a[o]=i[r>>18],'
            'a[o+1]=i[r>>12&63],a[o+2]=i[r>>6&63],a[o+3]=i[63&r];'
            'return t%3===1?(r=n[t-1],a[o]=i[r>>2],a[o+1]=i[r<<4&63],a[o+2]=61,a[o+3]=61):'
            't%3===2&&(r=(n[t-2]<<8)+n[t-1],a[o]=i[r>>10],a[o+1]=i[r>>4&63],a[o+2]=i[r<<2&63],a[o+3]=61),'
            'new TextDecoder("ascii").decode(a)};'
            'var xhr = new XMLHttpRequest();'
            "xhr.responseType = 'arraybuffer';"
            'xhr.onload = function(){ callback(toBase64(xhr.response)) };'
            'xhr.onerror = function(){ callback(xhr.status) };'
            "xhr.open('GET', uri);"
            'xhr.send();',url)
        if type(result) == int:
            raise Exception("Request failed with status %s" % result)
        return b64decode(result)

class MessageType(Enum):
    TEXT=0
    AUDIO=1
    IMAGE=2

class Message:
    def __init__(self,sender:str,message:Union[str,bytes,Tuple[str,bytes]],who:str=None,
                 message_type:MessageType=MessageType.TEXT):
        self.sender:str=sender
        self.message:Union[str,bytes,Tuple[str,bytes]]=message
        self.message_type:MessageType=message_type
        self.who:Optional[str]=who

    def __repr__(self):
        return str({'sender':self.sender,
                    'message':self.message if self.message_type==MessageType.TEXT else self.message_type.name,
                    'who':self.who})


class ThreadStopError(Exception):
    def __init__(self)->NoReturn:
        super(ThreadStopError, self).__init__('The thread must be stopped')

class UserNotFoundError(Exception):
    def __init__(self,who:str)->NoReturn:
        super(UserNotFoundError, self).__init__(f'Whatsapp user {who} not found')
