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


INTRINSIC_OPS = ["lt", "le", "eq", "ne", "gt", "ge", "is", "is_true", "len",
                 "neg", "pos", "invert", "add", "sub", "mul", "truediv",
                 "floordiv", "div", "mod", "pow", "lshift", "rshift", "and",
                 "or", "xor", "inplace_add", "inplace_sub", "inplace_mul",
                 "inplace_truediv", "inplace_floordiv", "inplace_div",
                 "inplace_mod", "inplace_pow", "inplace_lshift",
                 "inplace_rshift", "inplace_and", "inplace_or", "inplace_xor",
                 "getitem", "setitem", "delitem", "contains", "newlist",
                 "alloc_and_set"]

C_SIMPLE_TYPES = {annmodel.SomeChar: "char",
                  annmodel.SomeBool: "unsigned char",
                  annmodel.SomeInteger: "int"}

debug = 0


def llvmcompile(transl):
    gen = LLVMGenerator(transl)
    return gen.compile()


class CompileError(exceptions.Exception):
    pass

class LLVMGenerator(object):
    def __init__(self, transl):
        self.translator = transl
        self.annotator = self.translator.annotator
        self.global_count = 0
        self.repr_classes = [eval(s)
                             for s in dir(sys.modules.get(self.__module__))
                             if "Repr" in s]
        self.llvm_reprs = {}
        self.l_entrypoint = self.get_repr(self.translator.functions[0])

    def compile(self):
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
        mod = build_llvm_module.make_module_from_llvm(llvmfile, pyxfile)
        return getattr(mod, "wrap_%s" % name)

    def get_global_tmp(self, used_by=None):
        self.global_count += 1
        return "%%glb.%s.%i" % ((used_by or "unknown"), self.global_count)

    def get_repr(self, obj):
        if debug:
            print "looking for object", obj, type(obj).__name__, obj.__class__,
        if obj in self.llvm_reprs:
            if debug:
                print "->exists already"
            return self.llvm_reprs[obj]
        for cl in self.repr_classes:
            if debug:
                print "trying", cl
            g = cl.get(obj, self)
            if g is not None:
                self.llvm_reprs[obj] = g
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
        
class LLVMRepr(object):
    def get(obj, gen):
        return None
    get = staticmethod(get)
    
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

    def llvmname(self):
        return self.name

    def llvmtype(self):
        return self.type


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
        self.dependencies = [self.type]

    def llvmname(self):
        return "%" + self.var.name
        

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
        self.dependencies = [self.type]

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
        if self.includefile != "":
            f = file(autopath.this_dir + "/" + self.includefile, "r")
            s = f.read()
            f.close()
            return s
        return ""

    def llvmname(self):
        return self.name + "*"

    def llvmname_wo_pointer(self):
        return self.name

class ListTypeRepr(TypeRepr):
    l_listtypes = {}
    def get(obj, gen):
        if obj.__class__ is annmodel.SomeList:
            if obj.s_item.__class__ in ListTypeRepr.l_listtypes:
                return ListTypeRepr.l_listtypes[obj.s_item.__class__]
            l_repr = ListTypeRepr(obj, gen)
            ListTypeRepr.l_listtypes[obj.s_item.__class__] = l_repr
            return l_repr
        return None
    get = staticmethod(get)

    def __init__(self, obj, gen):
        if debug:
            print "ListTypeRepr: %s, %s" % (obj, obj.s_item)
        self.gen = gen
        self.l_itemtype = gen.get_repr(obj.s_item)
        self.dependencies = [self.l_itemtype]
        itemtype = self.l_itemtype.llvmname()
        self.name = "%%std.list.%s" % itemtype.strip("%")
        self.definition = self.name + " = type {uint, %s*}" % itemtype

    def get_functions(self):
        f = file(autopath.this_dir + "/list_template.ll", "r")
        s = f.read()
        f.close()
        s = s.replace("%(item)s", self.l_itemtype.llvmname().strip("%"))
        #XXX assuming every type consists of 4 bytes
        s = s.replace("%(sizeof)i", str(4))
        return s

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
        self.dependencies = []
        self.includefile = ""

    def llvmname(self):
        return "void"

    def typed_name(self):
        return self.llvmtype() + " " + self.llvmname()

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
        elif type(obj).__name__ == 'function':
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
        self.translator.simplify()
        self.name = "%" + name
        self.graph = self.translator.getflowgraph(self.func)
        self.annotator = gen.translator.annotator
        transform.transform_allocate(self.annotator)
        self.blocknum = {}
        self.allblocks = []
        self.pyrex_source = ""
        self.dependencies = sets.Set()
        self.get_bbs()
        self.build_bbs()

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
                if op.opname == "simple_call" and \
                       isinstance(op.args[0], Constant) and \
                       op.args[0].value == self.func:
                    l_args = [self] + \
                             [self.gen.get_repr(arg) for arg in op.args[1:]]
                else:
                    l_args = [self.gen.get_repr(arg) for arg in op.args]
                l_target = self.gen.get_repr(op.result)
                self.dependencies.update(l_args)
                self.dependencies.add(l_target)
                if op.opname in INTRINSIC_OPS:
                    lblock.spaceop(l_target, op.opname, l_args)
                elif op.opname == "simple_call":
                    lblock.call(l_target, l_args[0], l_args[1:])
                else:
                    self.translator.view()
                    raise CompileError, "Unhandeled SpaceOp %s" % op.opname
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
        l_retv = self.gen.get_repr(self.graph.returnblock.inputargs[0])
        l_args = [self.gen.get_repr(ar)
                  for ar in self.graph.startblock.inputargs]
        self.dependencies.update(l_args)
        self.dependencies.add(l_retv)
        s = "%s %s(" % (l_retv.llvmtype(), self.name)
        return s + ", ".join([a.typed_name() for a in l_args]) + ")"
        return llvmbc.function(l_retv, self.name, l_args)

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


    def get_functions(self):
        return str(self.llvm_func)

    def llvmname(self):
        return self.name

    def llvmtype(self):
        assert self.llvmfuncdef().count(self.name) == 1
        return self.llvmfuncdef().replace(self.name + "(", "(")

