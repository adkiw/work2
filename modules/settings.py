

DEFAULT_CATEGORY = "Numatytas priekabos tipas"


def get_default_trailer_types(c, imone: str) -> list[str]:
    """Return ordered list of default trailer types for a company."""
    rows = c.execute(
        "SELECT reiksme FROM company_default_trailers WHERE imone=? ORDER BY priority",
        (imone,),
    ).fetchall()
    return [r[0] for r in rows]


def set_default_trailer_types(conn, c, imone: str, values: list[str]) -> None:
    """Replace company's default trailer type list with the given values."""
    c.execute("DELETE FROM company_default_trailers WHERE imone=?", (imone,))
    for pr, val in enumerate(values):
        c.execute(
            "INSERT INTO company_default_trailers (imone, reiksme, priority) VALUES (?,?,?)",
            (imone, val, pr),
        )
    conn.commit()



