"""
Implementation of interpreter-level builtins.
"""
import os
from pypy.interpreter.module import Module
from pypy.interpreter.pycode import PyCode
from pypy.interpreter.error import OperationError
_noarg = object()

import __builtin__ as cpy_builtin
w_file = space.wrap(cpy_builtin.file)

# import useful app-level functions
from __applevel__ import execfile, callable, _iter_generator


def _actframe(position=0):
    return space.getexecutioncontext().framestack.top(position)

def globals():
    return _actframe().w_globals

def locals():
    return _actframe().getdictscope()

def _caller_globals(w_index=None):
    position = space.unwrapdefault(w_index, 1)
    return _actframe(position).w_globals

def _caller_locals(w_index=None):
    position = space.unwrapdefault(w_index, 1)
    return _actframe(position).getdictscope()


def try_import_mod(w_modulename,f):
    w = space.wrap
    if os.path.exists(f):
        w_mod = space.wrap(Module(space, w_modulename))
        space.sys.setmodule(w_mod)
        space.setattr(w_mod, w('__file__'), w(f))
        w_dict = space.getattr(w_mod, w('__dict__'))
        execfile(w(f), w_dict, w_dict)
        return w_mod
    else:
        return None


def __import__(w_modulename, w_globals=None,
               w_locals=None, w_fromlist=None):
    modulename = space.unwrap(w_modulename)
    if not isinstance(modulename, str):
        try:
            helper = ', not ' + modulename.__class__.__name__
        except AttributeError:
            helper = ''
        raise OperationError(space.w_TypeError,
              space.wrap("__import__() argument 1 must be string" + helper))
    w = space.wrap
    try:
        w_mod = space.getitem(space.sys.w_modules, w_modulename)
    except OperationError,e:
        pass
    else:
        return w_mod
    if not e.match(space, space.w_KeyError):
        raise
    w_mod = space.get_builtin_module(modulename)
    if w_mod is not None:
        return w_mod

    import os
    for path in space.unpackiterable(space.sys.w_path):
        f = os.path.join(space.unwrap(path), modulename + '.py')
        w_mod = try_import_mod(w_modulename,f)
        if w_mod is not None:
            return w_mod
        dir = os.path.join(space.unwrap(path),modulename)
        if not os.path.isdir(dir):
            continue
        f = os.path.join(dir,'__init__.py')
        w_mod = try_import_mod(w_modulename,f)
        if w_mod is not None:
            return w_mod
        
    w_exc = space.call_function(space.w_ImportError, w_modulename)
    raise OperationError(space.w_ImportError, w_exc)


def compile(w_str, w_filename, w_startstr,
            w_supplied_flags=None, w_dont_inherit=None):
    str_ = space.unwrap(w_str)
    filename = space.unwrap(w_filename)
    startstr = space.unwrap(w_startstr)
    supplied_flags = space.unwrapdefault(w_supplied_flags, 0)
    dont_inherit   = space.unwrapdefault(w_dont_inherit, 0)

    #print (str_, filename, startstr, supplied_flags, dont_inherit)
    # XXX we additionally allow GENERATORS because compiling some builtins
    #     requires it. doesn't feel quite right to do that here. 
    try:
        c = cpy_builtin.compile(str_, filename, startstr, supplied_flags|4096, dont_inherit)
    # It would be nice to propagate all exceptions to app level,
    # but here we only propagate the 'usual' ones, until we figure
    # out how to do it generically.
    except ValueError,e:
        raise OperationError(space.w_ValueError,space.wrap(str(e)))
    except TypeError,e:
        raise OperationError(space.w_TypeError,space.wrap(str(e)))
    return space.wrap(PyCode()._from_code(c))

def eval(w_source, w_globals=None, w_locals=None):
    w = space.wrap

    if space.is_true(space.isinstance(w_source, space.w_str)):
        w_codeobj = compile(w_source, w("<string>"), w("eval"))
    elif isinstance(space.unwrap(w_source), PyCode):
        w_codeobj = w_source
    else:
        raise OperationError(space.w_TypeError,
              w('eval() arg 1 must be a string or code object'))

    if w_globals is None:
        w_globals = globals()
        w_locals = locals()
    elif w_locals is None:
        w_locals = w_globals

    return space.unwrap(w_codeobj).exec_code(space, w_globals, w_locals)

def abs(w_val):
    return space.abs(w_val)

def chr(w_ascii):
    w_character = space.newstring([w_ascii])
    return w_character

def len(w_obj):
    return space.len(w_obj)

def delattr(w_object, w_name):
    space.delattr(w_object, w_name)
    return space.w_None

def getattr(w_object, w_name, w_defvalue = _noarg):
    try:
        return space.getattr(w_object, w_name)
    except OperationError, e:
        if e.match(space, space.w_AttributeError):
            if w_defvalue is not _noarg:
                return w_defvalue
        raise

def hash(w_object):
    return space.hash(w_object)

def oct(w_val):
    # XXX does this need to be a space operation? 
    return space.oct(w_val)

def hex(w_val):
    return space.hex(w_val)

def round(w_val, w_n=None):
    if w_n is None:
        w_n = space.wrap(0)
    return space.round(w_val, w_n)

def id(w_object):
    return space.id(w_object)

#XXX works only for new-style classes.
#So we have to fix it, when we add support for old-style classes
def issubclass(w_cls1, w_cls2):
    return space.issubtype(w_cls1, w_cls2)

def iter(w_collection_or_callable, w_sentinel = _noarg):
    if w_sentinel is _noarg:
        return space.iter(w_collection_or_callable)
    else:
        if not space.is_true(callable(w_collection_or_callable)):
            raise OperationError(space.w_TypeError,
                    space.wrap('iter(v, w): v must be callable'))
        return _iter_generator(w_collection_or_callable, w_sentinel)

def ord(w_val):
    return space.ord(w_val)

def pow(w_base, w_exponent, w_modulus=None):
    if w_modulus is None:
        w_modulus = space.w_None
    return space.pow(w_base, w_exponent, w_modulus)

def repr(w_object):
    return space.repr(w_object)

def setattr(w_object, w_name, w_val):
    space.setattr(w_object, w_name, w_val)
    return space.w_None

def _pypy_get(w_value, w_self, w_class=None):   # XXX temporary
    if w_class is None:
        w_class = space.w_None
    return space.get(w_value, w_self, w_class)
