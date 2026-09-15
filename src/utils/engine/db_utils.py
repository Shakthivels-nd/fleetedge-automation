import os
import time
from datetime import datetime, timedelta

import psycopg2
from psycopg2 import OperationalError, ProgrammingError

from ..logger import setup_logger

logger = setup_logger()

DB_CONFIG = {
    "host": os.getenv("HOST", "host.info"),
    "dbname": os.getenv("DB_NAME", "database-name"),
    "user": os.getenv("DB_USER", "username"),
    "password": os.getenv("DB_PASSWORD", "password"),
    "port": os.getenv("DB_PORT", 5432)
}
DB_CONFIG_2 = {
    "host": os.getenv("HOST_2", os.getenv("HOST_2", "host.info")),
    "dbname": os.getenv("DB_NAME", os.getenv("DB_NAME", "database-name")),
    "user": os.getenv("DB_USER", os.getenv("DB_USER", "username")),
    "password": os.getenv("DB_PASSWORD", os.getenv("DB_PASSWORD", "password")),
    "port": int(os.getenv("DB_PORT", 5432)),
}


def run_postgresql_query(query: str, params: tuple = ()):
    """
    Run a PostgreSQL query using the DB_CONFIG settings.
    Returns fetched rows for SELECT queries, or None otherwise.
    """
    try:
        print("Connecting to the database...")
        with psycopg2.connect(**DB_CONFIG) as conn:
            conn.autocommit = True  # avoids 'transaction already closed' issues
            with conn.cursor() as cur:
                # Optional: use sql module to safely format query (if needed)
                # cur.execute("SET statement_timeout = 30000")
                cur.execute(query, params or ())
                print("Query executed successfully.")

                if query.strip().lower().startswith("select"):
                    try:
                        rows = cur.fetchall()
                        return rows
                    except psycopg2.ProgrammingError:
                        # In case no result set is returned
                        return []
                else:
                    return None

    except (OperationalError, ProgrammingError) as e:
        logger.error(f"Database operational error: {e}")
        print(f"Database operational error: {e}")
        return None
    except Exception as e:
        logger.error(f"Database query failed: {e}", exc_info=True)
        print(f"Database query failed: {e}")
        return None

def wait_for_postgresql_result(query: str, params: tuple = (), timeout: int = 300, interval: int = 10):
    """
    Repeatedly executes a PostgreSQL query until it returns non-empty results or the timeout expires.

    Args:
        query: SQL query string.
        params: Query parameters as a tuple.
        timeout: Total wait time in seconds before failing.
        interval: Delay between retries in seconds.

    Returns:
        List of fetched rows if found; otherwise raises pytest failure.
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        rows = run_postgresql_query(query, params)
        if rows:
            print(f"Found {len(rows)} record(s) for {params} in database.")
            return rows
        print(f"No matching records yet. Retrying in {interval}s...")
        time.sleep(interval)
    print(f"Timeout reached. No records found for {params} in database.")
    return None

def fetch_api_calls_window(device_id: str, msg_id: int, minutes_before: int = 30, minutes_after: int = 30,
                           poll: bool = False, timeout: int = 120, interval: int = 10):
    """
    Fetch ndrequest_audit_log rows for device_id in a time window:
    [now - minutes_before, now + minutes_after).
    Args:
        device_id: target device_id (string).
        minutes_before: window start offset (default 30).
        minutes_after: window end offset (default 30).
        poll: whether to poll until at least one row appears.
        timeout: total seconds for polling.
        interval: seconds between retries.
    Returns dict: {status, count, start_time, end_time, rows, details}
    """
    details = []
    if not device_id:
        return {"status": "Fail", "count": 0, "start_time": None, "end_time": None, "rows": [], "details": ["device_id required"]}

    now_utc = datetime.utcnow()
    start_dt = now_utc - timedelta(minutes=minutes_before)
    end_dt = now_utc + timedelta(minutes=minutes_after)
    start_str = start_dt.strftime("%Y-%m-%d %H:%M:%S")
    end_str = end_dt.strftime("%Y-%m-%d %H:%M:%S")
    details.append(f"Window: {start_str} <= time_stamp < {end_str}")

    query = """
        SELECT
            device_id AS device_id,
            session_id AS session_id,
            time_stamp AS timestamp,
            msg_id AS msg_id
        FROM ndrequest_audit_log
        WHERE device_id = %s
          AND time_stamp >= %s
          AND time_stamp < %s
          AND msg_id = %s;
    """
    params = (device_id, start_str, end_str, msg_id)

    def _exec():
        try:
            with psycopg2.connect(**DB_CONFIG_2) as conn:
                conn.autocommit = True
                with conn.cursor() as cur:
                    cur.execute(query, params)
                    return cur.fetchall()
        except Exception as e:
            details.append(f"DB error: {e}")
            return None

    rows = None
    if poll:
        deadline = time.time() + timeout
        while time.time() < deadline:
            rows = _exec()
            if rows:
                break
            details.append(f"No rows yet; retry in {interval}s")
            time.sleep(interval)
    else:
        rows = _exec()

    if not rows:
        return {
            "status": "Fail",
            "count": 0,
            "start_time": start_str,
            "end_time": end_str,
            "rows": [],
            "details": details or ["No records found"]
        }

    mapped = [{
        "device_id": r[0],
        "session_id": r[1],
        "timestamp": (r[2].strftime("%Y-%m-%d %H:%M:%S") if hasattr(r[2], "strftime") else str(r[2])),
        "msg_id": r[3]
    } for r in rows]

    details.append(f"Fetched {len(mapped)} row(s) from HOST_2")
    return {
        "status": "Pass",
        "count": len(mapped),
        "start_time": start_str,
        "end_time": end_str,
        "rows": mapped,
        "details": details
    }
