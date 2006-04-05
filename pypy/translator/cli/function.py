try:
    set
except NameError:
    from sets import Set as set

from pypy.objspace.flow import model as flowmodel
from pypy.rpython.lltypesystem.lltype import Void
from pypy.rpython.ootypesystem.ootype import Instance
from pypy.translator.cli.option import getoption
from pypy.translator.cli import cts
from pypy.translator.cli.opcodes import opcodes
from pypy.translator.cli.metavm import InstructionList, Generator
from pypy.translator.cli.node import Node

from pypy.tool.ansi_print import ansi_log
import py
log = py.log.Producer("cli") 
py.log.setconsumer("cli", ansi_log) 

class Function(Node, Generator):
    def __init__(self, graph, name = None, is_method = False, is_entrypoint = False):
        self.graph = graph
        self.name = name or graph.name
        self.is_method = is_method
        self.is_entrypoint = is_entrypoint
        self.blocknum = {}
        self.classdefs = set()
        self._set_args()
        self._set_locals()

    def get_name(self):
        return self.name

    def _is_return_block(self, block):
        return (not block.exits) and len(block.inputargs) == 1

    def _is_raise_block(self, block):
        return (not block.exits) and len(block.inputargs) == 2        

    def render(self, ilasm):
        self.ilasm = ilasm
        graph = self.graph
        returntype, returnvar = cts.llvar_to_cts(graph.getreturnvar())

        if self.is_method:
            args = self.args[1:] # self is implicit
            meth_type = 'virtual'
        else:
            args = self.args
            meth_type = 'static'

        self.ilasm.begin_function(self.name, args, returntype, self.is_entrypoint, meth_type)
        self.ilasm.locals(self.locals)

        return_blocks = []
        for block in graph.iterblocks():
            if self._is_return_block(block):
                return_blocks.append(block)
                continue

            self.ilasm.label(self._get_block_name(block))

            handle_exc = (block.exitswitch == flowmodel.c_last_exception)
            if handle_exc:
                self.ilasm.begin_try()

            for op in block.operations:
                self._search_for_classes(op)
                self._render_op(op)

            if self._is_raise_block(block):
                exc = block.inputargs[1]
                self.load(exc)
                self.ilasm.opcode('throw')

            if handle_exc:
                # search for the "default" block to be executed when no exception is raised
                for link in block.exits:
                    if link.exitcase is None:
                        self._setup_link(link)
                        target_label = self._get_block_name(link.target)
                        self.ilasm.leave(target_label)
                self.ilasm.end_try()

                # catch the exception and dispatch to the appropriate block
                for link in block.exits:
                    if link.exitcase is None:
                        continue # see above

                    assert issubclass(link.exitcase, Exception)
                    cts_exc = cts.pyexception_to_cts(link.exitcase)
                    self.ilasm.begin_catch(cts_exc)

                    target = link.target
                    if self._is_raise_block(target):
                        # the exception value is on the stack, use it as the 2nd target arg
                        assert len(link.args) == 2
                        assert len(target.inputargs) == 2
                        self.store(link.target.inputargs[1])
                    else:
                        # pop the unused exception value
                        self.ilasm.opcode('pop')
                        self._setup_link(link)
                    
                    target_label = self._get_block_name(target)
                    self.ilasm.leave(target_label)
                    self.ilasm.end_catch()

            else:
                # no exception handling, follow block links
                for link in block.exits:
                    self._setup_link(link)
                    target_label = self._get_block_name(link.target)
                    if link.exitcase is None:
                        self.ilasm.branch(target_label)
                    else:
                        assert type(link.exitcase is bool)
                        assert block.exitswitch is not None
                        self.load(block.exitswitch)
                        self.ilasm.branch_if(link.exitcase, target_label)

        # render return blocks at the end just to please the .NET
        # runtime that seems to need a return statement at the end of
        # the function
        for block in return_blocks:
            self.ilasm.label(self._get_block_name(block))
            return_var = block.inputargs[0]
            if return_var.concretetype is not Void:
                self.load(return_var)
            self.ilasm.opcode('ret')

        self.ilasm.end_function()

    def _setup_link(self, link):
        target = link.target
        for to_load, to_store in zip(link.args, target.inputargs):
            if to_load.concretetype is not Void:
                self.load(to_load)
                self.store(to_store)


    def _set_locals(self):
        # this code is partly borrowed from pypy.translator.c.funcgen.FunctionCodeGenerator
        # TODO: refactoring to avoid code duplication

        graph = self.graph
        mix = [graph.getreturnvar()]
        for block in graph.iterblocks():
            self.blocknum[block] = len(self.blocknum)
            mix.extend(block.inputargs)

            for op in block.operations:
                mix.extend(op.args)
                mix.append(op.result)
                if getattr(op, "cleanup", None) is not None:
                    cleanup_finally, cleanup_except = op.cleanup
                    for cleanupop in cleanup_finally + cleanup_except:
                        mix.extend(cleanupop.args)
                        mix.append(cleanupop.result)
            for link in block.exits:
                mix.extend(link.getextravars())
                mix.extend(link.args)

        # filter only locals variables, i.e.:
        #  - must be variables
        #  - must appear only once
        #  - must not be function parameters
        #  - must not have 'void' type

        args = {}
        for ctstype, name in self.args:
            args[name] = True
        
        locals = []
        seen = {}
        for v in mix:
            is_var = isinstance(v, flowmodel.Variable)
            if id(v) not in seen and is_var and v.name not in args and v.concretetype is not Void:
                locals.append(cts.llvar_to_cts(v))
                seen[id(v)] = True

        self.locals = locals

    def _set_args(self):
        self.args = map(cts.llvar_to_cts, self.graph.getargs())
        self.argset = set([argname for argtype, argname in self.args])

    def _get_block_name(self, block):
        return 'block%s' % self.blocknum[block]

    def _search_for_classes(self, op):
        for arg in op.args:
            lltype = None
            if isinstance(arg, flowmodel.Variable):
                lltype = arg.concretetype
            elif isinstance(arg, flowmodel.Constant):
                lltype = arg.value

            if isinstance(lltype, Instance):
                self.classdefs.add(lltype)


    def _render_op(self, op):
        instr_list = opcodes.get(op.opname, None)
        if instr_list is not None:
            assert isinstance(instr_list, InstructionList)
            instr_list.render(self, op)
        else:
            if getoption('nostop'):
                log.WARNING('Unknown opcode: %s ' % op)
                self.ilasm.opcode(str(op))
            else:
                assert False, 'Unknown opcode: %s ' % op

    def field_name(self, obj, field):
        class_name = self.class_name(obj)
        field_type = cts.lltype_to_cts(obj._field_type(field))
        return '%s %s::%s' % (field_type, class_name, field)

    def ctor_name(self, ooinstance):
        return 'instance void class %s::.ctor()' % self.class_name(ooinstance)

    # following methods belongs to the Generator interface

    def function_signature(self, graph):
        return cts.graph_to_signature(graph, False)

    def method_signature(self, graph, name):
        return cts.graph_to_signature(graph, True, name)

    def class_name(self, ooinstance):
        return ooinstance._name.replace('__main__.', '') # TODO: modules

    def emit(self, instr, *args):
        self.ilasm.opcode(instr, *args)

    def call(self, func_name):
        self.ilasm.call(func_name)

    def new(self, obj):
        self.ilasm.new(self.ctor_name(obj))

    def set_field(self, obj, name):
        self.ilasm.opcode('stfld ' + self.field_name(obj, name))

    def get_field(self, obj, name):
        self.ilasm.opcode('ldfld ' + self.field_name(obj, name))

    def call_method(self, obj, name):
        owner, meth = obj._lookup(name)
        full_name = '%s::%s' % (self.class_name(obj), name)
        self.ilasm.call_method(self.method_signature(meth.graph, full_name))

    def load(self, v):
        if isinstance(v, flowmodel.Variable):
            if v.name in self.argset:
                selftype, selfname = self.args[0]
                if self.is_method and v.name == selfname:
                    self.ilasm.opcode('ldarg.0') # special case for 'self'
                else:
                    self.ilasm.opcode('ldarg', repr(v.name))
            else:
                self.ilasm.opcode('ldloc', repr(v.name))

        elif isinstance(v, flowmodel.Constant):
            iltype, ilvalue = cts.llconst_to_ilasm(v)
            self.ilasm.opcode('ldc.' + iltype, ilvalue)
        else:
            assert False

    def store(self, v):
        if isinstance(v, flowmodel.Variable):
            if v.concretetype is not Void:
                self.ilasm.opcode('stloc', repr(v.name))
        else:
            assert False
