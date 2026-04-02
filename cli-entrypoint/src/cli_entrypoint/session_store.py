"""
Session store for the CLI Entrypoint Adapter.

Persists session metadata (labels, timestamps, message counts) to a local
JSON file so sessions survive process restarts.  SAM is the source of truth
for conversation history and artifacts — this store only keeps the lightweight
index the adapter needs to map labels to session IDs.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)

# Default storage directory (overridable via SAM_CLI_SESSIONS_DIR env var)
_DEFAULT_DIR = os.path.expanduser("~/.sam-cli-entrypoint")
_INDEX_FILENAME = "sessions.json"


class SessionStore:
    """Manage the local session index file."""

    def __init__(self, entrypoint_id: str, storage_dir: Optional[str] = None):
        self._entrypoint_id = entrypoint_id
        self._dir = os.path.expanduser(
            storage_dir or os.environ.get("SAM_CLI_SESSIONS_DIR", _DEFAULT_DIR)
        )
        self._path = os.path.join(self._dir, _INDEX_FILENAME)
        self._data: Dict[str, Any] = {}
        self._load()

    # --- Public API ---

    @property
    def active_session(self) -> Optional[str]:
        return self._data.get("active_session")

    @active_session.setter
    def active_session(self, session_id: str) -> None:
        self._data["active_session"] = session_id
        self._save()

    def list_sessions(self) -> List[Dict[str, Any]]:
        """Return all sessions sorted by last_active (most recent first)."""
        sessions = self._data.get("sessions", {})
        result = [{"id": sid, **meta} for sid, meta in sessions.items()]
        result.sort(key=lambda s: s.get("last_active", ""), reverse=True)
        return result

    def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a session by ID."""
        return self._data.get("sessions", {}).get(session_id)

    def find_by_label(self, label: str) -> Optional[str]:
        """Return the session ID for a given label, or None."""
        for sid, meta in self._data.get("sessions", {}).items():
            if meta.get("label") == label:
                return sid
        return None

    def label_exists(self, label: str) -> bool:
        """Check if a label is already in use."""
        return self.find_by_label(label) is not None

    def create(self, session_id: str, label: Optional[str] = None) -> Dict[str, Any]:
        """Register a new session in the index."""
        now = datetime.now(timezone.utc).isoformat()
        meta = {
            "label": label,
            "created": now,
            "last_active": now,
            "message_count": 0,
        }
        self._data.setdefault("sessions", {})[session_id] = meta
        self._save()
        return meta

    def update(self, session_id: str, **fields) -> None:
        """Update fields on an existing session."""
        session = self._data.get("sessions", {}).get(session_id)
        if session is None:
            return
        session.update(fields)
        self._save()

    def increment_message_count(self, session_id: str) -> None:
        """Bump message_count and last_active for a session."""
        session = self._data.get("sessions", {}).get(session_id)
        if session is None:
            return
        session["message_count"] = session.get("message_count", 0) + 1
        session["last_active"] = datetime.now(timezone.utc).isoformat()
        self._save()

    def delete(self, session_id: str) -> bool:
        """Remove a session from the local index. Returns True if it existed.

        Note: This only removes the local metadata (label, message count, etc.).
        SAM retains the conversation history and artifacts server-side — there is
        currently no framework API to delete those.
        """
        sessions = self._data.get("sessions", {})
        if session_id in sessions:
            del sessions[session_id]
            # If we deleted the active session, clear it
            if self._data.get("active_session") == session_id:
                self._data["active_session"] = None
            self._save()
            return True
        return False

    def resolve(self, label_or_id: str) -> Optional[str]:
        """Resolve a label or partial/full ID to a session ID.

        Returns the session ID, or None if not found.
        Raises ValueError if the input matches multiple sessions (ambiguous).
        """
        # Try exact label match first
        by_label = self.find_by_label(label_or_id)
        if by_label:
            return by_label
        # Try exact ID match
        sessions = self._data.get("sessions", {})
        if label_or_id in sessions:
            return label_or_id
        # Try partial ID match
        matches = [sid for sid in sessions if sid.endswith(label_or_id) or label_or_id in sid]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise ValueError(f"Ambiguous — matches {len(matches)} sessions. Be more specific.")
        return None

    # --- Persistence ---

    def _load(self) -> None:
        """Load the index from disk, or initialize a fresh one."""
        if os.path.isfile(self._path):
            try:
                with open(self._path, "r") as f:
                    self._data = json.load(f)
                # Migrate legacy "gateway_id" key to "entrypoint_id"
                if "gateway_id" in self._data and "entrypoint_id" not in self._data:
                    self._data["entrypoint_id"] = self._data.pop("gateway_id")
                    self._save()
                # Verify entrypoint_id matches
                if self._data.get("entrypoint_id") != self._entrypoint_id:
                    log.warning(
                        "Session index entrypoint_id mismatch: expected %s, got %s. Starting fresh.",
                        self._entrypoint_id,
                        self._data.get("entrypoint_id"),
                    )
                    self._data = {}
            except (json.JSONDecodeError, OSError) as e:
                log.warning("Could not load session index %s: %s. Starting fresh.", self._path, e)
                self._data = {}

        if not self._data:
            self._data = {
                "entrypoint_id": self._entrypoint_id,
                "active_session": None,
                "sessions": {},
            }

    def _save(self) -> None:
        """Write the index to disk."""
        try:
            os.makedirs(self._dir, exist_ok=True)
            with open(self._path, "w") as f:
                json.dump(self._data, f, indent=2)
        except OSError as e:
            log.error("Could not save session index %s: %s", self._path, e)
