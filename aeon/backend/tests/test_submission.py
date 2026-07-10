"""
Tests the retry logic in isolation (mocking httpx), without requiring a
live Celery worker or Redis broker — this is more portable than
pytest-celery, which needs a running broker to execute tasks for real.

If you do want true end-to-end Celery task execution in CI, add
pytest-celery and a celery_config fixture pointing at a test Redis
instance; the assertions below would stay the same either way.
"""
from unittest.mock import patch, MagicMock

import httpx

from app.workers.submission_worker import _call_authority_api, TransientSubmissionError, PermanentSubmissionError


def test_retries_on_5xx_then_succeeds():
    responses = [
        MagicMock(status_code=500, text="server error"),
        MagicMock(status_code=500, text="server error"),
        MagicMock(status_code=200, text="OK"),
    ]

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.side_effect = responses
        mock_client_cls.return_value = mock_client

        result = _call_authority_api("https://fake-endpoint.test", "<xml/>", {})

        assert result.status_code == 200
        assert mock_client.post.call_count == 3


def test_permanent_error_on_4xx_does_not_retry():
    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.return_value = MagicMock(status_code=400, text="bad request")
        mock_client_cls.return_value = mock_client

        try:
            _call_authority_api("https://fake-endpoint.test", "<xml/>", {})
            assert False, "expected PermanentSubmissionError"
        except PermanentSubmissionError:
            pass

        assert mock_client.post.call_count == 1
