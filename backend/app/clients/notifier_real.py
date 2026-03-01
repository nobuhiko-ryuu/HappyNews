"""Real PushNotifier using Firebase Admin SDK"""
from __future__ import annotations
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from app.ports.notifier import MulticastResult, NotificationPayload, PushNotifier

logger = logging.getLogger("happynews.clients.notifier_real")
_executor = ThreadPoolExecutor(max_workers=2)


def _send_sync(tokens: list[str], payload: NotificationPayload) -> dict:
    from firebase_admin import messaging

    message = messaging.MulticastMessage(
        tokens=tokens,
        notification=messaging.Notification(
            title=payload.title,
            body=payload.body,
        ),
        data={
            "day_key": payload.day_key,
            "deeplink": payload.deeplink,
        },
    )
    response = messaging.send_each_for_multicast(message)
    return {"success": response.success_count, "failure": response.failure_count}


class RealPushNotifier(PushNotifier):
    async def send_multicast(
        self, tokens: list[str], payload: NotificationPayload
    ) -> MulticastResult:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(_executor, _send_sync, tokens, payload)
        logger.info(
            f"FCM multicast: {result['success']} success, {result['failure']} failure"
        )
        return result
