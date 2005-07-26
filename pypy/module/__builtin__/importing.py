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

def try_import_mod(space, w_modulename, filename, w_parent, w_name, pkgdir=None):
    if os.path.exists(filename):
        w = space.wrap
        w_mod = w(Module(space, w_modulename))
        space.sys.setmodule(w_mod)
        space.setattr(w_mod, w('__file__'), space.wrap(filename))
        space.setattr(w_mod, w('__doc__'), space.w_None)
        if pkgdir is not None:
            space.setattr(w_mod, w('__path__'), space.newlist([w(pkgdir)]))

        e = None
        try:
            fd = os.open(filename, os.O_RDONLY, 0777) # XXX newlines? 
            load_source_module(space, w_modulename, w_mod, filename, fd) 

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
    modulename = '.'.join(prefix + [partname])
    w_modulename = w(modulename)
    w_mod = check_sys_modules(space, w_modulename)
    if w_mod is not None:
        if not space.is_true(space.is_(w_mod, space.w_None)):
            return w_mod
    else:
        w_mod = space.sys.getmodule(modulename) 
        if w_mod is not None:
            return w_mod
        
        if w_path is not None:
            for path in space.unpackiterable(w_path):
                dir = os.path.join(space.str_w(path), partname)
                if os.path.isdir(dir):
                    fn = os.path.join(dir, '__init__.py')
                    w_mod = try_import_mod(space, w_modulename, fn, w_parent,
                                           w(partname), pkgdir=dir)
                    if w_mod is not None:
                        return w_mod
                fn = os.path.join(space.str_w(path), partname + '.py')
                w_mod = try_import_mod(space, w_modulename, fn, w_parent,
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

# __________________________________________________________________
#
# .pyc file support

"""
   Magic word to reject .pyc files generated by other Python versions.
   It should change for each incompatible change to the bytecode.

   The value of CR and LF is incorporated so if you ever read or write
   a .pyc file in text mode the magic number will be wrong; also, the
   Apple MPW compiler swaps their values, botching string constants.

   The magic numbers must be spaced apart atleast 2 values, as the
   -U interpeter flag will cause MAGIC+1 being used. They have been
   odd numbers for some time now.

   There were a variety of old schemes for setting the magic number.
   The current working scheme is to increment the previous value by
   10.

   Known values:
       Python 1.5:   20121
       Python 1.5.1: 20121
       Python 1.5.2: 20121
       Python 2.0:   50823
       Python 2.0.1: 50823
       Python 2.1:   60202
       Python 2.1.1: 60202
       Python 2.1.2: 60202
       Python 2.2:   60717
       Python 2.3a0: 62011
       Python 2.3a0: 62021
       Python 2.3a0: 62011 (!)
       Python 2.4a0: 62041
       Python 2.4a3: 62051
       Python 2.4b1: 62061
"""

# XXX how do we configure this ???
MAGIC = 62061 | (ord('\r')<<16) | (ord('\n')<<24)

"""Magic word as global; note that _PyImport_Init() can change the
   value of this global to accommodate for alterations of how the
   compiler works which are enabled by command line switches.
"""

pyc_magic = MAGIC


PLAN = """
have a function that finds a .py or .pyc file and decides what to use.

CPython: Looks into both and uses .pyc if alone.
We want this option, too, but disabled.

implement
- check_compiled_module()
- read_compiled_module
     header is skipped
     check for valid code object
- load_compiled_module
- load_source_module
- write_compiled_module
    called by load_source_module (maybe also optional)

- load_module
    loads what it gets, flag controls mode decision.
    move the module creation stuff from try_import_mod into
    load_module.
    
modify imp_execfile to accept .pyc files as well.
The decision what to use has been driven, already.
"""

def load_module(space, name, fd, type): # XXX later: loader):
    """
    Load an external module using the default search path and return
    its module object.
    """

def load_source_module(space, w_modulename, w_mod, pathname, fd):
    """
    Load a source module from a given file and return its module
    object.  XXX Wrong: If there's a matching byte-compiled file, use that instead.
    """
    w = space.wrap
    try:
        size = os.fstat(fd)[6]
        source = os.read(fd, size)
    finally:
        os.close(fd)
        
    w_source = w(source)
    w_mode = w("exec")
    w_pathname = w(pathname)
    w_code = space.builtin.call('compile', w_source, w_pathname, w_mode) 
    pycode = space.interpclass_w(w_code)

    w_dict = space.getattr(w_mod, w('__dict__'))                                      
    space.call_method(w_dict, 'setdefault', 
                      w('__builtins__'), 
                      w(space.builtin))
    pycode.exec_code(space, w_dict, w_dict) 

    #XXX write file 

    return w_mod

# helper, to avoid exposing internals ofmarshal
def r_long(fd):
    a = ord(os.read(fd, 1))
    b = ord(os.read(fd, 1))
    c = ord(os.read(fd, 1))
    d = ord(os.read(fd, 1))
    x = a | (b<<8) | (c<<16) | (d<<24)
    if d & 0x80 and x > 0:
        x = -((1L<<32) - x)
    return int(x)

def check_compiled_module(space, pathname, mtime, cpathname):
    """
    Given a pathname for a Python source file, its time of last
    modification, and a pathname for a compiled file, check whether the
    compiled file represents the same version of the source.  If so,
    return a FILE pointer for the compiled file, positioned just after
    the header; if not, return NULL.
    Doesn't set an exception.
    """
    #w_marshal = space.getbuiltinmodule('marshal')
    fd = os.open(cpathname, os.O_BINARY | os.O_RDONLY, 0777) # using no defaults
    magic = r_long(fd)
    if magic != pyc_magic:
        # XXX what to do about Py_VerboseFlag ?
        # PySys_WriteStderr("# %s has bad magic\n", cpathname);
        os.close(fd)
        return -1
    pyc_mtime = r_long(fd)
    if pyc_mtime != mtime:
        # PySys_WriteStderr("# %s has bad mtime\n", cpathname);
        os.close(fd)
        return -1
    # if (Py_VerboseFlag)
        # PySys_WriteStderr("# %s matches %s\n", cpathname, pathname);
    return fd

def load_compiled_module(space, name, cpathname, fd):
    """
    Load a module from a compiled file, execute it, and return its
    module object.
    """

def read_compiled_module(space, cpathname, fd):
    """ Read a code object from a file and check it for validity """


def write_compiled_module(space, co, cpathname, mtime):
    """
    Write a compiled module to a file, placing the time of last
    modification of its source into the header.
    Errors are ignored, if a write error occurs an attempt is made to
    remove the file.
    """
