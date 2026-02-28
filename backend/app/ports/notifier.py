from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class NotificationPayload:
    title: str
    body: str
    day_key: str          # DeepLink用

class PushNotifier(ABC):
    @abstractmethod
    async def send_multicast(self, tokens: list[str], payload: NotificationPayload) -> dict:
        """FCM multicast送信。{success: int, failure: int} を返す"""
        ...
