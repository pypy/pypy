from pypy.jit.tl import tiny3_hotpath as tiny3
from pypy.jit.codegen.hlinfo import highleveljitinfo


def help(err="Invalid command line arguments."):
    print err
    print highleveljitinfo.sys_executable,
    print "[-j param=value,...]",
    print "'tiny3 program string' arg0 [arg1 [arg2 [...]]]"
    return 1

def entry_point(args):
    """Main entry point of the stand-alone executable:
    takes a list of strings and returns the exit code.
    """
    # store args[0] in a place where the JIT log can find it (used by
    # viewcode.py to know the executable whose symbols it should display)
    highleveljitinfo.sys_executable = args.pop(0)
    if len(args) < 1:
        return help()
    if args[0] == '-j':
        if len(args) < 3:
            return help()
        try:
            tiny3.tinyjitdriver.set_user_param(args[1])
        except ValueError:
            return help("Bad argument to -j.")
        args = args[2:]
    bytecode = [s for s in args[0].split(' ') if s != '']
    real_args = []
    for arg in args[1:]:
        try:
            real_args.append(tiny3.IntBox(int(arg)))
        except ValueError:
            real_args.append(tiny3.FloatBox(tiny3.myfloat(arg)))
    res = tiny3.interpret(bytecode, real_args)
    print tiny3.repr(res)
    return 0

def target(driver, args):
    return entry_point, None

# ____________________________________________________________

from pypy.jit.hintannotator.policy import HintAnnotatorPolicy

class MyHintAnnotatorPolicy(HintAnnotatorPolicy):
    novirtualcontainer = True
    oopspec = True
    hotpath = True

    def look_inside_graph(self, graph):
        # temporary workaround
        return getattr(graph, 'func', None) not in (tiny3.myint_internal,
                                                    tiny3.myfloat)

def portal(driver):
    """Return the 'portal' function, and the hint-annotator policy.
    The portal is the function that gets patched with a call to the JIT
    compiler.
    """
    return None, MyHintAnnotatorPolicy()

if __name__ == '__main__':
    import sys
    entry_point(sys.argv)
