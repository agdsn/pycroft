from datetime import datetime, date


def parse_iso_date(date_str: str) -> date:
    return datetime.strptime(date_str, '%Y-%m-%d').date()
