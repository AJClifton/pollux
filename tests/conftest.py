import os
import tempfile

# Must be set before importing anything from app.*, because
# GunicornInternalPrometheusMetrics asserts PROMETHEUS_MULTIPROC_DIR at import.
_METRIC_DIR = tempfile.mkdtemp(prefix="prom_multiproc_")
os.environ["PROMETHEUS_MULTIPROC_DIR"] = _METRIC_DIR

from unittest.mock import MagicMock  # noqa: E402

import pytest  # noqa: E402

from app import create_app  # noqa: E402
from app.core.config import TestingConfig  # noqa: E402
from app.core.extensions import db as _db  # noqa: E402


@pytest.fixture
def app():
    app = create_app(TestingConfig)
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.rollback()
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db_session(app):
    with app.app_context():
        yield _db.session


@pytest.fixture
def mock_redis(app, monkeypatch):
    fake = MagicMock()
    fake.get.return_value = None
    fake.ping.return_value = True
    monkeypatch.setattr("app.core.extensions.redis_client", fake)
    monkeypatch.setattr("app.services.redis_service.redis_client", fake)
    monkeypatch.setattr("app.api.health.redis_client", fake)
    return fake
