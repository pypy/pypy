"""Flow Graph Pickling

This file contains the necessary plumbing for pickle.py

note that cPickle respected copy_reg for local since
a long time. Pickle still seems to ignore it.
"""

from pickle import Pickler, loads, dumps, PicklingError
from types import *
import copy_reg
from copy_reg import dispatch_table

# taken from Stackless' pickle correction patch:
if 1:
    def save_function(self, obj):
        print "SAVE_GLOB:", obj
        try:
            return self.save_global(obj)
        except PicklingError, e:
            print e
            pass
        # Check copy_reg.dispatch_table
        reduce = dispatch_table.get(type(obj))
        if reduce:
            rv = reduce(obj)
        else:
            # Check for a __reduce_ex__ method, fall back to __reduce__
            reduce = getattr(obj, "__reduce_ex__", None)
            if reduce:
                rv = reduce(self.proto)
            else:
                reduce = getattr(obj, "__reduce__", None)
                if reduce:
                    rv = reduce()
                else:
                    raise e
        return self.save_reduce(obj=obj, *rv)

def run_patched(func, *args, **kwds):
    dispatch = Pickler.dispatch
    hold = dispatch[FunctionType]
    table = dispatch_table.copy()
    try:
        dispatch[FunctionType] = save_global_fallback
        copy_reg.pickle(FunctionType, func_reduce)
        return func(*args, **kwds)
    finally:
        dispatch[FunctionType] = hold
        dispatch_table.clear()
        dispatch_table.update(table)

def func_reduce(f):
    print "FUNC:", f, f.func_globals.get(__name__, "NAME?")
    print "class_:", getattr(f,"class_", None)
    global hack
    hack = f
    #if hasattr(f, 'class_'):
    #    return (func_class_restore, (f.class_, f.__name__))
    return (func_restore, (f.func_code, f.func_globals and {},
                           f.func_name, f.func_defaults,
                           ()and f.func_closure),)##!! f.func_dict)

def builtin_meth_reduce(m):
    print "BUILTIN METH:", m
    return (builtin_meth_restore, (m.__name__, m.__self__))

def builtin_meth_restore(name, obj):
    return getattr(obj, name)

def func_class_restore(klass, name):
    return getattr(klass, name).im_func

def func_restore(*args):
    # general fallback
    return FunctionType(*args)

def code_reduce(c):
    return (code_restore, (c.co_argcount, c.co_nlocals, c.co_stacksize,
                           c.co_flags, c.co_code, c.co_consts, c.co_names,
                           c.co_varnames, c.co_filename, c.co_name,
                           c.co_firstlineno, c.co_lnotab, c.co_freevars,
                           c.co_cellvars) )

def code_restore(*args):
    return CodeType(*args)

class dummy: pass

type_registry = {
    FunctionType: lambda:1,
    NoneType:     None,
    ClassType:    dummy,
    }

def type_reduce(t):
    try:
        return type_restore, (type_registry[t],)
    except KeyError:
        print 79*"_"
        raise PicklingError, "cannot reduce type %r" % t

def type_restore(*args):
    return type(args[0])

def mydumps(*args, **kwds):
    return run_patched(dumps, *args, **kwds)

