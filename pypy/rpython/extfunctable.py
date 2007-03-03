"""
information table about external functions for annotation/rtyping and backends
"""
import os
import time
import math
import types
from pypy.rlib.rarithmetic import r_longlong

class ExtFuncInfo:
    def __init__(self, func, annotation, ll_function_path, ll_annotable, backend_functiontemplate):
        self.func = func
        self.ll_function_path = ll_function_path
        self.annotation = annotation
        self.ll_annotable = ll_annotable
        self.backend_functiontemplate = backend_functiontemplate

    def get_ll_function(self, type_system):
        """Get the ll_*() function implementing the given high-level 'func'."""
        modulename, tail = self.ll_function_path.split('/')
        if '.' not in modulename:
            modulename = 'pypy.rpython.module.%s' % modulename
        mod = self.import_module(modulename)
        lastmodulename = modulename[modulename.rfind('.')+1:]
        ll_function_name = '%s_%s' % (lastmodulename, tail)
        try:
            ll_function = getattr(mod, ll_function_name)
        except AttributeError:
            mod = self.import_module("pypy.rpython.%s.module.%s"
                    % (type_system.name, lastmodulename))
            ll_function = getattr(mod.Implementation, ll_function_name)
        return ll_function

    def import_module(self, module_name):
        ll_module = ImportMe(module_name)
        return ll_module.load()


class ExtTypeInfo:
    def __init__(self, typ, tag, methods,
                 needs_container=True, needs_gc=False):
        self.typ = typ
        self.tag = tag
        self._TYPE = None
        self.methods = methods     # {'name': ExtFuncInfo()}
        self.needs_container = needs_container
        self.needs_gc = needs_gc

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
            if self.needs_gc:
                OPAQUE = lltype.GcOpaqueType(self.tag)
            else:
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
def declaretype1(typ, tag, methodsdecl, needs_container, needs_gc=False):
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
    info = ExtTypeInfo(typ, tag, methods, needs_container, needs_gc)
    typetable[typ] = info
    for callback in table_callbacks:
        callback()
    return info

def declaretype(typ, tag, **methodsdecl):
    return declaretype1(typ, tag, methodsdecl, needs_container=True)

def declareptrtype(typ, tag, **methodsdecl):
    return declaretype1(typ, tag, methodsdecl, needs_container=False)

def declaregcptrtype(typ, tag, **methodsdecl):
    return declaretype1(typ, tag, methodsdecl, needs_container=False,
                        needs_gc=True)

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
    from pypy.rpython.lltypesystem.module.ll_os import Implementation
    from pypy.annotation.model import SomeInteger, SomeTuple
    record_call(Implementation.ll_stat_result, [SomeInteger()]*10, 'OS_STAT')
    return SomeTuple((SomeInteger(),)*10)

def pipeannotation(*args):
    from pypy.rpython.lltypesystem.module.ll_os import Implementation
    from pypy.annotation.model import SomeInteger, SomeTuple
    record_call(Implementation.ll_pipe_result, [SomeInteger()]*2, 'OS_PIPE')
    return SomeTuple((SomeInteger(),)*2)

def waitpidannotation(*args):
    from pypy.rpython.lltypesystem.module.ll_os import Implementation
    from pypy.annotation.model import SomeInteger, SomeTuple
    record_call(Implementation.ll_waitpid_result, [SomeInteger()]*2,
                'OS_WAITPID')
    return SomeTuple((SomeInteger(),)*2)

def strnullannotation(*args):
    from pypy.annotation.model import SomeString
    return SomeString(can_be_None=True)

# external function declarations
posix = __import__(os.name)
declare(os.open     , int           , 'll_os/open')
declare(os.read     , str           , 'll_os/read')
declare(os.write    , posannotation , 'll_os/write')
declare(os.close    , noneannotation, 'll_os/close')
declare(os.access   , int           , 'll_os/access')
declare(os.lseek    , r_longlong    , 'll_os/lseek')
declare(os.isatty   , bool          , 'll_os/isatty')
if hasattr(posix, 'ftruncate'):
    declare(os.ftruncate, noneannotation, 'll_os/ftruncate')
declare(os.fstat    , statannotation, 'll_os/fstat')
declare(os.stat     , statannotation, 'll_os/stat')
declare(os.lstat    , statannotation, 'll_os/lstat')
declare(os.system   , int           , 'll_os/system')
declare(os.strerror , str           , 'll_os/strerror')
declare(os.unlink   , noneannotation, 'll_os/unlink')
declare(os.getcwd   , str           , 'll_os/getcwd')
declare(os.chdir    , noneannotation, 'll_os/chdir')
declare(os.mkdir    , noneannotation, 'll_os/mkdir')
declare(os.rmdir    , noneannotation, 'll_os/rmdir')
if hasattr(posix, 'unsetenv'):   # note: faked in os
    declare(os.unsetenv , noneannotation, 'll_os/unsetenv')
declare(os.pipe     , pipeannotation, 'll_os/pipe')
declare(os.chmod    , noneannotation, 'll_os/chmod')
declare(os.rename   , noneannotation, 'll_os/rename')
declare(os.umask    , int           , 'll_os/umask')
declare(os._exit    , noneannotation, 'll_os/_exit')
if hasattr(os, 'kill'):
    declare(os.kill     , noneannotation, 'll_os/kill')
if hasattr(os, 'getpid'):
    declare(os.getpid   , int,            'll_os/getpid')
if hasattr(os, 'link'):
    declare(os.link     , noneannotation, 'll_os/link')
if hasattr(os, 'symlink'):
    declare(os.symlink  , noneannotation, 'll_os/symlink')
if hasattr(os, 'readlink'):
    declare(os.readlink , str,            'll_os/readlink')
if hasattr(os, 'fork'):
    declare(os.fork ,     int,            'll_os/fork')
if hasattr(os, 'spawnv'):
    declare(os.spawnv,    int,            'll_os/spawnv')
if hasattr(os, 'waitpid'):
    declare(os.waitpid ,  waitpidannotation, 'll_os/waitpid')
#if hasattr(os, 'execv'):
#    declare(os.execv, noneannotation, 'll_os/execv')
#    declare(os.execve, noneannotation, 'll_os/execve')

declare(os.path.exists, bool        , 'll_os_path/exists')
declare(os.path.isdir, bool         , 'll_os_path/isdir')
declare(time.time   , float         , 'll_time/time')
declare(time.clock  , float         , 'll_time/clock')
declare(time.sleep  , noneannotation, 'll_time/sleep')

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
from pypy.rlib import rarithmetic
declare(rarithmetic.parts_to_float, float, 'll_strtod/parts_to_float')
# float->string helper
declare(rarithmetic.formatd, str, 'll_strtod/formatd')

# ___________________________________________________________
# special helpers for os with no equivalent
from pypy.rlib import ros
declare(ros.putenv, noneannotation, 'll_os/putenv')
declare(ros.environ, strnullannotation, 'll_os/environ')
declare(ros.opendir, ros.DIR, 'll_os/opendir')
declareptrtype(ros.DIR, "DIR",
               readdir = (strnullannotation, 'll_os/readdir'),
               closedir = (noneannotation,   'll_os/closedir'))

# ___________________________________________________________
# stackless
from pypy.rlib import rstack
declare(rstack.stack_frames_depth, int, 'll_stackless/stack_frames_depth')
declare(rstack.stack_too_big, bool, 'll_stack/too_big')
declare(rstack.stack_check, noneannotation, 'll_stack/check')
declare(rstack.stack_unwind, noneannotation, 'll_stack/unwind')
declare(rstack.stack_capture, rstack.frame_stack_top, 'll_stack/capture')
frametop_type_info = declaregcptrtype(rstack.frame_stack_top,'frame_stack_top',
                                        switch = (rstack.frame_stack_top,
                                                  'll_stackless/switch'))

# ___________________________________________________________
# javascript
from pypy.rlib import rjs
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



# ______________________________________________________________
# this declarations use the new interface for external functions
# all the above declaration should me moved here at some point.

from extfunc import register_external

# ___________________________
# math functions

from pypy.rpython.lltypesystem.module import ll_math
from pypy.rpython.ootypesystem.module import ll_math as oo_math

# the following functions all take one float, return one float
# and are part of math.h
simple_math_functions = [
    'acos', 'asin', 'atan', 'ceil', 'cos', 'cosh', 'exp', 'fabs',
    'floor', 'log', 'log10', 'sin', 'sinh', 'sqrt', 'tan', 'tanh'
    ]
for name in simple_math_functions:
    register_external(getattr(math, name), [float], float, "ll_math.ll_math_%s" % name)

def frexp_hook():
    from pypy.annotation.model import SomeInteger, SomeTuple, SomeFloat
    from pypy.rpython.lltypesystem.module.ll_math import ll_frexp_result
    record_call(ll_frexp_result, (SomeFloat(), SomeInteger()), 'MATH_FREXP')

def modf_hook():
    from pypy.annotation.model import SomeTuple, SomeFloat
    from pypy.rpython.lltypesystem.module.ll_math import ll_modf_result
    record_call(ll_modf_result, (SomeFloat(), SomeFloat()), 'MATH_MODF')

complex_math_functions = [
    ('frexp', [float],        (float, int),   frexp_hook),
    ('atan2', [float, float], float,          None),
    ('fmod',  [float, float], float,          None),
    ('ldexp', [float, int],   float,          None),
    ('modf',  [float],        (float, float), modf_hook),
    ('hypot', [float, float], float,          None),
    ('pow',   [float, float], float,          None),
    ]

for name, args, res, hook in complex_math_functions:
    func = getattr(math, name)
    llfake = getattr(ll_math, 'll_math_%s' % name, None)
    oofake = getattr(oo_math, 'll_math_%s' % name, None)
    register_external(func, args, res, 'll_math.ll_math_%s' % name,
                      llfakeimpl=llfake, oofakeimpl=oofake,
                      annotation_hook = hook)
