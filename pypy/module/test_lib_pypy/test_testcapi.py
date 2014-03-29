import py, sys

if '__pypy__' not in sys.builtin_module_names:
    py.test.skip('pypy only test')

from lib_pypy import _testcapi #this should insure _testcapi is built

def test_get_hashed_dir():
    import sys
    script = '''import _testcapi
            assert 'get_hashed_dir' in dir(_testcapi)
            return 0
            '''
    output = py.process.cmdexec('''"%s" -c "%s"''' %
                             (sys.executable, script))
    assert output == ''
            
