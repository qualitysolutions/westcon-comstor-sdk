from __future__ import annotations

import pytest

from westcon_comstor import Config
from westcon_comstor.errors import ConfigurationError


def test_environment_selects_gateway():
    prod = Config(client_id="c", client_secret="s", resource="r")
    assert prod.environment == "prod"
    assert prod.gateway_base_url == "https://api.westconcomstor.com"

    uat = Config(client_id="c", client_secret="s", resource="r", environment="uat")
    assert uat.gateway_base_url == "https://westconapiuat.azure-api.net"


def test_explicit_gateway_wins_over_environment():
    cfg = Config(client_id="c", client_secret="s", resource="r", environment="uat",
                 gateway_base_url="https://example.test/gw/")
    assert cfg.gateway_base_url == "https://example.test/gw"  # trailing slash trimmed


def test_unknown_environment_without_gateway_raises():
    with pytest.raises(ConfigurationError):
        Config(client_id="c", client_secret="s", resource="r", environment="staging")


def test_tenant_id_defaults_to_westcon(monkeypatch):
    from westcon_comstor.config import WESTCON_AZURE_AD_TENANT_ID
    monkeypatch.delenv("WESTCON_TENANT_ID", raising=False)
    cfg = Config(client_id="c", client_secret="s", resource="r")  # no tenant_id -> default
    assert cfg.tenant_id == WESTCON_AZURE_AD_TENANT_ID


def test_from_env_uses_environment_specific_vars(monkeypatch):
    monkeypatch.setenv("WESTCON_ENV", "uat")
    # env-specific values present for uat, plus generic (prod-ish) values that must be ignored
    monkeypatch.setenv("WESTCON_UAT_CLIENT_ID", "uat-id")
    monkeypatch.setenv("WESTCON_UAT_CLIENT_SECRET", "uat-secret")
    monkeypatch.setenv("WESTCON_UAT_RESOURCE", "uat-res")
    monkeypatch.setenv("WESTCON_UAT_SUBSCRIPTION_KEY", "uat-sub")
    monkeypatch.setenv("WESTCON_CLIENT_ID", "generic-id")  # should be overridden by UAT-specific
    monkeypatch.setenv("WESTCON_PARTNER_KEY", "generic-partner")  # no UAT-specific -> fallback used

    cfg = Config.from_env()
    assert cfg.environment == "uat"
    assert cfg.client_id == "uat-id"
    assert cfg.subscription_key == "uat-sub"
    assert cfg.partner_key == "generic-partner"  # fell back to generic
    assert cfg.gateway_base_url == "https://westconapiuat.azure-api.net"


def test_from_env_tenant_id_override(monkeypatch):
    monkeypatch.delenv("WESTCON_ENV", raising=False)
    monkeypatch.setenv("WESTCON_CLIENT_ID", "id")
    monkeypatch.setenv("WESTCON_CLIENT_SECRET", "secret")
    monkeypatch.setenv("WESTCON_RESOURCE", "res")
    monkeypatch.setenv("WESTCON_TENANT_ID", "override-tenant")
    assert Config.from_env().tenant_id == "override-tenant"


def test_from_env_defaults_to_prod(monkeypatch):
    monkeypatch.delenv("WESTCON_ENV", raising=False)
    monkeypatch.delenv("WESTCON_ENVIRONMENT", raising=False)
    monkeypatch.setenv("WESTCON_CLIENT_ID", "id")
    monkeypatch.setenv("WESTCON_CLIENT_SECRET", "secret")
    monkeypatch.setenv("WESTCON_RESOURCE", "res")
    cfg = Config.from_env()
    assert cfg.environment == "prod"
    assert cfg.gateway_base_url == "https://api.westconcomstor.com"
