"""
CLI Entrypoint Component for the Solace Agent Mesh Gateway Framework.

Provides an interactive terminal REPL for conversing with SAM agents.
"""

import asyncio
import base64
import html as html_mod
import logging
import mimetypes
import os
import shlex
import signal
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

from prompt_toolkit import PromptSession, prompt as pt_prompt
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.shortcuts import checkboxlist_dialog
from prompt_toolkit.styles import Style as PTStyle
from rich.console import Console
from rich.markdown import Markdown
from rich.theme import Theme

from solace_agent_mesh.gateway.base.component import BaseGatewayComponent
from a2a.types import (
    Part as A2APart,
    Task,
    TaskStatusUpdateEvent,
    TaskArtifactUpdateEvent,
    JSONRPCError,
    TextPart,
    FilePart,
    FileWithUri,
    FileWithBytes,
    DataPart,
)

from cli_entrypoint.session_store import SessionStore

# Max upload size: 50 MB
MAX_UPLOAD_BYTES = 50 * 1024 * 1024

log = logging.getLogger(__name__)

# Solace brand green: RGB 0,200,149
_SOLACE_GREEN = "\033[38;2;0;200;149m"
_BOLD = "\033[1m"
_RESET = "\033[0m"

BANNER = (
    _BOLD + _SOLACE_GREEN
    + r"""
 ____    _    __  __    ____ _     ___   _____ _   _ _____ ______   ______   ___ ___ _   _ _____
/ ___|  / \  |  \/  |  / ___| |   |_ _| | ____| \ | |_   _|  _ \ \ / /  _ \ / _ \_ _| \ | |_   _|
\___ \ / _ \ | |\/| | | |   | |    | |  |  _| |  \| | | | | |_) \ V /| |_) | | | | ||  \| | | |
 ___) / ___ \| |  | | | |___| |___ | |  | |___| |\  | | | |  _ < | | |  __/| |_| | || |\  | | |
|____/_/   \_\_|  |_|  \____|_____|___| |_____|_| \_| |_| |_| \_\|_| |_|    \___/___|_| \_| |_|
"""
    + _RESET
)

# Rich console for markdown rendering
_solace_theme = Theme({
    "markdown.h1": "bold rgb(0,200,149)",
    "markdown.h2": "bold rgb(0,200,149)",
    "markdown.h3": "bold rgb(0,200,149)",
    "markdown.code": "dim white on grey11",
    "markdown.item.bullet": "rgb(0,200,149)",
})
_console = Console(theme=_solace_theme, highlight=False)

# Slash command auto-completion
_COMMANDS = [
    "/new", "/sessions", "/switch", "/rename", "/delete",
    "/agents", "/upload", "/artifacts", "/download",
    "/help", "/quit", "/exit",
    # TODO: Re-enable /feedback when BaseGatewayComponent exposes a feedback API
]

# Commands whose first argument should complete with session labels
_SESSION_ARG_COMMANDS = {"/switch", "/delete"}


_MULTI_SELECT_SENTINEL = "--interactive-multi-select--"


class _CliCompleter(Completer):
    """Dynamic completer: command names first, then session labels or artifact names."""

    def __init__(self):
        self._session_store: Optional[SessionStore] = None
        self._artifact_cache: List[str] = []

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor.lstrip()
        if " " not in text:
            for cmd in _COMMANDS:
                if cmd.startswith(text):
                    yield Completion(cmd, start_position=-len(text))
            return
        cmd, _, partial = text.partition(" ")
        partial = partial.lstrip()
        if cmd in _SESSION_ARG_COMMANDS and self._session_store:
            for session in self._session_store.list_sessions():
                label = session.get("label")
                if label and label.startswith(partial):
                    yield Completion(label, start_position=-len(partial))
        elif cmd == "/download" and self._artifact_cache:
            # Offer multi-select as the first option
            if _MULTI_SELECT_SENTINEL.startswith(partial) or not partial:
                yield Completion(_MULTI_SELECT_SENTINEL, start_position=-len(partial))
            for name in self._artifact_cache:
                if name.startswith(partial):
                    yield Completion(name, start_position=-len(partial))


info = {
    "class_name": "CliEntrypointComponent",
    "description": "Terminal REPL component for the CLI Entrypoint gateway.",
    "config_parameters": [],
    "input_schema": {"type": "object", "properties": {}},
    "output_schema": {"type": "object", "properties": {}},
}


class CliEntrypointComponent(BaseGatewayComponent):
    """A terminal-based entrypoint component for Solace Agent Mesh."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        log.info("%s Initializing CLI Entrypoint Component...", self.log_identifier)

        # Read adapter config
        adapter_config = self.get_config("adapter_config", {})
        self._prompt_name = adapter_config.get("prompt_name", "sam")
        self._user_id = adapter_config.get("user_id", "cli_entrypoint_user")
        self._show_status_updates = adapter_config.get("show_status_updates", True)
        self._default_agent = self.get_config("default_agent_name", "OrchestratorAgent")

        # REPL state — _response_event created in _start_listener on the correct event loop
        self._response_event: Optional[asyncio.Event] = None
        self._current_response_text: str = ""
        self._is_first_chunk: bool = True
        self._current_task_id: Optional[str] = None
        self._last_task_id: Optional[str] = None
        self._last_session_id: Optional[str] = None
        self._prompt_session: Optional[PromptSession] = None

        # Session management
        self._session_store: Optional[SessionStore] = None

        log.info("%s CLI Entrypoint Component initialized.", self.log_identifier)

    # --- Abstract method implementations ---

    async def _extract_initial_claims(self, external_event_data: Any) -> Optional[Dict[str, Any]]:
        """Return claims for the CLI user."""
        return {"id": self._user_id, "name": self._user_id, "source": "cli"}

    def _is_standalone_launch(self) -> bool:
        """Detect if this gateway was launched as its own `sam run` process."""
        if self.connector and hasattr(self.connector, "apps"):
            return len(self.connector.apps) == 1
        return False

    def _start_listener(self) -> None:
        """Start the REPL loop. Called by BaseGatewayComponent.run()."""
        if not self._is_standalone_launch():
            log.info(
                "%s CLI entrypoint loaded but not started — "
                "launch it in its own process with: sam run configs/gateways/cli-entrypoint.yaml",
                self.log_identifier,
            )
            return
        log.info("%s Starting CLI listener (REPL)...", self.log_identifier)

        # Initialize session store
        self._session_store = SessionStore(entrypoint_id=self.gateway_id)
        default_id = self._default_session_id()
        if not self._session_store.get(default_id):
            self._session_store.create(default_id, label="default")
        stored_active = self._session_store.active_session
        if not stored_active or not self._session_store.get(stored_active):
            self._session_store.active_session = default_id

        active_id = self._session_store.active_session
        active_meta = self._session_store.get(active_id) or {}
        active_label = active_meta.get("label") or active_id

        # Print banner
        g = _SOLACE_GREEN
        r = _RESET
        print(BANNER)
        print(f"  {g}Entrypoint ID:{r}  {self.gateway_id}")
        print(f"  {g}Namespace:{r}     {self.namespace}")
        print(f"  {g}User:{r}          {self._user_id}")
        print(f"  {g}Session:{r}       {active_label}")
        print()
        print(f"  Type a message to chat with SAM agents.")
        print(f"  Type {g}/help{r} for available commands.")
        print()

        # Create the response event on the component's async event loop
        loop = self.get_async_loop()
        if loop:
            self._response_event = asyncio.Event()
            asyncio.run_coroutine_threadsafe(self._repl_loop(), loop)
        else:
            log.error("%s No async loop available to start REPL.", self.log_identifier)

    def _stop_listener(self) -> None:
        """Stop the REPL loop. Called by BaseGatewayComponent.cleanup().

        The REPL coroutine is cancelled automatically when the event loop shuts down.
        The stdin-blocking thread (prompt_toolkit) is terminated by the SIGTERM
        that _shutdown() schedules.
        """
        log.info("%s Stopping CLI listener...", self.log_identifier)

    async def _translate_external_input(
        self, external_event: Any
    ) -> Tuple[str, List[A2APart], Dict[str, Any]]:
        """Convert CLI input dict to A2A parts and context."""
        text = external_event.get("text", "")
        session_id = external_event.get("session_id", "cli-default")
        target_agent = external_event.get("target_agent", self._default_agent)
        a2a_parts: List[A2APart] = []
        if text:
            a2a_parts.append(TextPart(text=text))

        external_request_context = {
            "app_name_for_artifacts": self.gateway_id,
            "user_id_for_artifacts": self._user_id,
            "a2a_session_id": session_id,
            "user_id_for_a2a": self._user_id,
            "target_agent_name": target_agent,
        }

        return target_agent, a2a_parts, external_request_context

    async def _send_update_to_external(
        self,
        external_request_context: Dict[str, Any],
        event_data: Union[TaskStatusUpdateEvent, TaskArtifactUpdateEvent],
        is_final_chunk_of_update: bool,
    ) -> None:
        """Handle streaming status and artifact updates from agents."""
        if isinstance(event_data, TaskStatusUpdateEvent):
            # Extract text from status update
            status = event_data.status
            if status and status.message and status.message.parts:
                for part_wrapper in status.message.parts:
                    # Parts are wrapped in a2a.types.Part (RootModel) — unwrap via .root
                    part = getattr(part_wrapper, "root", part_wrapper)
                    if isinstance(part, TextPart) and part.text:
                        # Accumulate text chunks
                        if self._is_first_chunk:
                            sys.stdout.write(f"\n{_SOLACE_GREEN}  Receiving...{_RESET}")
                            sys.stdout.flush()
                            self._is_first_chunk = False
                        self._current_response_text += part.text
                    elif isinstance(part, DataPart) and part.data:
                        # Status updates (agent progress)
                        data = part.data
                        if isinstance(data, dict):
                            # Handle both formats: SAM's agent_progress_update and legacy agent_status
                            data_type = data.get("type", "")
                            if data_type in ("agent_progress_update", "agent_status"):
                                status_text = data.get("status_text") or data.get("text", "")
                                if self._show_status_updates and status_text:
                                    print(f"\n\033[90m  [{status_text}]\033[0m", end="", flush=True)

        elif isinstance(event_data, TaskArtifactUpdateEvent):
            # File artifact notification
            if event_data.artifact and event_data.artifact.parts:
                for part_wrapper in event_data.artifact.parts:
                    part = getattr(part_wrapper, "root", part_wrapper)
                    if isinstance(part, FilePart) and part.file:
                        name = part.file.name or "unnamed"
                        mime = getattr(part.file, "mime_type", None) or "unknown"
                        uri = getattr(part.file, "uri", "") or ""
                        if uri:
                            print(f"\n  📎 File: {name} ({mime}) — {uri}")
                        else:
                            print(f"\n  📎 File: {name} ({mime})")

    async def _send_final_response_to_external(
        self, external_request_context: Dict[str, Any], task_data: Task
    ) -> None:
        """Render final response as markdown in the terminal."""
        # Clear the "Receiving..." line
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()

        # Extract any remaining text from the final task
        final_text = self._current_response_text
        if task_data.status and task_data.status.message and task_data.status.message.parts:
            for part_wrapper in task_data.status.message.parts:
                part = getattr(part_wrapper, "root", part_wrapper)
                if isinstance(part, TextPart) and part.text:
                    # Only add if not already accumulated via streaming
                    if not final_text:
                        final_text = part.text

        if final_text:
            print()
            _console.print(Markdown(final_text))
        print()

        # Track for /feedback
        task_id = task_data.id
        session_id = external_request_context.get("a2a_session_id")
        self._last_task_id = task_id
        self._last_session_id = session_id
        self._current_task_id = None
        self._current_response_text = ""
        self._is_first_chunk = True
        self._response_event.set()

        # Refresh artifact cache after each response (agent may have created artifacts)
        if session_id:
            await self._refresh_artifact_cache(session_id)

    async def _send_error_to_external(
        self, external_request_context: Dict[str, Any], error_data: JSONRPCError
    ) -> None:
        """Display errors in the terminal."""
        code = error_data.code if error_data.code else "unknown"
        message = error_data.message if error_data.message else "Unknown error"
        print(f"\n\033[91m  Error [{code}]: {message}\033[0m\n")

        self._last_task_id = external_request_context.get("a2a_task_id_for_event")
        self._last_session_id = external_request_context.get("a2a_session_id")
        self._current_task_id = None
        self._current_response_text = ""
        self._is_first_chunk = True
        self._response_event.set()

    # --- Session helpers ---

    def _default_session_id(self) -> str:
        return f"{self.gateway_id}__default"

    def _new_session_id(self) -> str:
        return f"{self.gateway_id}__cli-{uuid.uuid4().hex[:8]}"

    # --- REPL Loop ---

    def _build_prompt(self, session_id: str) -> HTML:
        """Build the prompt with the current session label or short ID."""
        meta = (self._session_store.get(session_id) or {}) if self._session_store else {}
        label = meta.get("label")
        if not label:
            label = session_id.split("__")[-1] if "__" in session_id else session_id[-12:]
        safe_name = html_mod.escape(self._prompt_name)
        safe_label = html_mod.escape(label)
        return HTML('<style fg="#00C895" bold="true">{}</style> [{}]&gt; '.format(safe_name, safe_label))

    async def _repl_loop(self) -> None:
        """Run the interactive read-eval-print loop."""
        session_id = self._session_store.active_session or self._default_session_id()
        loop = asyncio.get_running_loop()

        completer = _CliCompleter()
        completer._session_store = self._session_store
        self._completer = completer
        self._prompt_session = PromptSession(
            completer=completer,
            complete_while_typing=True,
        )

        # Seed artifact cache for the initial session
        await self._refresh_artifact_cache(session_id)

        while True:
            try:
                current_prompt = self._build_prompt(session_id)
                line = await loop.run_in_executor(
                    None, lambda: self._prompt_session.prompt(current_prompt)
                )
                line = line.strip()

                if not line:
                    continue

                # Handle CLI commands
                if line.startswith("/"):
                    result = await self._handle_command(line, session_id)
                    if result == "exit":
                        break
                    if isinstance(result, str) and result.startswith("new_session:"):
                        session_id = result.split(":", 1)[1]
                        self._session_store.active_session = session_id
                        await self._refresh_artifact_cache(session_id)
                    continue

                # Catch bare exit/quit
                if line.lower() in ("exit", "quit"):
                    confirm = await loop.run_in_executor(
                        None,
                        lambda: pt_prompt("  Did you mean /quit? [Y/n] "),
                    )
                    if confirm.strip().lower() in ("", "y", "yes"):
                        self._shutdown("Goodbye!")
                        return
                    continue

                # Reset response state and submit to SAM
                self._response_event.clear()
                self._current_response_text = ""
                self._is_first_chunk = True
                self._current_task_id = None

                external_event = {
                    "text": line,
                    "session_id": session_id,
                    "target_agent": self._default_agent,
                }

                try:
                    # Authenticate
                    user_identity = await self.authenticate_and_enrich_user(external_event)
                    if not user_identity:
                        print("\033[91m  Authentication failed.\033[0m\n")
                        continue

                    # Translate input
                    target_agent, a2a_parts, ext_ctx = await self._translate_external_input(external_event)

                    # Submit task
                    task_id = await self.submit_a2a_task(
                        target_agent_name=target_agent,
                        a2a_parts=a2a_parts,
                        external_request_context=ext_ctx,
                        user_identity=user_identity,
                        is_streaming=True,
                    )
                    self._current_task_id = task_id
                    self._session_store.increment_message_count(session_id)
                except Exception as e:
                    print(f"\n\033[91m  Error submitting task: {e}\033[0m\n")
                    continue

                # Wait for response
                await self._wait_for_response()

            except EOFError:
                self._shutdown("Goodbye!")
                return
            except KeyboardInterrupt:
                self._shutdown("Goodbye!")
                return
            except asyncio.CancelledError:
                return
            except Exception as e:
                log.exception("Error in REPL loop: %s", e)
                print(f"\n\033[91m  Unexpected error: {e}\033[0m\n")

    async def _refresh_artifact_cache(self, session_id: str) -> None:
        """Refresh the cached artifact list for tab completion."""
        if not self.shared_artifact_service or not hasattr(self, "_completer"):
            return
        try:
            artifacts = await self.shared_artifact_service.list_artifact_keys(
                app_name=self.gateway_id,
                user_id=self._user_id,
                session_id=session_id,
            )
            self._completer._artifact_cache = [
                str(a) for a in artifacts if not str(a).endswith(".metadata.json")
            ]
        except Exception as e:
            log.debug("Failed to refresh artifact cache: %s", e)

    async def _wait_for_response(self) -> None:
        try:
            await asyncio.wait_for(self._response_event.wait(), timeout=600)
        except asyncio.TimeoutError:
            print("\n\033[93m  Response timed out (10m)\033[0m\n")
            # Reset state so next message doesn't inherit stale event
            self._response_event.clear()
            self._current_response_text = ""
            self._is_first_chunk = True
            self._current_task_id = None

    async def _handle_command(self, command: str, session_id: str) -> Optional[str]:
        try:
            tokens = shlex.split(command)
        except ValueError:
            tokens = command.split()
        cmd = tokens[0].lower()
        args = tokens[1:]

        # Resolve short/prefix commands (e.g. /s -> /sessions, /sw -> /switch)
        if cmd not in _COMMANDS:
            matches = [c for c in _COMMANDS if c.startswith(cmd)]
            if len(matches) == 1:
                cmd = matches[0]
            elif len(matches) > 1:
                print(f"\033[93m  Ambiguous command: {cmd} (matches: {', '.join(matches)})\033[0m\n")
                return None

        if cmd in ("/quit", "/exit", "/q"):
            self._shutdown("Goodbye!")
            return "exit"

        elif cmd == "/new":
            return self._cmd_new(args, session_id)

        elif cmd == "/sessions":
            await self._cmd_sessions(session_id)

        elif cmd == "/switch":
            return await self._cmd_switch(args, session_id)

        elif cmd == "/rename":
            self._cmd_rename(args, session_id)

        elif cmd == "/delete":
            self._cmd_delete(args, session_id)

        elif cmd == "/agents":
            self._cmd_agents()

        elif cmd == "/upload":
            await self._cmd_upload(args, session_id)

        elif cmd == "/artifacts":
            await self._cmd_artifacts(session_id)
            await self._refresh_artifact_cache(session_id)

        elif cmd == "/download":
            await self._cmd_download(args, session_id)

        # TODO: Re-enable /feedback when BaseGatewayComponent exposes a feedback API
        # elif cmd == "/feedback":
        #     await self._cmd_feedback(args, session_id)

        elif cmd == "/help":
            self._cmd_help()

        else:
            print(f"\033[93m  Unknown command: {cmd}. Type /help for available commands.\033[0m\n")

        return None

    # --- Command Implementations ---

    def _cmd_new(self, args: List[str], current_session_id: str) -> Optional[str]:
        label = args[0] if args else None
        if label and self._session_store.label_exists(label):
            print(f"\033[93m  A session with label \"{label}\" already exists. Use /switch {label} or pick a different name.\033[0m\n")
            return None
        new_id = self._new_session_id()
        self._session_store.create(new_id, label=label)
        display = label or new_id
        print(f"\033[92m  New session started: {display}\033[0m\n")
        return f"new_session:{new_id}"

    async def _cmd_sessions(self, current_session_id: str) -> None:
        sessions = self._session_store.list_sessions()
        if not sessions:
            print("\n  No sessions.\n")
            return
        print()
        for s in sessions:
            sid = s["id"]
            label = s.get("label")
            count = s.get("message_count", 0)
            last = s.get("last_active", "")
            age = self._format_age(last)
            marker = "*" if sid == current_session_id else " "
            short_id = sid.split("__")[-1] if "__" in sid else sid[-12:]

            # Get artifact count for this session
            artifact_count = 0
            if self.shared_artifact_service:
                try:
                    artifacts = await self.shared_artifact_service.list_artifact_keys(
                        app_name=self.gateway_id,
                        user_id=self._user_id,
                        session_id=sid,
                    )
                    artifact_count = len([a for a in artifacts if not str(a).endswith(".metadata.json")])
                except Exception:
                    pass

            stats = f"{count} msgs, {artifact_count} artifacts, {age}"
            if label:
                print(f"  {marker} {_BOLD}{label}{_RESET}  \033[90m[{short_id}]\033[0m  ({stats})")
            else:
                print(f"  {marker} {short_id}  ({stats})")
        print()

    async def _cmd_switch(self, args: List[str], current_session_id: str) -> Optional[str]:
        if not args:
            print("\033[93m  Usage: /switch <label|id>\033[0m\n")
            return None
        target = args[0]
        try:
            session_id = self._session_store.resolve(target)
        except ValueError as e:
            print(f"\033[93m  {e}\033[0m\n")
            return None
        if not session_id:
            print(f"\033[93m  No session found matching \"{target}\". Use /sessions to list.\033[0m\n")
            return None
        if session_id == current_session_id:
            print("\033[93m  Already in that session.\033[0m\n")
            return None
        meta = self._session_store.get(session_id) or {}
        display = meta.get("label") or session_id
        count = meta.get("message_count", 0)
        age = self._format_age(meta.get("last_active", ""))
        artifact_count = 0
        if self.shared_artifact_service:
            try:
                artifacts = await self.shared_artifact_service.list_artifact_keys(
                    app_name=self.gateway_id,
                    user_id=self._user_id,
                    session_id=session_id,
                )
                artifact_count = len([a for a in artifacts if not str(a).endswith(".metadata.json")])
            except Exception:
                pass
        stats = f"{count} msgs, {artifact_count} artifacts, {age}"
        print(f"\033[92m  Switched to: {display} ({stats})\033[0m\n")
        return f"new_session:{session_id}"

    def _cmd_rename(self, args: List[str], current_session_id: str) -> None:
        if not args:
            print("\033[93m  Usage: /rename <new-label>\033[0m\n")
            return
        new_label = args[0]
        if self._session_store.label_exists(new_label):
            print(f"\033[93m  A session with label \"{new_label}\" already exists.\033[0m\n")
            return
        self._session_store.update(current_session_id, label=new_label)
        print(f"\033[92m  Current session renamed to: {new_label}\033[0m\n")

    def _cmd_delete(self, args: List[str], current_session_id: str) -> None:
        if not args:
            print("\033[93m  Usage: /delete <label|id>\033[0m\n")
            return
        target = args[0]
        try:
            session_id = self._session_store.resolve(target)
        except ValueError as e:
            print(f"\033[93m  {e}\033[0m\n")
            return
        if not session_id:
            print(f"\033[93m  No session found matching \"{target}\".\033[0m\n")
            return
        if session_id == current_session_id:
            print("\033[93m  Cannot delete the active session. Switch to another session first.\033[0m\n")
            return
        if session_id == self._default_session_id():
            print("\033[93m  Cannot delete the default session.\033[0m\n")
            return
        meta = self._session_store.get(session_id) or {}
        display = meta.get("label") or session_id
        self._session_store.delete(session_id)
        print(f"\033[92m  Removed session \"{display}\" from local index.\033[0m")
        print(f"\033[90m  Note: Conversation history and artifacts remain on SAM's side.\033[0m\n")

    @staticmethod
    def _format_age(iso_timestamp: str) -> str:
        if not iso_timestamp:
            return "unknown"
        try:
            then = datetime.fromisoformat(iso_timestamp)
            now = datetime.now(timezone.utc)
            delta = now - then
            seconds = int(delta.total_seconds())
            if seconds < 60:
                return "just now"
            elif seconds < 3600:
                return f"{seconds // 60}m ago"
            elif seconds < 86400:
                return f"{seconds // 3600}h ago"
            else:
                return f"{seconds // 86400}d ago"
        except (ValueError, TypeError):
            return "unknown"

    def _cmd_agents(self) -> None:
        agent_names = self.agent_registry.get_agent_names()
        if agent_names:
            print("\n  Available agents:")
            for name in agent_names:
                agent = self.agent_registry.get_agent(name)
                desc = getattr(agent, "description", "") if agent else ""
                print(f"    \033[1m{name}\033[0m")
                if desc:
                    print(f"      {desc}")
            print()
        else:
            print("\n  No agents currently registered.\n")

    async def _cmd_upload(self, args: List[str], session_id: str) -> None:
        if not args:
            print("\033[93m  Usage: /upload <filepath> [message]\033[0m\n")
            return

        filepath = args[0]
        message = " ".join(args[1:]) if len(args) > 1 else ""

        filepath = os.path.expanduser(filepath)
        if not os.path.isabs(filepath):
            filepath = os.path.abspath(filepath)

        if not os.path.isfile(filepath):
            print(f"\033[91m  File not found: {filepath}\033[0m\n")
            return

        filename = os.path.basename(filepath)
        mime_type = mimetypes.guess_type(filepath)[0] or "application/octet-stream"
        try:
            with open(filepath, "rb") as f:
                content = f.read()
        except Exception as e:
            print(f"\033[91m  Error reading file: {e}\033[0m\n")
            return

        if len(content) > MAX_UPLOAD_BYTES:
            max_mb = MAX_UPLOAD_BYTES / (1024 * 1024)
            print(f"\033[91m  File too large. Maximum upload size is {max_mb:.0f} MB.\033[0m\n")
            return

        size_kb = len(content) / 1024
        print(f"\033[90m  Uploading {filename} ({mime_type}, {size_kb:.1f} KB)...\033[0m")

        # Save artifact and submit task
        self._response_event.clear()
        self._current_response_text = ""
        self._is_first_chunk = True
        self._current_task_id = None

        try:
            user_identity = await self.authenticate_and_enrich_user({})
            if not user_identity:
                print("\033[91m  Authentication failed.\033[0m\n")
                return

            a2a_parts: List[A2APart] = []

            # Save artifact to artifact service if available
            if self.shared_artifact_service:
                from solace_agent_mesh.agent.utils.artifact_helpers import save_artifact_with_metadata
                save_result = await save_artifact_with_metadata(
                    artifact_service=self.shared_artifact_service,
                    app_name=self.gateway_id,
                    user_id=self._user_id,
                    session_id=session_id,
                    filename=filename,
                    content_bytes=content,
                    mime_type=mime_type,
                    metadata_dict={
                        "source": "cli_gateway_upload",
                        "original_filename": filename,
                        "upload_timestamp_utc": datetime.now(timezone.utc).isoformat(),
                        "gateway_id": self.gateway_id,
                        "a2a_session_id": session_id,
                    },
                    timestamp=datetime.now(timezone.utc),
                )
                if save_result["status"] in ["success", "partial_success"]:
                    data_version = save_result.get("data_version", 0)
                    artifact_uri = f"artifact://{self.gateway_id}/{self._user_id}/{session_id}/{filename}?version={data_version}"
                    file_content = FileWithUri(
                        name=filename,
                        mime_type=mime_type,
                        uri=artifact_uri,
                    )
                    a2a_parts.append(FilePart(file=file_content))
                    message = (
                        f"The user uploaded the following file(s):\n"
                        f"- {filename} ({mime_type}, {len(content)} bytes, URI: {artifact_uri})\n\n"
                        f"User message: {message or f'I uploaded a file: {filename}'}"
                    )
                else:
                    print(f"\033[91m  Error saving artifact: {save_result.get('message')}\033[0m\n")
                    return
            else:
                message = message or f"I've uploaded a file: {filename}"

            if message:
                a2a_parts.append(TextPart(text=message))

            ext_ctx = {
                "app_name_for_artifacts": self.gateway_id,
                "user_id_for_artifacts": self._user_id,
                "a2a_session_id": session_id,
                "user_id_for_a2a": self._user_id,
                "target_agent_name": self._default_agent,
            }

            task_id = await self.submit_a2a_task(
                target_agent_name=self._default_agent,
                a2a_parts=a2a_parts,
                external_request_context=ext_ctx,
                user_identity=user_identity,
                is_streaming=True,
            )
            self._current_task_id = task_id
            self._session_store.increment_message_count(session_id)
        except Exception as e:
            print(f"\033[91m  Error uploading: {e}\033[0m\n")
            return

        await self._wait_for_response()

    async def _cmd_artifacts(self, session_id: str) -> None:
        """List artifacts in the current session."""
        if not self.shared_artifact_service:
            print("\033[93m  Artifact service not configured.\033[0m\n")
            return

        try:
            artifacts = await self.shared_artifact_service.list_artifact_keys(
                app_name=self.gateway_id,
                user_id=self._user_id,
                session_id=session_id,
            )
        except Exception as e:
            print(f"\033[91m  Error listing artifacts: {e}\033[0m\n")
            return

        # Filter out internal metadata files
        artifacts = [a for a in artifacts if not str(a).endswith(".metadata.json")]

        if not artifacts:
            print("\n  No artifacts in this session.\n")
            return

        print("\n  Artifacts:")
        for i, artifact_key in enumerate(artifacts, 1):
            print(f"    {i}. \033[1m{artifact_key}\033[0m")
        print()
        print("  Use /download to select and save, or /download <artifact> for a specific file.\n")

    async def _cmd_download(self, args: List[str], session_id: str) -> None:
        """Download artifacts to local disk."""
        if not self.shared_artifact_service:
            print("\033[93m  Artifact service not configured.\033[0m\n")
            return

        if args and args[0] != _MULTI_SELECT_SENTINEL:
            await self._download_artifact(session_id, args[0], args[1] if len(args) > 1 else args[0])
            return

        # Interactive mode
        try:
            artifacts = await self.shared_artifact_service.list_artifact_keys(
                app_name=self.gateway_id,
                user_id=self._user_id,
                session_id=session_id,
            )
        except Exception as e:
            print(f"\033[91m  Error listing artifacts: {e}\033[0m\n")
            return

        # Filter out internal metadata files
        artifacts = [a for a in artifacts if not str(a).endswith(".metadata.json")]

        if not artifacts:
            print("\n  No artifacts in this session.\n")
            return

        choices = []
        for artifact_key in artifacts:
            choices.append((str(artifact_key), str(artifact_key)))

        _dialog_style = PTStyle.from_dict({
            "dialog.body checkbox-list":           "bg:#093B5F #ffffff",
            "dialog.body checkbox-list checkbox":  "#ffffff",
            "dialog.body checkbox-list checkbox focused": "bg:#00C895 #000000 bold",
            "dialog.body checkbox-list checkbox checked": "#00C895 bold",
            "dialog.body checkbox-list checkbox checked focused": "bg:#00C895 #000000 bold",
        })

        loop = asyncio.get_running_loop()
        selected = await loop.run_in_executor(None, lambda: checkboxlist_dialog(
            title="Download Artifacts",
            text="Select artifacts to download (Space to toggle, Enter to confirm):",
            values=choices,
            style=_dialog_style,
        ).run())

        if not selected:
            print("  No artifacts selected.\n")
            return

        for filename in selected:
            await self._download_artifact(session_id, filename, filename)

    async def _download_artifact(self, session_id: str, filename: str, local_path: str) -> None:
        try:
            content = await self.shared_artifact_service.load_artifact(
                app_name=self.gateway_id,
                user_id=self._user_id,
                session_id=session_id,
                filename=filename,
            )
        except Exception as e:
            print(f"\033[91m  Error loading artifact '{filename}': {e}\033[0m")
            return

        if content is None:
            print(f"\033[91m  Artifact not found: {filename}\033[0m")
            return

        # Extract bytes from the Part returned by the artifact service.
        # load_artifact returns an adk_types.Part with inline_data (data + mime_type).
        inline_data = getattr(content, "inline_data", None)
        if inline_data is not None and hasattr(inline_data, "data"):
            data = inline_data.data if isinstance(inline_data.data, bytes) else str(inline_data.data).encode("utf-8")
        elif isinstance(content, bytes):
            data = content
        else:
            # Fallback for A2A part types
            part = getattr(content, "root", content)
            if isinstance(part, FilePart) and part.file:
                file_data = part.file
                if isinstance(file_data, FileWithBytes):
                    data = base64.b64decode(file_data.bytes)
                else:
                    print(f"\033[91m  Artifact '{filename}' is a URI reference, not downloadable content.\033[0m")
                    return
            elif isinstance(part, TextPart):
                data = part.text.encode("utf-8")
            else:
                data = str(content).encode("utf-8")

        local_path = os.path.expanduser(local_path)
        if not os.path.isabs(local_path):
            local_path = os.path.abspath(local_path)

        if os.path.exists(local_path):
            print(f"\033[93m  Overwriting: {local_path}\033[0m")

        try:
            os.makedirs(os.path.dirname(local_path) or ".", exist_ok=True)
            with open(local_path, "wb") as f:
                f.write(data)
            size = len(data)
            size_str = f"{size} bytes" if size < 1024 else f"{size / 1024:.1f} KB"
            print(f"\033[92m  Saved: {local_path} ({size_str})\033[0m")
        except Exception as e:
            print(f"\033[91m  Error saving '{filename}': {e}\033[0m")

    async def _cmd_feedback(self, args: List[str], session_id: str) -> None:
        if not args or args[0] not in ("up", "down"):
            print("\033[93m  Usage: /feedback up|down [comment]\033[0m\n")
            return

        if not self._last_task_id:
            print("\033[93m  No completed task to give feedback on.\033[0m\n")
            return

        rating = args[0]
        comment = " ".join(args[1:]) if len(args) > 1 else None

        # TODO: Implement feedback submission via new API when available
        icon = "\033[92m+1\033[0m" if rating == "up" else "\033[91m-1\033[0m"
        msg = f"  [{icon}] Feedback noted"
        if comment:
            msg += f" — \"{comment}\""
        print(msg + "\n")

    def _shutdown(self, message: str = "Goodbye!") -> None:
        print(message)
        log.info("CLI exit requested, scheduling SIGTERM for graceful shutdown.")
        loop = asyncio.get_running_loop()
        loop.call_later(0.5, os.kill, os.getpid(), signal.SIGTERM)

    def _cmd_help(self) -> None:
        print()
        print("  \033[1mChat\033[0m")
        print("    Just type a message to chat with SAM agents.")
        print()
        print("  \033[1mSessions\033[0m")
        print("    /new [label]                — Start a new session (optionally named)")
        print("    /sessions                   — List all sessions")
        print("    /switch <label|id>          — Switch to an existing session")
        print("    /rename <label>             — Rename the current session")
        print("    /delete <label|id>          — Remove a session from local index (history stays on SAM)")
        print()
        print("  \033[1mCommands\033[0m")
        print("    /agents                     — List registered agents")
        print("    /upload <file> [message]    — Send a file to an agent")
        print("    /artifacts                  — List agent-created files in this session")
        print("    /download [artifact] [path] — Save artifacts (interactive if no artifact given)")
        print("    /help                       — Show this help message")
        print("    /quit                       — Exit the CLI")
        print()
