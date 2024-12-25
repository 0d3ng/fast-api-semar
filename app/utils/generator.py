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

from pytz import timezone


def generate_random_alphanumeric_hexa(length=6):
    characters = string.ascii_letters + string.digits + 'abcdef'
    return (''.join(random.choice(characters) for _ in range(length))).lower()


def calculate_minutes_between_dates(date1: str, date2: str, date_format: str = "%Y-%m-%d %H:%M:%S") -> int:
    try:
        # Convert the string dates into datetime objects
        dt1 = datetime.strptime(date1, date_format)
        dt2 = datetime.strptime(date2, date_format)

        # Calculate the difference in time and convert seconds to minutes
        delta_minutes = abs((dt2 - dt1).total_seconds() / 60)
        return int(delta_minutes)
    except ValueError as e:
        # Raise an error if date parsing fails
        raise ValueError(f"Error parsing dates: {e}")


def add_day_to_date_string(days: int, date_format: str = "%Y-%m-%d %H:%M:%S") -> str:
    try:
        future = (datetime.now(tz=timezone("Asia/Tokyo")) + timedelta(days=days)).strftime(date_format)
        return future
    except ValueError as e:
        # Raise an error if date parsing fails
        raise ValueError(f"Error parsing dates: {e}")


def convert_to_datetime(date_string):
    try:
        return datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return None
