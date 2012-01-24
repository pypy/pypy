from pypy.objspace.flow.model import SpaceOperation, Constant, Variable
from pypy.objspace.flow.model import Block, Link, checkgraph
from pypy.annotation import model as annmodel
from pypy.translator.stm import _rffi_stm
from pypy.translator.unsimplify import varoftype, copyvar
from pypy.rpython.lltypesystem import lltype, lloperation


ALWAYS_ALLOW_OPERATIONS = set([
    'direct_call', 'force_cast', 'keepalive', 'cast_ptr_to_adr',
    'debug_print', 'debug_assert', 'cast_opaque_ptr', 'hint',
    'indirect_call', 'stack_current',
    ])
ALWAYS_ALLOW_OPERATIONS |= set(lloperation.enum_tryfold_ops())

def op_in_set(opname, set):
    return opname in set

# ____________________________________________________________


class STMTransformer(object):

    def __init__(self, translator=None):
        self.translator = translator

    def transform(self):  ##, entrypointptr):
        assert not hasattr(self.translator, 'stm_transformation_applied')
##        entrypointgraph = entrypointptr._obj.graph
        for graph in self.translator.graphs:
##            self.seen_transaction_boundary = False
##            self.seen_gc_stack_bottom = False
            self.transform_graph(graph)
##            if self.seen_transaction_boundary:
##                self.add_stm_declare_variable(graph)
##            if self.seen_gc_stack_bottom:
##                self.add_descriptor_init_stuff(graph)
##        self.add_descriptor_init_stuff(entrypointgraph, main=True)
        self.translator.stm_transformation_applied = True

    def transform_block(self, block):
        if block.operations == ():
            return
        newoperations = []
        self.current_block = block
        self.array_of_stm_access_directly = set()
        for i, op in enumerate(block.operations):
            self.current_op_index = i
            try:
                meth = getattr(self, 'stt_' + op.opname)
            except AttributeError:
                if (op_in_set(op.opname, ALWAYS_ALLOW_OPERATIONS) or
                        op.opname.startswith('stm_')):
                    meth = list.append
                else:
                    meth = turn_inevitable_and_proceed
                setattr(self.__class__, 'stt_' + op.opname,
                        staticmethod(meth))
            res = meth(newoperations, op)
            if res is True:
                newoperations.append(op)
            elif res is False:
                turn_inevitable_and_proceed(newoperations, op)
            else:
                assert res is None
        block.operations = newoperations
        self.current_block = None
        self.array_of_stm_access_directly = None

    def transform_graph(self, graph):
        for block in graph.iterblocks():
            self.transform_block(block)

##    def add_descriptor_init_stuff(self, graph, main=False):
##        if main:
##            self._add_calls_around(graph,
##                                   _rffi_stm.begin_inevitable_transaction,
##                                   _rffi_stm.commit_transaction)
##        self._add_calls_around(graph,
##                               _rffi_stm.descriptor_init,
##                               _rffi_stm.descriptor_done)

##    def _add_calls_around(self, graph, f_init, f_done):
##        c_init = Constant(f_init, lltype.typeOf(f_init))
##        c_done = Constant(f_done, lltype.typeOf(f_done))
##        #
##        block = graph.startblock
##        v = varoftype(lltype.Void)
##        op = SpaceOperation('direct_call', [c_init], v)
##        block.operations.insert(0, op)
##        #
##        v = copyvar(self.translator.annotator, graph.getreturnvar())
##        extrablock = Block([v])
##        v_none = varoftype(lltype.Void)
##        newop = SpaceOperation('direct_call', [c_done], v_none)
##        extrablock.operations = [newop]
##        extrablock.closeblock(Link([v], graph.returnblock))
##        for block in graph.iterblocks():
##            if block is not extrablock:
##                for link in block.exits:
##                    if link.target is graph.returnblock:
##                        link.target = extrablock
##        checkgraph(graph)

##    def add_stm_declare_variable(self, graph):
##        block = graph.startblock
##        v = varoftype(lltype.Void)
##        op = SpaceOperation('stm_declare_variable', [], v)
##        block.operations.insert(0, op)

    # ----------

    def stt_getfield(self, newoperations, op):
        STRUCT = op.args[0].concretetype.TO
        if op.result.concretetype is lltype.Void:
            op1 = op
        elif STRUCT._immutable_field(op.args[1].value):
            op1 = op
        elif 'stm_access_directly' in STRUCT._hints:
            self.array_of_stm_access_directly.add(op.result)
            op1 = op
        elif STRUCT._gckind == 'raw':
            turn_inevitable(newoperations, "getfield-raw")
            op1 = op
        else:
            op1 = SpaceOperation('stm_getfield', op.args, op.result)
        newoperations.append(op1)

    def stt_setfield(self, newoperations, op):
        STRUCT = op.args[0].concretetype.TO
        if op.args[2].concretetype is lltype.Void:
            op1 = op
        elif (STRUCT._immutable_field(op.args[1].value) or
              'stm_access_directly' in STRUCT._hints):
            op1 = op
        elif STRUCT._gckind == 'raw':
            turn_inevitable(newoperations, "setfield-raw")
            op1 = op
        else:
            op1 = SpaceOperation('stm_setfield', op.args, op.result)
        newoperations.append(op1)

    def stt_getarrayitem(self, newoperations, op):
        ARRAY = op.args[0].concretetype.TO
        if op.result.concretetype is lltype.Void:
            op1 = op
        elif ARRAY._immutable_field():
            op1 = op
        elif op.args[0] in self.array_of_stm_access_directly:
            op1 = op
        elif ARRAY._gckind == 'raw':
            turn_inevitable(newoperations, "getarrayitem-raw")
            op1 = op
        else:
            op1 = SpaceOperation('stm_getarrayitem', op.args, op.result)
        newoperations.append(op1)

    def stt_setarrayitem(self, newoperations, op):
        ARRAY = op.args[0].concretetype.TO
        if op.args[2].concretetype is lltype.Void:
            op1 = op
        elif ARRAY._immutable_field():
            op1 = op
        elif op.args[0] in self.array_of_stm_access_directly:
            op1 = op
        elif ARRAY._gckind == 'raw':
            turn_inevitable(newoperations, "setarrayitem-raw")
            op1 = op
        else:
            op1 = SpaceOperation('stm_setarrayitem', op.args, op.result)
        newoperations.append(op1)

    def stt_getinteriorfield(self, newoperations, op):
        OUTER = op.args[0].concretetype.TO
        if op.result.concretetype is lltype.Void:
            op1 = op
        elif OUTER._immutable_interiorfield(unwraplist(op.args[1:])):
            op1 = op
        elif OUTER._gckind == 'raw':
            turn_inevitable(newoperations, "getinteriorfield-raw")
            op1 = op
        else:
            op1 = SpaceOperation('stm_getinteriorfield', op.args, op.result)
        newoperations.append(op1)

    def stt_setinteriorfield(self, newoperations, op):
        OUTER = op.args[0].concretetype.TO
        if op.args[-1].concretetype is lltype.Void:
            op1 = op
        elif OUTER._immutable_interiorfield(unwraplist(op.args[1:-1])):
            op1 = op
        elif OUTER._gckind == 'raw':
            turn_inevitable(newoperations, "setinteriorfield-raw")
            op1 = op
        else:
            op1 = SpaceOperation('stm_setinteriorfield', op.args, op.result)
        newoperations.append(op1)

##    def stt_stm_transaction_boundary(self, newoperations, op):
##        self.seen_transaction_boundary = True
##        v_result = op.result
##        # record in op.args the list of variables that are alive across
##        # this call
##        block = self.current_block
##        vars = set()
##        for op in block.operations[:self.current_op_index:-1]:
##            vars.discard(op.result)
##            vars.update(op.args)
##        for link in block.exits:
##            vars.update(link.args)
##            vars.update(link.getextravars())
##        livevars = [v for v in vars if isinstance(v, Variable)]
##        newop = SpaceOperation('stm_transaction_boundary', livevars, v_result)
##        newoperations.append(newop)

    def stt_malloc(self, newoperations, op):
        flags = op.args[1].value
        return flags['flavor'] == 'gc'

    def stt_malloc_varsize(self, newoperations, op):
        flags = op.args[1].value
        return flags['flavor'] == 'gc'

    stt_malloc_nonmovable = stt_malloc

    def stt_gc_stack_bottom(self, newoperations, op):
##        self.seen_gc_stack_bottom = True
        newoperations.append(op)

    def stt_same_as(self, newoperations, op):
        if op.args[0] in self.array_of_stm_access_directly:
            self.array_of_stm_access_directly.add(op.result)
        newoperations.append(op)

    stt_cast_pointer = stt_same_as


def transform_graph(graph):
    # for tests: only transforms one graph
    STMTransformer().transform_graph(graph)


def turn_inevitable(newoperations, info):
    c_info = Constant(info, lltype.Void)
    op1 = SpaceOperation('stm_become_inevitable', [c_info],
                         varoftype(lltype.Void))
    newoperations.append(op1)

def turn_inevitable_and_proceed(newoperations, op):
    turn_inevitable(newoperations, op.opname)
    newoperations.append(op)

def unwraplist(list_v):
    for v in list_v:
        if isinstance(v, Constant):
            yield v.value
        elif isinstance(v, Variable):
            yield None    # unknown
        else:
            raise AssertionError(v)
