import autopath
import exceptions, sets, StringIO

from types import FunctionType

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
                 "contains", "newlist", "alloc_and_set"]

C_SIMPLE_TYPES = {annmodel.SomeChar: "char",
                  annmodel.SomeBool: "unsigned char",
                  annmodel.SomeInteger: "int"}


debug = 1


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

    def llvmname(self):
        return ""

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
int, bool, char (string of length 1)"""

    LLVM_SIMPLE_TYPES = {annmodel.SomeInteger: "int",
                         annmodel.SomeChar: "sbyte",
                         annmodel.SomeBool: "bool"}
    def get(obj, gen):
        if not isinstance(obj, Constant):
            return None
        type = gen.annotator.binding(obj)
        if type.__class__ in SimpleRepr.LLVM_SIMPLE_TYPES:
            llvmtype = SimpleRepr.LLVM_SIMPLE_TYPES[type.__class__]
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

    def llvmname(self):
        return self.name

    def llvmtype(self):
        return self.type

    def __getattr__(self, name):
        return getattr(self.type, name, None)


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
        else:
            raise AttributeError, ("VariableRepr instance has no attribute %s"
                                   % repr(name))

class StringRepr(LLVMRepr):
    def get(obj, gen):
        if isinstance(obj, Constant):
            type = gen.annotator.binding(obj)
            if type.__class__ is annmodel.SomeString:
                l_repr = StringRepr(obj, gen)
                return l_repr
        return None
    get = staticmethod(get)

    def __init__(self, obj, gen):
        if debug:
            print "StringRepr: %s" % obj.value
        self.s = obj.value
        self.gen = gen
        self.glvar1 = gen.get_global_tmp("StringRepr")
        self.glvar2 = gen.get_global_tmp("StringRepr")
        self.type = gen.get_repr(gen.annotator.binding(obj))
        self.dependencies = sets.Set([self.type])

    def llvmname(self):
        return self.glvar2

    def get_globals(self):
        d = {"len": len(self.s), "gv1": self.glvar1, "gv2": self.glvar2,
             "type": self.type.llvmname_wo_pointer(), "string": self.s}
        s = """%(gv1)s = internal constant [%(len)i x sbyte] c"%(string)s"
%(gv2)s = internal constant %(type)s {uint %(len)i,\
sbyte* getelementptr ([%(len)i x sbyte]* %(gv1)s, uint 0, uint 0)}"""
        return s % d

class TypeRepr(LLVMRepr):
    l_stringtype = None
    def get(obj, gen):
##         print "TypeRepr", obj
        if obj.__class__ is annmodel.SomeString or obj is str:
            if TypeRepr.l_stringtype is None:
                l_repr = TypeRepr("%std.string",
                                  "%std.string = type {uint, sbyte*}",
                                  "string.ll", gen)
                TypeRepr.l_stringtype = l_repr
            return TypeRepr.l_stringtype
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
    

class SimpleTypeRepr(TypeRepr):
    def get(obj, gen):
        if obj.__class__ in [annmodel.SomeInteger, int]:
            l_repr = SimpleTypeRepr("int", gen)
            return l_repr            
        elif obj.__class__ in [annmodel.SomeBool, bool]:
            l_repr = SimpleTypeRepr("bool", gen)
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

class NoneRepr(TypeRepr):
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


class ClassRepr(TypeRepr):
    def get(obj, gen):
        if obj.__class__ is Constant:
            bind = gen.annotator.binding(obj)
            if bind.__class__ is annmodel.SomePBC and \
               bind.const.__class__ == type:
                classdef = gen.annotator.bookkeeper.userclasses[bind.const]
                return ClassRepr(classdef, gen)
        if isinstance(obj, annmodel.SomeInstance):
            return ClassRepr(obj.classdef, gen)
        return None
    get = staticmethod(get)

    def __init__(self, obj, gen):
        if 1:
            print "ClassRepr: %s", obj
        self.classdef = obj
        self.gen = gen
        self.includefile = ""
        self.name = gen.get_global_tmp("class.%s" % self.classdef.cls.__name__)
        self.dependencies = sets.Set()
        self.attr_num = {}
        self.se = False

    def setup(self):
        self.se = True
        print "ClassRepr.setup()", id(self)
        gen = self.gen
        attribs = []
        meth = []
        print "attributes"
        for key, attr in self.classdef.attrs.iteritems():
            print key, attr, attr.sources, attr.s_value,
            if len(attr.sources) != 0:
                func = self.classdef.cls.__dict__[attr.name]
                meth.append((key, func))
                print "--> method"
                continue
            if isinstance(attr.s_value, annmodel.SomePBC) and \
               attr.s_value.knowntype is FunctionType:
                func = self.classdef.cls.__dict__[attr.name]
                meth.append((key, func))
                print "--> method"
                continue
            attribs.append(attr)
            print "--> value"
        self.l_attrs_types = [gen.get_repr(attr.s_value) for attr in attribs]
        self.dependencies = sets.Set(self.l_attrs_types)
        attributes = ", ".join([at.llvmname() for at in self.l_attrs_types])
        self.definition = "%s = type {int*, %s}" % (self.name, attributes)
        self.attr_num = {}
        for i, attr in enumerate(attribs):
            self.attr_num[attr.name] = i + 1
        self.methods = dict(meth)
        print "setup: ", self, self.attr_num, self.methods

    def op_simple_call(self, l_target, args, lblock, l_func):
        l_init = self.gen.get_repr(self.methods["__init__"])
        l_func.dependencies.add(l_init)
        l_args = [self.gen.get_repr(arg) for arg in args[1:]]
        self.dependencies.update(l_args)
        lblock.malloc(l_target, self)
        lblock.call_void(l_init, [l_target] + l_args)

    def t_op_getattr(self, l_target, args, lblock, l_func):
        print "t_op_getattrs", l_target, args
        if not isinstance(args[1], Constant):
            raise CompileError,"getattr called with non-constant: %s" % args[1]
        if args[1].value in self.attr_num:
            l_args0 = self.gen.get_repr(args[0])
            l_func.dependencies.add(l_args0)
            pter = self.gen.get_local_tmp(l_func)
            lblock.getelementptr(pter, l_args0,
                                 [0, self.attr_num[args[1].value]])
            lblock.load(l_target, pter)
        elif args[1].value in self.methods:
            print "method", 
            l_args0 = self.gen.get_repr(args[0])
            print l_args0, l_args0.typed_name()
            l_func.dependencies.add(l_args0)
            l_method = BoundMethodRepr(self.methods[args[1].value],
                                       l_args0, self, self.gen)
            l_target.type = l_method

    def t_op_setattr(self, l_target, args, lblock, l_func):
        if not isinstance(args[1], Constant):
            raise CompileError,"setattr called with non-constant: %s" % args[1]
        if args[1].value in self.attr_num:
            l_args0 = self.gen.get_repr(args[0])
            l_value = self.gen.get_repr(args[2])
            self.dependencies.update([l_args0, l_value])
            pter = self.gen.get_local_tmp(l_func)
            lblock.getelementptr(pter, l_args0,
                                 [0, self.attr_num[args[1].value]])
            lblock.store(l_value, pter)


class BuiltinFunctionRepr(LLVMRepr):
    def get(obj, gen):
        if isinstance(obj, Constant) and \
           type(obj.value).__name__ == 'builtin_function_or_method':
            l_repr = BuiltinFunctionRepr(obj.value, gen)
            return l_repr
        return None
    get = staticmethod(get)

    def __init__(self, bi, gen):
        self.name = "%std." + bi.__name__
        self.gen = gen

    def llvmname(self):
        return self.name

class FunctionRepr(LLVMRepr):
    def get(obj, gen):
        if isinstance(obj, Constant) and \
               type(obj.value).__name__ == 'function':
            name = obj.value.__name__
            l_repr = FunctionRepr(name, obj.value, gen)
            return l_repr
        elif isinstance(obj, annmodel.SomePBC):
            obj = obj.prebuiltinstances.keys()[0]
        if type(obj).__name__ == 'function':
            name = obj.__name__
            l_repr = FunctionRepr(name, obj, gen)
            return l_repr
        return None
    get = staticmethod(get)

    def __init__(self, name, function, gen):
        if debug:
            print "FunctionRepr: %s" % name
        self.gen = gen
        self.func = function
        self.translator = gen.translator
        self.name = "%" + name
        self.graph = self.translator.getflowgraph(self.func)
        self.annotator = gen.translator.annotator
        self.blocknum = {}
        self.allblocks = []
        self.pyrex_source = ""
        self.dependencies = sets.Set()
        self.get_bbs()

    def setup(self):
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
            #Create Phi nodes (but not for the first node)
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
                    self.dependencies.add(l_arg)
                    self.dependencies.update(l_values)
                    lblock.phi(l_arg, l_values,
                               ["%%block%i" % self.blocknum[l.prevblock]
                                for l in incoming_links])
            #Create a function call for every operation in the block
            for op in pyblock.operations:
                l_target = self.gen.get_repr(op.result)
                self.dependencies.add(l_target)
                if op.opname in INTRINSIC_OPS:
                    l_args = [self.gen.get_repr(arg) for arg in op.args]
                    self.dependencies.update(l_args)
                    lblock.spaceop(l_target, op.opname, l_args)
                else:
                    l_arg0 = self.gen.get_repr(op.args[0])
                    self.dependencies.add(l_arg0)
                    l_op = getattr(l_arg0, "op_" + op.opname, None)
                    if l_op is None:
                        s = "SpaceOperation %s not supported. Target: %s " \
                            "Args: %s" % (op.opname, l_target, op.args)
                        raise CompileError, s
                    l_op(l_target, op.args, lblock, self)
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

    def cfuncdef(self):
        a = self.translator.annotator
        retv = self.graph.returnblock.inputargs[0]
        rettype_c = C_SIMPLE_TYPES[a.binding(retv).__class__]
        args = self.graph.startblock.inputargs
        argtypes_c = [C_SIMPLE_TYPES[a.binding(v).__class__] for v in args]
        fd = "%s %s(%s)" % (rettype_c, self.func.func_name,
                            ", ".join(argtypes_c))
        return fd

    def llvmfuncdef(self):
        a = self.translator.annotator
        l_args = [self.gen.get_repr(ar)
                  for ar in self.graph.startblock.inputargs]
        self.dependencies.update(l_args)
        s = "%s %s(" % (self.retvalue.llvmtype(), self.name)
        return s + ", ".join([a.typed_name() for a in l_args]) + ")"

    def get_pyrex_source(self):
        name = self.func.func_name
        args = self.graph.startblock.inputargs
        self.pyrex_source = ["cdef extern %s\n" %
                             (self.cfuncdef())]
        self.pyrex_source += ["def wrap_%s(" % name]
        t = []
        for i, a in enumerate(args):
            t += ["%s" % a]
        t = ", ".join(t)
        self.pyrex_source += t + "):\n\treturn %s(%s)\n\n" % (name, t)
        self.pyrex_source += "\ndef test(a):\n\treturn a + 1\n\n"
        self.pyrex_source = "".join(self.pyrex_source)
        return self.pyrex_source

    def rettype(self):
        return self.retvalue.llvmtype()

    def get_functions(self):
        return str(self.llvm_func)

    def llvmname(self):
        return self.name

    def llvmtype(self):
        assert self.llvmfuncdef().count(self.name) == 1
        return self.llvmfuncdef().replace(self.name + "(", "(") + "*"

    def op_simple_call(self, l_target, args, lblock, l_func):
        l_args = [self.gen.get_repr(arg) for arg in args]
        self.dependencies.update(l_args)
        lblock.call(l_target, l_args[0], l_args[1:])

class BoundMethodRepr(LLVMRepr):
    def get(obj, gen):
        return None
    get = staticmethod(get)

    def __init__(self, func, l_self, l_class, gen):
        self.gen = gen
        self.func = func
        self.l_self = l_self
        self.l_class = l_class
        self.dependencies = sets.Set([l_self, l_class])
        self.se = False

    def setup(self):
        print "setup BoundMethodRepr"
        self.se = True
        self.l_func = self.gen.get_repr(self.func)
        self.dependencies.add(self.l_func)


    def t_op_simple_call(self, l_target, args, lblock, l_func):
        if not self.se:
            self.setup()
        self.l_func.op_simple_call(l_target,
                                   [self.l_func, self.l_self] + args[1:],
                                   lblock, l_func)
