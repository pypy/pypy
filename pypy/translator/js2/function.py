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
from pypy.translator.cli.metavm import Generator,InstructionList
from pypy.translator.cli.node import Node
from pypy.translator.cli.class_ import Class

from pypy.tool.ansi_print import ansi_log
import py
log = py.log.Producer("cli") 
py.log.setconsumer("cli", ansi_log) 

class LoopFinder:

    def __init__(self, startblock):
        self.loops = {}
        self.parents = {startblock: startblock}
        self.temps = {}
        self.seen = set ()
        self.block_seeing_order = {}
        self.visit_Block(startblock)
   
    def visit_Block(self, block, switches=[]):
        #self.temps.has_key()
        self.seen.add(block)
        self.block_seeing_order[block] = []
        if block.exitswitch:
            switches.append(block)
            self.parents[block] = block
        for link in block.exits:
            self.block_seeing_order[block].append(link)
            self.visit_Link(link, switches) 

    def visit_Link(self, link, switches):
        if link.target in switches:
            if len(self.block_seeing_order[link.target]) == 1:
                self.loops[link.target] = self.block_seeing_order[link.target][0].exitcase
            else:
                self.loops[link.target] = self.block_seeing_order[link.target][1].exitcase
            
        if not link.target in self.seen:
            self.parents[link.target] = self.parents[link.prevblock]
            self.visit_Block(link.target, switches)

class Function(Node, Generator):
    def __init__(self, db, graph, name = None, is_method = False, is_entrypoint = False ):
        self.db = db
        self.cts = db.type_system_class(db)
        self.graph = graph
        self.name = name or graph.name
        self.is_method = is_method
        self.is_entrypoint = is_entrypoint
        self.blocknum = {}
        self._set_args()
        self._set_locals()

    def get_name(self):
        return self.name

    def __hash__(self):
        return hash(self.graph)

    def __eq__(self, other):
        return self.graph == other.graph

    def _is_return_block(self, block):
        return (not block.exits) and len(block.inputargs) == 1

    def _is_raise_block(self, block):
        return (not block.exits) and len(block.inputargs) == 2        

    def render_block ( self , block ):
        for op in block.operations:
            self._render_op(op)
    
    def render_block(self, block, stop_block = None):
        if block is stop_block:
            return
        
        for op in block.operations:
            self._render_op(op)
        
        if len(block.exits) == 0:
            # return block
            return_var = block.inputargs[0]
            self.load(return_var)
            self.ilasm.ret()
        elif block.exitswitch is None:
            # single exit block
            assert(len(block.exits) == 1)
            link = block.exits[0]
            self._setup_link(link)
            self.render_block(link.target, stop_block)
        elif block.exitswitch is flowmodel.c_last_exception:
            raise NotImplementedError("Exception handling")
        else:
            if self.loops.has_key(block):
                # we've got loop
                self.ilasm.branch_while(block.exitswitch, self.loops[block])
                exit_case = block.exits[self.loops[block]]
                self._setup_link(exit_case)
                self.render_block(exit_case.target, block)
                for op in block.operations:
                    self._render_op(op)
                self.ilasm.close_branch()
                exit_case = block.exits[not self.loops[block]]
                self._setup_link(exit_case)
                #log (  )
                self.render_block(exit_case.target,block)
                #raise NotImplementedError ( "loop" )
            else:
                # just a simple if
                assert(len(block.exits) == 2)
                self.ilasm.branch_if(block.exitswitch, True)
                self._setup_link(block.exits[True])
                self.render_block(block.exits[True].target, stop_block)
                self.ilasm.branch_else()
                self._setup_link(block.exits[False])
                self.render_block(block.exits[False].target, stop_block)
                self.ilasm.close_branch()

    def render(self,ilasm):
        if self.db.graph_name(self.graph) is not None and not self.is_method:
            return # already rendered
        
        self.ilasm = ilasm
        
        self.loops = LoopFinder(self.graph.startblock).loops
        self.ilasm.begin_function(self.name, self.args, None, None, None)

        self.render_block(self.graph.startblock)
##            if self._is_return_block(block):
##                return_blocks.append(block)
##                continue
##            
##            for op in block.operations:
##                self._render_op(op)
##            
##            for link in block.exits:
##                target_label = self._get_block_name(link.target)
##                if link.exitcase is None:
##                    pass
##                    self.ilasm.branch(target_label)
##                else:
##                    assert type(link.exitcase is bool)
##                    assert block.exitswitch is not None
##                    self.ilasm.branch_if( block.exitswitch, link.exitcase, target_label)
##                self._setup_link(link)

##        for block in return_blocks:
##            return_var = block.inputargs[0]
##            if return_var.concretetype is not Void:
##                self.load(return_var)
##            self.ilasm.ret()

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
        # FIXME: what to do here?
        instr_list = self.db.opcode_dict.get(op.opname, None)
        if instr_list is not None:
            #assert isinstance(instr_list, InstructionList)
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
        return (field_type, class_name, field)

    # following methods belongs to the Generator interface

    def function_signature(self, graph):
        return self.cts.graph_to_signature(graph, False)

    def class_name(self, ooinstance):
        return ooinstance._name

    def emit(self, instr, *args):
        self.ilasm.emit(instr, *args)

    def call_graph(self, graph):
        self.db.pending_function(graph)
        func_sig = self.function_signature(graph)        
        self.ilasm.call(func_sig)

    def call_signature(self, signature):
        self.ilasm.call(signature)

    def cast_to(self, lltype):
        cts_type = self.cts.lltype_to_cts(lltype, False)
        self.ilasm.castclass(cts_type)
        
    def new(self, obj):
        self.ilasm.new(self.cts.ctor_name(obj))

    def set_field(self, obj, name):
        self.ilasm.set_field(self.field_name(obj,name))

    def get_field(self, obj, name):
        self.ilasm.get_field(self.field_name(obj,name))
        
    def call_method(self, obj, name):
        # TODO: use callvirt only when strictly necessary
        signature, virtual = self.cts.method_signature(obj, name)
        self.ilasm.call_method(signature, virtual)

    def load(self, v):
        if isinstance(v, flowmodel.Variable):
            if v.name in self.argset:
                selftype, selfname = self.args[0]
                if self.is_method and v.name == selfname:
                    self.ilasm.load_self()
                else:
                    self.ilasm.load_arg(v)
            else:
                self.ilasm.load_local(v)

        elif isinstance(v, flowmodel.Constant):
            self._load_const(v)
        else:
            assert False

    def _load_const(self, const):        
        type_ = const.concretetype
        if type_ in [ Void , Bool , Float , Signed , Unsigned , SignedLongLong , UnsignedLongLong ]:
            self.ilasm.load_const(type_,const.value)
        else:
            name = self.db.record_const(const.value)
            cts_type = self.cts.lltype_to_cts(type_)
            self.ilasm.load_set_field(cts_type,name)
            #assert False, 'Unknown constant %s' % const

    def store(self, v):
        if isinstance(v, flowmodel.Variable):
            if v.concretetype is not Void:
                self.ilasm.store_local(v)
        else:
            assert False
    
    def change_name(self, name, to_name):
        self.ilasm.change_name(name, to_name)
    
    def cast_floor(self):
        self.ilasm.cast_floor()

