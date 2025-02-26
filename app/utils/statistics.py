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

from app.schemas.sensor_actuator_schema import DataSource
from app.utils.json_tools import extract_sensors, is_number
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


def corr_matrix(data):
    try:
        datasources = [ds.data for ds in data]
        df = pd.DataFrame(data=datasources)
        # convert to numeric first
        for col in df.columns:
            if not np.issubdtype(df[col].dtype, np.datetime64):
                df[col] = pd.to_numeric(df[col], errors='ignore')

        numeric_df = df.select_dtypes(include=['number'])
        logger.info(numeric_df.columns)
        logger.info(numeric_df.info)
        coor_matrix = df.corr()
        coor_matrix_json = coor_matrix.to_json()
        logger.info(f"type{type(coor_matrix)} correlation matrix:\n{coor_matrix_json}")
        return coor_matrix_json
    except Exception as e:
        logger.error(e)
        raise e


# datas = [
#     {
#         "data": {
#             "amedas": {
#                 "horizontal_visibility": 20,
#                 "humidity": 57,
#                 "pressure": 1024.1,
#                 "sea_level_pressure": 1025,
#                 "temperature": 3,
#                 "timestamp": "2025-02-10 22:10:00",
#                 "wind_direction": "WSW",
#                 "wind_speed": 4.8
#             },
#             "btevs1": {
#                 "co2": 903,
#                 "humidity": 25,
#                 "latitude": 0,
#                 "longitude": 0,
#                 "pm1": 1.3,
#                 "pm10": 1.4,
#                 "pm25": 1.4,
#                 "pm4": 1.4,
#                 "temp": 21.8,
#                 "timestamp": "2025-02-10 22:28:34"
#             }
#         }
#     },
#     {
#         "data": {
#             "amedas": {
#                 "horizontal_visibility": 21,
#                 "humidity": 58,
#                 "pressure": 1024.2,
#                 "sea_level_pressure": 1024,
#                 "temperature": 4,
#                 "timestamp": "2025-02-10 22:10:00",
#                 "wind_direction": "WSW",
#                 "wind_speed": 4.5
#             },
#             "btevs1": {
#                 "co2": 902,
#                 "humidity": 24,
#                 "latitude": 34.6894326,
#                 "longitude": 133.9226571,
#                 "pm1": 0.8,
#                 "pm10": 0.9,
#                 "pm25": 0.9,
#                 "pm4": 0.9,
#                 "temp": 21.9,
#                 "timestamp": "2025-02-10 22:29:25"
#             }
#         }
#     }
# ]
#
# data_sources = []
# for data in datas:
#     logger.info(data['data'])
#     json_data = extract_sensors(data['data'])
#     rs = {key: value for key, value in json_data.items() if is_number(value)}
#     dt_src: DataSource = DataSource(
#         data=rs,
#     )
#     data_sources.append(dt_src)
# logger.info(f"length: {len(data_sources)}")
# corr_matrix(data_sources)
