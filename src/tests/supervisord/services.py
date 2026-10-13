"""ND services the supervisord tests run against.

This is a copy of the list inside test_expected_services_running_itn2429 in
src/tests/test_sanity_functions.py (it is a variable inside that test, so it
cannot be imported). When services are added or removed, update both lists.
"""

EXPECTED_SERVICES = [
    "HealthStatsManager",
    "SendMetricgRPC",
    "analyticsService",
    "audioPlayback",
    "awsiot",
    "bagheera",
    "btfv",
    "circular_buffer",
    "cron",
    "inwardAnalyticsClient",
    "nd_fe_alerts",
    "nd_suspendresume",
    "nd_system_status",
    "outwardAnalyticsClient",
    "podlogger",
    "power_monitor",
    "scheduler_manager",
    "service_mon",
    "speed",
    "svc",
    "time_sync",
    "unifiedAnalyticsClient",
    "uploader",
]
