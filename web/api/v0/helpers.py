from datetime import datetime


def parse_iso_date(date_str: str):
    return datetime.strptime(date_str, '%Y-%m-%d').date()
