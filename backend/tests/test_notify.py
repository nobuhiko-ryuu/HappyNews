"""TEST: FCM通知ジョブのテスト（外部依存ゼロ）"""
from __future__ import annotations
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.notify.job import _BATCH_SIZE, _MAX_RETRY


class TestConstants:
    def test_batch_size(self):
        assert _BATCH_SIZE == 500

    def test_max_retry(self):
        assert _MAX_RETRY == 2


def _make_async_stream(docs):
    async def _stream(*args, **kwargs):
        for doc in docs:
            yield doc
    return _stream


def _make_db_mock(docs):
    mock_db = MagicMock()
    mock_db.collection.return_value.where.return_value.where.return_value.stream = \
        _make_async_stream(docs)
    mock_db.collection.return_value.document.return_value.set = AsyncMock()
    return mock_db


class TestRunNotifyJobNoTargets:
    @pytest.mark.asyncio
    async def test_no_tokens_returns_zero_sent(self):
        with patch("app.notify.job.get_db") as mock_get_db, \
             patch("app.notify.job.get_notifier") as mock_get_notifier:
            mock_get_db.return_value = _make_db_mock([])
            mock_notifier = AsyncMock()
            mock_get_notifier.return_value = mock_notifier

            from app.notify.job import run_notify_job
            result = await run_notify_job(hour=8)

            assert result["targeted"] == 0
            assert result["sent"] == 0
            assert result["failed"] == 0
            mock_notifier.send_multicast.assert_not_called()


class TestRunNotifyJobWithTargets:
    @pytest.mark.asyncio
    async def test_sends_to_single_target(self):
        doc = MagicMock()
        doc.to_dict.return_value = {
            "notification_enabled": True,
            "notification_time": 8,
            "fcm_token": "token-abc",
        }
        with patch("app.notify.job.get_db") as mock_get_db, \
             patch("app.notify.job.get_notifier") as mock_get_notifier, \
             patch("app.notify.job.today_jst", return_value="2026-03-01"):
            mock_get_db.return_value = _make_db_mock([doc])
            mock_notifier = AsyncMock()
            mock_notifier.send_multicast.return_value = {
                "success": 1, "failure": 0
            }
            mock_get_notifier.return_value = mock_notifier

            from app.notify.job import run_notify_job
            result = await run_notify_job(hour=8)

            assert result["targeted"] == 1
            assert result["sent"] == 1
            assert result["failed"] == 0
            mock_notifier.send_multicast.assert_called_once()
            args = mock_notifier.send_multicast.call_args.args
            assert args[0] == ["token-abc"]
            assert args[1].deeplink == "happynews://today"
            assert args[1].day_key == "2026-03-01"

    @pytest.mark.asyncio
    async def test_deeplink_payload(self):
        """ペイロードに DeepLink が含まれること"""
        doc = MagicMock()
        doc.to_dict.return_value = {"fcm_token": "tok1"}
        with patch("app.notify.job.get_db") as mock_get_db, \
             patch("app.notify.job.get_notifier") as mock_get_notifier, \
             patch("app.notify.job.today_jst", return_value="2026-03-01"):
            mock_get_db.return_value = _make_db_mock([doc])
            mock_notifier = AsyncMock()
            mock_notifier.send_multicast.return_value = {
                "success": 1, "failure": 0
            }
            mock_get_notifier.return_value = mock_notifier

            from app.notify.job import run_notify_job
            await run_notify_job(hour=9)

            args = mock_notifier.send_multicast.call_args.args
            assert args[1].title == "今日のハッピーニュース"
            assert "happynews://today" in args[1].deeplink

    @pytest.mark.asyncio
    async def test_send_failure_counted(self):
        """送信失敗がカウントされること"""
        doc = MagicMock()
        doc.to_dict.return_value = {"fcm_token": "bad-token"}
        with patch("app.notify.job.get_db") as mock_get_db, \
             patch("app.notify.job.get_notifier") as mock_get_notifier, \
             patch("app.notify.job.today_jst", return_value="2026-03-01"), \
             patch("asyncio.sleep", new_callable=AsyncMock):
            mock_get_db.return_value = _make_db_mock([doc])
            mock_notifier = AsyncMock()
            mock_notifier.send_multicast.side_effect = Exception("FCM error")
            mock_get_notifier.return_value = mock_notifier

            from app.notify.job import run_notify_job
            result = await run_notify_job(hour=10)

            assert result["failed"] == 1
            assert len(result["errors"]) > 0


class TestExtractTargetTokens:
    @pytest.mark.asyncio
    async def test_skips_users_without_token(self):
        """fcm_token が None のユーザーをスキップ"""
        doc_with_token = MagicMock()
        doc_with_token.to_dict.return_value = {"fcm_token": "valid-token"}
        doc_without_token = MagicMock()
        doc_without_token.to_dict.return_value = {"fcm_token": None}

        mock_db = _make_db_mock([doc_with_token, doc_without_token])

        from app.notify.job import _extract_target_tokens
        tokens = await _extract_target_tokens(mock_db, hour=8)
        assert tokens == ["valid-token"]
