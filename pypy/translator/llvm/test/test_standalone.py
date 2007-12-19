import py
from pypy.translator.llvm.test.runtest import compile_standalone

def cmdexec(exe_name, *args):
    from pypy.tool.udir import udir
    exe_name = udir.join(exe_name)
    args = ' '.join(args)
    return py.process.cmdexec('%s %s' % (exe_name, args))

def test_print():
    def entry_point(argv):
        print "argument count:", len(argv)
        print "arguments:", argv
        print "argument lengths:",
        print [len(s) for s in argv]
        return 0

    exe_name = 'test_print'
    compile_standalone(entry_point, exe_name=exe_name)
    data = cmdexec(exe_name, 'abc', 'def')
    assert data.startswith('argument count: 3')
    data = cmdexec(exe_name)
    assert data.startswith('argument count: 1')
    
def test_hello_world():
    import os
    def entry_point(argv):
        os.write(1, "hello world\n")
        argv = argv[1:]
        os.write(1, "argument count: " + str(len(argv)) + "\n")
        for s in argv:
            os.write(1, "   '" + str(s) + "'\n")
        return 0

    exe_name = 'test_hello_world'
    compile_standalone(entry_point, exe_name=exe_name)
    data = cmdexec(exe_name, 'hi', 'there')
    assert data.startswith('''hello world\nargument count: 2\n   'hi'\n   'there'\n''')

def test__del__():
    from pypy.rpython.lltypesystem import lltype
    from pypy.rpython.lltypesystem.lloperation import llop
    class State:
        pass
    s = State()
    class A(object):
        def __del__(self):
            s.a_dels += 1
    class B(A):
        def __del__(self):
            s.b_dels += 1
    class C(A):
        pass
    def f():
        s.a_dels = 0
        s.b_dels = 0
        A()
        B()
        C()
        A()
        B()
        C()
        llop.gc__collect(lltype.Void)
        return s.a_dels * 10 + s.b_dels

    def entry_point(args):
        res = 0
        res += f()
        res += f()
        print 'count %d' % res
        return 0

    exe_name = 'test__del__'
    compile_standalone(entry_point, exe_name=exe_name)
    data = cmdexec(exe_name, 'abc', 'def')
    print data
    #assert data.startswith('argument count: 3')

    #assert 0 < res <= 84 

def test_strtod():
    def entry_point(args):
        print float(args[1])
        return 0

    exe_name = 'test_strtod'
    compile_standalone(entry_point, exe_name=exe_name)
    data = cmdexec(exe_name, '3.13e1')

def test_exception_leaking():
    def entry_point(argv):
        if len(argv) > 5:
            raise ValueError
        print 'ok'
        return 0

    exe_name = 'test_exception_leaking'
    compile_standalone(entry_point, exe_name=exe_name)
    data = cmdexec(exe_name, 'abc', 'def')
    assert data.startswith('ok')
    try:
        data = cmdexec(exe_name, 'abc', 'def', 'abc', 'def', 'abc', 'def')
    except py.process.cmdexec.Error, exc:
        assert exc.err.startswith('DEBUG')
