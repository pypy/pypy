
from cStringIO import StringIO
from pypy.config.support import detect_number_of_processors
import os, sys, py

cpuinfo = """
processor	: 0

processor	: 1
vendor_id	: GenuineIntel
cpu family	: 6
model		: 37
model name	: Intel(R) Core(TM) i7 CPU       L 620  @ 2.00GHz
stepping	: 2

processor	: 2
vendor_id	: GenuineIntel
cpu family	: 6
model		: 37
model name	: Intel(R) Core(TM) i7 CPU       L 620  @ 2.00GHz
stepping	: 2

processor	: 3
vendor_id	: GenuineIntel
cpu family	: 6
model		: 37
model name	: Intel(R) Core(TM) i7 CPU       L 620  @ 2.00GHz
stepping	: 2
cpu MHz		: 1199.000
cache size	: 4096 KB
physical id	: 0
siblings	: 4
"""

class FakeEnviron:
    def __init__(self, value):
        self._value = value
    def get(self, varname):
        assert varname == 'MAKEFLAGS'
        return self._value

def test_cpuinfo():
    if sys.platform != 'linux2':
        py.test.skip("linux only")
    saved = os.environ
    try:
        os.environ = FakeEnviron(None)
        assert detect_number_of_processors(StringIO(cpuinfo)) == 4
        assert detect_number_of_processors('random crap that does not exist') == 1
        os.environ = FakeEnviron('-j2')
        assert detect_number_of_processors(StringIO(cpuinfo)) == 1
    finally:
        os.environ = saved
