# refer to 2.4.1/test/regrtest.py's runtest() for comparison
import sys
import unittest
from test import test_support
test_support.verbose = 1
sys.argv[:] = sys.argv[1:]

modname = sys.argv[0]
impname = 'test.' + modname
try:
    mod = __import__(impname, globals(), locals(), [modname])
    indirect_test = getattr(mod, 'test_main', None)
    if indirect_test is not None:
        indirect_test()
except unittest.SkipTest:
    sys.stderr.write("="*26 + "skipped" + "="*26 + "\n")
    raise
# else the test already ran during import
