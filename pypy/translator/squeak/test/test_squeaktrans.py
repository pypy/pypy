import os
import py
from pypy.tool.udir import udir
from pypy.translator.test import snippet
from pypy.translator.squeak.gensqueak import GenSqueak
from pypy.translator.translator import TranslationContext


def looping(i = (int), j = (int)):
    while i > 0:
        i -= 1
        while j > 0:
            j -= 1

def build_sqfunc(func):
    try: func = func.im_func
    except AttributeError: pass
    t = TranslationContext()
    graph = t.buildflowgraph(func)
    t._prebuilt_graphs[func] = graph
    gen = GenSqueak(udir, t)
    return gen

class TestSqueakTrans:

    def test_simple_func(self):
        build_sqfunc(snippet.simple_func)

    def test_if_then_else(self):
        build_sqfunc(snippet.if_then_else)

    def test_two_plus_two(self):
        build_sqfunc(snippet.two_plus_two)

    def test_my_gcd(self):
        build_sqfunc(snippet.my_gcd)

    def test_looping(self):
        build_sqfunc(looping)


# For now use pipes to communicate with squeak. This is very flaky
# and only works for posix systems. At some later point we'll
# probably need a socket based solution for this.
startup_script = """
| stdout src function result |
src := Smalltalk getSystemAttribute: 3.
FileStream fileIn: src.
function := Smalltalk getSystemAttribute: 4.
result := Compiler new evaluate: ('PyFunctions ' , function) in: nil to: nil.
stdout := StandardFileStream fileNamed: '/dev/stdout'.
stdout nextPutAll: result asString.
Smalltalk snapshot: false andQuit: true.
"""

class TestGenSqueak:

    def setup_class(self):
        self.startup_st = udir.join("startup.st")
        f = self.startup_st.open("w")
        f.write(startup_script)
        f.close()

    def run_on_squeak(self, function):
        try:
            import posix
        except ImportError:
            py.test.skip("Squeak tests only work on Unix right now.")
        try:
            py.path.local.sysfind("squeak")
        except py.error.ENOENT:
            py.test.skip("Squeak is not on your path.")
        if os.getenv("SQUEAK_IMAGE") is None:
            py.test.skip("Squeak tests expect the SQUEAK_IMAGE environment "
                    "variable to point to an image.")
        gen_squeak = build_sqfunc(function)
        squeak_process = os.popen("squeak -headless -- %s %s %s"
                % (self.startup_st, udir.join(gen_squeak.filename),
                   # HACK XXX. Only works for functions without arguments.
                   # Need to really rethink how selectors are assigned 
                   # to functions.
                   function.__name__))
        result = squeak_process.read()
        assert squeak_process.close() is None # exit status was 0
        return result

    def test_theanswer(self):
        def theanswer():
            return 42
        assert self.run_on_squeak(theanswer) == "42"

