import autopath
import sets

from types import FunctionType, MethodType

from pypy.objspace.flow.model import Constant
from pypy.annotation import model as annmodel
from pypy.annotation.classdef import ClassDef
from pypy.translator.llvm import llvmbc

from pypy.translator.llvm.representation import debug, LLVMRepr, CompileError
from pypy.translator.llvm.representation import TmpVariableRepr
from pypy.translator.llvm.typerepr import TypeRepr, PointerTypeRepr
from pypy.translator.llvm.typerepr import SimpleTypeRepr
from pypy.translator.llvm.funcrepr import FunctionRepr, BoundMethodRepr
from pypy.translator.llvm.funcrepr import VirtualMethodRepr
from pypy.translator.llvm.memorylayout import MemoryLayout

debug = True

class PBCTypeRepr(TypeRepr):
    def get(obj, gen):
        if (isinstance(obj, annmodel.SomePBC) and
            len(obj.prebuiltinstances) == 1 and   #only one pb instance for now
            not isinstance(obj.prebuiltinstances.keys()[0],
                           (FunctionType, MethodType))):
            return PBCTypeRepr(obj, gen)
        return None
    get = staticmethod(get)

    def __init__(self, obj, gen):
        if debug:
            print "PBCTypeRepr", obj
        self.ann = obj
        self.gen = gen
        self.dependencies = sets.Set()
        self.name = gen.get_global_tmp(
            "pbc.%s" % obj.prebuiltinstances.keys()[0].__class__.__name__)
        self.objectname = self.name + ".object"

    def setup(self):
        bk = self.gen.annotator.bookkeeper
        access_sets = bk.pbc_maximal_access_sets
        objects = self.ann.prebuiltinstances.keys()
        change, rep, access = access_sets.find(objects[0])
        for obj in objects:
            change1, rep, access = access_sets.union(rep, obj)
            change = change or change1
        self.methods = {}
        attribs = ["__class__"]
        l_types = [SimpleTypeRepr("%std.class*", self.gen)]
        if debug:
            print "PBC attributes:", access.attrs
        for attr in access.attrs:
            actuals = []
            for c in access.objects:
                if hasattr(c, attr):
                    actuals.append(bk.immutablevalue(getattr(c, attr)))
            s_value = annmodel.unionof(*actuals)
            if debug:
                print attr, s_value,
            if isinstance(s_value, annmodel.SomeImpossibleValue):
                if debug:
                    print "--> removed"
                continue
            elif isinstance(s_value, annmodel.SomePBC) and \
               s_value.knowntype in (FunctionType, MethodType):
                if debug:
                    print "--> method"
                func = objects[0].__class__.__dict__[attr]
                self.methods[attr] = func
            else:
                if debug:
                    print "--> value"
                attribs.append(attr)
                l_types.append(self.gen.get_repr(s_value))
        self.memlayout = MemoryLayout(attribs, l_types, self.gen)

    def get_globals(self):
        self.definition = "%s = %s" % (self.name, self.memlayout.definition())
        s = "\n%s = internal global %%std.class {%%std.class* null, uint %i}"
        s = s % (self.objectname, abs(id(self)))
        return self.definition + s

    def llvmtype(self):
        return "%std.class*"

    def llvmname(self):
        return self.objectname

    def t_op_getattr(self, l_target, args, lblock, l_func):
        if not isinstance(args[1], Constant):
            raise CompileError,"getattr called with non-constant: %s" % args[1]
        if debug:
            print "t_op_getattr of PBCTypeRepr called", args, self.name
        if args[1].value in self.memlayout.attrs:
            l_args0 = self.gen.get_repr(args[0])
            l_func.dependencies.add(l_args0)
            self.memlayout.get(l_target, l_args0, args[1].value, lblock,
                               l_func)
            return
        elif args[1].value in self.methods:
            print l_target, l_target.llvmname()
            if not isinstance(l_target.type, BoundMethodRepr):
                l_args0 = self.gen.get_repr(args[0])
                l_func.dependencies.add(l_args0)
                l_method = BoundMethodRepr(l_target.type, l_args0,
                                           self.gen)
                l_func.dependencies.add(l_method)
                l_method.setup()
                l_target.type = l_method
            return
        raise CompileError, ("getattr called with unknown attribute %s" % \
                             args[1].value)

    def t_op_setattr(self, l_target, args, lblock, l_func):
        raise CompileError, "setattr of PBC called!"

class PBCRepr(LLVMRepr):
    def get(obj, gen):
        if isinstance(obj, Constant):
            ann = gen.annotator.binding(obj)
            if (isinstance(ann, annmodel.SomePBC) and
                len(ann.prebuiltinstances) == 1 and
                not isinstance(ann.prebuiltinstances.keys()[0], FunctionType)):
                return PBCRepr(obj, gen)
        return None
    get = staticmethod(get)

    def __init__(self, obj, gen):
        if debug:
            print "PBCRepr: ", obj
        self.obj = obj
        self.gen = gen
        self.dependencies = sets.Set()
        self.name = gen.get_global_tmp(obj.value.__class__.__name__ + ".inst")

    def setup(self):
        self.type = self.gen.get_repr(self.gen.annotator.binding(self.obj))
        self.dependencies.add(self.type)
        self.l_attrib_values = [self.type]
        for attr in self.type.memlayout.attrs[1:]:
            s_a = self.gen.get_repr(Constant(getattr(self.obj.value, attr)))
            self.l_attrib_values.append(s_a)
        self.dependencies.update(self.l_attrib_values)
        self.definition = self.name + \
                          " = internal global %s" % self.llvmtype()[:-1] + \
                          self.type.memlayout.constant(self.l_attrib_values)

    def get_globals(self):
        return self.definition

    def __getattr__(self, name):
        if name.startswith("op_"):
            return getattr(self.type, "t_" + name, None)
        else:
            raise AttributeError, ("PBCRepr instance has no attribute %s"
                                   % repr(name))

