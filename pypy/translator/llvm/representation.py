import autopath
import sets

from pypy.objspace.flow.model import Variable, Constant
from pypy.annotation import model as annmodel

LLVM_SIMPLE_TYPES = {annmodel.SomeChar: "sbyte",
                     annmodel.SomeBool: "bool"}

debug = False


class CompileError(Exception):
    pass


class LLVMRepr(object):
    def get(obj, gen):
        return None
    get = staticmethod(get)

    def __init__(self, obj, gen):
        pass

    def setup(self):
        pass
    
    def get_globals(self):
        return ""

    def get_functions(self):
        return ""

    def collect_init_code(self, lblock, l_func):
        pass

    def llvmname(self):
        return self.name

    def llvmtype(self):
        return self.type.llvmname()

    def typed_name(self):
        return self.llvmtype() + " " + self.llvmname()

    def get_dependencies(self):
        try:
            return self.dependencies
        except AttributeError:
            return []


class SimpleRepr(LLVMRepr):
    """Representation of values that are directly mapped to types in LLVM:
bool, char (string of length 1)"""

    def get(obj, gen):
        if not isinstance(obj, Constant):
            return None
        type = gen.annotator.binding(obj)
        if type.__class__ in LLVM_SIMPLE_TYPES:
            llvmtype = LLVM_SIMPLE_TYPES[type.__class__]
            l_repr = SimpleRepr(llvmtype, repr(obj.value), gen)
            return l_repr
        return None
    get = staticmethod(get)
    
    def __init__(self, type, llvmname, gen):
        if debug:
            print "SimpleRepr: %s, %s" % (type, llvmname)
        self.type = type
        if llvmname in ("False", "True"):
            llvmname = llvmname.lower()
        self.name = llvmname
        self.gen = gen
        self.dependencies = sets.Set()

    def llvmtype(self):
        return self.type

    def __getattr__(self, name):
        return getattr(self.type, name, None)

class IntRepr(LLVMRepr):
    def get(obj, gen):
        if obj.__class__ is int:
            type = gen.annotator.binding(Constant(obj))
            return IntRepr(type, obj, gen)
        if not isinstance(obj, Constant):
            return None
        type = gen.annotator.binding(obj)
        if type.__class__ == annmodel.SomeInteger:
            return IntRepr(type, obj.value, gen)
    get = staticmethod(get)

    def __init__(self, annotation, value, gen):
        if debug:
            print "IntRepr", annotation, value
        self.value = value
        self.annotation = annotation
        self.type = gen.get_repr(annotation)
        self.gen = gen
        self.dependencies = sets.Set()

    def llvmname(self):
        return repr(self.value)

    def cast_to_unsigned(self, l_val, lblock, l_function):
        if self.type.annotation.unsigned:
            return self
        else:
            return IntRepr(annmodel.SomeInteger(True, True),
                           self.value, self.gen)

    def cast_to_signed(self, l_val, lblock, l_function):
        if not self.type.annotation.unsigned:
            return self
        else:
            return IntRepr(annmodel.SomeInteger(), self.value, self.gen)

class VariableRepr(LLVMRepr):
    def get(obj, gen):
        if isinstance(obj, Variable):
            return VariableRepr(obj, gen)
        return None
    get = staticmethod(get)

    def __init__(self, var, gen):
        if debug:
            print "VariableRepr: %s" % (var.name)
        self.var = var
        type = gen.annotator.binding(var)
        self.type = gen.get_repr(type)
        self.dependencies = sets.Set([self.type])

    def llvmname(self):
        return "%" + self.var.name

    def __getattr__(self, name):
        if name.startswith("op_"):
            return getattr(self.type, "t_" + name, None)
        elif name.startswith("cast_"):
            return getattr(self.type, name, None)
        else:
            raise AttributeError, ("VariableRepr instance has no attribute %s"
                                   % repr(name))

class TmpVariableRepr(LLVMRepr):
    def __init__(self, name, type, gen):
        if debug:
            print "TmpVariableRepr: %s %s" % (type, name)
        self.name = name
        self.type = type
        self.dependencies = sets.Set()

    def llvmname(self):
        return "%" + self.name

    def llvmtype(self):
        return self.type.llvmname()

class NoneRepr(LLVMRepr):
    def get(obj, gen):
        if isinstance(obj, Constant) and obj.value is None:
            return NoneRepr(gen)
    get = staticmethod(get)

    def __init__(self, gen):
        self.gen = gen
        self.type = gen.get_repr(type(None))
        self.dependencies = sets.Set([self.type])
        if debug:
            print "NoneRepr, llvmname: %s, llvmtype: %s" % (self.llvmname(),
                                                            self.llvmtype())
    def llvmname(self):
        return "null"

class StringRepr(LLVMRepr):
    def get(obj, gen):
        if isinstance(obj, Constant):
            type = gen.annotator.binding(obj)
            if isinstance(type, annmodel.SomeString):
                return StringRepr(obj.value, gen)
        elif isinstance(obj, str):
            return StringRepr(obj, gen)
        return None
    get = staticmethod(get)

    def __init__(self, obj, gen):
        if debug:
            print "StringRepr: %s" % obj
        self.s = obj
        self.gen = gen
        self.glvar1 = gen.get_global_tmp("StringRepr")
        self.glvar2 = gen.get_global_tmp("StringRepr")
        self.type = gen.get_repr(annmodel.SomeString())
        self.dependencies = sets.Set([self.type])

    def llvmname(self):
        return self.glvar2

    def get_globals(self):
        d = {"len": len(self.s), "gv1": self.glvar1, "gv2": self.glvar2,
             "type": self.type.llvmname_wo_pointer(), "string": self.s}
        s = """%(gv1)s = internal global [%(len)i x sbyte] c"%(string)s"
%(gv2)s = internal global %(type)s {uint %(len)i,\
sbyte* getelementptr ([%(len)i x sbyte]* %(gv1)s, uint 0, uint 0)}"""
        return s % d

    def __getattr__(self, name):
        if name.startswith("op_"):
            return getattr(self.type, "t_" + name, None)
        else:
            raise AttributeError, ("VariableRepr instance has no attribute %s"
                                   % repr(name))

class TupleRepr(LLVMRepr):
    def get(obj, gen):
        if isinstance(obj, Constant):
            type = gen.annotator.binding(obj)
            if isinstance(type, annmodel.SomeTuple):
                return TupleRepr(obj, gen)
        return None
    get = staticmethod(get)

    def __init__(self, obj, gen):
        if debug:
            print "TupleRepr", obj, obj.value
        self.const = obj
        self.tuple = obj.value
        self.gen = gen
        self.dependencies = sets.Set()

    def setup(self):
        self.l_tuple = [self.gen.get_repr(l) for l in list(self.tuple)]
        self.glvar = self.gen.get_global_tmp("TupleRepr")
        self.dependencies.update(self.l_tuple)
        self.type = self.gen.get_repr(self.gen.annotator.binding(self.const))

    def get_globals(self):
        s = "%s = internal global " % self.glvar + " " + self.llvmtype()
        s += "{" + ", ".join([l.typed_name() for l in self.l_tuple]) + "}"
        i = self.l_tuple[0]
        return s

    def llvmname(self):
        return self.glvar

    def __getattr__(self, name):
        if name.startswith("op_"):
            return getattr(self.type, "t_" + name, None)
        else:
            raise AttributeError, ("TupleRepr instance has no attribute %s"
                                   % repr(name))


