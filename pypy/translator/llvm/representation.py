import autopath
import exceptions, sets, StringIO

from types import FunctionType, MethodType
import new

from pypy.objspace.flow.model import Variable, Constant, SpaceOperation
from pypy.objspace.flow.model import FunctionGraph, Block, Link
from pypy.objspace.flow.model import last_exception, last_exc_value
from pypy.objspace.flow.model import traverse, uniqueitems, checkgraph
from pypy.annotation import model as annmodel
from pypy.annotation.classdef import ClassDef
from pypy.translator import transform
from pypy.translator.llvm import llvmbc


INTRINSIC_OPS = ["lt", "le", "eq", "ne", "gt", "ge", "is", "is_true", "len",
                 "neg", "pos", "invert", "add", "sub", "mul", "truediv",
                 "floordiv", "div", "mod", "pow", "lshift", "rshift", "and_",
                 "or", "xor", "inplace_add", "inplace_sub", "inplace_mul",
                 "inplace_truediv", "inplace_floordiv", "inplace_div",
                 "inplace_mod", "inplace_pow", "inplace_lshift",
                 "inplace_rshift", "inplace_and", "inplace_or", "inplace_xor",
                 "contains", "newlist", "newtuple", "alloc_and_set"]

C_SIMPLE_TYPES = {annmodel.SomeChar: "char",
                  annmodel.SomeString: "char*",
                  annmodel.SomeBool: "unsigned char",
                  annmodel.SomeInteger: "int"}


LLVM_SIMPLE_TYPES = {annmodel.SomeChar: "sbyte",
                     annmodel.SomeBool: "bool"}


debug = False


class CompileError(exceptions.Exception):
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
        except exceptions.AttributeError:
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
        except exceptions.AttributeError:
            return ""

    def get_functions(self):
        try:
            if self.includefile != "":
                f = file(autopath.this_dir + "/" + self.includefile, "r")
                s = f.read()
                f.close()
                return s
        except exceptions.AttributeError:
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

class ListTypeRepr(TypeRepr):
    l_listtypes = {}
    def get(obj, gen):
        if obj.__class__ is annmodel.SomeList:
            if (obj.s_item.__class__, gen) in ListTypeRepr.l_listtypes:
                return ListTypeRepr.l_listtypes[(obj.s_item.__class__, gen)]
            l_repr = ListTypeRepr(obj, gen)
            ListTypeRepr.l_listtypes[(obj.s_item.__class__, gen)] = l_repr
            return l_repr
        return None
    get = staticmethod(get)

    def __init__(self, obj, gen):
        if debug:
            print "ListTypeRepr: %s, %s" % (obj, obj.s_item)
        self.gen = gen
        self.l_itemtype = gen.get_repr(obj.s_item)
        self.dependencies = sets.Set([self.l_itemtype])
        itemtype = self.l_itemtype.llvmname()
        self.name = "%%std.list.%s" % itemtype.strip("%").replace("*", "")
        self.definition = self.name + " = type {uint, %s*}" % itemtype

    def get_functions(self):
        f = file(autopath.this_dir + "/list_template.ll", "r")
        s = f.read()
        f.close()
        itemtype = self.l_itemtype.llvmname()
        s = s.replace("%(item)s", self.l_itemtype.llvmname())
        s = s.replace("%(name)s", itemtype.strip("%").replace("*", ""))
        if isinstance(self.l_itemtype, IntTypeRepr):
            f1 = file(autopath.this_dir + "/int_list.ll", "r")
            s += f1.read()
            f1.close()
        return s

    def t_op_getitem(self, l_target, args, lblock, l_func):
        l_args = [self.gen.get_repr(arg) for arg in args]
        l_func.dependencies.update(l_args)
        lblock.spaceop(l_target, "getitem", l_args)

    def t_op_setitem(self, l_target, args, lblock, l_func):
        l_args = [self.gen.get_repr(arg) for arg in args]
        l_func.dependencies.update(l_args)
        lblock.spaceop(l_target, "setitem", l_args)

    def t_op_delitem(self, l_target, args, lblock, l_func):
        l_args = [self.gen.get_repr(arg) for arg in args]
        l_func.dependencies.update(l_args)
        lblock.spaceop(l_target, "delitem", l_args)

    def t_op_getattr(self, l_target, args, lblock, l_func):
        if isinstance(args[1], Constant) and \
               args[1].value in ["append", "reverse", "pop"]:
            l_args0 = self.gen.get_repr(args[0])
            l_func.dependencies.add(l_args0)
            l_method = BoundMethodRepr(l_target.type, l_args0, self, self.gen)
            l_method.setup()
            l_target.type = l_method
        else:
            raise CompileError, "List method %s not supported." % args[1].value

class TupleTypeRepr(TypeRepr):
    def get(obj, gen):
        if isinstance(obj, annmodel.SomeTuple):
            return TupleTypeRepr(obj, gen)
        return None
    get = staticmethod(get)

    def __init__(self, obj, gen):
        self.gen = gen
        self.l_itemtypes = [gen.get_repr(l) for l in obj.items]
        self.name = (("{" + ", ".join(["%s"] * len(self.l_itemtypes)) + "}") %
                     tuple([l.llvmname() for l in self.l_itemtypes]))

    def get_functions(self):
        s = ("internal int %%std.len(%s %%t) {\n\tret int %i\n}\n" %
             (self.llvmname(), len(self.l_itemtypes)))
        return s

    def t_op_newtuple(self, l_target, args, lblock, l_func):
        l_args = [self.gen.get_repr(arg) for arg in args]
        l_func.dependencies.update(l_args)
        lblock.malloc(l_target, self)
        l_ptrs = [self.gen.get_local_tmp(\
            PointerTypeRepr(l.llvmname(),self.gen), l_func)
                  for l in self.l_itemtypes]
        l_func.dependencies.update(l_ptrs)
        for i, l in enumerate(self.l_itemtypes):
            lblock.getelementptr(l_ptrs[i], l_target, [0, i])
            lblock.store(l_args[i], l_ptrs[i])

    def t_op_getitem(self, l_target, args, lblock, l_func):
        if not isinstance(args[1], Constant):
            raise CompileError, "index for tuple's getitem has to be constant"
        l_args = [self.gen.get_repr(arg) for arg in args]
        l_func.dependencies.update(l_args)
        l_tmp = self.gen.get_local_tmp(PointerTypeRepr(l_target.llvmtype(),
                                                       self.gen), l_func)
        cast = getattr(l_args[1], "cast_to_unsigned", None)
        if cast is not None:
            l_unsigned = cast(l_args[1], lblock, l_func)
        else:
            raise CompileError, "Invalid arguments to getitem"
        lblock.getelementptr(l_tmp, l_args[0], [0, l_unsigned])
        lblock.load(l_target, l_tmp)

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


class ClassRepr(TypeRepr):
    l_classes = {}
    def get(obj, gen):
        classdef = None
        if obj.__class__ is Constant:
            bind = gen.annotator.binding(obj)
            if bind.__class__ is annmodel.SomePBC and \
               bind.const.__class__ == type:
                classdef = gen.annotator.bookkeeper.userclasses[bind.const]
        elif isinstance(obj, annmodel.SomeInstance):
            classdef = obj.classdef
        elif isinstance(obj, ClassDef):
            classdef = obj
        if classdef is None:
            return None
        if (classdef, gen) not in ClassRepr.l_classes:
            ClassRepr.l_classes[(classdef, gen)] = ClassRepr(classdef, gen)
        return ClassRepr.l_classes[(classdef, gen)]
    get = staticmethod(get)

    def __init__(self, obj, gen):
        if debug:
            print "ClassRepr: %s, %s" % (obj, hex(id(self)))
        self.classdef = obj
        self.gen = gen
        self.includefile = ""
        self.name = gen.get_global_tmp("class.%s" % self.classdef.cls.__name__)
        self.objectname = gen.get_global_tmp("class.%s.object" %
                                             self.classdef.cls.__name__)
        if debug:
            print self.name
        self.dependencies = sets.Set()
        self.setup_done = False
        self.attr_num = {}

    def setup(self):
        if self.setup_done:
            return
        self.setup_done = True
        if debug:
            print "ClassRepr.setup()", id(self), hex(id(self)), self.setup_done
            print len(ClassRepr.l_classes)
        gen = self.gen
        if self.classdef.basedef is not None: #get attributes from base classes
            self.l_base = gen.get_repr(self.classdef.basedef)
            self.dependencies.add(self.l_base)
            attribs = self.l_base.attributes
        else:
            self.l_base = None
            attribs = []
        meth = []
        if debug:
            print "attributes", self.classdef.attrs
        #get attributes of this class and decide whether they are methods
        for key, attr in self.classdef.attrs.items():
            if debug:
                print key, attr, attr.sources, attr.s_value,
            if len(attr.sources) != 0:
                func = self.classdef.cls.__dict__[attr.name]
                meth.append((key, func))
                if debug:
                    print "--> method1"
            elif isinstance(attr.s_value, annmodel.SomePBC) and \
               attr.s_value.knowntype is FunctionType:
                func = self.classdef.cls.__dict__[attr.name]
                meth.append((key, func))
                if debug:
                    print "--> method2"
            else:
                attribs.append(attr)
                if debug:
                    print "--> value"
        self.l_attrs_types = [gen.get_repr(attr.s_value) for attr in attribs]
        self.dependencies = sets.Set(self.l_attrs_types)
        attributes = ", ".join([at.llvmname() for at in self.l_attrs_types])
        self.definition = "%s = type {%%std.class*, %s}" % (self.name,
                                                           attributes)
        self.attributes = attribs
        self.attr_num = {}
        for i, attr in enumerate(attribs):
            self.attr_num[attr.name] = i + 1
        self.methods = dict(meth)

    def get_globals(self):
        s = "\n%s = internal global %%std.class {%%std.class* null, uint %i}"
        s = s % (self.objectname, abs(id(self)))
        return self.definition + s

    def collect_init_code(self, lblock, l_func):
        if self.l_base is None:
            return
        l_tmp = self.gen.get_local_tmp(None, l_func)
        i = "%s = getelementptr %%std.class* %s, int 0, uint 0" % \
            (l_tmp.llvmname(), self.objectname)
        lblock.instruction(i)
        lblock.instruction("store %%std.class* %s, %%std.class** %s" %
                           (self.l_base.objectname, l_tmp.llvmname()))

    def llvmtype(self):
        return "%std.class* "

    def typed_name(self):
        #XXXX: Ouch. I get bitten by the fact that
        #      in LLVM typedef != class object
        # This will work, as long as class objects are only passed to functions
        return "%%std.class* %s" % self.objectname

    def op_simple_call(self, l_target, args, lblock, l_func):
        lblock.malloc(l_target, self)
        l_tmp = self.gen.get_local_tmp(
            PointerTypeRepr("%std.class*", self.gen), l_func)
        lblock.getelementptr(l_tmp, l_target, [0, 0])
        lblock.instruction("store %%std.class* %s, %s" %
                           (self.objectname, l_tmp.typed_name()))
        init = None
        for cls in self.classdef.getmro():
            if "__init__" in cls.attrs:
                init = cls.attrs["__init__"].getvalue()
                break
        if init is not None:
            l_init = self.gen.get_repr(init)
            l_func.dependencies.add(l_init)
            l_args = [self.gen.get_repr(arg) for arg in args[1:]]
            self.dependencies.update(l_args)
            # XXX
            if isinstance(l_init, VirtualMethodRepr):
                l_init = l_init.l_funcs[l_init.l_classes.index(self)]
            lblock.call_void(l_init, [l_target] + l_args)

    def t_op_getattr(self, l_target, args, lblock, l_func):
        if debug:
            print "t_op_getattr of ClassRepr called", l_target, args, self.name
        if not isinstance(args[1], Constant):
            raise CompileError,"getattr called with non-constant: %s" % args[1]
        if args[1].value in self.attr_num:
            l_args0 = self.gen.get_repr(args[0])
            l_func.dependencies.add(l_args0)
            l_pter = self.gen.get_local_tmp(
                PointerTypeRepr(l_target.llvmtype(), self.gen), l_func)
            lblock.getelementptr(l_pter, l_args0,
                                 [0, self.attr_num[args[1].value]])
            lblock.load(l_target, l_pter)
            return
        else:
            if debug:
                print list(self.classdef.getmro())
            for cls in self.classdef.getmro():
                l_cls = self.gen.get_repr(cls)
                self.dependencies.add(l_cls)
                if args[1].value in l_cls.methods:
                    if debug:
                        print "class %s, %s matches" % (cls, l_cls)
                    l_args0 = self.gen.get_repr(args[0])
                    l_func.dependencies.add(l_args0)
                    l_method = BoundMethodRepr(l_target.type, l_args0, l_cls,
                                               self.gen)
                    l_func.dependencies.add(l_method)
                    l_method.setup()
                    l_target.type = l_method
                    return
        raise CompileError, ("getattr called with unknown attribute %s" % \
                             args[1].value)

    def t_op_setattr(self, l_target, args, lblock, l_func):
        if not isinstance(args[1], Constant):
            raise CompileError,"setattr called with non-constant: %s" % args[1]
        if args[1].value in self.attr_num:
            l_args0 = self.gen.get_repr(args[0])
            l_value = self.gen.get_repr(args[2])
            self.dependencies.update([l_args0, l_value])
            l_pter = self.gen.get_local_tmp(
                PointerTypeRepr(l_value.llvmtype(), self.gen), l_func)
            lblock.getelementptr(l_pter, l_args0,
                                 [0, self.attr_num[args[1].value]])
            lblock.store(l_value, l_pter)
        else:
            raise CompileError, ("setattr called with unknown attribute %s" % \
                                 args[1].value)

    def iter_subclasses(self):
        for cls, classdef in self.classdef.subdefs.iteritems():
            l_cls = self.gen.get_repr(classdef)
            yield l_cls
            for l_c in l_cls.iter_subclasses():
                yield l_c

class BuiltinFunctionRepr(LLVMRepr):
    def get(obj, gen):
        if isinstance(obj, Constant) and \
           isinstance(gen.annotator.binding(obj), annmodel.SomeBuiltin):
            return BuiltinFunctionRepr(obj.value.__name__, gen)
        elif isinstance(obj, annmodel.SomeBuiltin):
            name = obj.analyser.__name__.replace("method_", "")
            return BuiltinFunctionRepr(name, gen)
        return None
    get = staticmethod(get)

    def __init__(self, name, gen):
        self.name = "%std." + name
        self.gen = gen

    def llvmname(self):
        return self.name

    def op_simple_call(self, l_target, args, lblock, l_func):
        l_args = [self.gen.get_repr(arg) for arg in args]
        l_func.dependencies.update(l_args)
        if self.name == "%std.isinstance":
            l_tmp = self.gen.get_local_tmp(PointerTypeRepr("%std.object",
                                                           self.gen), l_func)
            l_func.dependencies.add(l_tmp)
            lblock.cast(l_tmp, l_args[1])
            l_args[1] = l_tmp
        lblock.call(l_target, l_args[0], l_args[1:])

class FunctionRepr(LLVMRepr):
    l_functions = {}
    def get(obj, gen):
        name = None
        if isinstance(obj, annmodel.SomePBC) and \
                 len(obj.prebuiltinstances) == 1:
            obj = obj.prebuiltinstances.keys()[0]
        elif isinstance(obj, Constant):
            obj = obj.value
        if isinstance(obj, MethodType):
            name = obj.im_class.__name__ + "." + obj.im_func.__name__
            obj = obj.im_func
        if isinstance(obj, FunctionType):
            if (obj, gen) in FunctionRepr.l_functions:
                return FunctionRepr.l_functions[(obj, gen)]
            if name is None:
                name = obj.__name__
            l_func = FunctionRepr(gen.get_global_tmp(name), obj, gen)
            FunctionRepr.l_functions[(obj, gen)] = l_func
            return l_func
        return None
    get = staticmethod(get)

    def __init__(self, name, function, gen):
        if debug:
            print "FunctionRepr: %s" % name
        self.gen = gen
        self.func = function
        self.translator = gen.translator
        self.name = name
        self.graph = self.translator.getflowgraph(self.func)
        self.annotator = gen.translator.annotator
        self.blocknum = {}
        self.allblocks = []
        self.pyrex_source = ""
        self.dependencies = sets.Set()
        self.get_bbs()
        self.se = False

    def setup(self):
        if self.se:
            return
        self.se = True
        self.l_args = [self.gen.get_repr(ar)
                       for ar in self.graph.startblock.inputargs]
        self.dependencies.update(self.l_args)
        self.retvalue = self.gen.get_repr(self.graph.returnblock.inputargs[0])
        self.dependencies.add(self.retvalue)
        self.build_bbs()

    def get_returntype():
        return self.rettype.llvmname()

    def get_bbs(self):
        def visit(node):
            if isinstance(node, Block) and node not in self.blocknum:
                self.allblocks.append(node)
                self.blocknum[node] = len(self.blocknum)
        traverse(visit, self.graph)
        self.same_origin_block = [False] * len(self.allblocks)

    def build_bbs(self):
        a = self.annotator
        for number, pyblock in enumerate(self.allblocks):
            lblock = llvmbc.BasicBlock("block%i" % number)
            pyblock = self.allblocks[number]
            if number == 0:
                self.llvm_func = llvmbc.Function(self.llvmfuncdef(), lblock)
            else:
                self.llvm_func.basic_block(lblock)
            #Create Phi nodes (but not for the first block)
            incoming_links = []
            def visit(node):
                if isinstance(node, Link) and node.target == pyblock:
                    incoming_links.append(node)
            traverse(visit, self.graph)
            #special case if the incoming links are from the same block
            if len(incoming_links) == 2 and \
               incoming_links[0].prevblock == incoming_links[1].prevblock:
                for i, arg in enumerate(pyblock.inputargs):
                    l_select = self.gen.get_repr(
                        incoming_links[0].prevblock.exitswitch)
                    l_arg = self.gen.get_repr(arg)
                    l_v1 = self.gen.get_repr(incoming_links[1].args[i])
                    l_v2 = self.gen.get_repr(incoming_links[0].args[i])
                    self.dependencies.update([l_arg, l_switch, l_v1, l_v2])
                    lblock.select(l_arg, l_select, l_v1, l_v2)
            elif len(incoming_links) != 0:
                for i, arg in enumerate(pyblock.inputargs):
                    l_arg = self.gen.get_repr(arg)
                    l_values = [self.gen.get_repr(l.args[i])
                                for l in incoming_links]
                    for j in range(len(l_values)):
                        if l_values[j].llvmtype() != l_arg.llvmtype():
                            l_values[j] = l_values[j].alt_types[l_arg.llvmtype()]
                    self.dependencies.add(l_arg)
                    self.dependencies.update(l_values)
                    lblock.phi(l_arg, l_values,
                               ["%%block%i" % self.blocknum[l.prevblock]
                                for l in incoming_links])
            #Handle SpaceOperations
            for op in pyblock.operations:
                l_target = self.gen.get_repr(op.result)
                self.dependencies.add(l_target)
                l_arg0 = self.gen.get_repr(op.args[0])
                self.dependencies.add(l_arg0)
                l_op = getattr(l_arg0, "op_" + op.opname, None)
                if l_op is not None:
                    l_op(l_target, op.args, lblock, self)
                #XXX need to find more elegant solution for this special case
                elif op.opname == "newtuple":
                    l_target.type.t_op_newtuple(l_target, op.args,
                                                lblock, self)
                elif op.opname in INTRINSIC_OPS:
                    l_args = [self.gen.get_repr(arg) for arg in op.args[1:]]
                    self.dependencies.update(l_args)
                    lblock.spaceop(l_target, op.opname, [l_arg0] + l_args)
                else:
                        s = "SpaceOperation %s not supported. Target: %s " \
                            "Args: %s " % (op.opname, l_target, op.args) + \
                            "Dispatched on: %s" % l_arg0
                            
                        raise CompileError, s
            # XXX: If a variable is passed to another block and has a different
            # type there, we have to make the cast in this block since the phi
            # instructions in the next block cannot be preceded by any other
            # instrcution
            for link in pyblock.exits:
                for i, arg in enumerate(link.args):
                    localtype = self.annotator.binding(arg)
                    targettype = self.annotator.binding(
                        link.target.inputargs[i])
                    l_targettype = self.gen.get_repr(targettype)
                    l_localtype = self.gen.get_repr(localtype)
                    l_local = self.gen.get_repr(arg)
                    self.dependencies.update([l_targettype, l_localtype,
                                              l_local])
                    if l_targettype.llvmname() != l_localtype.llvmname():
                        l_tmp = self.gen.get_local_tmp(l_targettype, self)
                        lblock.cast(l_tmp, l_local)
                        l_local.alt_types = {l_targettype.llvmname(): l_tmp}
            #Create branches
            if pyblock.exitswitch is None:
                if pyblock.exits == ():
                    l_returnvalue = self.gen.get_repr(pyblock.inputargs[0])
                    self.dependencies.add(l_returnvalue)
                    lblock.ret(l_returnvalue)
                else:
                    lblock.uncond_branch(
                        "%%block%i" % self.blocknum[pyblock.exits[0].target])
            else:
                assert isinstance(a.binding(pyblock.exitswitch),
                                  annmodel.SomeBool)
                l_switch = self.gen.get_repr(pyblock.exitswitch)
                self.dependencies.add(l_switch)
                lblock.cond_branch(
                    l_switch,
                    "%%block%i" % self.blocknum[pyblock.exits[1].target],
                    "%%block%i" % self.blocknum[pyblock.exits[0].target])

    def llvmfuncdef(self):
        s = "internal %s %s(" % (self.retvalue.llvmtype(), self.name)
        return s + ", ".join([a.typed_name() for a in self.l_args]) + ")"

    def rettype(self):
        return self.retvalue.llvmtype()

    def get_functions(self):
        return str(self.llvm_func)

    def llvmtype(self):
        assert self.llvmfuncdef().count(self.name) == 1
        return self.llvmfuncdef().replace(self.name + "(", "(") + "*"

    def op_simple_call(self, l_target, args, lblock, l_func):
        l_args = [self.gen.get_repr(arg) for arg in args]
        for i, (l_a1, l_a2) in enumerate(zip(l_args[1:], self.l_args)):
            if l_a1.llvmtype() != l_a2.llvmtype():
                l_tmp = self.gen.get_local_tmp(l_a2.type, l_func)
                lblock.cast(l_tmp, l_a1)
                l_args[1 + i] = l_tmp
        l_func.dependencies.update(l_args)
        lblock.call(l_target, l_args[0], l_args[1:])

class EntryFunctionRepr(LLVMRepr):
    def get(obj, gen):
        return None
    get = staticmethod(get)

    def __init__(self, name, function, gen):
        self.gen = gen
        self.function = function
        self.name = name
        self.dependencies = sets.Set()
        self.branch_added = False

    def setup(self):
        self.l_function = self.gen.get_repr(self.function)
        self.dependencies.add(self.l_function)
        lblock = llvmbc.BasicBlock("entry")
        lblock.instruction("%tmp = load bool* %Initialized.0__")
        lblock.instruction("br bool %tmp, label %real_entry, label %init")
        self.llvm_func = llvmbc.Function(self.llvmfuncdef(), lblock)
        self.init_block = llvmbc.BasicBlock("init")
        self.init_block.instruction("store bool true, bool* %Initialized.0__")
        real_entry = llvmbc.BasicBlock("real_entry")
        l_ret = self.gen.get_local_tmp(self.l_function.retvalue.type, self)
        self.l_function.op_simple_call(
            l_ret, [self.function] + self.l_function.l_args, real_entry, self)
        real_entry.ret(l_ret)
        self.llvm_func.basic_block(real_entry)
        self.llvm_func.basic_block(self.init_block)
        
    def cfuncdef(self):
        a = self.l_function.translator.annotator
        retv = self.l_function.graph.returnblock.inputargs[0]
        rettype_c = C_SIMPLE_TYPES[a.binding(retv).__class__]
        args = self.l_function.graph.startblock.inputargs
        argtypes_c = [C_SIMPLE_TYPES[a.binding(v).__class__] for v in args]
        fd = "%s %s(%s)" % (rettype_c, self.name[1:],
                            ", ".join(argtypes_c))
        return fd

    def llvmfuncdef(self):
        s = "%s %s(" % (self.l_function.retvalue.llvmtype(), self.name)
        s += ", ".join([a.typed_name() for a in self.l_function.l_args]) + ")"
        return s

    def get_pyrex_source(self):
        name = self.name[1:]
        args = self.l_function.graph.startblock.inputargs
        self.pyrex_source = ["cdef extern %s\n" %
                             (self.cfuncdef())]
        self.pyrex_source += ["def wrap_%s(" % name]
        t = []
        for i, a in enumerate(args):
            t += ["%s" % a]
        t = ", ".join(t)
        self.pyrex_source += t + "):\n\treturn %s(%s)\n\n" % (name, t)
        self.pyrex_source = "".join(self.pyrex_source)
        return self.pyrex_source

    def rettype(self):
        return self.l_function.retvalue.llvmtype()

    def get_functions(self):
        if not self.branch_added:
            self.init_block.uncond_branch("%real_entry")
        return str(self.llvm_func)

    def get_globals(self):
        return "%Initialized.0__ = internal global bool false"

    def llvmtype(self):
        assert self.llvmfuncdef().count(self.name) == 1
        return self.llvmfuncdef().replace(self.name + "(", "(") + "*"

    def op_simple_call(self, l_target, args, lblock, l_func):
        self.l_function.op_simple_call(l_target, [self.function] + args,
                                       lblock, l_func)

class VirtualMethodRepr(LLVMRepr):
    # Really stupid implementation of virtual functions:
    # Do a switch on the id of the class of the object and cast the object
    # to the appropriate class
    # Should be replaced by function pointers
    def get(obj, gen):
        if isinstance(obj, annmodel.SomePBC) and \
                 len(obj.prebuiltinstances) > 1 and \
                 isinstance(obj.prebuiltinstances.keys()[0], FunctionType):
            return VirtualMethodRepr(obj.prebuiltinstances, gen)
        return None
    get = staticmethod(get)

    def __init__(self, prebuiltinstances, gen):
        if debug:
            print "VirtualMethodRepr: %s" % prebuiltinstances
        self.gen = gen
        classes = prebuiltinstances.values()
        self.commonbase = reduce(lambda a, b: a.commonbase(b), classes)
        self.funcs = prebuiltinstances.keys()
        self.name = "%" + self.funcs[0].__name__ + ".virtual"
        self.attribute = self.funcs[0].__name__
        self.dependencies = sets.Set()

    def setup(self):
        self.l_commonbase = self.gen.get_repr(self.commonbase)
        self.l_classes = [self.l_commonbase] + \
                         list(self.l_commonbase.iter_subclasses())
        self.dependencies.update(self.l_classes)
        self.l_funcs = []
        #find appropriate method for every class
        for l_cls in self.l_classes:
            for classdef in l_cls.classdef.getmro():
                if classdef.cls.__dict__.has_key(self.attribute):
                    self.l_funcs.append(self.gen.get_repr(
                        classdef.cls.__dict__[self.attribute]))
                    break
            else:
                raise CompileError, "Couldn't find method %s for %s" % \
                      (self.attribute, l_cls.classdef.cls)
        self.dependencies.update(self.l_funcs)
        self.retvalue = self.l_funcs[0].retvalue
        self.type_numbers = [id(l_c) for l_c in self.l_classes]
        self.l_args = [self.gen.get_repr(ar)
                       for ar in self.l_funcs[0].graph.startblock.inputargs]
        l_retvalue = self.retvalue
        self.dependencies.update(self.l_args)
        #create function
        #XXX pretty messy
        entryblock = llvmbc.BasicBlock("entry")
        l_clp = self.gen.get_local_tmp(PointerTypeRepr("%std.class*",
                                                       self.gen), self)
        l_cl = self.gen.get_local_tmp(PointerTypeRepr("%std.class",
                                                      self.gen), self)
        l_uip = self.gen.get_local_tmp(PointerTypeRepr("uint", self.gen),
                                       self)
        l_ui = self.gen.get_local_tmp(
            self.gen.get_repr(annmodel.SomeInteger(True, True)), self)
        self.dependencies.update([l_clp, l_cl, l_uip, l_ui])
        entryblock.getelementptr(l_clp, self.l_args[0], [0, 0])
        entryblock.load(l_cl, l_clp)
        entryblock.getelementptr(l_uip, l_cl, [0, 1])
        entryblock.load(l_ui, l_uip)
        entryblock.switch(l_ui, "%" + self.l_commonbase.classdef.cls.__name__,
                          [(str(abs(id(l_c))), "%" + l_c.classdef.cls.__name__)
                           for l_c in self.l_classes])
        lfunc = llvmbc.Function(self.llvmfuncdef(), entryblock)
        for i, l_cls in enumerate(self.l_classes):
            lblock = llvmbc.BasicBlock(l_cls.classdef.cls.__name__)
            lfunc.basic_block(lblock)
            l_tmp = self.gen.get_local_tmp(l_cls, self)
            lblock.cast(l_tmp, self.l_args[0])
            l_tmp_ret = self.gen.get_local_tmp(l_retvalue.type, self)
            self.l_funcs[i].op_simple_call(
                l_tmp_ret, [self.l_funcs[i], l_tmp] + 
                self.l_funcs[0].graph.startblock.inputargs[1:], lblock, self)
            lblock.ret(l_tmp_ret)
        self.llvm_func = lfunc

    def op_simple_call(self, l_target, args, lblock, l_func):
        name = self.name[1:-8]
        l_args = [self.gen.get_repr(arg) for arg in args]
        l_func.dependencies.update(l_args)
        # call the method directly if no subclass of the class of args[1] has
        # a special version of this method defined
        for l_cls in l_args[1].type.iter_subclasses():
            if l_cls.classdef.cls.__dict__.has_key(name):
                break
        else:
            for clsdef in l_args[1].type.classdef.getmro():
                if clsdef.cls.__dict__.has_key(name):
                    l_method = self.gen.get_repr(clsdef.cls.__dict__[name])
                    args[0] = l_method
                    print l_method.llvmname(), l_method
                    l_method.op_simple_call(l_target, args, lblock, l_func)
                    return
        if l_args[1].llvmtype() != self.l_args[0].llvmtype():
            l_tmp = self.gen.get_local_tmp(self.l_args[0].type, l_func)
            l_func.dependencies.add(l_tmp)
            lblock.cast(l_tmp, l_args[1])
            l_args[1] = l_tmp
        lblock.call(l_target, l_args[0], l_args[1:])
        return
        
    def get_functions(self):
        return str(self.llvm_func)

    def llvmfuncdef(self):
        s = "internal %s %s(" % (self.l_funcs[0].retvalue.llvmtype(),
                                 self.name)
        return s + ", ".join([a.typed_name() for a in self.l_args]) + ")"

    def rettype(self):
        return self.retvalue.llvmtype()

class BoundMethodRepr(LLVMRepr):
    def get(obj, gen):
        return None
    get = staticmethod(get)
    def __init__(self, l_func, l_self, l_class, gen):
        self.gen = gen
        self.l_func = l_func
        self.l_self = l_self
        self.l_class = l_class
        self.dependencies = sets.Set([l_self, l_class, l_func])

    def t_op_simple_call(self, l_target, args, lblock, l_func):
        self.l_func.op_simple_call(l_target,
                                   [self.l_func, self.l_self] + args[1:],
                                   lblock, l_func)
