
from pypy.objspace.flow import model as flowmodel
from pypy.rpython.lltypesystem.lltype import Signed, Unsigned, Void, Bool, Float
from pypy.rpython.lltypesystem.lltype import SignedLongLong, UnsignedLongLong
from pypy.rpython.ootypesystem import ootype
from pypy.translator.oosupport.metavm import Generator,InstructionList
from pypy.translator.oosupport import function

from pypy.translator.js.log import log
from types import FunctionType

import re

class BaseGenerator(object):
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
        elif isinstance(v, str):
            self.ilasm.load_const("'" + v + "'")
        else:
            assert False

    def store(self, v):
        assert isinstance(v, flowmodel.Variable)
        if v.concretetype is not Void:
            self.ilasm.store_local(v)
        else:
            self.ilasm.store_void()
    
    def change_name(self, name, to_name):
        self.ilasm.change_name(name, to_name)

    def add_comment(self, text):
        pass
    
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

    def oonewarray(self, obj, length):
        self.ilasm.oonewarray(self.cts.obj_name(obj), length)

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
        
    def instantiate(self):
        self.ilasm.runtimenew()
    
    def downcast(self, TYPE):
        pass
        
    def load_special(self, v):
        # special case for loading value
        # when setting builtin field we need to load function instead of None
        # FIXME: we cheat here
        if isinstance(v, flowmodel.Constant) and v.concretetype is ootype.Void and isinstance(v.value, FunctionType):
            graph = self.db.translator.annotator.bookkeeper.getdesc(v.value).cachedgraph(None)
            self.db.pending_function(graph)
            name = graph.name
            self.ilasm.load_str(name)
        else:
            self.load(v)
            
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

    def push_primitive_constant(self, TYPE, value):
        self.db.load_const(TYPE, value, self.ilasm)        

    def branch_unconditionally(self, target_label):
        self.ilasm.jump_block(self.block_map[target_label])

    def branch_conditionally(self, exitcase, target_label):
        self.ilasm.branch_if(exitcase)
        self.ilasm.jump_block(self.block_map[target_label])
        self.ilasm.close_branch()

class Function(function.Function, BaseGenerator):
    def __init__(self, db, graph, name=None, is_method=False,
                 is_entrypoint=False, _class=None):
        self._class = _class
        super(Function, self).__init__(db, graph, name, is_method, is_entrypoint)
        self._set_args()
        self._set_locals()
        self.order = 0
        self.name = name or self.db.get_uniquename(self.graph, self.graph.name)

    def _setup_link(self, link, is_exc_link = False):
        target = link.target
        for to_load, to_store in zip(link.args, target.inputargs):
            if to_load.concretetype is not Void:
                if is_exc_link and isinstance(to_load, flowmodel.Variable) and re.match("last_exc_value", to_load.name):
                    self.ilasm.load_str("exc")
                else:
                    self.load(to_load)
                self.store(to_store)

    def _create_generator(self, ilasm):
        return self

    def begin_render(self):
        block_map = {}
        for blocknum, block in enumerate(self.graph.iterblocks()):
            block_map[self._get_block_name(block)] = blocknum
        self.block_map = block_map

        if self.is_method:
            args = self.args[1:] # self is implicit
        else:
            args = self.args
        if self.is_method:
            self.ilasm.begin_method(self.name, self._class, [i[1] for i in args])
        else:
            self.ilasm.begin_function(self.name, args)
        self.ilasm.set_locals(",".join([i[1] for i in self.locals]))
        self.ilasm.begin_for()

    def render_return_block(self, block):
        return_var = block.inputargs[0]
        if return_var.concretetype is not Void:
            self.load(return_var)
            self.ilasm.ret()
        else:
            self.ilasm.load_void()
            self.ilasm.ret()

    def end_render(self):
        self.ilasm.end_for()        
        self.ilasm.end_function()

    def render_raise_block(self, block):
        self.ilasm.throw(block.inputargs[1])

    def end_try(self, target_label, cond):
        self.ilasm.jump_block(self.block_map[target_label])
        if cond:
            self.ilasm.catch()
        #self.ilasm.close_branch()

    # XXX: soon or later we should use the smarter version in oosupport
    def render_bool_switch(self, block):
        for link in block.exits:
            self._setup_link(link)
            target_label = self._get_block_name(link.target)
            if link is block.exits[-1]:
                self.generator.branch_unconditionally(target_label)
            else:
                assert type(link.exitcase) is bool
                assert block.exitswitch is not None
                self.generator.load(block.exitswitch)
                self.generator.branch_conditionally(link.exitcase, target_label)

    def record_ll_meta_exc(self, ll_meta_exc):
        pass

    def begin_catch(self, llexitcase):
        real_name = self.cts.lltype_to_cts(llexitcase._INSTANCE)
        s = "isinstanceof(exc, %s)"%real_name
        self.ilasm.branch_if_string(s)
    
    def end_catch(self, target_label):
        """ Ends the catch block, and branchs to the given target_label as the
        last item in the catch block """
        self.ilasm.close_branch()

    def store_exception_and_link(self, link):
        self._setup_link(link, True)
        self.ilasm.jump_block(self.block_map[self._get_block_name(link.target)])

    def after_except_block(self):
        #self.ilasm.close_branch()
        self.ilasm.throw_real("exc")
        self.ilasm.close_branch()

    def set_label(self, label):
        self.ilasm.write_case(self.block_map[label])
        #self.ilasm.label(label)

    def begin_try(self, cond):
        if cond:
            self.ilasm.begin_try()

    def clean_stack(self):
        self.ilasm.clean_stack()
