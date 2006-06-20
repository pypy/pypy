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

from pypy.translator.js.log import log

import re

class LoopFinder(object):

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
            #if self.loops.has_key(link.target):
            #    # double loop
            #    pass
            block_switch = self.block_seeing_order[link.target]
            if len(self.block_seeing_order[link.target]) == 1:
                self.loops[(block_switch[0].exitcase,link.target)] = block_switch[0].exitcase
            else:
                self.loops[(block_switch[1].exitcase,link.target)] = block_switch[1].exitcase
            
        if not link.target in self.seen:
            self.parents[link.target] = self.parents[link.prevblock]
            self.visit_Block(link.target, switches)

class Function(Node, Generator):
    def __init__(self, db, graph, name=None, is_method=False, is_entrypoint=False, _class = None):
        self.db = db
        self.cts = db.type_system_class(db)
        self.graph = graph
        self.name = name or self.db.get_uniquename(self.graph, graph.name)
        self.is_method = is_method
        self.is_entrypoint = is_entrypoint
        self.blocknum = {}
        self._class = _class
        self._set_args()
        self._set_locals()
        self.order = 0

    def get_name(self):
        return self.name

    def __hash__(self):
        return hash(self.graph)

    def __eq__(self, other):
        return self.graph == other.graph
    
    def __cmp__(self, other):
        return cmp(self.order, other.order)

    def _is_return_block(self, block):
        return self.graph.returnblock is block
    
    def _is_raise_block(self, block):
        return self.graph.exceptblock is block
        
    def loop_render_block(self, block, stop_blocks = []):
        # FIXME: This code is awfull, some refactoring please
        if block in stop_blocks:
            return
        log("Rendering block %r"%block)
        
        handle_exc = (block.exitswitch == flowmodel.c_last_exception)
        if handle_exc:
            self.ilasm.begin_try()

        for op in block.operations:
            self._render_op(op)
        
        if len(block.exits) == 0:
            # return block
            return_var = block.inputargs[0]
            if return_var.concretetype is not Void:
                self.load(return_var)
                self.ilasm.ret()
        elif block.exitswitch is None:
            # single exit block
            assert(len(block.exits) == 1)
            link = block.exits[0]
            self._setup_link(link)
            self.render_block(link.target, stop_blocks)
        elif block.exitswitch is flowmodel.c_last_exception:
            # we've got exception block
            raise NotImplementedError("Exception handling not implemented")
        else:
            if self.loops.has_key((True,block)) and self.loops.has_key((False,block)):
                # double loop
                #self.ilasm.branch_while
                self.ilasm.branch_while_true()
                self.ilasm.branch_if(block.exitswitch, self.loops[(True,block)])
                self._setup_link(block.exits[True])
                self.render_block(block.exits[True].target, stop_blocks+[block])
                self.ilasm.branch_else()
                self._setup_link(block.exits[False])
                self.render_block(block.exits[False].target, stop_blocks+[block])
                self.ilasm.close_branch()
                for op in block.operations:
                    self._render_op(op)
                self.ilasm.close_branch()
            elif self.loops.has_key((True, block)) or self.loops.has_key((False, block)):
                # we've got loop
                try:
                    loop_case = self.loops[(True, block)]
                except KeyError:
                    loop_case = self.loops[(False, block)]
                self.ilasm.branch_while(block.exitswitch, loop_case)
                exit_case = block.exits[loop_case]
                self._setup_link(exit_case)
                self.render_block(exit_case.target, stop_blocks+[block])
                for op in block.operations:
                    self._render_op(op)
                self.ilasm.close_branch()
                exit_case = block.exits[not loop_case]
                self._setup_link(exit_case)
                #log (  )
                self.render_block(exit_case.target, stop_blocks+[block])
                #raise NotImplementedError ( "loop" )
            else:
                # just a simple if
                assert(len(block.exits) == 2)
                self.ilasm.branch_if(block.exitswitch, True)
                self._setup_link(block.exits[True])
                self.render_block(block.exits[True].target, stop_blocks)
                self.ilasm.branch_else()
                self._setup_link(block.exits[False])
                self.render_block(block.exits[False].target, stop_blocks)
                self.ilasm.close_branch()
    
    def render_block_operations(self, block):
        for op in block.operations:
            self._render_op(op)
    
    def render_block(self, startblock):
        """ Block rendering routine using for variable trick
        """
        def basename(x):
            return str(x).replace('.', '_')#[-1]
        
        self.ilasm.begin_for()
        
        block_map = {}
        blocknum = 0
        
        graph = self.graph
        
        for block in graph.iterblocks():
            block_map[block] = blocknum
            blocknum += 1
        
        for block in graph.iterblocks():
            self.ilasm.write_case(block_map[block])
            
            is_exc_block = (block.exitswitch is flowmodel.c_last_exception)
            
            if is_exc_block:
                self.ilasm.begin_try()
                
            self.render_block_operations(block)
            if self._is_return_block(block):
                return_var = block.inputargs[0]
                #if return_var.concretetype is not Void:
                self.load(return_var)
                self.ilasm.ret()
            elif self._is_raise_block(block):
                self.ilasm.throw(block.inputargs[1])
            elif block.exitswitch is None:
                self._setup_link(block.exits[0])
                self.ilasm.jump_block(block_map[block.exits[0].target])
            elif block.exitswitch is flowmodel.c_last_exception:
                link = [i for i in block.exits if i.exitcase is None][0]
                self._setup_link(link)
                self.ilasm.jump_block(block_map[link.target])
                self.ilasm.catch()
                first = False
                for link in [i for i in block.exits if i.exitcase is not None]:
                    s = "isinstanceof(exc, %s)"%basename(link.exitcase)
                    if not first:
                        first = True
                        self.ilasm.branch_if_string(s)
                    else:
                        self.ilasm.branch_elsif_string(s)
                    self._setup_link(link, True)
                    self.ilasm.jump_block(block_map[link.target])
                self.ilasm.close_branch()
                self.ilasm.close_branch()
            elif len(block.exits) == 2:
                self.ilasm.branch_if(block.exitswitch, True)
                self._setup_link(block.exits[True])
                self.ilasm.jump_block(block_map[block.exits[True].target])
                self.ilasm.branch_else()
                self._setup_link(block.exits[False])
                self.ilasm.jump_block(block_map[block.exits[False].target])
                self.ilasm.close_branch()
            else:
                raise TypeError("Unknow block.exitswitch type %r"%block.exitswitch)
        
        self.ilasm.end_for()
        #self.render_operations(

    def render(self,ilasm):
        if self.db.graph_name(self.graph) is not None and not self.is_method:
            return # already rendered
        
        if self.is_method:
            args = self.args[1:] # self is implicit
        else:
            args = self.args
        
        self.ilasm = ilasm
        
        #self.loops = LoopFinder(self.graph.startblock).loops
        if self.is_method:
            self.ilasm.begin_method(self.name, self._class, [i[1] for i in args])
        else:
            self.ilasm.begin_function(self.name, args)
        #log("loops: %r"%self.loops)

        # render all variables
        
        self.ilasm.set_locals(",".join(self.locals))
        
        self.render_block(self.graph.startblock)

        self.ilasm.end_function()
        if self.is_method:
            pass # TODO
        else:
            self.db.record_function(self.graph, self.name)

    def _setup_link(self, link, is_exc_link = False):
        target = link.target
        for to_load, to_store in zip(link.args, target.inputargs):
            if to_load.concretetype is not Void:
                if is_exc_link and isinstance(to_load, flowmodel.Variable) and re.match("last_exc_value", to_load.name):
                    self.ilasm.load_str("exc")
                else:
                    self.load(to_load)
                self.store(to_store)


    def _set_locals(self):
        # this code is partly borrowed from pypy.translator.c.funcgen.FunctionCodeGenerator
        # TODO: refactoring to avoid code duplication
        # and borrowed again from gencli

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
            if id(v) not in seen and is_var and v.name not in args:
                locals.append(v.name)
                seen[id(v)] = True

        self.locals = locals

    def _set_args(self):
        args = self.graph.getargs()
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
    
    def call_external(self, name, args):
        self.ilasm.call((name, args))

    #def call_signature(self, signature):
    #    self.ilasm.call(signature)

    def cast_to(self, lltype):
        cts_type = self.cts.lltype_to_cts(lltype, False)
        self.ilasm.castclass(cts_type)
        
    def new(self, obj):
        self.ilasm.new(self.cts.obj_name(obj))

    def set_field(self, obj, name):
        self.ilasm.set_field(obj, name)
        #self.ilasm.set_field(self.field_name(obj,name))

    def get_field(self, useless_stuff, name):
        self.ilasm.get_field(name)
        
    def call_method(self, obj, name):
        func_name, signature = self.cts.method_signature(obj, name)
        self.ilasm.call_method(obj, name, signature)
    
    def call_external_method(self, name, arg_len):
        self.ilasm.call_method(None, name, [0]*arg_len)

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
            self.db.load_const(v.concretetype, v.value, self.ilasm)
        else:
            assert False
    
    def store(self, v):
        if isinstance(v, flowmodel.Variable):
            if v.concretetype is not Void:
                self.ilasm.store_local(v)
            else:
                self.ilasm.store_void()
        else:
            assert False
    
    def change_name(self, name, to_name):
        self.ilasm.change_name(name, to_name)
    
    def cast_function(self, name, num):
        self.ilasm.cast_function(name, num)

    def prefix_op(self, st):
        self.ilasm.prefix_op(st)
    
    def load_str(self, s):
        self.ilasm.load_str(s)
    
    def load_void(self):
        self.ilasm.load_void()
    
    def list_setitem(self, base_obj, item, val):
        self.load(base_obj)
        self.load(val)
        self.load(item)
        self.ilasm.list_setitem()
    
    def list_getitem(self, base_obj, item):
        self.load(base_obj)
        self.load(item)
        self.ilasm.list_getitem()
