"""CorrelatorComponent — Core gateway component for multi-source event correlation."""

from __future__ import annotations

import asyncio
import json
import logging
import queue
import uuid
from datetime import UTC, datetime
from typing import Any

from a2a.types import (
    DataPart,
    JSONRPCError,
    Task,
    TaskArtifactUpdateEvent,
    TaskStatusUpdateEvent,
    TextPart,
)
from solace_agent_mesh.gateway.base.component import BaseGatewayComponent
from solace_ai_connector.common.message import Message as SolaceMessage
from solace_ai_connector.components.component_base import ComponentBase

from .correlation_engine import CorrelationEngine
from .state_store import CorrelationState, create_state_store
from .trigger_rules import create_trigger_rules

log = logging.getLogger(__name__)

info = {
    "class_name": "CorrelatorComponent",
    "description": (
        "Event Correlator Gateway Component. "
        "Correlates events from multiple source systems and triggers an agent."
    ),
    "config_parameters": [],
    "input_schema": {"type": "object"},
    "output_schema": {"type": "object"},
}


class CorrelatorComponent(BaseGatewayComponent):
    """
    Gateway component that correlates trade events from multiple source systems
    and triggers a reconciliation agent when conditions are met.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            resolve_artifact_uris_in_gateway=False,
            supports_inline_artifact_resolution=False,
            filter_tool_data_parts=True,
            **kwargs,
        )

        # Load configuration
        self.data_plane_broker_config: dict[str, Any] = self.get_config(
            "data_plane_broker_config", {}
        )
        self.source_systems_config: list[dict[str, Any]] = self.get_config(
            "source_systems", []
        )
        self.correlation_config: dict[str, Any] = self.get_config(
            "correlation_config", {}
        )
        self.state_store_config: dict[str, Any] = self.get_config(
            "state_store", {"type": "in_memory"}
        )
        self.target_agent: str = self.get_config("target_agent_name", "ReconciliationAgent")
        self.default_user_identity_id: str = self.get_config(
            "default_user_identity", "event-correlator-service"
        )
        self.output_config: dict[str, str] = self.get_config("output_config", {})

        # Internal data plane resources
        self.data_plane_internal_app: Any | None = None
        self.data_plane_broker_input: Any | None = None
        self.data_plane_broker_output: Any | None = None
        self.data_plane_message_queue: queue.Queue = queue.Queue(maxsize=1000)
        self.data_plane_processor_task: asyncio.Task | None = None  # type: ignore[type-arg]
        self.data_plane_client_lock = asyncio.Lock()

        # Build source system topic → name mapping for fast lookup
        self._topic_to_source: list[tuple[str, str]] = []
        self._source_key_config: dict[str, dict[str, Any]] = {}
        for sys_cfg in self.source_systems_config:
            name = sys_cfg["name"]
            self._source_key_config[name] = sys_cfg.get("correlation_key_extraction", {})
            for sub in sys_cfg.get("subscriptions", []):
                self._topic_to_source.append((sub["topic"], name))

        # Correlation engine
        state_store = create_state_store(self.state_store_config)
        trigger_rules = create_trigger_rules(
            self.correlation_config.get("trigger_rules", [])
        )
        ttl_seconds = self.correlation_config.get("ttl_seconds", 86400)

        self.engine = CorrelationEngine(
            state_store=state_store,
            trigger_rules=trigger_rules,
            ttl_seconds=ttl_seconds,
            on_trigger=self._handle_trigger,
        )

        log.info(
            "%s CorrelatorComponent initialized. Sources: %s, Target agent: %s",
            self.log_identifier,
            [s["name"] for s in self.source_systems_config],
            self.target_agent,
        )

    # ===================================================================
    # Lifecycle
    # ===================================================================

    def _start_listener(self) -> None:
        log_id = f"{self.log_identifier}[StartListener]"
        log.info("%s Starting correlator listener...", log_id)

        async_loop = self.get_async_loop()
        if not async_loop:
            log.error("%s Async loop not available.", log_id)
            return

        async_loop.create_task(self._initialize_and_subscribe_data_plane())

        if self.data_plane_processor_task is None or self.data_plane_processor_task.done():
            self.data_plane_processor_task = async_loop.create_task(
                self._message_processor_loop()
            )

        # TTL sweep timer
        sweep_interval = self.correlation_config.get("ttl_sweep_interval_ms", 30000)
        self.add_timer(
            delay_ms=sweep_interval,
            timer_id=f"{self.gateway_id}_ttl_sweep",
            interval_ms=sweep_interval,
            callback=self._on_ttl_sweep,
        )
        log.info("%s Correlator listener started.", log_id)

    def _stop_listener(self) -> None:
        log_id = f"{self.log_identifier}[StopListener]"
        log.info("%s Stopping correlator listener...", log_id)

        self.cancel_timer(f"{self.gateway_id}_ttl_sweep")

        async_loop = self.get_async_loop()
        if async_loop and async_loop.is_running():
            if self.data_plane_internal_app:
                future = asyncio.run_coroutine_threadsafe(
                    self._stop_data_plane_client(), async_loop
                )
                try:
                    future.result(timeout=10)
                except Exception as e:
                    log.error("%s Error stopping data plane: %s", log_id, e)

            # Signal processor loop to stop
            import contextlib

            with contextlib.suppress(queue.Full):
                self.data_plane_message_queue.put_nowait(None)

            if self.data_plane_processor_task and not self.data_plane_processor_task.done():
                self.data_plane_processor_task.cancel()

        log.info("%s Correlator listener stopped.", log_id)

    # ===================================================================
    # Abstract method implementations
    # ===================================================================

    async def _extract_initial_claims(
        self, external_event_data: Any
    ) -> dict[str, Any] | None:
        return {"id": self.default_user_identity_id, "source": "correlator_service"}

    async def _translate_external_input(
        self, external_event: Any
    ) -> tuple[str, list, dict[str, Any]]:
        raise NotImplementedError(
            "Correlator does not use standard translate flow; "
            "messages are processed through the correlation engine."
        )

    async def _send_update_to_external(
        self,
        external_request_context: dict[str, Any],
        event_data: TaskStatusUpdateEvent | TaskArtifactUpdateEvent,
        is_final_chunk_of_update: bool,
    ) -> None:
        # Correlator doesn't forward intermediate updates
        pass

    async def _send_final_response_to_external(
        self, external_request_context: dict[str, Any], task_data: Task
    ) -> None:
        trade_id = external_request_context.get("trade_id", "unknown")
        trigger_name = external_request_context.get("trigger_name", "unknown")
        log.info(
            "%s Reconciliation completed for trade_id=%s, trigger=%s, status=%s",
            self.log_identifier,
            trade_id,
            trigger_name,
            task_data.status.state.value if task_data.status else "unknown",
        )

        # Publish result to output topic
        await self._publish_output(
            trade_id=trade_id,
            trigger_name=trigger_name,
            status="completed",
            response_data=self._extract_task_text(task_data),
        )

    async def _send_error_to_external(
        self, external_request_context: dict[str, Any], error_data: JSONRPCError
    ) -> None:
        trade_id = external_request_context.get("trade_id", "unknown")
        trigger_name = external_request_context.get("trigger_name", "unknown")
        log.error(
            "%s Reconciliation failed for trade_id=%s, trigger=%s, error=%s",
            self.log_identifier,
            trade_id,
            trigger_name,
            error_data.message if error_data else "unknown",
        )

        await self._publish_output(
            trade_id=trade_id,
            trigger_name=trigger_name,
            status="error",
            response_data=error_data.message if error_data else "unknown error",
        )

    # ===================================================================
    # Data Plane
    # ===================================================================

    async def _start_data_plane_client(self) -> None:
        log_id = f"{self.log_identifier}[DataPlane]"
        async with self.data_plane_client_lock:
            if self.data_plane_internal_app is not None:
                return

            if self.data_plane_broker_config.get("test_mode", False):
                log.info("%s Test mode — skipping data plane.", log_id)
                return

            log.info("%s Starting data plane client...", log_id)
            main_app = self.get_app()
            if not main_app or not hasattr(main_app, "connector") or not main_app.connector:
                raise RuntimeError("Main SAC App or Connector not available.")

            _forwarder_info = {
                "class_name": "EventForwarderComponent",
                "description": "Forwards SolaceMessages to correlator queue.",
                "config_parameters": [
                    {"name": "target_queue_ref", "required": True, "type": "queue.Queue"}
                ],
                "input_schema": {"type": "object"},
                "output_schema": None,
            }

            target_queue = self.data_plane_message_queue

            class EventForwarderComponent(ComponentBase):
                def __init__(self, **kw: Any) -> None:
                    super().__init__(_forwarder_info, **kw)
                    self.target_queue: queue.Queue = self.get_config("target_queue_ref")  # type: ignore[assignment]

                def invoke(self, message: SolaceMessage, data: dict[str, Any]) -> None:
                    try:
                        self.target_queue.put_nowait(message)
                        message.call_acknowledgements()
                    except queue.Full:
                        log.error("Correlator queue full. Message NACKed.")
                        message.call_negative_acknowledgements()
                    except Exception as e:
                        log.exception("Error forwarding to correlator queue: %s", e)
                        message.call_negative_acknowledgements()
                    return None  # type: ignore[return-value]

            broker_input_config = {
                "component_module": "broker_input",
                "component_name": f"{self.gateway_id}_dp_broker_input",
                "broker_queue_name": (
                    f"{self.namespace.strip('/')}/q/gdk/correlator/data/{self.gateway_id}/{uuid.uuid4().hex[:8]}"
                ),
                "create_queue_on_start": True,
                "temporary_queue": True,
                "component_config": {
                    **self.data_plane_broker_config,
                    "broker_subscriptions": [],
                    "payload_format": "text",
                },
            }
            forwarder_config = {
                "component_class": EventForwarderComponent,
                "component_name": f"{self.gateway_id}_dp_forwarder",
                "component_config": {"target_queue_ref": target_queue},
            }
            input_flow_config = {
                "name": f"{self.gateway_id}_dp_input_flow",
                "components": [broker_input_config, forwarder_config],
            }

            broker_output_config = {
                "component_module": "broker_output",
                "component_name": f"{self.gateway_id}_dp_broker_output",
                "component_config": {
                    **self.data_plane_broker_config,
                    "payload_format": "text",
                },
            }
            output_flow_config = {
                "name": f"{self.gateway_id}_dp_output_flow",
                "components": [broker_output_config],
            }

            self.data_plane_internal_app = main_app.connector.create_internal_app(
                app_name=f"{self.gateway_id}_dp_app",
                flows=[input_flow_config, output_flow_config],
            )
            if not self.data_plane_internal_app or not self.data_plane_internal_app.flows:
                raise RuntimeError("Failed to create internal data plane app.")

            self.data_plane_internal_app.run()

            # Get references to broker input/output components
            input_flow_name = input_flow_config["name"]
            input_flow = next(
                (f for f in self.data_plane_internal_app.flows if f.name == input_flow_name),
                None,
            )
            if input_flow and input_flow.component_groups:
                self.data_plane_broker_input = input_flow.component_groups[0][0]

            output_flow_name = output_flow_config["name"]
            output_flow = next(
                (f for f in self.data_plane_internal_app.flows if f.name == output_flow_name),
                None,
            )
            if output_flow and output_flow.component_groups:
                self.data_plane_broker_output = output_flow.component_groups[0][0]

            if not self.data_plane_broker_input or not self.data_plane_broker_output:
                raise RuntimeError("Failed to get data plane component references.")

            log.info("%s Data plane client started.", log_id)

    async def _stop_data_plane_client(self) -> None:
        async with self.data_plane_client_lock:
            if self.data_plane_internal_app:
                try:
                    self.data_plane_internal_app.cleanup()
                except Exception as e:
                    log.error("%s Error cleaning up data plane: %s", self.log_identifier, e)
                self.data_plane_internal_app = None
                self.data_plane_broker_input = None
                self.data_plane_broker_output = None

    async def _initialize_and_subscribe_data_plane(self) -> None:
        log_id = f"{self.log_identifier}[InitDataPlane]"
        log.info("%s Initializing data plane and adding subscriptions...", log_id)

        await self._start_data_plane_client()

        if not self.data_plane_broker_input:
            raise RuntimeError("Data plane BrokerInput not available.")

        topics: set[str] = set()
        for sys_cfg in self.source_systems_config:
            for sub in sys_cfg.get("subscriptions", []):
                topic = sub.get("topic")
                if topic:
                    topics.add(topic)

        for topic in topics:
            if not self.data_plane_broker_input.add_subscription(topic):
                log.error("%s Failed to subscribe to '%s'", log_id, topic)
            else:
                log.info("%s Subscribed to '%s'", log_id, topic)

    # ===================================================================
    # Message Processing
    # ===================================================================

    async def _message_processor_loop(self) -> None:
        log_id = f"{self.log_identifier}[Processor]"
        log.info("%s Message processor loop started.", log_id)
        loop = asyncio.get_running_loop()

        while not self.stop_signal.is_set():
            try:
                msg = await loop.run_in_executor(
                    None, self._queue_get_with_timeout
                )
                if msg is None:
                    break
                await self._handle_incoming_message(msg)
            except Exception:
                log.exception("%s Error in processor loop.", log_id)

        log.info("%s Message processor loop stopped.", log_id)

    def _queue_get_with_timeout(self) -> SolaceMessage | None:
        try:
            return self.data_plane_message_queue.get(timeout=1.0)
        except queue.Empty:
            return self.data_plane_message_queue  # sentinel that means "try again"

    async def _handle_incoming_message(self, msg: Any) -> None:
        # Skip non-message sentinels from queue timeout
        if msg is self.data_plane_message_queue:
            return

        topic = msg.get_topic()
        if not topic:
            log.warning("%s Received message with no topic, skipping.", self.log_identifier)
            return

        source_system = self._identify_source_system(topic)
        if not source_system:
            log.warning(
                "%s No source system matched for topic '%s'", self.log_identifier, topic
            )
            return

        payload = self._decode_payload(msg)
        trade_id = self._extract_correlation_key(payload, topic, source_system)
        if not trade_id:
            log.warning(
                "%s Could not extract trade_id from topic='%s' source='%s'",
                self.log_identifier,
                topic,
                source_system,
            )
            return

        log.info(
            "%s Event received: trade_id=%s, source=%s, topic=%s",
            self.log_identifier,
            trade_id,
            source_system,
            topic,
        )

        await self.engine.ingest_event(
            trade_id=trade_id,
            source_system=source_system,
            payload=payload,
            topic=topic,
            timestamp=datetime.now(UTC),
        )

    # ===================================================================
    # Source identification and key extraction
    # ===================================================================

    def _identify_source_system(self, topic: str) -> str | None:
        for pattern, source_name in self._topic_to_source:
            if self._topic_matches(topic, pattern):
                return source_name
        return None

    def _extract_correlation_key(
        self, payload: dict[str, Any], topic: str, source_system: str
    ) -> str | None:
        cfg = self._source_key_config.get(source_system, {})
        method = cfg.get("method", "json_path")

        if method == "topic_position":
            position = cfg.get("position", 3)
            parts = topic.split("/")
            if position < len(parts):
                return parts[position]
            return None

        # Default: json_path
        expression = cfg.get("expression", "$.tradeId")
        return self._evaluate_json_path(payload, expression)

    def _evaluate_json_path(self, payload: dict[str, Any], expression: str) -> str | None:
        try:
            from jsonpath_ng import parse

            matches = parse(expression).find(payload)
            if matches:
                return str(matches[0].value)
        except Exception as e:
            log.debug("JSONPath evaluation failed: %s", e)
        return None

    def _decode_payload(self, msg: SolaceMessage) -> dict[str, Any]:
        raw = msg.get_payload()
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, (str, bytes)):
            try:
                text = raw if isinstance(raw, str) else raw.decode("utf-8")
                return json.loads(text)  # type: ignore[no-any-return]
            except (json.JSONDecodeError, UnicodeDecodeError):
                text_val = raw if isinstance(raw, str) else raw.decode("utf-8", errors="replace")
                return {"_raw": text_val}
        return {"_raw": str(raw)}

    @staticmethod
    def _topic_matches(topic: str, pattern: str) -> bool:
        if pattern.endswith(">"):
            prefix = pattern[:-1]
            return topic.startswith(prefix)
        if "*" in pattern:
            pp = pattern.split("/")
            tp = topic.split("/")
            if len(pp) != len(tp):
                return False
            return all(a == "*" or a == b for a, b in zip(pp, tp, strict=True))
        return topic == pattern

    # ===================================================================
    # Trigger handling
    # ===================================================================

    async def _handle_trigger(
        self, trade_id: str, rule_name: str, state: CorrelationState
    ) -> None:
        log.info(
            "%s TRIGGER FIRED: trade_id=%s, rule=%s, sources=%s",
            self.log_identifier,
            trade_id,
            rule_name,
            list(state.events.keys()),
        )

        # Build A2A payload
        events_payload: dict[str, Any] = {}
        for source, event_record in state.events.items():
            events_payload[source] = {
                "payload": event_record.payload,
                "topic": event_record.topic,
                "timestamp": event_record.timestamp.isoformat(),
            }

        a2a_parts: list[Any] = [
            TextPart(text=f"Correlated event set ready for {trade_id} (trigger: {rule_name})"),
            DataPart(data={
                "trade_id": trade_id,
                "trigger_reason": rule_name,
                "correlation_state": events_payload,
            }),
        ]

        user_identity = {"id": self.default_user_identity_id, "source": "correlator"}
        session_id = f"recon-{trade_id}-{uuid.uuid4().hex[:8]}"

        external_request_context: dict[str, Any] = {
            "app_name_for_artifacts": self.gateway_id,
            "user_id_for_artifacts": self.default_user_identity_id,
            "a2a_session_id": session_id,
            "user_id_for_a2a": self.default_user_identity_id,
            "target_agent_name": self.target_agent,
            "trade_id": trade_id,
            "trigger_name": rule_name,
        }

        await self.submit_a2a_task(
            target_agent_name=self.target_agent,
            a2a_parts=a2a_parts,
            external_request_context=external_request_context,
            user_identity=user_identity,
            is_streaming=False,
        )

    # ===================================================================
    # Output publishing
    # ===================================================================

    async def _publish_output(
        self,
        trade_id: str,
        trigger_name: str,
        status: str,
        response_data: Any,
    ) -> None:
        if not self.data_plane_broker_output:
            log.warning("%s No broker output available for publishing.", self.log_identifier)
            return

        if status == "error":
            pattern = self.output_config.get(
                "error_topic_pattern", "correlator/errors/{trade_id}"
            )
        else:
            pattern = self.output_config.get(
                "success_topic_pattern", "correlator/results/{trade_id}"
            )

        topic = pattern.format(trade_id=trade_id)
        payload = json.dumps({
            "trade_id": trade_id,
            "trigger_reason": trigger_name,
            "status": status,
            "response": response_data,
            "timestamp": datetime.now(UTC).isoformat(),
        })

        try:
            self.data_plane_broker_output.send_message(
                topic=topic,
                payload=payload.encode("utf-8"),
            )
            log.info(
                "%s Published %s result to topic '%s' for trade_id=%s",
                self.log_identifier,
                status,
                topic,
                trade_id,
            )
        except Exception:
            log.exception(
                "%s Failed to publish result for trade_id=%s", self.log_identifier, trade_id
            )

    # ===================================================================
    # Helpers
    # ===================================================================

    def _extract_task_text(self, task_data: Task) -> str:
        if not task_data.status or not task_data.status.message:
            return ""
        parts = task_data.status.message.parts or []
        texts: list[str] = []
        for part in parts:
            if hasattr(part, "root") and isinstance(part.root, TextPart):
                texts.append(part.root.text)
            elif isinstance(part, TextPart):
                texts.append(part.text)
        return "\n".join(texts)

    def _on_ttl_sweep(self, timer_data: Any = None) -> None:
        async_loop = self.get_async_loop()
        if async_loop and async_loop.is_running():
            asyncio.run_coroutine_threadsafe(self._do_ttl_sweep(), async_loop)

    async def _do_ttl_sweep(self) -> None:
        expired = await self.engine.sweep_expired()
        if expired:
            expiry_action = self.correlation_config.get("ttl_expiry_action", "alert")
            if expiry_action == "alert":
                for trade_id in expired:
                    log.warning(
                        "%s Correlation expired: trade_id=%s",
                        self.log_identifier,
                        trade_id,
                    )
                    await self._publish_output(
                        trade_id=trade_id,
                        trigger_name="ttl_expiry",
                        status="expired",
                        response_data="Correlation window expired without all sources present.",
                    )
