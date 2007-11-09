"""
information table about external functions for annotation/rtyping and backends
"""

import os
import time
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

def noneannotation(*args):
    return None

def posannotation(*args):
    from pypy.annotation.model import SomeInteger
    return SomeInteger(nonneg=True)

def strnullannotation(*args):
    from pypy.annotation.model import SomeString
    return SomeString(can_be_None=True)

# external function declarations
declare(os.path.exists, bool        , 'll_os_path/exists')
declare(os.path.isdir, bool         , 'll_os_path/isdir')

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
    UnicodeDecodeError: True,
    UnicodeEncodeError: True,
    }

