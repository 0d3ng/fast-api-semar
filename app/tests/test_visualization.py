#  """
#  Copyright (c) 2025 lepen - All Rights Reserved
#  Created by lepen on 2025-01-17 21:28:28
#
#  Author: lepen
#  Email: noprianto@s.okayama-u.ac.jp
#  Last modified: 2025-01-17 21:28:28
#  File: test_visualization.py
#  Description:
#  """
import json
import unittest
from math import log10

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from app.services.sensor_actuator_service import SensorActuatorService


class VisualizeTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_histogram(self):
        sensors = await SensorActuatorService.get_data_sources(device_code='5f5sff', start='2025-01-01',
                                                               end='2025-01-10')
        print(sensors)
        # for sensor in sensors:
        #     print(sensor.data)
        extracted = [item.data for item in sensors]
        df = pd.DataFrame(extracted)
        df.hist(bins=10, figsize=(12, 8))
        plt.suptitle('Histogram for each columns')
        plt.show()

        def calculate_histogram_data(column):
            bin_count = int(1 + 3.322 * log10(len(df[column])))
            counts, bin_edges = np.histogram(df[column], bins=bin_count)
            bin_centers = 0.5 * (bin_edges[:-1] + bin_edges[1:])
            return {
                'bin_centers': bin_centers.tolist(),
                'frequencies': counts.tolist()
            }

        histogram_data = {col: calculate_histogram_data(col) for col in df.columns}
        histogram_json = json.dumps(histogram_data)
        print(histogram_json)


if __name__ == '__main__':
    unittest.main()
