import json
from datetime import datetime

import pandas as pd


def log_action(conn, c, user_id, action, table_name, record_id=None, details=None):
    """Insert a record into the audit log."""
    timestamp = datetime.utcnow().replace(second=0, microsecond=0).isoformat(timespec="minutes")
    c.execute(
        """INSERT INTO audit_log (user_id, action, table_name, record_id, timestamp, details)
               VALUES (?, ?, ?, ?, ?, ?)""",
        (
            user_id,
            action,
            table_name,
            record_id,
            timestamp,
            json.dumps(details) if details is not None else None,
        ),
    )
    conn.commit()


def fetch_logs(conn, c, imone: str | None = None) -> pd.DataFrame:
    """Return audit log entries as a DataFrame."""
    query = (
        "SELECT al.id, u.username as user, al.action, al.table_name, al.record_id,"
        " al.timestamp, al.details FROM audit_log al LEFT JOIN users u ON al.user_id = u.id"
    )
    params = ()
    if imone is not None:
        query += " WHERE u.imone = ?"
        params = (imone,)
    query += " ORDER BY al.timestamp DESC"
    df = pd.read_sql_query(query, conn, params=params)

    def parse_details(val: str) -> str:
        if not val:
            return ""
        try:
            obj = json.loads(val)
            return json.dumps(obj, ensure_ascii=False)
        except Exception:
            return str(val)

    if not df.empty:
        df["details"] = df["details"].apply(parse_details)
    return df


