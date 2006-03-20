from pypy.annotation.annrpython import RPythonAnnotator, _registeroperations
from pypy.jit import hintmodel
from pypy.jit.hintbookkeeper import HintBookkeeper


class HintAnnotator(RPythonAnnotator):

    def __init__(self, translator=None, policy=None):
        bookkeeper = HintBookkeeper(self)
        RPythonAnnotator.__init__(self, translator, policy=policy,
                                  bookkeeper=bookkeeper)

    def build_types(self, origgraph, input_args_hs):
        desc = self.bookkeeper.getdesc(origgraph)
        flowgraph = desc.specialize(input_args_hs)
        return self.build_graph_types(flowgraph, input_args_hs)

    def simplify(self):
        pass

    def consider_op_malloc(self, hs_TYPE):
        TYPE = hs_TYPE.const
        vstructdef = self.bookkeeper.getvirtualcontainerdef(TYPE)
        return hintmodel.SomeLLAbstractContainer(vstructdef)

    def consider_op_malloc_varsize(self, hs_TYPE, hs_length):
        TYPE = hs_TYPE.const
        vcontainerdef = self.bookkeeper.getvirtualcontainerdef(TYPE)
        return hintmodel.SomeLLAbstractContainer(vcontainerdef)

    def consider_op_keepalive(self, hs_v):
        pass


_registeroperations(HintAnnotator.__dict__, hintmodel)
