
""" some javascript transform test examples
"""

from pypy.translator.js.main import rpython2javascript
from pypy.translator.js.test.runtest import compile_function
from pypy.translator.transformer.debug import traceback_handler

def check_tb(tb_entry_str, callname, args, func, relline):
    tb_entry = tb_entry_str.split(":")
    funname, callargs, filename, lineno = tb_entry
    assert funname == callname
    if args is not None:
        assert callargs.startswith(args)
    assert filename == __file__ or filename == __file__[:-1]
    assert int(lineno) == func.func_code.co_firstlineno + relline

def test_simple_tansform():
    def g():
        raise ValueError()
    
    def f():
        g()
    
    def wrapper():
        try:
            # XXX: this is needed to make annotator happy
            traceback_handler.enter("entrypoint", "()", "", 0)
            f()
        except:
            return "|".join(["%s:%s:%s:%s" % k for k in traceback_handler.tb])
        return ""
    
    fn = compile_function(wrapper, [], debug_transform = True)
    retval = fn()
    lst = retval.split('|')
    assert len(lst) == 3
    check_tb(lst[1], 'f', '()', wrapper, 4)
    check_tb(lst[2], 'g', '()', f, 1)

def test_sophisticated_transform():
    def g():
        raise ValueError()
    
    def f():
        try:
            g()
        except:
            pass
    
    def z():
        f()
        raise TypeError()
    
    def wrapper():
        try:
            traceback_handler.enter("entrypoint", "()", "", 0)
            z()
        except:
            return "|".join(["%s:%s:%s:%s" % k for k in traceback_handler.tb])
        return ""
    
    fn = compile_function(wrapper, [], debug_transform = True)
    retval = fn()
    lst = retval.split("|")
    assert len(lst) == 2
    check_tb(lst[1], 'z', '()', wrapper, 3)

def test_args():
    def f(a, b, c):
        raise TypeError()
    
    def g():
        f(3, "dupa", [1,2,3])
    
    def wrapper():
        try:
            traceback_handler.enter("entrypoint", "()", "", 0)
            g()
        except:
            return "|".join(["%s:%s:%s:%s" % k for k in traceback_handler.tb])
        return ""
    
    fn = compile_function(wrapper, [], debug_transform = True)
    retval = fn()
    lst = retval.split("|")
    check_tb(lst[1], "g", "()", wrapper, 3)
    check_tb(lst[2], "f", "(3, 'dupa'", g, 1)
