"""Reversible pseudonymization using HMAC-based tokenization."""

import hashlib
import hmac

from gdpr_agent.config import (
    MIN_PSEUDONYM_KEY_LENGTH,
    PSEUDONYM_KEY_ENV_VAR,
    PSEUDONYM_TOKEN_HEX_CHARS,
)
from gdpr_agent.models import DEPSEUDONYMISATION_ROLES, Role


class PseudonymVault:
    """Holds the mapping from token back to original value.

    GDPR Art. 4(5) only treats data as pseudonymised while the "additional
    information" needed to re-identify it is *kept separately* and subject to
    its own safeguards. Keeping that mapping as an attribute of the
    pseudonymiser gave every holder of the pseudonymiser silent re-identification
    power, so it lives here instead: a separate object, held by whoever is
    entitled to it, that checks the caller's role and records a reason.
    """

    def __init__(self, authorized_roles: frozenset[Role] = DEPSEUDONYMISATION_ROLES):
        self._authorized_roles = authorized_roles
        self._reverse_map: dict[str, str] = {}

    def store(self, token: str, value: str) -> None:
        self._reverse_map[token] = value

    def resolve(self, token: str, role: Role, justification: str) -> str | None:
        """Reverse a pseudonym. Raises PermissionError for unauthorised roles."""
        if role not in self._authorized_roles:
            raise PermissionError(
                f"role '{role.value}' is not authorised to reverse pseudonyms"
            )
        if not justification or not justification.strip():
            raise PermissionError("de-pseudonymisation requires a justification")
        return self._reverse_map.get(token)

    def clear(self) -> None:
        """Drop the re-identification data once the session is finished."""
        self._reverse_map.clear()

    def __len__(self) -> int:
        return len(self._reverse_map)


class Pseudonymizer:
    """Deterministic HMAC tokenisation.

    One-way by default: without a vault, nothing retains the original value.
    """

    def __init__(self, secret_key: str, vault: PseudonymVault | None = None):
        if not secret_key or not secret_key.strip():
            raise ValueError(
                "a pseudonymisation key is required; set the "
                f"{PSEUDONYM_KEY_ENV_VAR} environment variable"
            )
        if len(secret_key) < MIN_PSEUDONYM_KEY_LENGTH:
            raise ValueError(
                f"pseudonymisation key must be at least {MIN_PSEUDONYM_KEY_LENGTH} "
                f"characters; got {len(secret_key)}"
            )
        self._key = secret_key.encode()
        self._vault = vault

    @property
    def is_reversible(self) -> bool:
        return self._vault is not None

    def pseudonymize(self, value: str) -> str:
        """Replace a value with a deterministic pseudonym.

        The digest is truncated to 128 bits rather than the previous 48. At 48
        bits a birthday collision becomes likely in the low millions of values,
        and a collision silently merges two data subjects into one pseudonym.
        """
        token_hash = hmac.new(
            self._key, value.encode(), hashlib.sha256
        ).hexdigest()[:PSEUDONYM_TOKEN_HEX_CHARS]
        token = f"PSE-{token_hash}"
        if self._vault is not None:
            self._vault.store(token, value)
        return token

    def depseudonymize(self, token: str, role: Role, justification: str) -> str | None:
        """Reverse a pseudonym, subject to the vault's authorisation check."""
        if self._vault is None:
            raise PermissionError(
                "this pseudonymiser is one-way; no vault holds the original values"
            )
        return self._vault.resolve(token, role=role, justification=justification)
