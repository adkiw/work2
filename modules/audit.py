import json
import pandas as pd
import streamlit as st
from datetime import datetime


def log_action(conn, c, user_id, action, table_name, record_id=None, details=None):
    """Insert a record into the audit log."""
    c.execute(
        """INSERT INTO audit_log (user_id, action, table_name, record_id, timestamp, details)
               VALUES (?, ?, ?, ?, ?, ?)""",
        (
            user_id,
            action,
            table_name,
            record_id,
            datetime.utcnow().isoformat(),
            json.dumps(details) if details is not None else None,
        ),
    )
    conn.commit()


def show(conn, c):
    st.title("Audit log")
    df = pd.read_sql_query(
        """SELECT al.id, u.username as user, al.action, al.table_name, al.record_id,
                  al.timestamp, al.details
           FROM audit_log al LEFT JOIN users u ON al.user_id = u.id
           ORDER BY al.timestamp DESC""",
        conn,
    )
    if df.empty:
        st.info("Nėra įrašų")
    else:
        st.dataframe(df)
