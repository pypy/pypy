import os
import py
from pypy.tool.udir import udir
from pypy.translator.test import snippet
from pypy.translator.squeak.gensqueak import GenSqueak, Selector
from pypy.translator.translator import TranslationContext
from pypy import conftest


def looping(i, j):
    while i > 0:
        i -= 1
        while j > 0:
            j -= 1

def build_sqfunc(func, args=[]):
    try: func = func.im_func
    except AttributeError: pass
    t = TranslationContext()
    t.buildannotator().build_types(func, args)
    t.buildrtyper(type_system="ootype").specialize()
    if conftest.option.view:
       t.viewcg()
    return GenSqueak(udir, t)

class TestSqueakTrans:

    def test_simple_func(self):
        build_sqfunc(snippet.simple_func, [int])

    def test_if_then_else(self):
        build_sqfunc(snippet.if_then_else, [bool, int, int])

    def test_my_gcd(self):
        build_sqfunc(snippet.my_gcd, [int, int])

    def test_looping(self):
        build_sqfunc(looping, [int, int])


# For now use pipes to communicate with squeak. This is very flaky
# and only works for posix systems. At some later point we'll
# probably need a socket based solution for this.
startup_script = """
| stdout src selector result arguments arg i |
src := Smalltalk getSystemAttribute: 3.
FileStream fileIn: src.
selector := (Smalltalk getSystemAttribute: 4) asSymbol.
arguments := OrderedCollection new.
i := 4.
[(arg := Smalltalk getSystemAttribute: (i := i + 1)) notNil]
    whileTrue: [arguments add: arg asInteger].

result := (PyFunctions perform: selector withArguments: arguments asArray).
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

    def run_on_squeak(self, function, *args):
        # NB: only integers arguments are supported currently
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
        arg_types = [type(arg) for arg in args]
        gen_squeak = build_sqfunc(function, arg_types)
        cmd = 'squeak -headless -- %s %s "%s" %s' \
                % (self.startup_st, udir.join(gen_squeak.filename),
                   Selector(function.__name__, len(args)).symbol(),
                   " ".join(['"%s"' % a for a in args]))
        squeak_process = os.popen(cmd)
        result = squeak_process.read()
        assert squeak_process.close() is None # exit status was 0
        return result

    def test_theanswer(self):
        def theanswer():
            return 42
        assert self.run_on_squeak(theanswer) == "42"

    def test_simplemethod(self):
        class A:
            def m(self):
                return 42
        def simplemethod():
            return A().m()
        assert self.run_on_squeak(simplemethod) == "42"

    def test_argfunction(self):
        def function(i, j=2):
            return i + j
        assert self.run_on_squeak(function, 1, 3) == "4"

    def test_argmethod(self):
        class A:
            def m(self, i, j, h=2):
                return i + j + h
        def simplemethod(i):
            return A().m(i, j=3)
        assert self.run_on_squeak(simplemethod, 1) == "6"

    def test_nameclash_classes(self):
        from pypy.translator.squeak.test.support import A as A2
        class A:
            def m(self, i): return 2 + i
        def f():
            return A().m(0) + A2().m(0)
        assert self.run_on_squeak(f) == "3"

    def test_nameclash_camel_case(self):
        class ASomething:
            def m(self, i): return 1 + i
        class Asomething:
            def m(self, i): return 2 + i
        def f():
            x = ASomething().m(0) + Asomething().m(0)
            return x + ASomething().m(0) + Asomething().m(0)
        assert self.run_on_squeak(f) == "6"


class TestSelector:

    def test_selector(self):
        assert Selector("bla_bla", 0).symbol() == "blaBla"
        assert Selector("bla", 1).symbol() == "bla:"
        assert Selector("bla_bla_bla", 3).symbol() == "blaBlaBla:with:with:"
        assert Selector("+", 1).symbol() == "+"

    def test_signature(self):
        assert Selector("bla", 0).signature([]) == "bla"
        assert Selector("bla", 1).signature(["v"]) == "bla: v"
        assert Selector("bla", 2).signature(["v0", "v1"]) == "bla: v0 with: v1"
        assert Selector("+", 1).signature(["v"]) == "+ v"

