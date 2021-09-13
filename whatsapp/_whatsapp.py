from pathlib import Path
from pyvirtualdisplay import Display  # type: ignore
from arsenic import start_session, stop_session  # type: ignore
from arsenic.services import Chromedriver  # type: ignore
from arsenic.browsers import Chrome  # type: ignore
from arsenic.session import Session, Element  # type: ignore
from arsenic.errors import ArsenicTimeout, NoSuchElement  # type: ignore
from arsenic.keys import RIGHT, BACKSPACE  # type: ignore
from typing import Optional, Callable, BinaryIO, NoReturn
from ._xpaths import (
    QR_CODE,
    HOME_PAGE,
    SEARCH_BAR,
    CONTACT_BOX,
    UNREAD_MESSAGES,
    WHO_FROM_UNREAD,
    MESSAGES,
)
from collections import Awaitable
from queue import Queue
from contextlib import AbstractAsyncContextManager
from asyncio import sleep, CancelledError
from logging import ERROR
from structlog import configure, make_filtering_bound_logger
from aiohttp.client_exceptions import ClientConnectorError
from ._messages import SelectorType, Chat, Message, MESSAGE_TYPES

configure(wrapper_class=make_filtering_bound_logger(ERROR))


# Whatsapp chat not found exception
class NoSuchChatError(Exception):
    pass


# Message type not supported
class MessageNotSupportedError(Exception):
    pass


# Context manager to keep the search bar clear to avoid errors
class SearchBarContextManager(AbstractAsyncContextManager):
    def __init__(self, session: Session, chat: Chat):
        self._session = session
        self._chat = chat

    async def __aenter__(self) -> Element:
        assert self._session is not None
        search_bar = await self._session.get_element(SEARCH_BAR, SelectorType.XPATH)
        await search_bar.click()
        await search_bar.send_keys(self._chat)
        try:
            element = await self._session.wait_for_element(
                2, CONTACT_BOX.format(self._chat), SelectorType.XPATH
            )
        except ArsenicTimeout:
            await self.__aexit__(None, None, None)
            raise NoSuchChatError(self._chat)
        # Wait 2 seconds to avoid clicking the wrong chat because during the search the elements move
        await sleep(2)
        return element

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        search_bar: Element = await self._session.get_element(
            SEARCH_BAR, SelectorType.XPATH
        )
        # Clear the search bar
        await search_bar.click()
        await search_bar.send_keys(RIGHT * len(self._chat))
        await search_bar.send_keys(BACKSPACE * len(self._chat))


def search_chat(session: Session, chat: Chat) -> SearchBarContextManager:
    return SearchBarContextManager(session, chat)


# Context manager to handle the return to the default chat after a switch
class ChatSelectionContextManager(AbstractAsyncContextManager):
    def __init__(self, session: Session, default_chat: Optional[Chat]):
        self._session = session
        self._default_chat = default_chat
        self._changed = False

    async def select_chat(self, chat: Chat) -> None:
        self._changed = True
        async with search_chat(self._session, chat) as contact:
            await contact.click()
            # Wait for the messages to load
            await sleep(2)

    async def __aenter__(self) -> "ChatSelectionContextManager":
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        # Return to the default chat
        if self._default_chat is not None and self._changed:
            await self.select_chat(self._default_chat)


def select_chat(
    session: Session, default_chat: Optional[Chat]
) -> ChatSelectionContextManager:
    return ChatSelectionContextManager(session, default_chat)


class Whatsapp:
    def __init__(
        self,
        profile_dir: Path,
        default_chat: Optional[Chat],
        show: bool,
        debug: bool,
        qr_callback: Callable[[BinaryIO], Awaitable[None]],
        login_callback: Callable[[], Awaitable[None]],
        message_callback: Callable[[Message], Awaitable[None]],
        exception_callback: Callable[[], Awaitable[None]],
    ) -> None:
        # Create a virtual display with xvfb to fake a window with size
        # Headless mode on whatsapp web causes some elements to not appear
        self._display = Display(visible=show)
        # Data dir is used to restore the cookies between sessions
        self._chrome = Chrome(
            **{"goog:chromeOptions": {"args": [f"--user-data-dir={profile_dir}"]}}
        )
        self._session: Optional[Session] = None
        # Callback to use to send the qr code to scan
        self._qr_callback = qr_callback
        # Callback for a successful login
        self._login_callback = login_callback
        # Callback for a received message
        self._message_callback = message_callback
        # Callback for an error in the engine
        self._exception_callback = exception_callback
        # Message queue used to avoid concurrent access to the WebDriver
        self._message_queue: Queue[Message] = Queue()
        # If a chat is open, new messages in that chat will not cause a notification
        # This chat is used as a placeholder to fix this problem
        self.default_chat = default_chat

    async def start(self) -> NoReturn:
        self._display.start()
        self._session = await start_session(Chromedriver(), self._chrome)
        await self._session.get("https://web.whatsapp.com")
        while True:
            try:
                # Search for the qr code
                await self._session.wait_for_element(20, QR_CODE, SelectorType.XPATH)
            except ArsenicTimeout:
                # If no qr code is found then the user is already logged in and the home
                # page should be visible
                await self._session.wait_for_element(20, HOME_PAGE, SelectorType.XPATH)
                break
            try:
                # Send the qr code to the user and wait for the home page to appear,
                # after 20 seconds Whatsapp changes the qr code, so the process must be repeated
                await self._qr_callback(await self._session.get_screenshot())
                await self._session.wait_for_element(20, HOME_PAGE, SelectorType.XPATH)
                break
            except ArsenicTimeout:
                pass
        await self._login_callback()
        await self._pool_messages()

    async def _pool_messages(self) -> NoReturn:
        while True:
            try:
                # If a message is enqueued, sends the message to the correct chat
                while not self._message_queue.empty():
                    message = self._message_queue.get()
                    async with select_chat(
                        self._session, self.default_chat
                    ) as selector:
                        await selector.select_chat(message.chat)
                        await message.send(self._session)
                # Checks for new messages to forward
                messages = await self._get_unread_messages()
                for message in messages:
                    await self._message_callback(message)
                # Perform these check every seconds
                await sleep(1)
            except (KeyboardInterrupt, CancelledError):
                raise
            except ClientConnectorError:
                # A ClientConnectorError indicates that the session has already
                # been closed by a KeyboardInterrupt
                raise KeyboardInterrupt()
            except:
                # Logs unhandled exceptions to the user
                await self._exception_callback()

    async def _get_unread_messages(self) -> list[Message]:
        assert self._session is not None
        result: list[Message] = []
        async with select_chat(self._session, self.default_chat) as selector:
            for bubble in await self._session.get_elements(
                UNREAD_MESSAGES, SelectorType.XPATH
            ):
                # Reads the bubble near the chat to discover the number of new messages
                how_many = int(await bubble.get_text())
                chat = await (
                    await bubble.get_element(WHO_FROM_UNREAD, SelectorType.XPATH)
                ).get_text()
                result.extend(await self._get_messages(selector, chat, how_many))
        return result

    async def _get_messages(
        self, selector: ChatSelectionContextManager, chat: Chat, how_many: int
    ) -> list[Message]:
        assert self._session is not None
        await selector.select_chat(chat)
        messages = await self._session.get_elements(MESSAGES, SelectorType.XPATH)
        result: list[Message] = []
        for i in range(len(messages) - 1, len(messages) - how_many - 1, -1):
            result.append(await self._get_message(chat, messages[i]))
        return result

    async def _get_message(self, chat: Chat, div: Element) -> Message:
        # Tries to decode the message into any of the know message types
        for type in MESSAGE_TYPES:
            try:
                return await type.receive(self._session, chat, div)
            except NoSuchElement:
                pass
        raise MessageNotSupportedError()

    async def close(self) -> None:
        # If a KeyboardInterruption is raised from here, trying to close the session
        # will cause a ClientConnectorError
        self._display.stop()
        try:
            await stop_session(self._session)
        except ClientConnectorError:
            pass

    def send_message(self, message: Message) -> None:
        # Enqueues a new message
        self._message_queue.put(message)
