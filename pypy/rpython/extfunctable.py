"""
information table about external functions for annotation/ rtyping and backends
"""
import os
import time
import types
from pypy.annotation.model import SomeInteger, SomeTuple


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

nonefactory = lambda *args: None
tuplefactory = lambda *args: SomeTuple((SomeInteger(),)*10)

# external function declarations
declare(os.open     , int        , 'll_os/open')
declare(os.read     , str        , 'll_os/read')
declare(os.write    , int        , 'll_os/write')
declare(os.close    , nonefactory, 'll_os/close')
declare(os.getcwd   , str        , 'll_os/getcwd')
declare(os.dup      , int        , 'll_os/dup')
declare(os.lseek    , int        , 'll_os/lseek')
declare(os.isatty   , bool       , 'll_os/isatty')
declare(os.ftruncate, nonefactory, 'll_os/ftruncate')
declare(os.fstat    , tuplefactory, 'll_os/fstat')
declare(time.time   , float      , 'll_time/time')
declare(time.clock  , float      , 'll_time/clock')
declare(time.sleep  , nonefactory, 'll_time/sleep')
