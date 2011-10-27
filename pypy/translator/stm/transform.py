from pypy.objspace.flow.model import SpaceOperation


class STMTransformer(object):

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

    def stt_getfield(self, newoperations, op):
        op1 = SpaceOperation('stm_getfield', op.args, op.result)
        newoperations.append(op1)

    def stt_setfield(self, newoperations, op):
        op1 = SpaceOperation('stm_setfield', op.args, op.result)
        newoperations.append(op1)


def transform_graph(graph):
    STMTransformer().transform_graph(graph)
