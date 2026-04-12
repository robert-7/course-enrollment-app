from datetime import timedelta

import pytest

from application import app
from config import DevelopmentConfig
from config import get_config_for_env
from config import ProductionConfig
from config import TestingConfig as _TestingConfig


def test_application_bootstrap_uses_testing_config():
    assert app.config["PERMANENT_SESSION_LIFETIME"] == timedelta(minutes=30)
    assert app.config["TESTING"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    assert app.config["SESSION_COOKIE_SECURE"] is False


def test_get_config_for_env_defaults_to_development(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("MONGO_URI", "mongodb://localhost:27017/course_enrollment")

    config = get_config_for_env()

    assert isinstance(config, DevelopmentConfig)
    assert config.PERMANENT_SESSION_LIFETIME == timedelta(minutes=30)
    assert config.SESSION_COOKIE_SAMESITE == "Lax"
    assert config.SESSION_COOKIE_SECURE is False


def test_get_config_for_env_returns_testing_config(monkeypatch):
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("MONGO_URI", "mongodb://localhost:27017/course_enrollment")

    config = get_config_for_env()

    assert isinstance(config, _TestingConfig)
    assert config.PERMANENT_SESSION_LIFETIME == timedelta(minutes=30)
    assert config.SESSION_COOKIE_SAMESITE == "Lax"
    assert config.TESTING is True


def test_get_config_for_env_returns_production_config(monkeypatch):
    monkeypatch.setenv("APP_ENV", "PrOdUcTiOn")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("MONGO_URI", "mongodb://localhost:27017/course_enrollment")

    config = get_config_for_env()

    assert isinstance(config, ProductionConfig)
    assert config.PERMANENT_SESSION_LIFETIME == timedelta(minutes=30)
    assert config.SESSION_COOKIE_SAMESITE == "Lax"
    assert config.SESSION_COOKIE_SECURE is True


def test_get_config_for_env_rejects_invalid_values(monkeypatch):
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("MONGO_URI", "mongodb://localhost:27017/course_enrollment")

    with pytest.raises(RuntimeError, match="Unsupported APP_ENV value 'prod'"):
        get_config_for_env()
