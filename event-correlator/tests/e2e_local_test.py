#!/usr/bin/env python3
"""
Local end-to-end test script.

Starts the event-correlator gateway with a real Solace broker,
publishes test events, and verifies correlation triggers fire.

Requirements:
  - Solace broker running on tcp://localhost:55554
  - SAM venv with event_correlator installed

Usage:
  python tests/e2e_local_test.py
"""

import json
import os
import signal
import subprocess
import sys
import tempfile
import time

# Minimal config for the E2E test (dev_mode: false = real broker)
E2E_CONFIG = """
log:
  stdout_log_level: INFO
  log_file_level: DEBUG
  log_file: /tmp/event-correlator-e2e.log

shared_config:
  - broker_connection: &broker_connection
      broker_url: tcp://localhost:55554
      broker_username: default
      broker_password: default
      broker_vpn: default

apps:
  - name: event-correlator-app
    app_module: event_correlator.app
    broker:
      <<: *broker_connection

    app_config:
      gateway_id: e2e-correlator-01
      namespace: "SAM/"
      artifact_service:
        type: "filesystem"
        base_path: "/tmp/sam-e2e-artifacts"
        artifact_scope: "namespace"

      data_plane_broker_config:
        broker_url: tcp://localhost:55554
        broker_vpn: default
        broker_username: default
        broker_password: default

      source_systems:
        - name: orders
          subscriptions:
            - topic: "acme/orders/>"
          correlation_key_extraction:
            method: "json_path"
            expression: "$.orderId"

        - name: payments
          subscriptions:
            - topic: "acme/payments/>"
            - topic: "acme/payment-updates/>"
          correlation_key_extraction:
            method: "json_path"
            expression: "$.orderId"

        - name: shipping
          subscriptions:
            - topic: "acme/shipping/>"
          correlation_key_extraction:
            method: "json_path"
            expression: "$.orderId"

      correlation_config:
        ttl_seconds: 300
        ttl_sweep_interval_ms: 10000
        ttl_expiry_action: "alert"
        trigger_rules:
          - type: "all_sources_present"
            required_sources: ["orders", "payments", "shipping"]
          - type: "immediate_on_source"
            source: "payments"
            topic_pattern: "acme/payment-updates/>"

      state_store:
        type: "in_memory"

      target_agent_name: "OrderReconciliationAgent"
      default_user_identity: "correlator-e2e"

      output_config:
        success_topic_pattern: "acme/correlator/results/{trade_id}"
        error_topic_pattern: "acme/correlator/errors/{trade_id}"
"""


def publish_events():
    """Publish test events to the broker."""
    from solace.messaging.messaging_service import MessagingService
    from solace.messaging.resources.topic import Topic

    props = {
        "solace.messaging.transport.host": "tcp://localhost:55554",
        "solace.messaging.service.vpn-name": "default",
        "solace.messaging.authentication.scheme.basic.username": "default",
        "solace.messaging.authentication.scheme.basic.password": "default",
    }
    service = MessagingService.builder().from_properties(props).build()
    service.connect()
    publisher = service.create_direct_message_publisher_builder().build()
    publisher.start()
    time.sleep(0.5)

    print("\n--- Publishing events for order ORD-12345 ---")

    # Event 1: Order placed
    order_event = json.dumps({
        "orderId": "ORD-12345",
        "customer": "ACME Corp",
        "amount": 2500.00,
        "items": ["widget-A", "gadget-B"],
    })
    publisher.publish(order_event, Topic.of("acme/orders/ORD-12345"))
    print("  [orders]    Published order event")
    time.sleep(0.5)

    # Event 2: Payment received
    payment_event = json.dumps({
        "orderId": "ORD-12345",
        "paymentId": "PAY-99887",
        "amount": 2500.00,
        "method": "wire_transfer",
    })
    publisher.publish(payment_event, Topic.of("acme/payments/ORD-12345"))
    print("  [payments]  Published payment event")
    time.sleep(0.5)

    # Event 3: Shipping dispatched → this completes the correlation!
    shipping_event = json.dumps({
        "orderId": "ORD-12345",
        "trackingId": "SHIP-44556",
        "carrier": "FedEx",
        "estimatedDelivery": "2024-04-01",
    })
    publisher.publish(shipping_event, Topic.of("acme/shipping/ORD-12345"))
    print("  [shipping]  Published shipping event → TRIGGER EXPECTED")
    time.sleep(1)

    # Event 4: Payment update for a different order (immediate trigger)
    print("\n--- Publishing payment update for ORD-67890 ---")
    update_event = json.dumps({
        "orderId": "ORD-67890",
        "updateType": "refund",
        "amount": -150.00,
        "reason": "partial_return",
    })
    publisher.publish(update_event, Topic.of("acme/payment-updates/ORD-67890"))
    print("  [payments]  Published payment update → IMMEDIATE TRIGGER EXPECTED")
    time.sleep(2)

    publisher.terminate()
    service.disconnect()


def main():
    # Write config to temp file
    config_file = tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", prefix="e2e_correlator_", delete=False
    )
    config_file.write(E2E_CONFIG)
    config_file.close()

    log_file = "/tmp/event-correlator-e2e.log"
    os.makedirs("/tmp/sam-e2e-artifacts", exist_ok=True)

    # Find SAM binary
    sam_bin = "/Users/raphaelcaillon/Documents/sam/sam2/venv/bin/solace-agent-mesh"
    if not os.path.exists(sam_bin):
        print(f"ERROR: SAM binary not found at {sam_bin}")
        sys.exit(1)

    print("=" * 60)
    print("EVENT CORRELATOR - LOCAL END-TO-END TEST")
    print("=" * 60)
    print(f"\nConfig: {config_file.name}")
    print(f"Log:    {log_file}")
    print(f"Broker: tcp://localhost:55554")

    # Start SAM
    print("\n[1] Starting SAM with event-correlator gateway...")
    env = os.environ.copy()
    env["LOGGING_CONFIG_PATH"] = ""
    proc = subprocess.Popen(
        [sam_bin, "run", config_file.name],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    time.sleep(10)

    if proc.poll() is not None:
        output = proc.stdout.read().decode() if proc.stdout else ""
        print(f"ERROR: SAM exited early. Output:\n{output[-2000:]}")
        sys.exit(1)

    print("    SAM is running (PID: %d)" % proc.pid)

    # Publish events
    print("\n[2] Publishing test events...")
    try:
        publish_events()
    except Exception as e:
        print(f"ERROR publishing: {e}")
        proc.send_signal(signal.SIGINT)
        proc.wait(timeout=10)
        sys.exit(1)

    # Give time for processing
    time.sleep(2)

    # Stop SAM
    print("\n[3] Stopping SAM...")
    proc.send_signal(signal.SIGINT)
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()

    # Check results
    print("\n[4] Checking results...")
    print("-" * 60)

    if not os.path.exists(log_file):
        print("WARNING: Log file not found, checking stdout...")
        output = proc.stdout.read().decode() if proc.stdout else ""
        lines = output.split("\n")
    else:
        with open(log_file) as f:
            lines = f.readlines()

    # Look for key events
    events_received = [l for l in lines if "Event received" in l]
    triggers_fired = [l for l in lines if "TRIGGER FIRED" in l]
    subscribed = [l for l in lines if "Subscribed to" in l]
    errors = [l for l in lines if "ERROR" in l and "PermissionError" not in l]

    print(f"\nSubscriptions:     {len(subscribed)}")
    for s in subscribed:
        print(f"  {s.strip()}")

    print(f"\nEvents received:   {len(events_received)}")
    for e in events_received:
        print(f"  {e.strip()}")

    print(f"\nTriggers fired:    {len(triggers_fired)}")
    for t in triggers_fired:
        print(f"  {t.strip()}")

    if errors:
        print(f"\nErrors (non-auth): {len(errors)}")
        for e in errors[:5]:
            print(f"  {e.strip()}")

    # Validate
    print("\n" + "=" * 60)
    success = True

    if len(subscribed) >= 4:
        print("✓ All topic subscriptions established")
    else:
        print("✗ Missing subscriptions")
        success = False

    if len(events_received) >= 4:
        print("✓ All 4 events received from broker")
    else:
        print(f"✗ Expected 4 events, got {len(events_received)}")
        success = False

    if len(triggers_fired) >= 2:
        print("✓ Both trigger rules fired (all_sources_present + immediate_on_source)")
    else:
        print(f"✗ Expected 2 triggers, got {len(triggers_fired)}")
        success = False

    print("=" * 60)
    if success:
        print("RESULT: PASS ✓")
    else:
        print("RESULT: FAIL ✗")

    # Cleanup
    os.unlink(config_file.name)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
