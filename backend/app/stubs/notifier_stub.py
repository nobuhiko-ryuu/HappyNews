from app.ports.notifier import PushNotifier, NotificationPayload

class StubPushNotifier(PushNotifier):
    async def send_multicast(self, tokens: list[str], payload: NotificationPayload) -> dict:
        print(f"[STUB NOTIFY] title={payload.title!r} day_key={payload.day_key} to {len(tokens)} tokens")
        return {"success": len(tokens), "failure": 0}
