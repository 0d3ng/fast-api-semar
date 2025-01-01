#   """
#   Copyright (c) 2024 lepen - All Rights Reserved
#   Created by lepen on 2024-12-06 21:54:04
#
#   Author: lepen
#   Email: noprianto@s.okayama-u.ac.jp
#   Last modified: 2024-12-06 21:53:04
#   File: generator.py
#   Description:
#   """

import random
import string
from datetime import datetime, timedelta

import pytz
from pytz import timezone


def generate_random_alphanumeric_hexa(length=6):
    characters = string.ascii_letters + string.digits + 'abcdef'
    return (''.join(random.choice(characters) for _ in range(length))).lower()


def calculate_minutes_between_dates(date1: datetime, date2: datetime) -> int:
    try:
        # Calculate the difference in time and convert seconds to minutes
        if date2.tzinfo is None:
            date2 = date2.replace(tzinfo=pytz.UTC)
        delta_minutes = abs((date2 - date1).total_seconds() / 60)
        return int(delta_minutes)
    except ValueError as e:
        # Raise an error if date parsing fails
        raise ValueError(f"Error parsing dates: {e}")


def add_day_to_date(days: int) -> datetime:
    try:
        future = (datetime.now(tz=pytz.UTC) + timedelta(days=days))
        return future
    except ValueError as e:
        # Raise an error if date parsing fails
        raise ValueError(f"Error parsing dates: {e}")


def convert_to_datetime(date_string):
    try:
        return datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return None
