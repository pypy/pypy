'''
Added this because ctypes on my computer was missing cdecl.
'''
from llvmcapi import *

class Method(object):
    def __init__(self, instance, method):
        self.instance = instance
        self.method   = method

    def __call__(self, *args):
        a = [self.instance]
        for arg in args:
            if isinstance(arg, Wrapper): #pass on value to actual C (not Python) object
                a.append(arg.instance)
            else:
                a.append(arg)
        return apply(self.method, a)

class Wrapper(object):
    def __getattr__(self, name):
        global_funcname = self.__class__.__name__ + "_" + name
        return Method(self.instance, globals()[global_funcname])


def to_llvm_value(pythonvalue, type_):
    value = GenericValue_()
    value.LongVal = 0
    id_ = type_.getTypeID()
    if id_ == PointerTyID and type_.getContainedType(0).getTypeID() == SByteTyID:
        value.PointerVal = pointer(pythonvalue)
    elif id_ == VoidTyID:
        pass
    elif id_ == BoolTyID:
        value.BoolVal = pythonvalue
    elif id_ == UByteTyID:
        value.UByteVal = pythonvalue
    elif id_ == SByteTyID:
        value.SByteVal = pythonvalue
    elif id_ == UShortTyID:
        value.UShortVal = pythonvalue
    elif id_ == ShortTyID:
        value.ShortVal = pythonvalue
    elif id_ == UIntTyID:
        value.UIntVal = pythonvalue
    elif id_ == IntTyID:
        value.IntVal = pythonvalue
    elif id_ == ULongTyID:
        value.ULongVal = pythonvalue
    elif id_ == LongTyID:
        value.ULongVal = pythonvalue
    else:
        raise Exception("don't know how to convert pythontype '%s' to llvm" % type_.getDescription())
    return value


def to_python_value(llvmvalue, type_):
    value = GenericValue_()
    value.LongVal = llvmvalue # XXX convert llvmvalue from long long
    id_ = type_.getTypeID()
    if id_ == PointerTyID and type_.getContainedType(0).getTypeID() == SByteTyID:
        return STRING(value.PointerVal).value
    elif id_ == VoidTyID:
        return None
    elif id_ == BoolTyID:
        return value.BoolVal
    elif id_ == UByteTyID:
        return value.UByteVal
    elif id_ == SByteTyID:
        return value.SByteVal
    elif id_ == UShortTyID:
        return value.UShortVal
    elif id_ == ShortTyID:
        return value.ShortVal
    elif id_ == UIntTyID:
        return value.UIntVal
    elif id_ == IntTyID:
        return value.IntVal
    elif id_ == ULongTyID:
        return value.ULongVal
    elif id_ == LongTyID:
        return value.ULongVal
    raise Exception("don't know how to convert llvmtype '%s' to python" % type_.getDescription())
