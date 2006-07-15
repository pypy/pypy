try:
    set
except NameError:
    from sets import Set as set

from pypy.objspace.flow import model as flowmodel
from pypy.rpython.lltypesystem.lltype import Signed, Unsigned, Void, Bool, Float
from pypy.rpython.lltypesystem.lltype import SignedLongLong, UnsignedLongLong
from pypy.rpython.ootypesystem import ootype
from pypy.translator.cli.option import getoption
from pypy.translator.cli.cts import CTS
from pypy.translator.cli.opcodes import opcodes
from pypy.translator.cli.metavm import InstructionList, Generator
from pypy.translator.cli.node import Node
from pypy.translator.cli.class_ import Class

from pypy.tool.ansi_print import ansi_log
import py
log = py.log.Producer("cli") 
py.log.setconsumer("cli", ansi_log) 

class Function(Node, Generator):
    def __init__(self, db, graph, name = None, is_method = False, is_entrypoint = False):
        self.db = db
        self.cts = CTS(db)
        self.graph = graph
        self.name = self.cts.escape_name(name or graph.name)
        self.is_method = is_method
        self.is_entrypoint = is_entrypoint
        self.blocknum = {}
        self._set_args()
        self._set_locals()

    def get_name(self):
        return self.name

    def __repr__(self):
        return '<Function %s>' % self.name

    def __hash__(self):
        return hash(self.graph)

    def __eq__(self, other):
        return self.graph == other.graph

    def __ne__(self, other):
        return not self == other

    def _is_return_block(self, block):
        return (not block.exits) and len(block.inputargs) == 1

    def _is_raise_block(self, block):
        return (not block.exits) and len(block.inputargs) == 2        

    def render(self, ilasm):
        if self.db.graph_name(self.graph) is not None and not self.is_method:
            return # already rendered

        if getattr(self.graph.func, 'suggested_primitive', False):
            assert False, 'Cannot render a suggested_primitive'

        self.ilasm = ilasm
        graph = self.graph
        returntype, returnvar = self.cts.llvar_to_cts(graph.getreturnvar())

        if self.is_method:
            args = self.args[1:] # self is implicit
            meth_type = 'virtual' # TODO: mark as virtual only when strictly necessary
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
                #self._search_for_classes(op)
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
                    #cts_exc = self.cts.pyexception_to_cts(link.exitcase)
                    #cts_exc = str(link.exitcase) # TODO: is it a bit hackish?
                    ll_meta_exc = link.llexitcase
                    self.db.record_const(ll_meta_exc)
                    ll_exc = ll_meta_exc._inst.class_._INSTANCE
                    cts_exc = self.cts.lltype_to_cts(ll_exc, False)
                    self.ilasm.begin_catch(cts_exc)

                    target = link.target
                    if self._is_raise_block(target):
                        # the exception value is on the stack, use it as the 2nd target arg
                        assert len(link.args) == 2
                        assert len(target.inputargs) == 2
                        self.store(link.target.inputargs[1])
                    else:
                        # the exception value is on the stack, store it in the proper place
                        self.store(link.last_exc_value)
                        self._setup_link(link)
                    
                    target_label = self._get_block_name(target)
                    self.ilasm.leave(target_label)
                    self.ilasm.end_catch()

            else:
                # no exception handling, follow block links
                for link in block.exits:
                    self._setup_link(link)
                    target_label = self._get_block_name(link.target)
                    if link.exitcase is None or link is block.exits[-1]:
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
        if self.is_method:
            pass # TODO
        else:
            self.db.record_function(self.graph, self.name)

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
                locals.append(self.cts.llvar_to_cts(v))
                seen[id(v)] = True

        self.locals = locals

    def _set_args(self):
        args = [arg for arg in self.graph.getargs() if arg.concretetype is not Void]
        self.args = map(self.cts.llvar_to_cts, args)
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

            if isinstance(lltype, ootype._view) and isinstance(lltype._inst, ootype._instance):
                lltype = lltype._inst._TYPE

            if isinstance(lltype, ootype.Instance):
                self.db.pending_class(lltype)

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
        class_, type_ = obj._lookup_field(field)
        assert type_ is not None, 'Cannot find the field %s in the object %s' % (field, obj)
        
        class_name = self.class_name(class_)
        field_type = self.cts.lltype_to_cts(type_)
        field = self.cts.escape_name(field)
        return '%s %s::%s' % (field_type, class_name, field)

    # following methods belongs to the Generator interface

    def function_signature(self, graph, func_name=None):
        return self.cts.graph_to_signature(graph, False, func_name)

    def class_name(self, TYPE):
        if isinstance(TYPE, ootype.Instance):
            return TYPE._name
        elif isinstance(TYPE, ootype.Record):
            return self.db.get_record_name(TYPE)

    def emit(self, instr, *args):
        self.ilasm.opcode(instr, *args)

    def call_graph(self, graph, func_name=None):
        if func_name is None: # else it is a suggested primitive
            self.db.pending_function(graph)
        func_sig = self.function_signature(graph, func_name)
        self.ilasm.call(func_sig)

    def call_signature(self, signature):
        self.ilasm.call(signature)

    def cast_to(self, lltype):
        cts_type = self.cts.lltype_to_cts(lltype, False)
        self.ilasm.opcode('castclass', cts_type)

    def new(self, obj):
        self.ilasm.new(self.cts.ctor_name(obj))

    def set_field(self, obj, name):
        self.ilasm.opcode('stfld ' + self.field_name(obj, name))

    def get_field(self, obj, name):
        self.ilasm.opcode('ldfld ' + self.field_name(obj, name))

    def call_method(self, obj, name):
        # TODO: use callvirt only when strictly necessary
        signature, virtual = self.cts.method_signature(obj, name)
        self.ilasm.call_method(signature, virtual)

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
            self._load_const(v)
        else:
            assert False

    def _load_const(self, const):
        from pypy.translator.cli.database import AbstractConst
        AbstractConst.load(self.db, const.concretetype, const.value, self.ilasm)

    def store(self, v):
        if isinstance(v, flowmodel.Variable):
            if v.concretetype is not Void:
                self.ilasm.opcode('stloc', repr(v.name))
        else:
            assert False

    def isinstance(self, class_name):
        self.ilasm.opcode('isinst', class_name)
