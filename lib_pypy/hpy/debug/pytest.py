# hpy.debug / pytest integration

import pytest
from .leakdetector import LeakDetector

# For now "hpy_debug" just does leak detection, but in the future it might
# grows extra features: that's why it's called generically "hpy_debug" instead
# of "detect_leaks".

# NOTE: the fixture itself is currently untested :(. It turns out that testing
# that the fixture raises during the teardown is complicated and probably
# requires to write a full-fledged plugin. We might want to turn this into a
# real plugin in the future, but for now I think this is enough.

@pytest.fixture
def hpy_debug(request):
    """
    pytest fixture which makes it possible to control hpy.debug from within a test.

    In particular, it automatically check that the test doesn't leak.
    """
    with LeakDetector() as ld:
        yield ld
