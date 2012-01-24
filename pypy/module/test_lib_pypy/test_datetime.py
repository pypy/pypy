"""Additional tests for datetime."""

import time
import datetime
import os

def test_utcfromtimestamp():
    """Confirm that utcfromtimestamp and fromtimestamp give consistent results.

    Based on danchr's test script in https://bugs.pypy.org/issue986
    """
    try:
        prev_tz = os.environ.get("TZ")
        os.environ["TZ"] = "GMT"
        for unused in xrange(100):
            now = time.time()
            delta = (datetime.datetime.utcfromtimestamp(now) -
                     datetime.datetime.fromtimestamp(now))
            assert delta.days * 86400 + delta.seconds == 0
    finally:
        if prev_tz is None:
            del os.environ["TZ"]
        else:
            os.environ["TZ"] = prev_tz
