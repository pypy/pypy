from pypy.objspace.flow.model import SpaceOperation
from pypy.translator.stm import _rffi_stm


class STMTransformer(object):

    def __init__(self, translator=None):
        self.translator = translator

    def transform(self):
        self.add_descriptor_init_stuff()
        for graph in self.translator.graphs:
            self.transform_graph(graph)
        self.translator.stm_transformation_applied = True

    def transform_block(self, block):
        if block.operations == ():
            return
        newoperations = []
        for op in block.operations:
            meth = getattr(self, 'stt_' + op.opname, list.append)
            meth(newoperations, op)
        block.operations = newoperations

    def transform_graph(self, graph):
        for block in graph.iterblocks():
            self.transform_block(block)

    def add_descriptor_init_stuff(self):
        from pypy.translator.unsimplify import call_initial_function
        from pypy.translator.unsimplify import call_final_function
        def descriptor_init():
            _rffi_stm.descriptor_init()
        def descriptor_done():
            _rffi_stm.descriptor_done()
        call_initial_function(self.translator, descriptor_init)
        call_final_function(self.translator, descriptor_done)

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


def transform_graph(graph):
    # for tests: only transforms one graph
    STMTransformer().transform_graph(graph)
