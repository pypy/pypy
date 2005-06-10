"""
The representations of objects that can be the type of other objects.
"""


import autopath
import sets

from types import ClassType

from pypy.objspace.flow.model import Variable, Constant
from pypy.annotation import model as annmodel
from pypy.annotation.listdef import ListDef

from pypy.translator.llvm.representation import debug, LLVMRepr, CompileError
from pypy.translator.llvm.representation import LLVM_SIMPLE_TYPES

from pypy.rpython import lltype

import sys

if 2147483647 == sys.maxint:
    BYTES_IN_INT = 4
else:
    BYTES_IN_INT = 8

lazy_debug = False
debug = False

class TypeRepr(LLVMRepr):
    def get(obj, gen):
        if (isinstance(obj, annmodel.SomePBC) and \
               obj.prebuiltinstances.keys()[0] is None) or obj is type(None):
            return TypeRepr("%std.void", "%std.void = type sbyte", "", gen)
    get = staticmethod(get)

    def __init__(self, typename, definition, includefile, gen):
        if debug: 
            print "TypeRepr: %s, %s" % (typename, definition)
        self.name = typename
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

    def typename(self):
        return self.name + "*"

    def typename_wo_pointer(self):
        return self.name

    def llvmname(self):
        raise NotImplementedError, "This type is not an object."

    def llvmtype(self):
        raise NotImplementedError, \
              "This type is not an object. %s" % self.__class__

    def llvmsize(self):
        raise NotImplementedError, "This type does not have a size."
        

class SignedTypeRepr(TypeRepr):
    directly_supported_binary_ops = {
        "int_add": "add",
        "int_sub": "sub",
        "int_mul": "mul",
        "int_div": "div",
        "int_mod": "rem",
        "int_xor": "xor",
        "int_and": "and",
        "int_lshift": "shl",
        "int_rshift": "shr",
        "int_or": "or",
        "int_eq": "seteq",
        "int_ne": "setne",
        "int_gt": "setgt",
        "int_ge": "setge",
        "int_lt": "setlt",
        "int_le": "setle"}

    def __init__(self, gen):
        if debug:
            print "SignedTypeRepr"
        self.gen = gen

    def t_op(self, opname, l_target, args, lblock, l_func):
        if opname in SignedTypeRepr.directly_supported_binary_ops:
            assert len(args) == 2
            l_args = [self.gen.get_repr(arg) for arg in args]
            l_func.dependencies.update(l_args)
            l_op = SignedTypeRepr.directly_supported_binary_ops[opname]
            if l_op in ('shl', 'shr'):  #feel free to refactor this
                lblock.shift_instruction(
                    l_op, l_target,
                    l_args[0], l_args[1])
            else:
                lblock.binary_instruction(
                    l_op, l_target,
                    l_args[0], l_args[1])

    def t_op_int_pos(self, l_target, args, lblock, l_func):
        pass

    def t_op_int_neg(self, l_target, args, lblock, l_func):
        l_arg = self.gen.get_repr(args[0])
        l_func.dependencies.add(l_arg)
        lblock.instruction("%s = sub int 0, %s" % (l_target.llvmname(),
                                                   l_arg.llvmname()))

    def t_op_int_invert(self, l_target, args, lblock, l_func):
        l_arg = self.gen.get_repr(args[0])
        l_func.dependencies.add(l_arg)
        lblock.instruction("%s = xor int -1, %s" % (l_target.llvmname(),
                                                   l_arg.llvmname()))

    def t_op_int_abs(self, l_target, args, lblock, l_func):
        l_arg = self.gen.get_repr(args[0])
        l_func.dependencies.add(l_arg)
        lblock.instruction("%s = and int 2147483647, %s" % (l_target.llvmname(),
                                                            l_arg.llvmname()))

    def typename(self):
        return "int"

    def llvmsize(self):
        return BYTES_IN_INT

class UnsignedTypeRepr(TypeRepr):
    def __init__(self, gen):
        if debug:
            print "UnsignedTypeRepr"
        self.gen = gen

    def typename(self):
        return "uint"

    def llvmsize(self):
        return BYTES_IN_INT

class BoolTypeRepr(TypeRepr):
    def __init__(self, gen):
        if debug:
            print "BoolTypeRepr"
        self.gen = gen

    def typename(self):
        return "bool"

    def llvmsize(self):
        return 1


class FloatTypeRepr(TypeRepr):
    directly_supported_binary_ops = {
        "float_add": "add",
        "float_sub": "sub",
        "float_mul": "mul",
        "float_div": "div",
        "float_mod": "rem",
        "float_xor": "xor",
        "float_and_": "and",
        "float_eq": "seteq",
        "float_ne": "setne",
        "float_gt": "setgt",
        "float_ge": "setge",
        "float_lt": "setlt",
        "float_le": "setle"}
        
    def __init__(self, gen):
        if debug:
            print "FloatTypeRepr"
        self.gen = gen

    def typename(self):
        return "double"

    def t_op(self, opname, l_target, args, lblock, l_func):
        if opname in FloatTypeRepr.directly_supported_binary_ops:
            assert len(args) == 2
            l_args = [self.gen.get_repr(arg) for arg in args]
            l_func.dependencies.update(l_args)
            lblock.binary_instruction(
                FloatTypeRepr.directly_supported_binary_ops[opname], l_target,
                l_args[0], l_args[1])

    def llvmsize(self):
        return 8

class CharTypeRepr(TypeRepr):
    def __init__(self, gen):
        if debug:
            print "CharTypeRepr"
        self.gen = gen

    def typename(self):
        return "sbyte"

    def llvmsize(self):
        return 1

class FuncTypeRepr(TypeRepr):
    def get(obj, gen):
        if obj.__class__ is lltype.FuncType:
            return FuncTypeRepr(obj, gen)
    get = staticmethod(get)

    def __init__(self, functype, gen):
        if debug:
            print "FuncTypeRepr: %s" % functype
        self.gen = gen
        self.functype = functype
        self.l_returntype = self.gen.get_repr(functype.RESULT)
        self.l_argtypes = [self.gen.get_repr(arg) for arg in functype.ARGS]
        self.dependencies = sets.Set(self.l_argtypes + [self.l_returntype])

    def typename(self):
        argtypes = ", ".join([l_arg.llvmname() for arg in self.l_argtypes])
        return "%s (%s)" % (self.l_returntype.llvmname(), argtypes)
        

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
        self.l_charlist = self.gen.get_repr(
            annmodel.SomeList(ListDef(None, annmodel.SomeChar())))
        self.dependencies.add(self.l_charlist)
        self.name = self.l_charlist.typename_wo_pointer()

    def t_op_getitem(self, l_target, args, lblock, l_func):
        l_args = [self.gen.get_repr(arg) for arg in args]
        l_func.dependencies.update(l_args)
        lblock.spaceop(l_target, "getitem", l_args)

    def t_op_inplace_add(self, l_target, args, lblock, l_func):
        l_args = [self.gen.get_repr(arg) for arg in args]
        l_func.dependencies.update(l_args)
        lblock.spaceop(l_target, "add", l_args)

    def t_op_inplace_mul(self, l_target, args, lblock, l_func):
        l_args = [self.gen.get_repr(arg) for arg in args]
        l_func.dependencies.update(l_args)
        lblock.spaceop(l_target, "mul", l_args)


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

    def typename(self):
        return self.name

    #def cast_to_signed(self, l_val, lblock, l_function):
    #    if not self.annotation.unsigned:
    #        return l_val
    #    ann = annmodel.SomeInteger()
    #    l_type = self.gen.get_repr(ann)
    #    l_tmp = self.gen.get_local_tmp(l_type, l_function)
    #    l_function.dependencies.update([l_type, l_tmp])
    #    lblock.cast(l_tmp, l_val, l_type)
    #    return l_tmp
    #
    #def cast_to_unsigned(self, l_val, lblock, l_function):
    #    if self.annotation.unsigned:
    #        return l_val
    #    ann = annmodel.SomeInteger(True, True)
    #    l_type = self.gen.get_repr(ann)
    #    l_tmp = self.gen.get_local_tmp(l_type, l_function)
    #    l_function.dependencies.update([l_type, l_tmp])
    #    lblock.cast(l_tmp, l_val, l_type)
    #    return l_tmp

class SimpleTypeRepr(TypeRepr):
    def get(obj, gen):
        if obj.__class__ is annmodel.SomeFloat:
            return SimpleTypeRepr("double", gen)
        elif obj.__class__ is annmodel.SomeBool:
            l_repr = SimpleTypeRepr("bool", gen)
            return l_repr
        elif obj.__class__ is annmodel.SomeChar:
            l_repr = SimpleTypeRepr("sbyte", gen)
            return l_repr
        elif obj.__class__ is annmodel.SomeObject and \
             hasattr(obj, "is_type_of"):
            return SimpleTypeRepr("%std.class*", gen)
        elif obj.__class__ is annmodel.SomeObject:
            return SimpleTypeRepr("%std.object*", gen)
        return None
    get = staticmethod(get)

    def __init__(self, typename, gen):
        if debug:
            print "SimpleTypeRepr: %s" % typename
        self.name = typename
        self.gen = gen
        self.definition = ""
        self.includefile = ""

    def typename(self):
        return self.name

class PointerTypeRepr(TypeRepr):
    def __init__(self, type_, gen):
        self.type = type_

    def typename(self):
        return self.type + "*"


#This should only be used as the return value for "void" functions
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

    def typename(self):
        return "void"

