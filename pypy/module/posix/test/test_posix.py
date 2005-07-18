from pypy.rpython.test.test_llinterp import interpret

def test_open():
    def f():
        import os
        ff = os.open('test_posix.py',0,0755)
        return ff
    func = interpret(f,[])
    assert func

def test_dup():
    def ff():
        import os
        fi = os.open('test_posix.py',0,0755)
        g = os.dup(fi)
        #fi.close()
        return g
    func = interpret(ff,[])
    assert func
    
def test_fstat():
    def fo():
        import os
        fi = os.open('test_posix.py',0,0755)
        g = os.fstat(fi)
        return g
    func = interpret(fo,[],True)
    assert func
