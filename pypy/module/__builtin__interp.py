"""
Implementation of interpreter-level builtins.
"""
from pypy.interpreter.module import Module
from pypy.interpreter.pycode import PyCode
from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import BaseWrappable, W_Root
from pypy.interpreter.gateway import NoneNotWrapped

import __builtin__ as cpy_builtin

# import useful app-level functions
from __applevel__ import execfile, callable, _iter_generator


def _actframe(position=0):
    return space.getexecutioncontext().framestack.top(position)

def globals():
    return _actframe().w_globals

def locals():
    return _actframe().getdictscope()

def _caller_globals(position=1):
    return _actframe(position).w_globals
#
_caller_globals.unwrap_spec = [int]

def _caller_locals(position=1):
    return _actframe(position).getdictscope()
#
_caller_locals.unwrap_spec = [int]


def try_import_mod(w_modulename, f, w_parent, w_name, pkgdir=None):
    import os
    w = space.wrap
    if os.path.exists(f):
        w_mod = space.wrap(Module(space, w_modulename))
        space.sys.setmodule(w_mod)
        space.setattr(w_mod, w('__file__'), w(f))
        if pkgdir is not None:
            space.setattr(w_mod, w('__path__'), space.newlist([w(pkgdir)]))
        w_dict = space.getattr(w_mod, w('__dict__'))
        execfile(w(f), w_dict, w_dict)
        w_mod = check_sys_modules(w_modulename)
        if w_mod is not None and w_parent is not None:
            space.setattr(w_parent, w_name, w_mod)
        return w_mod
    else:
        return None

def try_getattr(w_obj,w_name):
    try:
        return space.getattr(w_obj, w_name)
    except OperationError, e:
        # ugh, but blame CPython :-/ this is supposed to emulate
        # hasattr, which eats all exceptions.
        return None

def try_getitem(w_obj,w_key):
    try:
        return space.getitem(w_obj, w_key)
    except OperationError, e:
        if not e.match(space, space.w_KeyError):
            raise
        return None


def check_sys_modules(w_modulename):
    try:
        w_mod = space.getitem(space.sys.w_modules, w_modulename)
    except OperationError, e:
        pass
    else:
        return w_mod
    if not e.match(space, space.w_KeyError):
        raise
    return None

il_len = len

def __import__(modulename, w_globals=None,
               w_locals=None, w_fromlist=None):
    if not isinstance(modulename, str):
        try:
            helper = ', not ' + modulename.__class__.__name__
        except AttributeError:
            helper = ''
        raise OperationError(space.w_TypeError,
              space.wrap("__import__() argument 1 must be string" + helper))
    w = space.wrap

    if w_globals is not None and not space.is_true(space.is_(w_globals, space.w_None)):
        ctxt_w_name = try_getitem(w_globals,w('__name__'))
        ctxt_w_path = try_getitem(w_globals,w('__path__'))
    else:
        ctxt_w_name = None
        ctxt_w_path = None

    rel_modulename = None
    if ctxt_w_name is not None:

        ctxt_name_prefix_parts = space.str_w(ctxt_w_name).split('.')
        if ctxt_w_path is None: # context is a plain module
            ctxt_name_prefix_parts = ctxt_name_prefix_parts[:-1]
            if ctxt_name_prefix_parts:
                rel_modulename = '.'.join(ctxt_name_prefix_parts+[modulename])
        else: # context is a package module
            rel_modulename = space.str_w(ctxt_w_name)+'.'+modulename
        if rel_modulename is not None:
            w_mod = check_sys_modules(w(rel_modulename))
            if (w_mod is None or
                not space.is_true(space.is_(w_mod,space.w_None))):
                
                w_mod = absolute_import(rel_modulename,
                                        il_len(ctxt_name_prefix_parts),
                                        w_fromlist, tentative=1)
                if w_mod is not None:
                    return w_mod
            else:
                rel_modulename = None

    w_mod = absolute_import(modulename,0,w_fromlist, tentative=0)
    if rel_modulename is not None:
        space.setitem(space.sys.w_modules, w(rel_modulename),space.w_None)
    return w_mod
#
__import__.unwrap_spec = [str,W_Root,W_Root,W_Root]

def absolute_import(modulename, baselevel, w_fromlist, tentative):
    w = space.wrap
    
    w_mod = None
    parts = modulename.split('.')
    prefix = []
    # it would be nice if we could do here: w_path = space.sys.w_path
    # instead:
    w_path = space.getitem(space.sys.w_dict, space.wrap('path'))

    first = None
    level = 0

    for part in parts:
        w_mod = load_part(w_path, prefix, part, w_mod, tentative=tentative)
        if w_mod is None:
            return None

        if baselevel == level:
            first = w_mod
            tentative = 0
        prefix.append(part)
        w_path = try_getattr(w_mod,w('__path__'))
        level += 1

    if w_fromlist is not None and space.is_true(w_fromlist):
        if w_path is not None:
            for w_name in space.unpackiterable(w_fromlist):
                load_part(w_path, prefix, space.str_w(w_name), w_mod,
                          tentative=1)
        return w_mod
    else:
        return first

def load_part(w_path, prefix, partname, w_parent, tentative):
    w = space.wrap
    modulename = '.'.join(prefix+[partname])
    w_modulename = w(modulename)
    w_mod = check_sys_modules(w_modulename)
    if w_mod is not None:
        if not space.is_true(space.is_(w_mod,space.w_None)):
            return w_mod
    else:
        w_mod = space.get_builtin_module(modulename)
        if w_mod is not None:
            return w_mod
        import os
        for path in space.unpackiterable(w_path):
            dir = os.path.join(space.str_w(path), partname)
            if os.path.isdir(dir):
                f = os.path.join(dir,'__init__.py')
                w_mod = try_import_mod(w_modulename, f, w_parent, w(partname),
                                       pkgdir=dir)
                if w_mod is not None:
                    return w_mod
            f = os.path.join(space.str_w(path), partname + '.py')
            w_mod = try_import_mod(w_modulename, f, w_parent, w(partname))
            if w_mod is not None:
                return w_mod

    if tentative:
        return None
    else:
        # ImportError
        w_failing = w_modulename
        w_exc = space.call_function(space.w_ImportError, w_failing)
        raise OperationError(space.w_ImportError, w_exc)

def compile(w_str_, w_filename, w_startstr,
            w_supplied_flags=None, w_dont_inherit=None):
    if space.is_true(space.isinstance(w_str_, space.w_unicode)):
        str_ = space.unwrap(w_str_)
    else:
        str_ = space.str_w(w_str_)
    filename = space.str_w(w_filename)
    startstr = space.str_w(w_startstr)
    supplied_flags = 0
    if not space.is_w(w_supplied_flags, space.w_None):
        supplied_flags = space.int_w(w_supplied_flags)
    dont_inherit = 0
    if not space.is_w(w_dont_inherit, space.w_None):
        dont_inherit = space.int_w(w_dont_inherit)
    #print (str_, filename, startstr, supplied_flags, dont_inherit)
    # XXX we additionally allow GENERATORS because compiling some builtins
    #     requires it. doesn't feel quite right to do that here.
    supplied_flags |= 4096 
    if not dont_inherit:
        try:
            frame = _actframe()
        except IndexError:
            pass
        else:
            supplied_flags |= frame.get_compile_flags()
    try:
        c = cpy_builtin.compile(str_, filename, startstr, supplied_flags, 1)
    # It would be nice to propagate all exceptions to app level,
    # but here we only propagate the 'usual' ones, until we figure
    # out how to do it generically.
    except SyntaxError,e:
        raise OperationError(space.w_SyntaxError,space.wrap(str(e)))
    except ValueError,e:
        raise OperationError(space.w_ValueError,space.wrap(str(e)))
    except TypeError,e:
        raise OperationError(space.w_TypeError,space.wrap(str(e)))
    return space.wrap(PyCode(space)._from_code(c))
#
#compile.unwrap_spec = [str,str,str,int,int]


def eval(w_source, w_globals=NoneNotWrapped, w_locals=NoneNotWrapped):
    w = space.wrap

    if (space.is_true(space.isinstance(w_source, space.w_str)) or
        space.is_true(space.isinstance(w_source, space.w_unicode))):
        w_codeobj = compile(space.call_method(w_source, 'lstrip', space.wrap(' \t')), space.wrap("<string>"), space.wrap("eval"), space.w_None, space.w_None)
    elif isinstance(space.interpclass_w(w_source), PyCode):
        w_codeobj = w_source
    else:
        raise OperationError(space.w_TypeError,
              w('eval() arg 1 must be a string or code object'))

    if w_globals is None:
        w_globals = globals()
        w_locals = locals()
    elif w_locals is None:
        w_locals = w_globals

    return space.interpclass_w(w_codeobj).exec_code(space, w_globals, w_locals)

def abs(w_val):
    "abs(number) -> number\n\nReturn the absolute value of the argument."
    return space.abs(w_val)

def chr(w_ascii):
    w_character = space.newstring([w_ascii])
    return w_character

def len(w_obj):
    return space.len(w_obj)

def delattr(w_object, w_name):
    space.delattr(w_object, w_name)
    return space.w_None

def getattr(w_object, w_name, w_defvalue=NoneNotWrapped):
    if space.is_true(space.isinstance(w_name, space.w_unicode)):
        w_name = space.call_method(w_name, 'encode')
    try:
        return space.getattr(w_object, w_name)
    except OperationError, e:
        if e.match(space, space.w_AttributeError):
            if w_defvalue is not None:
                return w_defvalue
        raise

def hash(w_object):
    return space.hash(w_object)

def oct(w_val):
    # XXX does this need to be a space operation?
    return space.oct(w_val)

def hex(w_val):
    return space.hex(w_val)

def round(w_val, w_n=0):
    return space.round(w_val, w_n)

def id(w_object):
    return space.id(w_object)

def cmp(w_x, w_y):
    """return 0 when x == y, -1 when x < y and 1 when x > y """
    return space.cmp(w_x, w_y)

def coerce(w_x, w_y):
    """coerce(x, y) -> (x1, y1)

    Return a tuple consisting of the two numeric arguments converted to
    a common type, using the same rules as used by arithmetic operations.
    If coercion is not possible, raise TypeError."""
    return space.coerce(w_x, w_y)


#XXX works only for new-style classes.
#So we have to fix it, when we add support for old-style classes
def _issubtype(w_cls1, w_cls2):
    return space.issubtype(w_cls1, w_cls2)

def iter(w_collection_or_callable, w_sentinel=NoneNotWrapped):
    if w_sentinel is None:
        return space.iter(w_collection_or_callable)
    else:
        if not space.is_true(callable(w_collection_or_callable)):
            raise OperationError(space.w_TypeError,
                    space.wrap('iter(v, w): w must be callable'))
        return _iter_generator(w_collection_or_callable, w_sentinel)

def _seqiter(w_obj):
    return space.newseqiter(w_obj)

def ord(w_val):
    return space.ord(w_val)

def pow(w_base, w_exponent, w_modulus=None):
    return space.pow(w_base, w_exponent, w_modulus)

def repr(w_object):
    return space.repr(w_object)

def setattr(w_object, w_name, w_val):
    space.setattr(w_object, w_name, w_val)
    return space.w_None
