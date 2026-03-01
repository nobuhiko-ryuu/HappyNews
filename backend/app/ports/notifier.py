from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TypedDict


@dataclass
class NotificationPayload:
    title: str
    body: str
    day_key: str
    deeplink: str = "happynews://today"


class MulticastResult(TypedDict):
    success: int
    failure: int


class PushNotifier(ABC):
    @abstractmethod
    async def send_multicast(self, tokens: list[str], payload: NotificationPayload) -> MulticastResult:
        """FCM multicast送信。{success: int, failure: int} を返す"""
        ...
