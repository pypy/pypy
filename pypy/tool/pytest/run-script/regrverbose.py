# refer to 2.4.1/test/regrtest.py's runtest() for comparison
import sys
from test import test_support
test_support.verbose = int(sys.argv[1])
sys.argv[:] = sys.argv[2:]

modname = sys.argv[0] 
impname = 'test.' + modname 
mod = __import__(impname, globals(), locals(), [modname])
indirect_test = getattr(mod, 'test_main', None)
if indirect_test is not None:
    indirect_test()
# else the test already ran during import 
