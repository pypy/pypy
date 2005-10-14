"""
Dummy low-level implementations for the external functions of the 'time' module.
"""

# See ll_os.py.

import time


def ll_time_time():
    return time.time()
ll_time_time.suggested_primitive = True

def ll_time_clock():
    return time.clock()
ll_time_clock.suggested_primitive = True

def ll_time_sleep(t):
    time.sleep(t)
ll_time_sleep.suggested_primitive = True
