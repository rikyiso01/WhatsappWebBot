from selenium.webdriver import Chrome,ChromeOptions
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import TimeoutException,NoSuchElementException
from selenium.webdriver.common.keys import Keys
from threading import Thread
from typing import Optional,NoReturn,Callable,List
from atexit import register
from time import sleep
from pyvirtualdisplay import Display
from logging import getLogger,INFO,DEBUG,Logger
from os.path import basename

QR_CODE="//canvas[@aria-label='Scan me!']"
HOME_PAGE_IMAGE='//div[@data-asset-intro-image-light="true"][@style="transform: scale(1); opacity: 1;"]'
HOME_PAGE_IMAGE2='//div[@data-asset-intro-image-light="true"][@style="opacity: 1;"]'
SEARCH_BAR='//div[@contenteditable="true"][@data-tab="3"]'
CONTACT_BOX='//span[contains(@title,"{}")]'
INPUT_BOX='//div[@contenteditable="true"][@spellcheck="true"]'
UNREAD_MESSAGES='//span[contains(@aria-label,"unread message")]'
MESSAGES='//div[contains(@class,"message-in focusable-list-item")][@tabindex="-1"]'
TEXT_IN_MESSAGE='.//span[contains(@class,"selectable-text invisible-space copyable-text")]'
WHO_FROM_UNREAD='./../../../../../div[1]/div[1]'
SENDER_IN_MESSAGE='./div/div/div/div/span'
# //*[@id="main"]/div[3]/div/div/div[3]/div[17]/div/div/div/div[1]/span[1]

class WhatsappOptions:
    def __init__(self):
        self.interactive:bool=False
        self.show:bool=False
        self.block:bool=False
        self.debug:bool=False

class Whatsapp:
    def __init__(self,profile_dir:str,options:WhatsappOptions=WhatsappOptions())->NoReturn:
        self.display:Optional[Display]=None
        if not options.interactive:
            self.display=Display(visible=options.show)
            self.display.start()
        self._logged_in:bool=False
        self.block:bool=options.block
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
        self.driver:WebDriver = Chrome(chrome_options=options)
        self.driver.get("https://web.whatsapp.com")
        register(self.close)
        self._thread_name:str=f'{self.name}-qr-thread'
        self._qr_thread:Thread=Thread(target=self._qr_code_thread,name=self._thread_name)
        self._qr_thread.start()

    def _set_qr_callback(self,qr_callback:Optional[Callable[[bytes],NoReturn]])->NoReturn:
        self._qr_callback=qr_callback
        if self._qr_code_png is not None:
            qr_callback(self._qr_code_png)

    qr_callback:Optional[Callable[[bytes],NoReturn]]=property(None,_set_qr_callback)
    logged_in:bool=property(lambda self:self._logged_in)

    def close(self)->NoReturn:
        self.running=False
        self.driver.quit()
        if self.display is not None:
            self.display.stop()

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

    def select_chat(self,who:str):
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
        self.select_chat(who)
        messages: List[WebElement] = self.driver.find_elements_by_xpath(MESSAGES)
        result: List[Message] = []
        for i in range(len(messages) - 1, len(messages) - how_many - 1, -1):
            try:
                text = messages[i].find_element_by_xpath(TEXT_IN_MESSAGE)
                sender=None
                try:
                    sender = messages[i].find_element_by_xpath(SENDER_IN_MESSAGE).text
                except NoSuchElementException:
                    print('Not in a group')
                result.append(Message(who,text.text,sender))
            except NoSuchElementException:
                pass
        return result

    def get_unread_messages(self)->List['Message']:
        result:List[Message]=[]
        for bubble in self.driver.find_elements_by_xpath(UNREAD_MESSAGES):
            how_many:int=int(bubble.text)
            who:str=bubble.find_element_by_xpath(WHO_FROM_UNREAD).text
            result.extend(self.get_messages(who,how_many))
        return result

    def send_message(self,who:str,message:str):
        self.select_chat(who)

        input_box = self.driver.find_element_by_xpath(INPUT_BOX)
        text:str=message if self.block else message + Keys.ENTER
        input_box.send_keys(text)

class Message:
    def __init__(self,sender:str,message:str,who:str=None):
        self.sender:str=sender
        self.message:str=message
        self.who:Optional[str]=who

    def __repr__(self):
        return str({'sender':self.sender,'message':self.message,'who':self.who})


class ThreadStopError(Exception):
    def __init__(self)->NoReturn:
        super(ThreadStopError, self).__init__('The thread must be stopped')

class UserNotFoundError(Exception):
    def __init__(self,who:str)->NoReturn:
        super(UserNotFoundError, self).__init__(f'Whatsapp user {who} not found')
