#  """
#  Copyright 2024 lepen - All Rights Reserved
#  Created by lepen on 2024-12-04 22:47:31
#
#  Author: lepen
#  Email: noprianto@s.okayama-u.ac.jp
#  Last modified: 2024-11-27 21:29:14
#  File: logger.py
#  Description:
#  """

import logging

from app.utils.config import LOG_LEVEL


def get_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)

    # Create handlers
    console_handler = logging.StreamHandler()

    # Create formatters and add them to the handlers
    console_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)')
    console_handler.setFormatter(console_format)

    # Add handlers to the logger
    logger.addHandler(console_handler)

    return logger

# Example usage
# logger = get_logger(__name__)
# logger.info("Logger is set up and ready to go!")
