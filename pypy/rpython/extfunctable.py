"""
information table about external functions for annotation/ rtyping and backends
"""
import os
import time
import math
import types


class ExtFuncInfo:
    def __init__(self, func, annotation, ll_function_path, ll_annotable, backend_functiontemplate):
        self.func = func
        self.annotation = annotation
        modulename, ignored = ll_function_path.split('/')
        self.ll_module = ImportMe('pypy.rpython.module.%s' % modulename)
        self.ll_function_name = ll_function_path.replace('/', '_')
        self.ll_annotable = ll_annotable
        self.backend_functiontemplate = backend_functiontemplate

    def get_ll_function(self):
        """Get the ll_*() function implementing the given high-level 'func'."""
        mod = self.ll_module.load()
        return getattr(mod, self.ll_function_name)
    ll_function = property(get_ll_function)


class ImportMe:
    "Lazily imported module, for circular imports :-/"
    def __init__(self, modulename):
        self.modulename = modulename
        self._mod = None
    def load(self):
        if self._mod is None:
            self._mod = __import__(self.modulename, None, None, ['__doc__'])
        return self._mod


table = {}
def declare(func, annotation, ll_function, ll_annotable=True, backend_functiontemplate=None):
    # annotation can be a function computing the annotation
    # or a simple python type from which an annotation will be constructed
    global table
    if not isinstance(annotation, types.FunctionType):
        typ = annotation
        def annotation(*args_s):
            from pypy.annotation import bookkeeper
            return bookkeeper.getbookkeeper().valueoftype(typ)
    table[func] = ExtFuncInfo(func, annotation, ll_function, ll_annotable, backend_functiontemplate)

# _____________________________________________________________



def noneannotation(*args):
    return None

def statannotation(*args):
    from pypy.annotation.model import SomeInteger, SomeTuple
    return SomeTuple((SomeInteger(),)*10)

def frexpannotation(*args):
    from pypy.annotation.model import SomeInteger, SomeTuple, SomeFloat
    return SomeTuple((SomeFloat(), SomeInteger()))

def modfannotation(*args):
    from pypy.annotation.model import SomeTuple, SomeFloat
    return SomeTuple((SomeFloat(), SomeFloat()))

# external function declarations
declare(os.open     , int           , 'll_os/open')
declare(os.read     , str           , 'll_os/read')
declare(os.write    , int           , 'll_os/write')
declare(os.close    , noneannotation, 'll_os/close')
declare(os.getcwd   , str           , 'll_os/getcwd')
declare(os.dup      , int           , 'll_os/dup')
declare(os.lseek    , int           , 'll_os/lseek')
declare(os.isatty   , bool          , 'll_os/isatty')
declare(os.ftruncate, noneannotation, 'll_os/ftruncate')
declare(os.fstat    , statannotation, 'll_os/fstat')
declare(os.stat     , statannotation, 'll_os/stat')
declare(os.path.exists, bool        , 'll_os_path/exists')
declare(os.path.isdir, bool         , 'll_os_path/isdir')
declare(time.time   , float         , 'll_time/time')
declare(time.clock  , float         , 'll_time/clock')
declare(time.sleep  , noneannotation, 'll_time/sleep')

# ___________________________
# math functions

declare(math.frexp  , frexpannotation, 'll_math/frexp')
declare(math.atan2  , float         , 'll_math/atan2')
declare(math.fmod   , float         ,  'll_math/fmod')
declare(math.floor  , float         ,  'll_math/floor')
declare(math.ldexp  , float         ,  'll_math/ldexp')
declare(math.modf   , modfannotation, 'll_math/modf')
declare(math.hypot  , float         , 'll_math/hypot')

# the following functions all take one float, return one float
# and are part of math.h
simple_math_functions = [
    'acos', 'asin', 'atan', 'ceil', 'cos', 'cosh', 'exp', 'fabs',
    'floor', 'log', 'log10', 'sin', 'sinh', 'sqrt', 'tan', 'tanh'
    ]

for name in simple_math_functions:
    declare(getattr(math, name), float, 'll_math/%s' % name)
