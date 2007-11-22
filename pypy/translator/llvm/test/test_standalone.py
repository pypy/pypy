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

