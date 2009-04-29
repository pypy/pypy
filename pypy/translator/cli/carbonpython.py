#! /usr/bin/env python
"""
Usage:  carbonpython.py <module-name> [dll-name]

Compiles an RPython module into a .NET dll.
"""

import sys
import new
import types
import os.path
import inspect

from pypy.translator.driver import TranslationDriver
from pypy.translator.cli.entrypoint import DllEntryPoint

class DllDef:
    def __init__(self, name, namespace, functions=[], dontmangle=True, isnetmodule=False):
        self.name = name
        self.namespace = namespace
        self.functions = functions # [(function, annotation), ...]
        self.isnetmodule = isnetmodule
        self.driver = TranslationDriver()
        if dontmangle:
            self.driver.config.translation.ootype.mangle = False
        self.driver.setup_library(self)

    def add_function(self, func, inputtypes):
        self.functions.append((func, inputtypes))

    def get_entrypoint(self, bk):
        graphs = [bk.getdesc(f).cachedgraph(None) for f, _ in self.functions]
        return DllEntryPoint(self.name, graphs, self.isnetmodule)

    def compile(self):
        # add all functions to the appropriate namespace
        if self.namespace:
            for func, _ in self.functions:
                if not hasattr(func, '_namespace_'):
                    func._namespace_ = self.namespace
        self.driver.proceed(['compile_cli'])

class export(object):
    def __new__(self, *args, **kwds):
        if len(args) == 1 and isinstance(args[0], types.FunctionType):
            func = args[0]
            func._inputtypes_ = ()
            return func
        return object.__new__(self, *args, **kwds)
    
    def __init__(self, *args, **kwds):
        self.inputtypes = args
        self.namespace = kwds.pop('namespace', None)
        if len(kwds) > 0:
            raise TypeError, "unexpected keyword argument: '%s'" % kwds.keys()[0]

    def __call__(self, func):
        func._inputtypes_ = self.inputtypes
        if self.namespace is not None:
            func._namespace_ = self.namespace
        return func

def is_exported(obj):
    return isinstance(obj, (types.FunctionType, types.UnboundMethodType)) \
           and hasattr(obj, '_inputtypes_')

def collect_entrypoints(dic):
    entrypoints = []
    for item in dic.itervalues():
        if is_exported(item):
            entrypoints.append((item, item._inputtypes_))
        elif isinstance(item, types.ClassType) or isinstance(item, type):
            entrypoints += collect_class_entrypoints(item)
    return entrypoints

def collect_class_entrypoints(cls):
    try:
        __init__ = cls.__init__
        if not is_exported(__init__):
            return []
    except AttributeError:
        return []

    entrypoints = [(wrap_init(cls, __init__), __init__._inputtypes_)]
    for item in cls.__dict__.itervalues():
        if item is not __init__.im_func and is_exported(item):
            inputtypes = (cls,) + item._inputtypes_
            entrypoints.append((wrap_method(item), inputtypes))
    return entrypoints

def getarglist(meth):
    arglist, starargs, kwargs, defaults = inspect.getargspec(meth)
    assert starargs is None, '*args not supported yet'
    assert kwargs is None, '**kwds not supported yet'
    assert defaults is None, 'default values not supported yet'
    return arglist

def wrap_init(cls, meth):
    arglist = getarglist(meth)[1:] # discard self
    args = ', '.join(arglist)
    source = 'def __internal__ctor(%s): return %s(%s)' % (
        args, cls.__name__, args)
    mydict = {cls.__name__: cls}
    print source
    exec source in mydict
    return mydict['__internal__ctor']

def wrap_method(meth, is_init=False):
    arglist = getarglist(meth)
    name = '__internal__%s' % meth.func_name
    selfvar = arglist[0]
    args = ', '.join(arglist)
    params = ', '.join(arglist[1:])
    source = 'def %s(%s): return %s.%s(%s)' % (
        name, args, selfvar, meth.func_name, params)
    mydict = {}
    print source
    exec source in mydict
    return mydict[name]


def compile_dll(filename, dllname=None, copy_dll=True):
    dirname, name = os.path.split(filename)
    if dllname is None:
        dllname, _ = os.path.splitext(name)
    elif dllname.endswith('.dll'):
        dllname, _ = os.path.splitext(dllname)
    module = new.module(dllname)
    namespace = module.__dict__.get('_namespace_', dllname)
    sys.path.insert(0, dirname)
    execfile(filename, module.__dict__)
    sys.path.pop(0)

    dll = DllDef(dllname, namespace)
    dll.functions = collect_entrypoints(module.__dict__)
    dll.compile()
    if copy_dll:
        dll.driver.copy_cli_dll()

def main(argv):
    if len(argv) == 2:
        filename = argv[1]
        dllname = None
    elif len(argv) == 3:
        filename = argv[1]
        dllname = argv[2]
    else:
        print >> sys.stderr, __doc__
        sys.exit(2)

    if not filename.endswith('.py'):
        filename += '.py'
    if not os.path.exists(filename):
        print >> sys.stderr, "Cannot find file %s" % filename
        sys.exit(1)
    compile_dll(filename, dllname)

if __name__ == '__main__':
    main(sys.argv)

