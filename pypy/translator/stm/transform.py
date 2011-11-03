from pypy.objspace.flow.model import SpaceOperation, Constant
from pypy.objspace.flow.model import Block, Link, checkgraph
from pypy.annotation import model as annmodel
from pypy.translator.stm import _rffi_stm
from pypy.translator.unsimplify import varoftype, copyvar
from pypy.rpython.lltypesystem import lltype, lloperation


ALWAYS_ALLOW_OPERATIONS = set([
    'direct_call',
    'debug_print', 'debug_assert',
    ])
ALWAYS_ALLOW_OPERATIONS |= set(lloperation.enum_foldable_ops())

def op_in_set(opname, set):
    return opname in set

# ____________________________________________________________


class STMTransformer(object):

    def __init__(self, translator=None):
        self.translator = translator

    def transform(self, entrypointptr):
        assert not hasattr(self.translator, 'stm_transformation_applied')
        entrypointgraph = entrypointptr._obj.graph
        for graph in self.translator.graphs:
            self.seen_transaction_boundary = False
            self.seen_gc_stack_bottom = False
            self.transform_graph(graph)
            if self.seen_transaction_boundary:
                self.add_stm_declare_variable(graph)
            if self.seen_gc_stack_bottom:
                self.add_descriptor_init_stuff(graph)
        self.add_descriptor_init_stuff(entrypointgraph, main=True)
        self.translator.stm_transformation_applied = True

    def transform_block(self, block):
        if block.operations == ():
            return
        newoperations = []
        for op in block.operations:
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

    def transform_graph(self, graph):
        for block in graph.iterblocks():
            self.transform_block(block)

    def add_descriptor_init_stuff(self, graph, main=False):
        if main:
            self._add_calls_around(graph,
                                   _rffi_stm.begin_inevitable_transaction,
                                   _rffi_stm.commit_transaction)
        self._add_calls_around(graph,
                               _rffi_stm.descriptor_init,
                               _rffi_stm.descriptor_done)

    def _add_calls_around(self, graph, f_init, f_done):
        c_init = Constant(f_init, lltype.typeOf(f_init))
        c_done = Constant(f_done, lltype.typeOf(f_done))
        #
        block = graph.startblock
        v = varoftype(lltype.Void)
        op = SpaceOperation('direct_call', [c_init], v)
        block.operations.insert(0, op)
        #
        v = copyvar(self.translator.annotator, graph.getreturnvar())
        extrablock = Block([v])
        v_none = varoftype(lltype.Void)
        newop = SpaceOperation('direct_call', [c_done], v_none)
        extrablock.operations = [newop]
        extrablock.closeblock(Link([v], graph.returnblock))
        for block in graph.iterblocks():
            if block is not extrablock:
                for link in block.exits:
                    if link.target is graph.returnblock:
                        link.target = extrablock
        checkgraph(graph)

    def add_stm_declare_variable(self, graph):
        block = graph.startblock
        v = varoftype(lltype.Void)
        op = SpaceOperation('stm_declare_variable', [], v)
        block.operations.insert(0, op)

    # ----------

    def stt_getfield(self, newoperations, op):
        STRUCT = op.args[0].concretetype.TO
        if STRUCT._immutable_field(op.args[1].value):
            op1 = op
        elif STRUCT._gckind == 'raw':
            turn_inevitable(newoperations, "getfield-raw")
            op1 = op
        else:
            op1 = SpaceOperation('stm_getfield', op.args, op.result)
        newoperations.append(op1)

    def stt_setfield(self, newoperations, op):
        STRUCT = op.args[0].concretetype.TO
        if STRUCT._immutable_field(op.args[1].value):
            op1 = op
        elif STRUCT._gckind == 'raw':
            turn_inevitable(newoperations, "setfield-raw")
            op1 = op
        else:
            op1 = SpaceOperation('stm_setfield', op.args, op.result)
        newoperations.append(op1)

    def stt_stm_transaction_boundary(self, newoperations, op):
        self.seen_transaction_boundary = True
        return True

    def stt_malloc(self, newoperations, op):
        flags = op.args[1].value
        return flags['flavor'] == 'gc'

    def stt_gc_stack_bottom(self, newoperations, op):
        self.seen_gc_stack_bottom = True
        newoperations.append(op)


def transform_graph(graph):
    # for tests: only transforms one graph
    STMTransformer().transform_graph(graph)


def turn_inevitable(newoperations, info):
    c_info = Constant(info, lltype.Void)
    op1 = SpaceOperation('stm_try_inevitable', [c_info],
                         varoftype(lltype.Void))
    newoperations.append(op1)

def turn_inevitable_and_proceed(newoperations, op):
    turn_inevitable(newoperations, op.opname)
    newoperations.append(op)
