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
import numpy as np
import pandas as pd

from app.utils.logger import get_logger

logger = get_logger(__name__)


def descriptive(data):
    try:
        # logger.info(f"data: {data} type: {type(data)}")
        datasources = [ds.data for ds in data]
        df = pd.DataFrame(data=datasources)

        # convert to numeric first
        for col in df.columns:
            if not np.issubdtype(df[col].dtype, np.datetime64):
                df[col] = pd.to_numeric(df[col], errors='ignore')

        numeric_df = df.select_dtypes(include=['number'])
        mean = numeric_df.mean().round(2)
        std = numeric_df.std().round(2) if len(numeric_df) > 1 else {col: 'N/A' for col in numeric_df.columns}
        min = numeric_df.min().round(2)
        max = numeric_df.max().round(2)
        median = numeric_df.median().round(2)
        # logger.info(f"mean: {mean} type: {type(mean)} std: {std} min: {min} max: {max} median: {median}")
        return {
            "mean": mean.to_dict(),
            "std": std.to_dict() if len(numeric_df) > 1 else {col: 'N/A' for col in numeric_df.columns},
            "min": min.to_dict(),
            "max": max.to_dict(),
            "median": median.to_dict()
        }
    except Exception as e:
        logger.error(e)
        return {
            "mean": 0,
            "std": 0,
            "min": 0,
            "max": 0,
            "median": 0
        }
