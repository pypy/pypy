"""
This is the entry point of genllvm.d

The class LLVMGenerator coordinates the creation of LLVM representations and
drives the creation of the .ll file and the compilation:
The methods get_repr loops over all Repr classes and calls there static get
method. If this method returns None, it continues searching, else it returns
the object. It caches representations so that only one is generated for a given
object.
"""

import autopath
import sets, StringIO

from pypy.objspace.flow.model import Constant, Variable
from pypy.annotation import model as annmodel

from pypy.rpython import rtyper, lltype

from pypy.translator import transform
from pypy.translator.translator import Translator
from pypy.translator.llvm import llvmbc
from pypy.translator.llvm import build_llvm_module
from pypy.translator.test import snippet as test
from pypy.translator.llvm.test import llvmsnippet as test2

from pypy.translator.llvm import representation, funcrepr, typerepr, seqrepr
from pypy.translator.llvm import classrepr, pbcrepr, pointerrepr

from pypy.translator.llvm.representation import LLVMRepr, TmpVariableRepr
from pypy.translator.llvm.representation import CompileError
from pypy.translator.llvm.funcrepr import EntryFunctionRepr

from pypy.translator.llvm import reprmap

debug = False


def llvmcompile(transl, optimize=False):
    gen = LLVMGenerator(transl)
    return gen.compile(optimize)

def get_key(obj):
    if isinstance(obj, list):
        return id(obj)
    return obj
    #XXX Get rid of this:
    #LLVMGenerator should only cache gen_repr requestes,
    #the Repr classes should be responsible for deciding which queries
    #should result in the same representation
    if isinstance(obj, Constant):
        #To avoid getting "bool true" as representation for int 1
        if obj.value is True or obj.value is False:
            return obj
        try:
            hash(obj.value)
        except TypeError:
            return id(obj.value)
        return obj.value
    if isinstance(obj, annmodel.SomeInstance):
        return obj.classdef.cls
    if isinstance(obj, list):
        return id(obj)
    return obj

class LLVMGenerator(object):
    def __init__(self, transl):
        self.translator = transl
        self.annotator = self.translator.annotator
        self.rtyper = rtyper.RPythonTyper(self.annotator)
        self.rtyper.specialize()
        self.global_counts = {}
        self.local_counts = {}
        self.repr_classes = []
        for mod in [representation, funcrepr, typerepr, pointerrepr]:
            self.repr_classes += [getattr(mod, s)
                                  for s in dir(mod) if "Repr" in s]
        self.repr_classes = [c for c in self.repr_classes if hasattr(c, "get")]
        self.llvm_reprs = {}
        self.depth = 0
        self.entryname = self.translator.functions[0].__name__
        self.lazy_objects = sets.Set()
        self.l_entrypoint = EntryFunctionRepr("%__entry__" + self.entryname,
                                              self.translator.functions[0],
                                              self)
        self.local_counts[self.l_entrypoint] = 0
        #self.l_entrypoint.setup()

    def compile(self, optimize=False):
        from pypy.tool.udir import udir
        name = self.entryname
        llvmfile = udir.join('%s.ll' % name)
        if debug:
            print "llvmfile:", llvmfile
        f = llvmfile.open('w')
        self.write(f)
        f.close()
        pyxfile = udir.join('%s_wrap.pyx' % name)
        f = pyxfile.open('w')
        f.write(self.l_entrypoint.get_pyrex_source())
        f.close()
        mod = build_llvm_module.make_module_from_llvm(llvmfile, pyxfile,
                                                      optimize)
        return getattr(mod, "wrap_%s" % self.l_entrypoint.llvmname()[1:])

    def get_global_tmp(self, used_by=None):
        used_by = (used_by or "unknown")
        assert "%" not in used_by
        if used_by in self.global_counts:
            self.global_counts[used_by] += 1
            return "%%glb.%s.%i" % (used_by, self.global_counts[used_by])
        else:
            self.global_counts[used_by] = 0
            return "%%glb.%s" % used_by

    def get_local_tmp(self, type, l_function):
        self.local_counts[l_function] += 1
        return TmpVariableRepr("tmp.%i" % self.local_counts[l_function], type,
                               self)

    def get_repr(self, obj):
        self.depth += 1
        key = get_key(obj)
        if debug:
            print "  " * self.depth,
            print "looking for object", obj, type(obj).__name__,
            print id(obj), get_key(obj),
        if isinstance(obj, LLVMRepr):
            self.depth -= 1
            return obj
        if key in self.llvm_reprs:
            self.depth -= 1
            if debug:
                print "->exists already:", self.llvm_reprs[key]
            return self.llvm_reprs[key]
        elif isinstance(obj, Variable):
            result = representation.VariableRepr(obj, self)
            self.llvm_reprs[key] = result
            self.depth -= 1
            return result
        elif isinstance(obj, lltype.Primitive):
            result = reprmap.PRIMITIVE_TYPES[obj](self)
            self.llvm_reprs[key] = result
            self.depth -= 1
            return result
        if isinstance(obj, Constant):
            try:
                concretetype = obj.concretetype
                if isinstance(concretetype, lltype.Primitive):
                    result = reprmap.PRIMITIVE_REPRS[concretetype](obj.value,
                                                                   self)
                    self.llvm_reprs[key] = result
                    self.depth -= 1
                    return result
                if isinstance(concretetype, lltype.Ptr):
                    return pointerrepr.PointerRepr(obj.value, self)
            except AttributeError:
                pass
        for cl in self.repr_classes:
            if debug and 0:
                print 'try cl.get(obj, self) where cl=', cl
            try:
                g = cl.get(obj, self)
            except AttributeError:
                continue
            if g is not None:
                self.llvm_reprs[key] = g
                self.local_counts[g] = 0
                self.depth -= 1
                return g
        raise CompileError, "Can't get repr of %s, %s" % (obj, obj.__class__)

    def write(self, f, include=True):
        self.unlazyify()
        seen_reprs = sets.Set()
        remove_loops(self.l_entrypoint, seen_reprs)
        seen_reprs = sets.Set()
        init_block = self.l_entrypoint.init_block
        for l_repr in traverse_dependencies(self.l_entrypoint, seen_reprs):
            l_repr.collect_init_code(init_block, self.l_entrypoint)
        if include == True:
            include_files = ["class.ll"]
        else:
            include_files = []
        for i, fn in enumerate(include_files):
            f1 = file(autopath.this_dir + "/" + fn)
            s = f1.read()
            include_files[i] = s.split("\nimplementation")
            if len(include_files[i]) == 1:
                include_files[i].insert(0, "")
            f1.close()
        f.write("\n\n; +-------+\n; |globals|\n; +-------+\n\n")
        for inc in include_files:
            f.write(inc[0])
        seen_reprs = sets.Set()
        for l_repr in traverse_dependencies(self.l_entrypoint, seen_reprs):
            s = l_repr.get_globals()
            if s != "":
                f.write(s + "\n")
        f.write("implementation\n")
        f.write("\n\n; +---------+\n; |space_ops|\n; +---------+\n\n")
        for inc in include_files:
            f.write(inc[1])
        f.write("\n\n; +---------+\n; |functions|\n; +---------+\n\n")
        seen_reprs = sets.Set()
        for l_repr in traverse_dependencies(self.l_entrypoint, seen_reprs):
            s = l_repr.get_functions()
            if s != "":
                f.write(s + "\n")

    def unlazyify(self):
        if debug:
            print 
            print "unlazyify"
        while len(self.lazy_objects):
            obj = self.lazy_objects.pop()
            if debug:
                print obj
            obj.setup()

    def __str__(self):
        f = StringIO.StringIO()
        self.write(f, False)
        return f.getvalue()

#traverse dependency-tree starting from the leafes upward
#this is only safe if there are no direct loops
def traverse_dependencies(l_repr, seen_reprs):
    while 1:
        length = len(seen_reprs)
        if (len(l_repr.get_dependencies() - seen_reprs) == 0 and
            l_repr not in seen_reprs):
            seen_reprs.add(l_repr)
            yield l_repr
            break
        for l_dep in l_repr.get_dependencies():
            if l_dep in seen_reprs:
                continue
            for l_dep1 in traverse_dependencies(l_dep, seen_reprs):
                yield l_dep1
        if len(seen_reprs) == length:
            break

def remove_loops(l_repr, seen_repr):
    deps = l_repr.get_dependencies()
    if l_repr in deps:
        print "removed direct loop from %s to itself" % l_repr
        deps.remove(l_repr)
    remove = sets.Set()
    for l_dep in deps:
        if l_dep in seen_repr:
            print "removed loop from %s to %s" % (l_repr, l_dep)
            remove.add(l_dep)
        else:
            remove_loops(l_dep, seen_repr.union(sets.Set([l_repr])))
    deps.difference_update(remove)

