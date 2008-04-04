import py
import ctypes

if ctypes.__version__ < "1.0.2":
    py.test.skip("we expect a ctypes implementation with ver >= 1.0.2")

class WhiteBoxTests:

    def setup_class(cls):
        try:
             import _rawffi
        except ImportError:
            py.test.skip("these tests are white-box tests for pypy _rawffi based ctypes impl")

class BaseCTypesTestChecker:
    def setup_class(cls):
        try:
            import _rawffi
        except ImportError:
            pass
        else:
            import gc
            for _ in range(4):
                gc.collect()
            cls.old_num = _rawffi._num_of_allocated_objects()
    
    def teardown_class(cls):
        #return
        try:
            import _rawffi
        except ImportError:
            pass
        else:
            import gc
            for _ in range(4):
                gc.collect()
            # there is one reference coming from the byref() above
            assert _rawffi._num_of_allocated_objects() == cls.old_num
