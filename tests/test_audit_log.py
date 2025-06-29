from db import init_db
from modules.audit import log_action


def test_audit_log_table_exists(tmp_path):
    db_file = tmp_path / "audit.db"
    conn, c = init_db(str(db_file))
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_log'")
    assert c.fetchone() is not None


def test_log_action_inserts_row(tmp_path):
    db_file = tmp_path / "audit_insert.db"
    conn, c = init_db(str(db_file))
    log_action(conn, c, 1, "insert", "tbl", 3, {"k": "v"})
    c.execute("SELECT action, table_name, record_id FROM audit_log")
    row = c.fetchone()
    assert row == ("insert", "tbl", 3)
