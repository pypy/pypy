from pypy.objspace.flow.model import SpaceOperation, Constant
from pypy.annotation import model as annmodel
from pypy.rpython.annlowlevel import MixLevelHelperAnnotator
from pypy.translator.stm import _rffi_stm
from pypy.translator.unsimplify import varoftype
from pypy.rpython.lltypesystem import lltype


ALWAYS_ALLOW_OPERATIONS = set([
    'int_*', 'uint_*', 'llong_*', 'ullong_*', 'float_*',
    'same_as', 'cast_*',
    'direct_call',
    'debug_print', 'debug_assert',
    ])

def op_in_set(opname, set):
    if opname in set:
        return True
    for i in range(len(opname)-1, -1, -1):
        if (opname[:i] + '*') in set:
            return True
    return False

# ____________________________________________________________


class STMTransformer(object):

    def __init__(self, translator=None):
        self.translator = translator

    def transform(self, entrypointptr):
        assert not hasattr(self.translator, 'stm_transformation_applied')
        entrypointgraph = entrypointptr._obj.graph
        for graph in self.translator.graphs:
            if graph is entrypointgraph:
                continue
            self.seen_transaction_boundary = False
            self.transform_graph(graph)
            if self.seen_transaction_boundary:
                self.add_stm_declare_variable(graph)
        self.add_descriptor_init_stuff(entrypointgraph)
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

    def add_descriptor_init_stuff(self, entrypointgraph):
        #
        def descriptor_init():
            _rffi_stm.descriptor_init()
            _rffi_stm.begin_inevitable_transaction()
        #def descriptor_done():
        #    _rffi_stm.commit_transaction()
        #    _rffi_stm.descriptor_done()
        #
        annhelper = MixLevelHelperAnnotator(self.translator.rtyper)
        c_init = annhelper.constfunc(descriptor_init, [], annmodel.s_None)
        #c_done = annhelper.constfunc(descriptor_done, [], annmodel.s_None)
        annhelper.finish()
        block = entrypointgraph.startblock
        v = varoftype(lltype.Void)
        op = SpaceOperation('direct_call', [c_init], v)
        block.operations.insert(0, op)
        #...add c_done...

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
        else:
            op1 = SpaceOperation('stm_getfield', op.args, op.result)
        newoperations.append(op1)

    def stt_setfield(self, newoperations, op):
        op1 = SpaceOperation('stm_setfield', op.args, op.result)
        newoperations.append(op1)

    def stt_stm_transaction_boundary(self, newoperations, op):
        self.seen_transaction_boundary = True
        return True

    def stt_malloc(self, newoperations, op):
        flags = op.args[1].value
        return flags['flavor'] == 'gc'


def transform_graph(graph):
    # for tests: only transforms one graph
    STMTransformer().transform_graph(graph)


def turn_inevitable_and_proceed(newoperations, op):
    c_info = Constant(op.opname, lltype.Void)
    op1 = SpaceOperation('stm_try_inevitable', [c_info],
                         varoftype(lltype.Void))
    newoperations.append(op1)
    newoperations.append(op)
