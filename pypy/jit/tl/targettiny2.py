from pypy.jit.tl import tiny2
from pypy.jit.codegen.hlinfo import highleveljitinfo


def entry_point(args):
    highleveljitinfo.sys_executable = args[0]
    if len(args) < 3:
        print "Invalid command line arguments."
        print args[0] + " 'tiny2 program string' arg0 [arg1 [arg2 [...]]]"
        return 1
    bytecode = [s for s in args[1].split(' ') if s != '']
    args = [tiny2.StrBox(arg) for arg in args[2:]]
    res = tiny2.interpret(bytecode, args)
    print res.as_str()
    return 0

def target(driver, args):
    return entry_point, None

# ____________________________________________________________

from pypy.jit.hintannotator.annotator import HintAnnotatorPolicy

class MyHintAnnotatorPolicy(HintAnnotatorPolicy):
    novirtualcontainer = True
    oopspec = True

    def look_inside_graph(self, graph):
        return getattr(graph, 'func', None) is not tiny2.myint_internal

def portal(driver):
    return tiny2.interpret, MyHintAnnotatorPolicy()
