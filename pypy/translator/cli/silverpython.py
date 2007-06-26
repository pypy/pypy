#! /usr/bin/env python
"""
Usage:  silverpython.py <module-name>.py

Compiles an RPython module into a .NET dll.
"""

import sys
import new
import types
import os.path

from pypy.translator.driver import TranslationDriver
from pypy.translator.cli.entrypoint import DllEntryPoint

class DllDef:
    def __init__(self, name, namespace, functions=[]):
        self.name = name
        self.namespace = namespace
        self.functions = functions # [(function, annotation), ...]

    def add_function(self, func, inputtypes):
        self.functions.append((func, inputtypes))

    def get_entrypoint(self, bk):
        graphs = [bk.getdesc(f).cachedgraph(None) for f, _ in self.functions]
        return DllEntryPoint(self.name, graphs)

    def compile(self):
        # add all functions to the appropriate namespace
        for func, _ in self.functions:
            if not hasattr(func, '_namespace_'):
                func._namespace_ = self.namespace
        driver = TranslationDriver()
        driver.config.translation.ootype.mangle = False
        driver.setup_library(self)
        driver.proceed(['compile_cli'])
        return driver

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

def collect_entrypoints(dic):
    entrypoints = []
    for item in dic.itervalues():
        if isinstance(item, types.FunctionType) and hasattr(item, '_inputtypes_'):
            entrypoints.append((item, item._inputtypes_))
    return entrypoints

def compile_dll(filename):
    _, name = os.path.split(filename)
    dllname, _ = os.path.splitext(name)

    module = new.module(dllname)
    execfile(filename, module.__dict__)
    entrypoints = collect_entrypoints(module.__dict__)
    namespace = module.__dict__.get('_namespace_', dllname)
    
    dll = DllDef(dllname, namespace, entrypoints)
    driver = dll.compile()
    driver.copy_cli_dll()

def main(argv):
    if len(argv) != 2:
        print >> sys.stderr, __doc__
        sys.exit(2)
    filename = argv[1]
    if not os.path.exists(filename):
        print >> sys.stderr, "Cannot find file %s" % filename
        sys.exit(1)
    compile_dll(filename)    

if __name__ == '__main__':
    main(sys.argv)

