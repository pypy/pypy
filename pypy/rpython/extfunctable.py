"""
information table about external functions for annotation/rtyping and backends
"""
import os
import time
import math
import types
from pypy.rpython.rarithmetic import r_longlong

class ExtFuncInfo:
    def __init__(self, func, annotation, ll_function_path, ll_annotable, backend_functiontemplate):
        self.func = func
        self.annotation = annotation
        modulename, tail = ll_function_path.split('/')
        if '.' not in modulename:
            modulename = 'pypy.rpython.module.%s' % modulename
        self.ll_module = ImportMe(modulename)
        lastmodulename = modulename[modulename.rfind('.')+1:]
        self.ll_function_name = '%s_%s' % (lastmodulename, tail)
        self.ll_annotable = ll_annotable
        self.backend_functiontemplate = backend_functiontemplate

    def get_ll_function(self):
        """Get the ll_*() function implementing the given high-level 'func'."""
        mod = self.ll_module.load()
        return getattr(mod, self.ll_function_name)
    ll_function = property(get_ll_function)


class ExtTypeInfo:
    def __init__(self, typ, tag, methods, needs_container=True):
        self.typ = typ
        self.tag = tag
        self._TYPE = None
        self.methods = methods     # {'name': ExtFuncInfo()}
        self.needs_container = needs_container

    def get_annotation(self, methodname):
        return self.methods[methodname].annotation

    def get_annotations(self):
        return dict([(name, self.get_annotation(name))
                     for name in self.methods])

    def get_func_infos(self):
        for extfuncinfo in self.methods.itervalues():
            if extfuncinfo.func is not None:
                yield (extfuncinfo.func, extfuncinfo)

    def get_lltype(self):
        if self._TYPE is None:
            from pypy.rpython.lltypesystem import lltype
            OPAQUE = lltype.OpaqueType(self.tag)
            OPAQUE._exttypeinfo = self
            if self.needs_container:
                STRUCT = lltype.GcStruct(self.tag, ('obj', OPAQUE))
                self._TYPE = STRUCT
            else:
                self._TYPE = OPAQUE
        return self._TYPE

    def set_lltype(self, TYPE):
        self._TYPE = TYPE

class ImportMe:
    "Lazily imported module, for circular imports :-/"
    def __init__(self, modulename):
        self.modulename = modulename
        self._mod = None
    def load(self):
        if self._mod is None:
            self._mod = __import__(self.modulename, None, None, ['__doc__'])
        return self._mod


table_callbacks = []   # to track declare() that occur after 'table' is read

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
    info = ExtFuncInfo(func, annotation, ll_function, ll_annotable, backend_functiontemplate)
    if func is not None:
        table[func] = info
        for callback in table_callbacks:
            callback()
    return info

typetable = {}
def declaretype1(typ, tag, methodsdecl, needs_container):
    assert isinstance(typ, type)
    methods = {}
    for name, args in methodsdecl.items():
        # try to get the method object from the typ
        for cls in typ.__mro__:
            if name in typ.__dict__:
                func = typ.__dict__[name]
                break
        else:
            func = None   # failed (typical for old-style C types), ignore it
        methods[name] = declare(func, *args)
    info = ExtTypeInfo(typ, tag, methods, needs_container)
    typetable[typ] = info
    for callback in table_callbacks:
        callback()
    return info

def declaretype(typ, tag, **methodsdecl):
    return declaretype1(typ, tag, methodsdecl, needs_container=True)

def declareptrtype(typ, tag, **methodsdecl):
    return declaretype1(typ, tag, methodsdecl, needs_container=False)

# _____________________________________________________________

def record_call(func, args_s, symbol):
    from pypy.annotation import bookkeeper
    bk = bookkeeper.getbookkeeper()
    # this would be nice!
    #bk.pbc_call(bk.immutablevalue(func),
    #            bk.build_args("simple_call", args_s),
    #            emulated=True)
    bk.annotator.translator._implicitly_called_by_externals.append(
        (func, args_s, symbol))

def noneannotation(*args):
    return None

def posannotation(*args):
    from pypy.annotation.model import SomeInteger
    return SomeInteger(nonneg=True)

def statannotation(*args):
    from pypy.annotation.model import SomeInteger, SomeTuple
    from pypy.rpython.module.ll_os import ll_stat_result
    record_call(ll_stat_result, [SomeInteger()]*10, 'OS_STAT')
    return SomeTuple((SomeInteger(),)*10)

def frexpannotation(*args):
    from pypy.annotation.model import SomeInteger, SomeTuple, SomeFloat
    from pypy.rpython.module.ll_math import ll_frexp_result
    record_call(ll_frexp_result, (SomeFloat(), SomeInteger()), 'MATH_FREXP')
    return SomeTuple((SomeFloat(), SomeInteger()))

def modfannotation(*args):
    from pypy.annotation.model import SomeTuple, SomeFloat
    from pypy.rpython.module.ll_math import ll_modf_result
    record_call(ll_modf_result, (SomeFloat(), SomeFloat()), 'MATH_MODF')
    return SomeTuple((SomeFloat(), SomeFloat()))

def strnullannotation(*args):
    from pypy.annotation.model import SomeString
    return SomeString(can_be_None=True)

# external function declarations
posix = __import__(os.name)
declare(os.open     , int           , 'll_os/open')
declare(os.read     , str           , 'll_os/read')
declare(os.write    , posannotation , 'll_os/write')
declare(os.close    , noneannotation, 'll_os/close')
declare(os.dup      , int           , 'll_os/dup')
declare(os.lseek    , r_longlong    , 'll_os/lseek')
declare(os.isatty   , bool          , 'll_os/isatty')
if hasattr(posix, 'ftruncate'):
    declare(os.ftruncate, noneannotation, 'll_os/ftruncate')
declare(os.fstat    , statannotation, 'll_os/fstat')
declare(os.stat     , statannotation, 'll_os/stat')
declare(os.system   , int           , 'll_os/system')
declare(os.strerror , str           , 'll_os/strerror')
declare(os.unlink   , noneannotation, 'll_os/unlink')
declare(os.getcwd   , str           , 'll_os/getcwd')
declare(os.chdir    , noneannotation, 'll_os/chdir')
declare(os.mkdir    , noneannotation, 'll_os/mkdir')
declare(os.rmdir    , noneannotation, 'll_os/rmdir')
if hasattr(posix, 'unsetenv'):   # note: faked in os
    declare(os.unsetenv , noneannotation, 'll_os/unsetenv')
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
declare(math.pow    , float         , 'll_math/pow')

# the following functions all take one float, return one float
# and are part of math.h
simple_math_functions = [
    'acos', 'asin', 'atan', 'ceil', 'cos', 'cosh', 'exp', 'fabs',
    'floor', 'log', 'log10', 'sin', 'sinh', 'sqrt', 'tan', 'tanh'
    ]

for name in simple_math_functions:
    declare(getattr(math, name), float, 'll_math/%s' % name)

# ___________________________________________________________
# win/NT hack: patch ntpath.isabs() to be RPythonic

import ntpath
def isabs(s):
    """Test whether a path is absolute"""
    s = ntpath.splitdrive(s)[1]
    return s != '' and s[0] in '/\\'
ntpath.isabs = isabs

# ___________________________________________________________
# string->float helper
from pypy.rpython import rarithmetic
declare(rarithmetic.parts_to_float, float, 'll_strtod/parts_to_float')
# float->string helper
declare(rarithmetic.formatd, str, 'll_strtod/formatd')

# ___________________________________________________________
# special helpers for os with no equivalent
from pypy.rpython import ros
declare(ros.putenv, noneannotation, 'll_os/putenv')
declare(ros.environ, strnullannotation, 'll_os/environ')
declare(ros.opendir, ros.DIR, 'll_os/opendir')
declareptrtype(ros.DIR, "DIR",
               readdir = (strnullannotation, 'll_os/readdir'),
               closedir = (noneannotation,   'll_os/closedir'))

# ___________________________________________________________
# stackless
from pypy.rpython import rstack
declare(rstack.stack_frames_depth, int, 'll_stackless/stack_frames_depth')
declare(rstack.stack_too_big, bool, 'll_stack/too_big')
declare(rstack.stack_check, noneannotation, 'll_stack/check')
declare(rstack.stack_unwind, noneannotation, 'll_stack/unwind')
frametop_type_info = declareptrtype(rstack.frame_stack_top, 'frame_stack_top',
                                        switch = (rstack.frame_stack_top,
                                                  'll_stackless/switch'))

# ___________________________________________________________
# javascript
from pypy.rpython import rjs
declare(rjs.jseval, str, 'll_js/jseval')

# ___________________________________________________________
# the exceptions that can be implicitely raised by some operations
standardexceptions = {
    TypeError        : True,
    OverflowError    : True,
    ValueError       : True,
    ZeroDivisionError: True,
    MemoryError      : True,
    IOError          : True,
    OSError          : True,
    StopIteration    : True,
    KeyError         : True,
    IndexError       : True,
    AssertionError   : True,
    RuntimeError     : True,
    }
