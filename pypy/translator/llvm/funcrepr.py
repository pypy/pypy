import autopath
import sets, StringIO

from types import FunctionType, MethodType

from pypy.objspace.flow.model import Variable, Constant, Block, Link
from pypy.objspace.flow.model import last_exception, last_exc_value
from pypy.objspace.flow.model import traverse, checkgraph
from pypy.annotation import model as annmodel
from pypy.translator.llvm import llvmbc
from pypy.translator.unsimplify import remove_double_links

from pypy.translator.llvm.representation import debug, LLVMRepr
from pypy.translator.llvm.typerepr import TypeRepr, PointerTypeRepr


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
        remove_double_links(self.translator, self.graph)
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
        checkgraph(self.graph)
        a = self.annotator
        for number, pyblock in enumerate(self.allblocks):
            pyblock = self.allblocks[number]
            is_tryblock = isinstance(pyblock.exitswitch, Constant) and \
                          pyblock.exitswitch.value == last_exception
            if is_tryblock:
                regularblock = "block%i" % self.blocknum[
                    pyblock.exits[0].target]
                exceptblock = "block%i.except" % self.blocknum[pyblock]
                lblock = llvmbc.TryBasicBlock("block%i" % number,
                                              regularblock, exceptblock)
                l_excblock = llvmbc.BasicBlock("block%i.except" % number)
                l_excp = self.gen.get_repr(last_exception)
                l_uip = self.gen.get_local_tmp(PointerTypeRepr("uint",
                                                               self.gen), self)
                l_ui = self.gen.get_local_tmp(
                    self.gen.get_repr(annmodel.SomeInteger(True, True)), self)
                self.dependencies.update([l_excp, l_uip, l_ui])
                l_excblock.load(l_cl, l_excp)
                l_excblock.getelementptr(l_uip, l_cl, [0, 1])
                l_excblock.load(l_ui, l_uip)
                l_excblock.switch(l_ui, "%%block%i.unwind" % number,
                                  [(str(abs(id(l_c))),
                                    XXXXXXXXXXXXX)
                                   for exc in pyblock.exits[1:]])
            else:
                lblock = llvmbc.BasicBlock("block%i" % number)
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
            if len(incoming_links) != 0:
                for i, arg in enumerate(pyblock.inputargs):
                    l_arg = self.gen.get_repr(arg)
                    l_values = [self.gen.get_repr(l.args[i])
                                for l in incoming_links]
                    for j in range(len(l_values)):
                        if l_values[j].llvmtype() != l_arg.llvmtype():
                            try:
                                l_values[j] = \
                                        l_values[j].alt_types[l_arg.llvmtype()]
                            except KeyError:
                                pass
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
            # instruction
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
                if pyblock == self.graph.returnblock:
                    l_returnvalue = self.gen.get_repr(pyblock.inputargs[0])
                    self.dependencies.add(l_returnvalue)
                    lblock.ret(l_returnvalue)
                else:
                    lblock.uncond_branch(
                        "%%block%i" % self.blocknum[pyblock.exits[0].target])
            elif isinstance(pyblock.exitswitch, Constant) and \
                 pyblock.exitswitch.value == last_exception:
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
