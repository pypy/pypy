"""
Generate a llvm .ll file from an annotated flowgraph.
"""

import autopath
import os, sys, exceptions, sets, StringIO

from pypy.objspace.flow.model import Variable, Constant, SpaceOperation
from pypy.objspace.flow.model import FunctionGraph, Block, Link
from pypy.objspace.flow.model import last_exception, last_exc_value
from pypy.objspace.flow.model import traverse, uniqueitems, checkgraph
from pypy.annotation import model as annmodel
from pypy.translator import transform
from pypy.translator.translator import Translator
from pypy.translator.llvm import llvmbc
from pypy.translator.llvm import build_llvm_module
from pypy.translator.test import snippet as test


from pypy.translator.llvm.representation import *


debug = 1


def llvmcompile(transl, optimize=False):
    gen = LLVMGenerator(transl)
    return gen.compile(optimize)

def get_key(obj):
    if isinstance(obj, Constant):
        #To avoid getting "bool true" as representation for int 1
        if obj.value is True or obj.value is False:
            return obj
        return obj.value
    if isinstance(obj, annmodel.SomeInstance):
        return obj.classdef.cls
    return obj

class LLVMGenerator(object):
    def __init__(self, transl):
        self.translator = transl
        self.annotator = self.translator.annotator
##         transform.transform_allocate(self.annotator)
        self.global_counts = {}
        self.local_counts = {}
        self.repr_classes = [eval(s)
                             for s in dir(sys.modules.get(self.__module__))
                             if "Repr" in s]
        self.llvm_reprs = {}
        self.depth = 0
        try:
            self.l_entrypoint = self.get_repr(
                Constant(self.translator.functions[0]))
        except:
##             self.translator.view()
            raise

    def compile(self, optimize=False):
        from pypy.tool.udir import udir
        name = self.l_entrypoint.llvmname()[1:]
        llvmfile = udir.join('%s.ll' % name)
        f = llvmfile.open('w')
        self.write(f)
        f.close()
        pyxfile = udir.join('%s_wrap.pyx' % name)
        f = pyxfile.open('w')
        f.write(self.l_entrypoint.get_pyrex_source())
        f.close()
        mod = build_llvm_module.make_module_from_llvm(llvmfile, pyxfile,
                                                      optimize)
        return getattr(mod, "wrap_%s" % name)

    def get_global_tmp(self, used_by=None):
        used_by = (used_by or "unknown")
        if used_by in self.global_counts:
            self.global_counts[used_by] += 1
            return "%%glb.%s.%i" % (used_by, self.global_counts[used_by])
        else:
            self.global_counts[used_by] = 0
            return "%%glb.%s" % used_by

    def get_local_tmp(self, l_repr):
        self.local_counts[l_repr] += 1
        return "%%tmp_%i" % self.local_counts[l_repr]

    def get_repr(self, obj):
        self.depth += 1
        if debug:
            print "  " * self.depth,
            print "looking for object", obj, type(obj).__name__, obj.__class__,
            print id(obj), get_key(obj),
        if isinstance(obj, LLVMRepr):
            self.depth -= 1
            return obj
        if get_key(obj) in self.llvm_reprs:
            self.depth -= 1
            if debug:
                print "->exists already:", self.llvm_reprs[get_key(obj)]
            return self.llvm_reprs[get_key(obj)]
        for cl in self.repr_classes:
            g = cl.get(obj, self)
            if g is not None:
                self.llvm_reprs[get_key(obj)] = g
                self.local_counts[g] = 0
                if debug:
                    print "  " * self.depth,
                    print "calling setup of %s, repr of %s" % (g, obj)
                g.setup()
                self.depth -= 1
                return g
        raise CompileError, "Can't get repr of %s, %s" % (obj, obj.__class__)

    def write(self, f):
        f.write("\n\n; +-------+\n; |globals|\n; +-------+\n\n")
        seen_reprs = sets.Set()
        for l_repr in traverse_dependencies(self.l_entrypoint, seen_reprs):
            s = l_repr.get_globals()
            if s != "":
                f.write(s + "\n")
        f.write("\n\n; +---------+\n; |space_ops|\n; +---------+\n\n")
        f1 = file(autopath.this_dir + "/operations.ll", "r")
        s = f1.read()
        f.write(s)
        f1.close()
        f.write("\n\n; +---------+\n; |functions|\n; +---------+\n\n")
        seen_reprs = sets.Set()
        for l_repr in traverse_dependencies(self.l_entrypoint, seen_reprs):
            s = l_repr.get_functions()
            if s != "":
                f.write(s + "\n")

    def __str__(self):
        f = StringIO.StringIO()
        self.write(f)
        return f.getvalue()

def traverse_dependencies(l_repr, seen_reprs):
    seen_reprs.add(l_repr)
    for l_dep in l_repr.get_dependencies():
        if l_dep in seen_reprs:
            continue
        seen_reprs.add(l_dep)
        for l_dep1 in traverse_dependencies(l_dep, seen_reprs):
            yield l_dep1
    yield l_repr

