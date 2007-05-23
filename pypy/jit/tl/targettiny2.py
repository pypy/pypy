from pypy.jit.tl import tiny2
from pypy.jit.codegen.hlinfo import highleveljitinfo


def entry_point(args):
    """Main entry point of the stand-alone executable:
    takes a list of strings and returns the exit code.
    """
    # store args[0] in a place where the JIT log can find it (used by
    # viewcode.py to know the executable whose symbols it should display)
    highleveljitinfo.sys_executable = args[0]
    if len(args) < 2:
        print "Invalid command line arguments."
        print args[0] + " 'tiny2 program string' arg0 [arg1 [arg2 [...]]]"
        return 1
    bytecode = [s for s in args[1].split(' ') if s != '']
    args = [tiny2.StrBox(arg) for arg in args[2:]]
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

    def look_inside_graph(self, graph):
        # temporary workaround
        return getattr(graph, 'func', None) is not tiny2.myint_internal

def portal(driver):
    """Return the 'portal' function, and the hint-annotator policy.
    The portal is the function that gets patched with a call to the JIT
    compiler.
    """
    return tiny2.interpret, MyHintAnnotatorPolicy()
