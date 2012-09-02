from pypy.objspace.flow.model import SpaceOperation, Constant, Variable
from pypy.objspace.flow.model import checkgraph
from pypy.translator.unsimplify import varoftype
from pypy.rpython.lltypesystem import lltype



class STMTransformer(object):

    def __init__(self, translator):
        self.translator = translator

    def transform(self):
        assert not hasattr(self.translator, 'stm_transformation_applied')
        self.start_log()
        for graph in self.translator.graphs:
            pre_insert_stm_barrier(self.translator, graph)
        self.translator.stm_transformation_applied = True
        self.print_logs()

    def start_log(self):
        from pypy.translator.c.support import log
        log.info("Software Transactional Memory transformation")

    def print_logs(self):
        from pypy.translator.c.support import log
        log.info("Software Transactional Memory transformation applied")



def is_immutable(op):
    if op.opname in ('getfield', 'setfield'):
        STRUCT = op.args[0].concretetype.TO
        return STRUCT._immutable_field(op.args[1].value)
    if op.opname in ('getarrayitem', 'setarrayitem'):
        ARRAY = op.args[0].concretetype.TO
        return ARRAY._immutable_field()
    if op.opname == 'getinteriorfield':
        OUTER = op.args[0].concretetype.TO
        return OUTER._immutable_interiorfield(unwraplist(op.args[1:]))
    if op.opname == 'setinteriorfield':
        OUTER = op.args[0].concretetype.TO
        return OUTER._immutable_interiorfield(unwraplist(op.args[1:-1]))
    if op.opname in ('gc_load', 'gc_store'):
        return False
    raise AssertionError(op)

def pre_insert_stm_barrier(translator, graph):
    for block in graph.iterblocks():
        if block.operations == ():
            continue
        #
        wants_a_barrier = {}
        for op in block.operations:
            if (op.opname in ('getfield', 'getarrayitem',
                              'getinteriorfield', 'gc_load') and
                  op.result.concretetype is not lltype.Void and
                  op.args[0].concretetype.TO._gckind == 'gc' and
                  not is_immutable(op)):
                wants_a_barrier.setdefault(op, 'R')
            elif (op.opname in ('setfield', 'setarrayitem',
                                'setinteriorfield', 'gc_store') and
                  op.args[-1].concretetype is not lltype.Void and
                  op.args[0].concretetype.TO._gckind == 'gc' and
                  not is_immutable(op)):
                wants_a_barrier[op] = 'W'
        #
        if wants_a_barrier:
            renamings = {}
            newoperations = []
            for op in block.operations:
                to = wants_a_barrier.get(op)
                if to is not None:
                    c_info = Constant('P2%s' % to, lltype.Void)
                    v = op.args[0]
                    v = renamings.get(v, v)
                    w = varoftype(v.concretetype)
                    newop = SpaceOperation('stm_barrier', [c_info, v], w)
                    newoperations.append(newop)
                    renamings[op.args[0]] = w
                newop = SpaceOperation(op.opname,
                                       [renamings.get(v, v) for v in op.args],
                                       op.result)
                newoperations.append(newop)
            block.operations = newoperations
