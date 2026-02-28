from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TypedDict


@dataclass
class NotificationPayload:
    title: str
    body: str
    day_key: str  # DeepLink用


class MulticastResult(TypedDict):
    success: int
    failure: int


class PushNotifier(ABC):
    @abstractmethod
    async def send_multicast(self, tokens: list[str], payload: NotificationPayload) -> MulticastResult:
        """FCM multicast送信。{success: int, failure: int} を返す"""
        ...
