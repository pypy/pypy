"""
Implementation of the interpreter-level default import logic.
"""

import sys, os

from pypy.interpreter.module import Module
from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import W_Root, ObjSpace

# XXX this uses the os.path module at interp-level, which means
# XXX that translate_pypy will produce a translated version of
# XXX PyPy that will only run on the same platform, as it contains
# XXX a frozen version of some routines of only one of the
# XXX posixpath/ntpath/macpath modules.


def try_import_mod(space, w_modulename, f, w_parent, w_name, pkgdir=None):
    w = space.wrap
    if os.path.exists(f):
        w_mod = space.wrap(Module(space, w_modulename))
        space.sys.setmodule(w_mod)
        space.setattr(w_mod, w('__file__'), w(f))
        space.setattr(w_mod, w('__doc__'), space.w_None)        
        if pkgdir is not None:
            space.setattr(w_mod, w('__path__'), space.newlist([w(pkgdir)]))
        w_dict = space.getattr(w_mod, w('__dict__'))
        e = None
        try:
            space.builtin.call('execfile', w(f), w_dict, w_dict)
        except OperationError, e:
            if e.match(space, space.w_SyntaxError):
                w_mods = space.sys.get('modules')
                try:
                    space.delitem(w_mods, w_modulename)
                except OperationError, kerr:
                    if not kerr.match(space, space.w_KeyError):
                        raise
        w_mod = check_sys_modules(space, w_modulename)
        if w_mod is not None and w_parent is not None:
            space.setattr(w_parent, w_name, w_mod)
        if e:
            raise e
        return w_mod
    else:
        return None

def try_getattr(space, w_obj, w_name):
    try:
        return space.getattr(w_obj, w_name)
    except OperationError, e:
        # ugh, but blame CPython :-/ this is supposed to emulate
        # hasattr, which eats all exceptions.
        return None

def try_getitem(space, w_obj, w_key):
    try:
        return space.getitem(w_obj, w_key)
    except OperationError, e:
        if not e.match(space, space.w_KeyError):
            raise
        return None


def check_sys_modules(space, w_modulename):
    w_modules = space.sys.get('modules')
    try:
        w_mod = space.getitem(w_modules, w_modulename) 
    except OperationError, e:
        pass
    else:
        return w_mod
    if not e.match(space, space.w_KeyError):
        raise
    return None

def importhook(space, modulename, w_globals=None,
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
        ctxt_w_name = try_getitem(space, w_globals, w('__name__'))
        ctxt_w_path = try_getitem(space, w_globals, w('__path__'))
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
            w_mod = check_sys_modules(space, w(rel_modulename))
            if (w_mod is None or
                not space.is_true(space.is_(w_mod,space.w_None))):
                
                w_mod = absolute_import(space, rel_modulename,
                                        len(ctxt_name_prefix_parts),
                                        w_fromlist, tentative=1)
                if w_mod is not None:
                    return w_mod
            else:
                rel_modulename = None

    w_mod = absolute_import(space, modulename, 0, w_fromlist, tentative=0)
    if rel_modulename is not None:
        space.setitem(space.sys.get('modules'), w(rel_modulename),space.w_None)
    return w_mod
#
importhook.unwrap_spec = [ObjSpace,str,W_Root,W_Root,W_Root]

def absolute_import(space, modulename, baselevel, w_fromlist, tentative):
    w = space.wrap
    
    w_mod = None
    parts = modulename.split('.')
    prefix = []
    # it would be nice if we could do here: w_path = space.sys.w_path
    # instead:
    w_path = space.sys.get('path') 

    first = None
    level = 0

    for part in parts:
        w_mod = load_part(space, w_path, prefix, part, w_mod,
                          tentative=tentative)
        if w_mod is None:
            return None

        if baselevel == level:
            first = w_mod
            tentative = 0
        prefix.append(part)
        w_path = try_getattr(space, w_mod, w('__path__'))
        level += 1

    if w_fromlist is not None and space.is_true(w_fromlist):
        if w_path is not None:
            fromlist_w = space.unpackiterable(w_fromlist)
            if len(fromlist_w) == 1 and space.eq_w(fromlist_w[0],w('*')):
                w_all = try_getattr(space, w_mod, w('__all__'))
                if w_all is not None:
                    fromlist_w = space.unpackiterable(w_all)
            for w_name in fromlist_w:
                if try_getattr(space, w_mod, w_name) is None:
                    load_part(space, w_path, prefix, space.str_w(w_name), w_mod,
                              tentative=1)
        return w_mod
    else:
        return first

def load_part(space, w_path, prefix, partname, w_parent, tentative):
    w = space.wrap
    modulename = '.'.join(prefix+[partname])
    w_modulename = w(modulename)
    w_mod = check_sys_modules(space, w_modulename)
    if w_mod is not None:
        if not space.is_true(space.is_(w_mod,space.w_None)):
            return w_mod
    else:
        w_mod = space.sys.getmodule(modulename) 
        if w_mod is not None:
            return w_mod
        
        if w_path is not None:
            for path in space.unpackiterable(w_path):
                dir = os.path.join(space.str_w(path), partname)
                if os.path.isdir(dir):
                    f = os.path.join(dir,'__init__.py')
                    w_mod = try_import_mod(space, w_modulename, f, w_parent,
                                           w(partname), pkgdir=dir)
                    if w_mod is not None:
                        return w_mod
                f = os.path.join(space.str_w(path), partname + '.py')
                w_mod = try_import_mod(space, w_modulename, f, w_parent,
                                       w(partname))
                if w_mod is not None:
                    return w_mod

    if tentative:
        return None
    else:
        # ImportError
        w_failing = w_modulename
        w_exc = space.call_function(space.w_ImportError, w_failing)
        raise OperationError(space.w_ImportError, w_exc)
