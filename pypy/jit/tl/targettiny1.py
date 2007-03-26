from pypy.jit.tl import tiny1
from pypy.jit.codegen.hlinfo import highleveljitinfo


def entry_point(args):
    highleveljitinfo.sys_executable = args[0]
    if len(args) < 4:
        print "Usage: %s bytecode x y" % (args[0],)
        return 2
    bytecode = args[1]
    x = int(args[2])
    y = int(args[3])
    res = tiny1.ll_plus_minus(bytecode, x, y)
    print res
    return 0

def target(driver, args):
    return entry_point, None

# ____________________________________________________________

from pypy.jit.hintannotator.annotator import HintAnnotatorPolicy

class MyHintAnnotatorPolicy(HintAnnotatorPolicy):
    novirtualcontainer = True
    oopspec = True

def portal(driver):
    return tiny1.ll_plus_minus, MyHintAnnotatorPolicy()
