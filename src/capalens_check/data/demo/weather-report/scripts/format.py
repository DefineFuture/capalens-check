"""Formats a forecast table (demo file; capalens-check lists it and never runs it)."""


def format_table(rows: list[tuple[str, float]]) -> str:
    return "\n".join(f"{day}: {high:.0f}" for day, high in rows)
