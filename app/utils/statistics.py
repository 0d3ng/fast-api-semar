#  """
#  Copyright (c) 2025 lepen - All Rights Reserved
#  Created by lepen on 2025-01-15 22:43:03
#
#  Author: lepen
#  Email: noprianto@s.okayama-u.ac.jp
#  Last modified: 2025-01-15 22:43:03
#  File: statistics.py
#  Description:
#  """
import pandas as pd

from app.utils.logger import get_logger

logger = get_logger(__name__)


def descriptive(data):
    logger.info(f"data: {data} type: {type(data)}")
    datasources = [ds.data for ds in data]
    df = pd.DataFrame(data=datasources)
    mean = df.mean().round(2)
    std = df.std().round(2) if len(df) > 1 else {col: 'N/A' for col in df.columns}
    min = df.min().round(2)
    max = df.max().round(2)
    median = df.median().round(2)
    logger.info(f"mean: {mean} type: {type(mean)} std: {std} min: {min} max: {max} median: {median}")
    return {
        "mean": mean.to_dict(),
        "std": std.to_dict() if len(df) > 1 else {col: 'N/A' for col in df.columns},
        "min": min.to_dict(),
        "max": max.to_dict(),
        "median": median.to_dict()
    }
