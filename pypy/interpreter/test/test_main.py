import autopath
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

testfn = 'tmp_hello_world.py'
testmodule = 'tmp_hello_module'
testpackage = 'tmp_package'

class TestMain: 
    def setup_class(cls):
        ofile = open(testfn, 'w')
        ofile.write(testcode)
        ofile.close()
        omodulefile = open(testmodule + '.py', 'w')
        omodulefile.write(testmodulecode)
        omodulefile.close()
        import os
        os.mkdir(testpackage)
        open(os.path.join(testpackage, '__init__.py'), 'w').close()
        file_name = os.path.join(testpackage, testmodule) + '.py'
        omodulefile = open(file_name,'w')
        omodulefile.write(testmodulecode)
        omodulefile.close()
        

    def teardown_class(cls):
        import os
        def remove_if_exists(fn):
            if os.path.exists(fn):
                os.remove(fn)
        remove_if_exists(testfn)
        remove_if_exists(testmodule + '.py')
        remove_if_exists(os.path.join(testpackage, '__init__.py'))
        remove_if_exists(os.path.join(testpackage, '__init__.pyc'))
        remove_if_exists(os.path.join(testpackage, testmodule) + '.py')
        os.rmdir(testpackage) 
                  

    def test_run_file(self):
        checkoutput(self.space, testresultoutput,main.run_file,testfn)

    def test_run_string(self):
        checkoutput(self.space, testresultoutput,
                                 main.run_string,testcode,testfn)

    def test_eval_string(self):
        w_x = main.eval_string('2+2', space=self.space)
        assert self.space.eq_w(w_x, self.space.wrap(4))

    def test_run_module(self):
         checkoutput(self.space, testresultoutput, main.run_module,
                     testmodule, ['hello world'])
         checkoutput(self.space, testresultoutput, main.run_module,
                     testpackage + '.' + testmodule, ['hello world'])
