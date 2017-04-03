import py, sys

if '__pypy__' not in sys.builtin_module_names:
    py.test.skip('pypy only test')

from lib_pypy import _testcapi #make sure _testcapi is built

def test_get_hashed_dir():
    import sys
    # This should not compile _testcapi, so the output is empty
    script = "import _testcapi; assert 'get_hashed_dir' not in dir(_testcapi)"
    output = py.process.cmdexec('''"%s" -c "%s"''' %
                             (sys.executable, script))
    assert output == ''
            
