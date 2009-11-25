from pypy.jit.tl import tiny2_hotpath as tiny2
from pypy.jit.codegen.hlinfo import highleveljitinfo


def help(err="Invalid command line arguments."):
    print err
    print highleveljitinfo.sys_executable,
    print "[-j param=value,...]",
    print "'tiny2 program string' arg0 [arg1 [arg2 [...]]]"
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
            tiny2.tinyjitdriver.set_user_param(args[1])
        except ValueError:
            return help("Bad argument to -j.")
        args = args[2:]
    bytecode = [s for s in args[0].split(' ') if s != '']
    args = [tiny2.StrBox(arg) for arg in args[1:]]
    res = tiny2.interpret(bytecode, args)
    print tiny2.repr(res)
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
        return getattr(graph, 'func', None) is not tiny2.myint_internal

def portal(driver):
    """Return the 'portal' function, and the hint-annotator policy.
    The portal is the function that gets patched with a call to the JIT
    compiler.
    """
    return None, MyHintAnnotatorPolicy()
