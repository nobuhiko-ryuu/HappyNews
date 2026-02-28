import pytest


@pytest.fixture(autouse=True)
def reset_firebase(monkeypatch):
    """各テスト前後でFirebase Appをリセット"""
    import firebase_admin
    yield
    if firebase_admin._apps:
        for app in list(firebase_admin._apps.values()):
            firebase_admin.delete_app(app)
