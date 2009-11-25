from cStringIO import StringIO

import py 
from pypy.tool.udir import udir
from pypy.interpreter.baseobjspace import OperationError
from pypy.interpreter import main

testcode = """\
def main():
    aStr = 'hello world'
    print len(aStr)

main()
"""

# On module test we want to ensure that the called module __name__ is
# '__main__' and argv is set as expected.
testmodulecode = """
import sys
if __name__ == '__main__':
    aStr = sys.argv[1]
    print len(aStr)
"""

testresultoutput = '11\n'

def checkoutput(space, expected_output,f,*args):
    w_oldout = space.sys.get('stdout') 
    capturefn = udir.join('capturefile')
    capturefile = capturefn.open('w') 
    w_sys = space.sys.getmodule('sys')
    space.setattr(w_sys, space.wrap("stdout"), space.wrap(capturefile))
    try:
        f(*(args + (space,)))
    finally:
        space.setattr(w_sys, space.wrap("stdout"), w_oldout)
    capturefile.close() 
    assert capturefn.read(mode='rU') == expected_output

testfn = udir.join('tmp_hello_world.py')
testmodule = 'tmp_hello_module'
testpackage = 'tmp_package'

class TestMain: 
    def setup_class(cls):
        testfn.write(testcode, 'w')
        udir.join(testmodule + '.py').write(testmodulecode, 'w')
        udir.ensure(testpackage, '__init__.py')
        udir.join(testpackage, testmodule + '.py').write(testmodulecode, 'w')
        space = cls.space
        cls.w_oldsyspath = space.appexec([space.wrap(str(udir))], """(udir):
            import sys
            old = sys.path[:]
            sys.path.insert(0, udir)
            return old
        """)

    def teardown_class(cls):
        cls.space.appexec([cls.w_oldsyspath], """(old):
            import sys
            sys.path[:] = old
        """)

    def test_run_file(self):
        checkoutput(self.space, testresultoutput, main.run_file, str(testfn))

    def test_run_string(self):
        checkoutput(self.space, testresultoutput,
                                main.run_string, testcode, str(testfn))

    def test_eval_string(self):
        w_x = main.eval_string('2+2', space=self.space)
        assert self.space.eq_w(w_x, self.space.wrap(4))

    def test_run_module(self):
        checkoutput(self.space, testresultoutput, main.run_module,
                    testmodule, ['hello world'])
        checkoutput(self.space, testresultoutput, main.run_module,
                    testpackage + '.' + testmodule, ['hello world'])
