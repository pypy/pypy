import autopath
import sets

from types import ClassType

from pypy.objspace.flow.model import Variable, Constant
from pypy.objspace.flow.model import last_exception, last_exc_value
from pypy.annotation import model as annmodel

from pypy.translator.llvm.representation import debug, LLVMRepr
from pypy.translator.llvm.representation import LLVM_SIMPLE_TYPES



class TypeRepr(LLVMRepr):
    def get(obj, gen):
        if (isinstance(obj, annmodel.SomePBC) and \
               obj.prebuiltinstances.keys()[0] is None) or obj is type(None):
            return TypeRepr("%std.void", "%std.void = type sbyte", "", gen)
    get = staticmethod(get)

    def __init__(self, llvmname, definition, includefile, gen):
        if debug:
            print "TypeRepr: %s, %s" % (llvmname, definition)
        self.name = llvmname
        self.definition = definition
        self.gen = gen
        self.includefile = includefile

    def get_globals(self):
        try:
            return self.definition
        except AttributeError:
            return ""

    def get_functions(self):
        try:
            if self.includefile != "":
                f = file(autopath.this_dir + "/" + self.includefile, "r")
                s = f.read()
                f.close()
                return s
        except AttributeError:
            pass
        return ""

    def llvmname(self):
        return self.name + "*"

    def llvmname_wo_pointer(self):
        return self.name

class StringTypeRepr(TypeRepr):
    def get(obj, gen):
        if obj.__class__ is annmodel.SomeString or obj is str:
            return StringTypeRepr(gen)
    get = staticmethod(get)

    def __init__(self, gen):
        if debug:
            print "StringTypeRepr"
        self.gen = gen
        self.dependencies = sets.Set()

    def setup(self):
        self.l_charlist = self.gen.get_repr(
            annmodel.SomeList(None, annmodel.SomeChar()))
        self.dependencies.add(self.l_charlist)
        self.name = self.l_charlist.llvmname_wo_pointer()

    def t_op_getitem(self, l_target, args, lblock, l_func):
        l_args = [self.gen.get_repr(arg) for arg in args]
        l_func.dependencies.update(l_args)
        lblock.spaceop(l_target, "getitem", l_args)

    def t_op_inplace_add(self, l_target, args, lblock, l_func):
        l_args = [self.gen.get_repr(arg) for arg in args]
        l_func.dependencies.update(l_args)
        lblock.spaceop(l_target, "add", l_args)


class IntTypeRepr(TypeRepr):
    def get(obj, gen):
        if obj.__class__ is annmodel.SomeInteger:
            return IntTypeRepr(obj, gen)
        return None
    get = staticmethod(get)

    def __init__(self, annotation, gen):
        if debug:
            print "IntTypeRepr: %s" % annotation
        self.annotation = annotation
        if annotation.unsigned:
            self.name = "uint"
        else:
            self.name = "int"
        self.gen = gen

    def llvmname(self):
        return self.name

    def cast_to_signed(self, l_val, lblock, l_function):
        if not self.annotation.unsigned:
            return l_val
        ann = annmodel.SomeInteger()
        l_type = self.gen.get_repr(ann)
        l_tmp = self.gen.get_local_tmp(l_type, l_function)
        l_function.dependencies.update([l_type, l_tmp])
        lblock.cast(l_tmp, l_val, l_type)
        return l_tmp

    def cast_to_unsigned(self, l_val, lblock, l_function):
        if self.annotation.unsigned:
            return l_val
        ann = annmodel.SomeInteger(True, True)
        l_type = self.gen.get_repr(ann)
        l_tmp = self.gen.get_local_tmp(l_type, l_function)
        l_function.dependencies.update([l_type, l_tmp])
        lblock.cast(l_tmp, l_val, l_type)
        return l_tmp


class SimpleTypeRepr(TypeRepr):
    def get(obj, gen):
        if obj.__class__ is annmodel.SomeInteger:
            l_repr = SimpleTypeRepr("int", gen)
            return l_repr
        elif obj.__class__ is annmodel.SomeBool:
            l_repr = SimpleTypeRepr("bool", gen)
            return l_repr
        elif obj.__class__ is annmodel.SomeChar:
            l_repr = SimpleTypeRepr("sbyte", gen)
            return l_repr
        elif obj.__class__ is annmodel.SomePBC:
            if obj.knowntype == object or obj.knowntype == ClassType:
                return SimpleTypeRepr("%std.class", gen)
        return None
    get = staticmethod(get)

    def __init__(self, llvmname, gen):
        if debug:
            print "SimpleTypeRepr: %s" % llvmname
        self.name = llvmname
        self.gen = gen
        self.definition = ""
        self.includefile = ""

    def llvmname(self):
        return self.name

class PointerTypeRepr(TypeRepr):
    def get(obj, gen):
        return None
    get = staticmethod(get)

    def __init__(self, type, gen):
        self.type = type

    def llvmname(self):
        return self.type + "*"

class ImpossibleValueRepr(TypeRepr):
    def get(obj, gen):
        if obj.__class__ is annmodel.SomeImpossibleValue:
            return ImpossibleValueRepr()
        return None
    get = staticmethod(get)
    
    def __init__(self):
        self.definition = ""
        self.dependencies = sets.Set()
        self.includefile = ""

    def llvmname(self):
        return "void"


