"""Configuration for the Westcon-Comstor SDK client."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from .errors import ConfigurationError

# Known environments and their gateway base URLs.
GATEWAY_URLS = {
    "prod": "https://api.westconcomstor.com",
    "uat": "https://westconapiuat.azure-api.net",
}
DEFAULT_ENVIRONMENT = "prod"
DEFAULT_GATEWAY_BASE_URL = GATEWAY_URLS["prod"]
# Westcon-Comstor's Azure AD tenant — the OAuth authority that issues tokens for their
# API. It is Westcon's tenant (embedded in the token-endpoint URL they hand out), the
# SAME for every partner, not the caller's own Azure AD tenant. Overridable via
# WESTCON_TENANT_ID only if Westcon ever issues a different token endpoint.
WESTCON_AZURE_AD_TENANT_ID = "ec8933c6-cfb2-4dd9-bfc9-621cde1dea8f"
# Azure AD v1 token endpoint template (client-credentials with a `resource` param).
AZURE_AD_TOKEN_URL_TEMPLATE = "https://login.microsoftonline.com/{tenant_id}/oauth2/token"


@dataclass
class Config:
    """Immutable configuration for a Westcon-Comstor client.

    All OAuth2 values (``client_id``, ``client_secret``, ``resource`` and the APIM
    ``subscription_key``) are provided by Westcon-Comstor via email when your partner
    account is set up, and are **per environment** (prod vs uat).

    ``environment`` selects the gateway when ``gateway_base_url`` is not given: ``"prod"``
    -> ``https://api.westconcomstor.com``, ``"uat"`` -> ``https://westconapiuat.azure-api.net``.
    UAT keys only work against the UAT gateway and vice versa.

    :meth:`from_env` reads ``WESTCON_*`` variables and supports keeping both environments
    in one ``.env`` via ``WESTCON_<ENV>_*`` overrides (see its docstring).
    """

    client_id: str
    client_secret: str
    resource: str
    subscription_key: str | None = None
    #: Reseller identifier ("partnerKey") sent in most request bodies. Optional here;
    #: it can also be passed per call. Provided by Westcon-Comstor.
    partner_key: str | None = None
    #: Azure AD tenant for the OAuth2 token endpoint. Defaults to Westcon-Comstor's
    #: tenant (the API's authority, same for all partners). Override via
    #: ``WESTCON_TENANT_ID`` only if Westcon issues a different token endpoint.
    tenant_id: str = WESTCON_AZURE_AD_TENANT_ID
    #: "prod" or "uat" (or any key in GATEWAY_URLS). Selects the gateway when
    #: gateway_base_url is not set explicitly.
    environment: str = DEFAULT_ENVIRONMENT
    #: Explicit gateway base URL. When None it is derived from ``environment``.
    gateway_base_url: str | None = None

    # Networking.
    timeout: float = 30.0
    max_retries: int = 2
    verify_tls: bool = True
    # Seconds subtracted from a token's real expiry before treating it as stale.
    token_expiry_leeway: float = 60.0
    # Optional extra headers applied to every gateway request.
    default_headers: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.client_id:
            raise ConfigurationError("client_id is required")
        if not self.client_secret:
            raise ConfigurationError("client_secret is required")
        if not self.resource:
            raise ConfigurationError("resource is required")
        self.environment = (self.environment or DEFAULT_ENVIRONMENT).lower()
        if not self.gateway_base_url:
            if self.environment not in GATEWAY_URLS:
                raise ConfigurationError(
                    f"Unknown environment {self.environment!r}; set gateway_base_url explicitly "
                    f"or use one of {sorted(GATEWAY_URLS)}"
                )
            self.gateway_base_url = GATEWAY_URLS[self.environment]
        self.gateway_base_url = self.gateway_base_url.rstrip("/")

    @property
    def token_url(self) -> str:
        """The Azure AD v1 token endpoint for the configured tenant."""
        return AZURE_AD_TOKEN_URL_TEMPLATE.format(tenant_id=self.tenant_id)

    @classmethod
    def from_env(cls, **overrides: object) -> "Config":
        """Build a :class:`Config` from ``WESTCON_*`` environment variables.

        The environment is chosen by ``WESTCON_ENV`` (or ``WESTCON_ENVIRONMENT``),
        default ``"prod"``. Each value is looked up **environment-first**: e.g. with
        ``WESTCON_ENV=uat`` the client id is ``WESTCON_UAT_CLIENT_ID`` if set, otherwise
        the generic ``WESTCON_CLIENT_ID``. That lets one ``.env`` hold both environments::

            WESTCON_ENV=uat
            WESTCON_UAT_CLIENT_ID=...     WESTCON_PROD_CLIENT_ID=...
            WESTCON_UAT_SUBSCRIPTION_KEY=...  WESTCON_PROD_SUBSCRIPTION_KEY=...
            ... (etc.)

        The gateway URL is derived from the environment unless
        ``WESTCON_[<ENV>_]GATEWAY_BASE_URL`` is set. Keyword overrides win over everything.
        """
        env = (os.getenv("WESTCON_ENV") or os.getenv("WESTCON_ENVIRONMENT") or DEFAULT_ENVIRONMENT).lower()
        prefix = f"WESTCON_{env.upper()}_"

        def pick(name: str, default: str | None = None) -> str | None:
            return os.getenv(prefix + name) or os.getenv("WESTCON_" + name) or default

        values: dict[str, object] = {
            "client_id": pick("CLIENT_ID", ""),
            "client_secret": pick("CLIENT_SECRET", ""),
            "resource": pick("RESOURCE", ""),
            "subscription_key": pick("SUBSCRIPTION_KEY"),
            "partner_key": pick("PARTNER_KEY"),
            "tenant_id": pick("TENANT_ID", WESTCON_AZURE_AD_TENANT_ID),
            "environment": env,
            "gateway_base_url": pick("GATEWAY_BASE_URL"),  # None -> derived from environment
        }
        values.update(overrides)
        return cls(**values)  # type: ignore[arg-type]
