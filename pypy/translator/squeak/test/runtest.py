import os
import py
from pypy.tool.udir import udir
from pypy.translator.squeak.gensqueak import GenSqueak, Selector
from pypy.translator.translator import TranslationContext
from pypy import conftest

def compile_function(func, annotation=[]):
    return SqueakFunction(func, annotation)


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

PyConstants setupConstants.
result := (PyFunctions perform: selector withArguments: arguments asArray).
stdout := StandardFileStream fileNamed: '/dev/stdout'.
stdout nextPutAll: result asString.
Smalltalk snapshot: false andQuit: true.
"""

class SqueakFunction:

    def __init__(self, func, annotation):
        self._func = func
        self._gen = self._build(func, annotation)

    def _build(self, func, annotation):
        try: 
            func = func.im_func
        except AttributeError: 
            pass
        t = TranslationContext()
        t.buildannotator().build_types(func, annotation)
        t.buildrtyper(type_system="ootype").specialize()
        self.graph = t.graphs[0]
        if conftest.option.view:
           t.viewcg()
        return GenSqueak(udir, t)

    def _write_startup(self):
        startup_st = udir.join("startup.st")
        try:
            # Erm, py.path.local has no "exists" method?
            startup_st.stat()
        except py.error.ENOENT:
            f = startup_st.open("w")
            f.write(startup_script)
            f.close()
        return startup_st

    def __call__(self, *args):
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
        startup_st = self._write_startup()
        options = "-headless"
        if conftest.option.showsqueak:
            options = ""
        cmd = 'squeak %s -- %s %s "%s" %s' \
                % (options, startup_st, udir.join(self._gen.filename),
                   Selector(self._func.__name__, len(args)).symbol(),
                   " ".join(['"%s"' % a for a in args]))
        squeak_process = os.popen(cmd)
        result = squeak_process.read()
        assert squeak_process.close() is None # exit status was 0
        return result

