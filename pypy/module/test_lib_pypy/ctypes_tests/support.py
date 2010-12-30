import py
import sys
import ctypes

py.test.importorskip("ctypes", "1.0.2")

try:
    import _rawffi
except ImportError:
    _rawffi = None

class WhiteBoxTests:

    def setup_class(cls):
        if _rawffi:
            py.test.skip("white-box tests for pypy _rawffi based ctypes impl")

class BaseCTypesTestChecker:
    def setup_class(cls):
        if _rawffi:
            import gc
            for _ in range(4):
                gc.collect()
            cls.old_num = _rawffi._num_of_allocated_objects()
    
    def teardown_class(cls):
        if sys.pypy_translation_info['translation.gc'] == 'boehm':
            return # it seems that boehm has problems with __del__, so not
                   # everything is freed
        if hasattr(cls, 'old_num'):
            import gc
            for _ in range(4):
                gc.collect()
            # there is one reference coming from the byref() above
            assert _rawffi._num_of_allocated_objects() == cls.old_num
