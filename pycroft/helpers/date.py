from datetime import timedelta


def diff_month(d1, d2):
    return (d1.year - d2.year) * 12 + d1.month - d2.month


def last_day_of_month(d):
    next_month = d.replace(day=28) + timedelta(4)
    return d.replace(day=(next_month - timedelta(days=next_month.day)).day)
