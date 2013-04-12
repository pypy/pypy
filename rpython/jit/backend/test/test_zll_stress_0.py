from rpython.jit.backend.test import zll_stress
import py
def test_stress_0():
    import sys
    if sys.platform.startswith('win'):
        py.test.skip('crashes test platform, fix crash and reenable test')
    zll_stress.do_test_stress(0)
