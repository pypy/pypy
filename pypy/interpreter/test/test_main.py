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

testresultoutput = '11\n'

def checkoutput(space, expected_output,f,*args):
    w_sys = space.get_builtin_module("sys")
    w_oldout = space.getattr(w_sys, space.wrap("stdout"))
    capturefn = udir.join('capturefile')
    capturefile = capturefn.open('w') 
    space.setattr(w_sys, space.wrap("stdout"), space.wrap(capturefile))
    try:
        f(*(args + (space,)))
    finally:
        space.setattr(w_sys, space.wrap("stdout"), w_oldout)
    capturefile.close() 
    assert capturefn.read(mode='rU') == expected_output


testfn = 'tmp_hello_world.py'

class TestMain: 
    def setup_class(cls):
        ofile = open(testfn, 'w')
        ofile.write(testcode)
        ofile.close()

    def teardown_class(cls):
        import os
        os.remove(testfn)

    def test_run_file(self):
        checkoutput(self.space, testresultoutput,main.run_file,testfn)

    def test_run_string(self):
        checkoutput(self.space, testresultoutput,
                                 main.run_string,testcode,testfn)

    def test_eval_string(self):
        w_x = main.eval_string('2+2', space=self.space)
        assert self.space.eq_w(w_x, self.space.wrap(4))
