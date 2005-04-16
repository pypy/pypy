import autopath
import sets, StringIO

from types import FunctionType, MethodType

from pypy.objspace.flow.model import Variable, Constant, Block, Link
from pypy.objspace.flow.model import last_exception, last_exc_value
from pypy.objspace.flow.model import traverse, checkgraph
from pypy.annotation import model as annmodel
from pypy.annotation.builtin import BUILTIN_ANALYZERS
from pypy.translator.llvm import llvmbc
from pypy.translator.unsimplify import remove_double_links

from pypy.translator.llvm.representation import debug, LLVMRepr, CompileError
from pypy.translator.llvm.typerepr import TypeRepr, PointerTypeRepr

debug = False

INTRINSIC_OPS = ["lt", "le", "eq", "ne", "gt", "ge", "is_", "is_true", "len",
                 "neg", "pos", "invert", "add", "sub", "mul", "truediv",
                 "floordiv", "div", "mod", "pow", "lshift", "rshift", "and_",
                 "or", "xor", "inplace_add", "inplace_sub", "inplace_mul",
                 "inplace_truediv", "inplace_floordiv", "inplace_div",
                 "inplace_mod", "inplace_pow", "inplace_lshift",
                 "inplace_rshift", "inplace_and", "inplace_or", "inplace_xor",
                 "contains", "newlist", "newtuple", "alloc_and_set",
                 "issubtype", "type", "ord"]

C_SIMPLE_TYPES = {annmodel.SomeChar: "char",
                  annmodel.SomeString: "char*",
                  annmodel.SomeBool: "unsigned char",
                  annmodel.SomeInteger: "int",
                  annmodel.SomeFloat: "double"}


class BuiltinFunctionRepr(LLVMRepr):
    def get(obj, gen):
        if isinstance(obj, Constant):
            print "BuiltinFunctionRepr", obj.value
        if (isinstance(obj, Constant) and
            (obj in BUILTIN_ANALYZERS or
             isinstance(gen.annotator.binding(obj), annmodel.SomeBuiltin))):
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
        self.lblocks = []

    def setup(self):
        if self.se:
            return
        self.se = True
        self.l_args = [self.gen.get_repr(ar)
                       for ar in self.graph.startblock.inputargs]
        self.dependencies.update(self.l_args)
        self.retvalue = self.gen.get_repr(self.graph.returnblock.inputargs[0])
        self.dependencies.add(self.retvalue)
        self.l_default_args = None
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
        for number, pyblock in enumerate(self.allblocks):
            is_tryblock = isinstance(pyblock.exitswitch, Constant) and \
                          pyblock.exitswitch.value == last_exception
            if is_tryblock:
                block = TryBlockRepr(self, pyblock, self.gen)
            elif pyblock == self.graph.returnblock:
                block = ReturnBlockRepr(self, pyblock, self.gen)
            elif pyblock == self.graph.exceptblock:
                block = ExceptBlockRepr(self, pyblock, self.gen)
            else:
                block = BlockRepr(self, pyblock, self.gen)
        self.llvm_func = llvmbc.Function(self.llvmfuncdef(), self.lblocks[0])
        for bl in self.lblocks[1:]:
            self.llvm_func.basic_block(bl)

    def add_block(self, lblock):
        self.lblocks.append(lblock)

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
        if len(l_args) - 1 < len(self.l_args):
            assert self.func.func_defaults is not None
            if self.l_default_args is None:
                self.l_default_args = [self.gen.get_repr(Constant(de))
                                       for de in self.func.func_defaults]
                self.dependencies.update(self.l_default_args)
            offset = len(self.l_args) - len(self.l_default_args)
            for i in range(len(l_args) - 1, len(self.l_args)):
                l_args.append(self.l_default_args[i - offset])
        for i, (l_a1, l_a2) in enumerate(zip(l_args[1:], self.l_args)):
            if l_a1.llvmtype() != l_a2.llvmtype():
                l_tmp = self.gen.get_local_tmp(l_a2.type, l_func)
                lblock.cast(l_tmp, l_a1)
                l_args[1 + i] = l_tmp
        l_func.dependencies.update(l_args)
        lblock.call(l_target, l_args[0], l_args[1:])

class BlockRepr(object):
    def __init__(self, l_func, pyblock, gen):
        if debug:
            print "BlockRepr"
        self.l_func = l_func
        self.pyblock = pyblock
        self.gen = gen
        self.l_args = [self.gen.get_repr(a) for a in pyblock.inputargs]
        self.l_func.dependencies.update(self.l_args)
        self.lblock = llvmbc.BasicBlock("block%i" % l_func.blocknum[pyblock])
        l_func.add_block(self.lblock)
        self.build_bb()

    def build_bb(self):
        self.create_phi_nodes()
        self.create_space_ops()
        self.create_terminator_instr()

    def create_phi_nodes(self):
        pyblock = self.pyblock
        l_incoming_links = []
        def visit(node):
            if isinstance(node, Link) and node.target == pyblock:
                l_incoming_links.append(LinkRepr.get_link(node, self.l_func,
                                                          self.gen))
        traverse(visit, self.l_func.graph)
        if len(l_incoming_links) != 0:
            for i, arg in enumerate(pyblock.inputargs):
                l_arg = self.gen.get_repr(arg)
                l_values = [l_l.l_args[i] for l_l in l_incoming_links]
                self.l_func.dependencies.add(l_arg)
                self.lblock.phi(l_arg, l_values, ["%" + l_l.fromblock
                                                  for l_l in l_incoming_links])

    def create_space_ops(self):
        for opnumber, op in enumerate(self.pyblock.operations):
            self.create_op(opnumber, op)

    def create_op(self, opnumber, op):
        l_target = self.gen.get_repr(op.result)
        l_arg0 = self.gen.get_repr(op.args[0])
        self.l_func.dependencies.update([l_arg0, l_target])
        l_op = getattr(l_arg0, "op_" + op.opname, None)
        if l_op is not None:
            l_op(l_target, op.args, self.lblock, self.l_func)
        #XXX need to find more elegant solution for this special case
        elif op.opname == "newtuple":
            l_target.type.t_op_newtuple(l_target, op.args,
                                        self.lblock, self.l_func)
        elif op.opname in INTRINSIC_OPS:
            l_args = [self.gen.get_repr(arg) for arg in op.args[1:]]
            self.l_func.dependencies.update(l_args)
            self.lblock.spaceop(l_target, op.opname, [l_arg0] + l_args)
        else:
            s = "SpaceOperation %s not supported. Target: %s " \
                "Args: %s " % (op.opname, l_target, op.args) + \
                "Dispatched on: %s" % l_arg0
            raise CompileError, s

    def create_terminator_instr(self):
        if debug:
            print "create_terminator_instr"
        pyblock = self.pyblock
        l_func = self.l_func
        l_link = LinkRepr.get_link(pyblock.exits[0], l_func, self.gen)
        if self.pyblock.exitswitch is None:
            self.lblock.uncond_branch("%" + l_link.toblock)
        else:
            l_switch = self.gen.get_repr(pyblock.exitswitch)
            l_link = LinkRepr.get_link(pyblock.exits[0], l_func, self.gen)
            l_link2 = LinkRepr.get_link(pyblock.exits[1], l_func, self.gen)
            l_func.dependencies.add(l_switch)
            self.lblock.cond_branch(l_switch, "%" + l_link2.toblock,
                                    "%" + l_link.toblock)
        #1 / 0


class ReturnBlockRepr(BlockRepr):
    def create_space_ops(self):
        pass
    
    def create_terminator_instr(self):
        l_returnvalue = self.gen.get_repr(self.pyblock.inputargs[0])
        self.l_func.dependencies.add(l_returnvalue)
        self.lblock.ret(l_returnvalue)


class TryBlockRepr(BlockRepr):
    def __init__(self, l_func, pyblock, gen):
        if debug:
            print "TryBlockRepr"
        self.l_func = l_func
        self.pyblock = pyblock
        self.gen = gen
        self.l_args = [self.gen.get_repr(a) for a in pyblock.inputargs]
        self.l_func.dependencies.update(self.l_args)
        #XXXXXXXXXXX
        regularblock = "DUMMY"
        exceptblock = "block%i.except" % l_func.blocknum[pyblock]
        self.lblock = llvmbc.TryBasicBlock("block%i" % \
                                           l_func.blocknum[pyblock],
                                           regularblock, exceptblock)
        l_func.add_block(self.lblock)
        l_link = LinkRepr.get_link(pyblock.exits[0], l_func, gen)
        self.lblock.regularblock = l_link.toblock
        self.build_bb()
        self.build_exc_block()

    def create_space_ops(self):
        for opnumber, op in enumerate(self.pyblock.operations):
            if opnumber == len(self.pyblock.operations) - 1:
                self.lblock.last_op = True
            self.create_op(opnumber, op)

    def create_terminator_instr(self):
        #The branch has already be created by the last space op
        assert self.lblock.closed

    def build_exc_block(self):
        lexcblock = llvmbc.BasicBlock(self.lblock.label + ".except")
        self.l_func.add_block(lexcblock)
        l_excp = self.gen.get_repr(last_exception)
        l_exc = self.gen.get_local_tmp(PointerTypeRepr("%std.class", self.gen),
                                       self.l_func)
        l_uip = self.gen.get_local_tmp(PointerTypeRepr("uint", self.gen),
                                       self.l_func)
        l_ui = self.gen.get_local_tmp(
            self.gen.get_repr(annmodel.SomeInteger(True, True)), self.l_func)
        self.l_func.dependencies.update([l_excp, l_exc, l_uip, l_ui])
        lexcblock.load(l_exc, l_excp)
        lexcblock.getelementptr(l_uip, l_exc, [0, 1])
        lexcblock.load(l_ui, l_uip)
        l_exits = [LinkRepr.get_link(l, self.l_func, self.gen)
                                     for l in self.pyblock.exits[1:]]
        l_exitcases = [self.gen.get_repr(ex.exitcase)
                       for ex in self.pyblock.exits[1:]]
        self.l_func.dependencies.update(l_exitcases)
        # XXX XXX XXX: For now we assume, that if there is only one exit
        # and it's exitcase is Exception, this should match anything
        if len(l_exits) == 1 and self.pyblock.exits[1].exitcase == Exception:
            lexcblock.uncond_branch("%" + l_exits[0].toblock)
        else:
            sw = [(str(abs(id(ex.exitcase))), "%" + l_l.toblock)
                  for ex, l_l in zip(self.pyblock.exits[1:], l_exits)]
            lexcblock.switch(l_ui, "%" + self.lblock.label + ".unwind", sw)
            lunwindblock = llvmbc.BasicBlock(self.lblock.label + ".unwind")
            lunwindblock.unwind()
            self.l_func.add_block(lunwindblock)

class ExceptBlockRepr(BlockRepr):
    def create_space_ops(self):
        pass

    def create_terminator_instr(self):
        l_exc = self.gen.get_repr(self.pyblock.inputargs[0])
        l_val = self.gen.get_repr(self.pyblock.inputargs[1])
        l_last_exception = self.gen.get_repr(last_exception)
        l_last_exc_value = self.gen.get_repr(last_exc_value)
        self.l_func.dependencies.update([l_exc, l_val, l_last_exception,
                                         l_last_exc_value])
        if "%std.class" != l_exc.llvmtype():
            l_tmp = self.gen.get_local_tmp(
                PointerTypeRepr("%std.class", self.gen), self.l_func)
            self.lblock.cast(l_tmp, l_exc)
            l_exc = l_tmp
        if  "%std.exception" != l_val.llvmtype():
            l_tmp = self.gen.get_local_tmp(
                PointerTypeRepr("%std.exception", self.gen), self.l_func)
            self.lblock.cast(l_tmp, l_val)
            l_val = l_tmp
        self.lblock.store(l_exc, l_last_exception)
        self.lblock.store(l_val, l_last_exc_value)
        self.lblock.unwind()


class LinkRepr(object):
    l_links = {}
    def get_link(link, l_func, gen):
        if (link, gen) not in LinkRepr.l_links:
            LinkRepr.l_links[(link, gen)] = LinkRepr(link, l_func, gen)
        return LinkRepr.l_links[(link, gen)]
    get_link = staticmethod(get_link)
            
    def __init__(self, link, l_func, gen):
        self.link = link
        self.l_func = l_func
        self.gen = gen
        self.l_args = [self.gen.get_repr(a) for a in self.link.args]
        self.l_targetargs = [self.gen.get_repr(a)
                             for a in self.link.target.inputargs]
        self.l_func.dependencies.update(self.l_args)
        self.l_func.dependencies.update(self.l_targetargs)
        assert len(self.l_args) == len(self.l_targetargs)
        self.create_link_block()

    def create_link_block(self):
        #a block is created in which the neccessary cast can be performed
        link = self.link
        l_func = self.l_func
        self.blockname = "bl%i_to_bl%i" % (l_func.blocknum[link.prevblock],
                                           l_func.blocknum[link.target])
        self.lblock = llvmbc.BasicBlock(self.blockname)
        if isinstance(link.prevblock.exitswitch, Constant) and \
           link.prevblock.exitswitch.value == last_exception and \
           len(self.l_args) == 2:
            l_tmp1 = self.gen.get_local_tmp(PointerTypeRepr("%std.class",
                                                            self.gen),
                                            self.l_func)
            l_tmp2 = self.gen.get_local_tmp(PointerTypeRepr("%std.exception",
                                                            self.gen),
                                            self.l_func)
            self.l_func.dependencies.update([l_tmp1, l_tmp2])
            self.lblock.load(l_tmp1, self.l_args[0])
            self.lblock.load(l_tmp2, self.l_args[1])
            self.l_args[0] = l_tmp1
            self.l_args[1] = l_tmp2
        for i, (l_a, l_ta) in enumerate(zip(self.l_args, self.l_targetargs)):
            if l_a.llvmtype() != l_ta.llvmtype():
                l_tmp = self.gen.get_local_tmp(l_ta.type, l_func)
                self.lblock.cast(l_tmp, l_a)
                self.l_args[i] = l_tmp
        self.lblock.uncond_branch("%%block%i" % l_func.blocknum[link.target])
        #try to remove unneded blocks to increase readability
        if len(self.lblock.instructions) == 1:
            prevblock = self.link.prevblock
            self.fromblock = "block%i" % self.l_func.blocknum[prevblock]
            is_tryblock = isinstance(prevblock.exitswitch, Constant) and \
                          prevblock.exitswitch.value == last_exception
            if is_tryblock and self.link.exitcase not in (None, True, False):
                 self.fromblock += ".except"
            self.toblock = "block%i" % self.l_func.blocknum[self.link.target]
        else:
            self.fromblock = self.toblock = self.blockname
            self.l_func.add_block(self.lblock)


class EntryFunctionRepr(LLVMRepr):
    def __init__(self, name, function, gen):
        self.gen = gen
        self.function = function
        self.name = name
        self.dependencies = sets.Set()
        self.branch_added = False

    def setup(self):
        self.l_function = self.gen.get_repr(self.function)
        self.dependencies.add(self.l_function)
        #XXX clean this up
        #create entry block
        lblock = llvmbc.BasicBlock("entry")
        lblock.instruction("%tmp = load bool* %Initialized.0__")
        lblock.instruction("br bool %tmp, label %real_entry, label %init")
        lblock.phi_done = True
        lblock.closed = True
        self.llvm_func = llvmbc.Function(self.llvmfuncdef(), lblock)
        #create init block. The LLVM "module" is initialized there
        self.init_block = llvmbc.BasicBlock("init")
        self.init_block.instruction("store bool true, bool* %Initialized.0__")
        self.llvm_func.basic_block(self.init_block)
        #create the block that calls the "real" function
        real_entry = llvmbc.TryBasicBlock("real_entry", "retblock", "exc")
        l_ret = self.gen.get_local_tmp(self.l_function.retvalue.type,
                                       self)
        real_entry.last_op = True
        self.l_function.op_simple_call(
            l_ret, [self.function] + self.l_function.l_args, real_entry, self)
        self.llvm_func.basic_block(real_entry)
        #create the block that catches remaining unwinds and sets
        #pypy____uncaught_exception to 1
        self.exceptblock = llvmbc.BasicBlock("exc")
        ins = """store int 1, int* %%pypy__uncaught_exception
\t%%dummy_ret = cast int 0 to %s
\tret %s %%dummy_ret""" % tuple([self.l_function.retvalue.llvmtype()] * 2)
        self.exceptblock.instruction(ins)
        self.exceptblock.closed = True
        self.llvm_func.basic_block(self.exceptblock)
        #create the return block
        retblock = llvmbc.BasicBlock("retblock")
        retblock.ret(l_ret)
        self.llvm_func.basic_block(retblock)
        
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
                             (self.cfuncdef()),
                             "cdef extern int pypy__uncaught_exception\n"]
        
        self.pyrex_source.append("def wrap_%s(" % name)
        t = []
        for i, a in enumerate(args):
            t += ["%s" % a]
        t = ", ".join(t)
        s = """
    result = %s(%s)
    global pypy__uncaught_exception
    if pypy__uncaught_exception != 0:
        pypy__uncaught_exception = 0
        raise RuntimeError('An uncaught exception occured in the LLVM code.')
    else:
        return result""" % (name, t)
        self.pyrex_source.append(t + "):\n" + s)
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
                    if debug:
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
