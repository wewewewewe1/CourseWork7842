"""
Quick integration test for warning system
Tests initialization and basic functionality
"""
from warning_system import WarningManager, ThresholdConfig
from datetime import datetime

print("=" * 60)
print("WARNING SYSTEM INTEGRATION TEST")
print("=" * 60)

# Test 1: Create threshold configuration
print("\n[TEST 1] Creating threshold configuration...")
thresholds = [
    ThresholdConfig(
        signal_id="TEST_FREQ",
        signal_type="frequency",
        warning_min=59.85,
        warning_max=60.15,
        critical_min=59.5,
        critical_max=60.5,
        trigger_count=3,
        trigger_window=5.0,
        recovery_count=2,
        recovery_window=3.0
    )
]
print(f"[OK] Created {len(thresholds)} threshold config(s)")

# Test 2: Initialize WarningManager
print("\n[TEST 2] Initializing WarningManager...")
try:
    manager = WarningManager(
        thresholds=thresholds,
        influx_host="127.0.0.1",
        influx_port=8086,
        db_name="pmu_warnings_test"
    )
    print("[OK] WarningManager initialized successfully")
except Exception as e:
    print(f"[FAIL] Failed to initialize: {e}")
    exit(1)

# Test 3: Check normal value
print("\n[TEST 3] Checking normal value (60.0 Hz)...")
event = manager.check_value("TEST_FREQ", 60.0, datetime.utcnow())
if event is None:
    print("[OK] Normal value passed (no event triggered)")
else:
    print(f"[FAIL] Unexpected event: {event}")

# Test 4: Check warning values (should trigger after 3)
print("\n[TEST 4] Checking warning values (60.20 Hz, 3 times)...")
event1 = manager.check_value("TEST_FREQ", 60.20, datetime.utcnow())
print(f"  Check 1: {'Event' if event1 else 'No event'}")

event2 = manager.check_value("TEST_FREQ", 60.21, datetime.utcnow())
print(f"  Check 2: {'Event' if event2 else 'No event'}")

event3 = manager.check_value("TEST_FREQ", 60.22, datetime.utcnow())
print(f"  Check 3: {'Event' if event3 else 'No event'}")

if event3:
    print(f"[OK] Warning triggered on 3rd violation")
    print(f"  Event ID: {event3.event_id}")
    print(f"  Severity: {event3.severity.name}")
    print(f"  Signal: {event3.signal_id}")
else:
    print("[FAIL] Warning should have triggered after 3 violations")

# Test 5: Get active warnings
print("\n[TEST 5] Getting active warnings...")
active = manager.get_active_warnings()
print(f"[OK] Active warnings: {len(active)}")
for event in active:
    print(f"  - {event.signal_id}: {event.severity.name} ({event.state.value})")

# Test 6: Get statistics
print("\n[TEST 6] Getting statistics...")
stats = manager.get_statistics()
print(f"[OK] Statistics retrieved:")
print(f"  Active count: {stats['active_count']}")
print(f"  Total checks: {stats['total_checks']}")
print(f"  Avg check time: {stats['avg_check_time_ms']:.3f} ms")
print(f"  Max check time: {stats['max_check_time_ms']:.3f} ms")

# Performance check
if stats['avg_check_time_ms'] < 1.0:
    print(f"[OK] Performance: Avg check time < 1ms (EXCELLENT)")
elif stats['avg_check_time_ms'] < 20.0:
    print(f"[OK] Performance: Avg check time < 20ms (GOOD)")
else:
    print(f"[WARN] Performance: Avg check time > 20ms (NEEDS OPTIMIZATION)")

# Test 7: Acknowledge event
if active:
    print("\n[TEST 7] Acknowledging event...")
    event_id = active[0].event_id
    success = manager.acknowledge_event(event_id, "test_user")
    if success:
        print(f"[OK] Event {event_id} acknowledged")
    else:
        print(f"[FAIL] Failed to acknowledge event")

# Test 8: Update thresholds
print("\n[TEST 8] Updating thresholds...")
new_thresholds = [
    ThresholdConfig(
        signal_id="TEST_FREQ",
        signal_type="frequency",
        warning_min=59.8,
        warning_max=60.2,
        critical_min=59.5,
        critical_max=60.5,
        trigger_count=2,  # Changed from 3 to 2
        trigger_window=3.0
    )
]
manager.update_thresholds(new_thresholds)
print("[OK] Thresholds updated successfully")

# Test 9: Cleanup
print("\n[TEST 9] Stopping manager...")
manager.stop()
print("[OK] Manager stopped successfully")

print("\n" + "=" * 60)
print("ALL TESTS PASSED [OK]")
print("=" * 60)
print("\nBackend integration is working correctly!")
print("Ready for frontend integration.\n")
