# pytest hooks, installed by pypy.conftest.

import py
from pypy.tool import leakfinder

class LeakFinder:
    """Track memory allocations during test execution.
    
    So far, only used by the function lltype.malloc(flavor='raw').
    """
    def pytest_runtest_setup(self, __multicall__, item):
        __multicall__.execute()
        if not isinstance(item, py.test.collect.Function):
            return
        if not getattr(item.obj, 'dont_track_allocations', False):
            leakfinder.start_tracking_allocations()

    def pytest_runtest_call(self, __multicall__, item):
        __multicall__.execute()
        if not isinstance(item, py.test.collect.Function):
            return
        item._success = True

    def pytest_runtest_teardown(self, __multicall__, item):
        __multicall__.execute()
        if not isinstance(item, py.test.collect.Function):
            return
        if (not getattr(item.obj, 'dont_track_allocations', False)
            and leakfinder.TRACK_ALLOCATIONS):
            item._pypytest_leaks = leakfinder.stop_tracking_allocations(False)
        else:            # stop_tracking_allocations() already called
            item._pypytest_leaks = None

        # check for leaks, but only if the test passed so far
        if getattr(item, '_success', False) and item._pypytest_leaks:
            raise leakfinder.MallocMismatch(item._pypytest_leaks)
