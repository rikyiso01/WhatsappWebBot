from abc import abstractmethod, ABC
from tempfile import NamedTemporaryFile
from os import remove
from typing import Optional, Type
from arsenic.keys import ENTER  # type: ignore
from base64 import b64decode
from arsenic.session import Session, Element  # type: ignore
from enum import Enum
from arsenic.errors import NoSuchElement  # type: ignore
from ._xpaths import (
    SENDER_IN_MESSAGE,
    DIV,
    IMAGE_IN_MESSAGE,
    IMAGE_CAPTION,
    TEXT_IN_MESSAGE,
    AUDIO_IN_MESSAGE,
    DOWNLOAD_BLOB_SCRIPT,
    ADD_FILE,
    CLIP,
    ATTACH_IMAGE,
    SEND,
    INPUT_BOX,
)

Chat = str

# Fix Arsenic bug
class SelectorType(Enum):
    XPATH = "xpath"


# Base class of a Whatsapp message
class Message(ABC):
    # Base static method to create the message from its type
    @classmethod
    @abstractmethod
    async def receive(cls, session: Session, chat: Chat, div: Element) -> "Message":
        ...

    def __init__(self, chat: Chat, group_sender: Optional[str]):
        self.group_sender = group_sender
        self.chat = chat

    @abstractmethod
    async def send(self, session: Session) -> None:
        ...

    @property
    def is_in_group(self) -> bool:
        return self.group_sender is not None


async def download_blob(session: Session, url: str) -> bytes:
    # Downloads a raw asset
    assert session is not None
    result = await session.execute_async_script(DOWNLOAD_BLOB_SCRIPT, url)
    if type(result) == int:
        raise Exception("Request failed with status %s" % result)
    return b64decode(result)


async def get_group_sender(element: Element, divs: int) -> Optional[str]:
    # Every message type in a group has a different number of div between the message container
    # and the sender caption
    try:
        return await (
            await element.get_element(
                SENDER_IN_MESSAGE.format(DIV * divs), SelectorType.XPATH
            )
        ).get_text()
    except NoSuchElement:
        return None


MESSAGE_TYPES: list[Type[Message]] = []

# Decorator to simplify the process of adding a new type of message to the list
def message_subclass(cls: Type[Message]) -> Type[Message]:
    MESSAGE_TYPES.append(cls)
    return cls


# Custom message types


@message_subclass
class ImageMessage(Message):
    @classmethod
    async def receive(cls, session: Session, chat: Chat, div: Element) -> Message:
        image = await div.get_element(IMAGE_IN_MESSAGE, SelectorType.XPATH)
        caption: str
        try:
            caption = await (
                await div.get_element(IMAGE_CAPTION, SelectorType.XPATH)
            ).get_text()
        except NoSuchElement:
            caption = ""
        return ImageMessage(
            chat,
            caption,
            await download_blob(session, await image.get_attribute("src")),
            await get_group_sender(div, 6),
        )

    def __init__(
        self, chat: Chat, caption: str, image: bytes, group_sender: Optional[str] = None
    ):
        super().__init__(chat, group_sender)
        self.caption = caption
        self.image = image

    async def send(self, session: Session) -> None:
        await (
            await session.get_element(ADD_FILE.format(CLIP), SelectorType.XPATH)
        ).click()
        button = await session.wait_for_element(
            2, ADD_FILE.format(ATTACH_IMAGE), SelectorType.XPATH
        )
        inp = await button.get_element("./../input", SelectorType.XPATH)
        # The WebDriver requires an accessible file in the file system
        with NamedTemporaryFile(mode="wb", delete=False, suffix=".png") as tmp:
            tmp.write(self.image)
            path = tmp.name
        await inp.send_keys(path)
        await session.wait_for_element(2, ADD_FILE.format(SEND), SelectorType.XPATH)
        caption_bar = await session.get_element(INPUT_BOX, SelectorType.XPATH)
        await caption_bar.send_keys(self.caption + ENTER)
        remove(path)


@message_subclass
class TextMessage(Message):
    @classmethod
    async def receive(cls, session: Session, chat: Chat, div: Element) -> Message:
        text = await div.get_element(TEXT_IN_MESSAGE, SelectorType.XPATH)
        return TextMessage(chat, await text.get_text(), await get_group_sender(div, 4))

    def __init__(self, chat: Chat, text: str, group_sender: Optional[str] = None):
        super().__init__(chat, group_sender)
        self.text = text

    async def send(self, session: Session) -> None:
        input_box = await session.get_element(INPUT_BOX, SelectorType.XPATH)
        await input_box.send_keys(self.text + ENTER)


@message_subclass
class AudioMessage(Message):
    @classmethod
    async def receive(cls, session: Session, chat: Chat, div: Element) -> Message:
        audio = await div.get_element(AUDIO_IN_MESSAGE, SelectorType.XPATH)
        return AudioMessage(
            chat,
            await download_blob(session, await audio.get_attribute("src")),
            await get_group_sender(div, 5),
        )

    def __init__(self, chat: Chat, audio: bytes, group_sender: Optional[str] = None):
        super().__init__(chat, group_sender)
        self.audio = audio

    async def send(self, session: Session) -> None:
        # TODO: Implement audio send
        raise NotImplementedError()
