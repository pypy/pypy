from pypy.annotation.annrpython import RPythonAnnotator
from pypy.jit.hintannotator import model as hintmodel
from pypy.jit.hintannotator.bookkeeper import HintBookkeeper
from pypy.rpython.lltypesystem import lltype


class HintAnnotator(RPythonAnnotator):

    def __init__(self, translator=None, base_translator=None, policy=None):
        bookkeeper = HintBookkeeper(self)        
        RPythonAnnotator.__init__(self, translator, policy=policy,
                                  bookkeeper=bookkeeper)

        self.base_translator = base_translator
        assert base_translator is not None      # None not supported any more
        self.exceptiontransformer = base_translator.getexceptiontransformer()

    def build_types(self, origgraph, input_args_hs):
        desc = self.bookkeeper.getdesc(origgraph)
        flowgraph = desc.specialize(input_args_hs)
        return self.build_graph_types(flowgraph, input_args_hs)

    def simplify(self):
        pass

    def consider_op_malloc(self, hs_TYPE):
        TYPE = hs_TYPE.const
        if getattr(self.policy, 'novirtualcontainer', False):
            return hintmodel.SomeLLAbstractVariable(lltype.Ptr(TYPE))
        else:
            vstructdef = self.bookkeeper.getvirtualcontainerdef(TYPE)
            return hintmodel.SomeLLAbstractContainer(vstructdef)

    def consider_op_malloc_varsize(self, hs_TYPE, hs_length):
        TYPE = hs_TYPE.const
        if getattr(self.policy, 'novirtualcontainer', False):
            return hintmodel.SomeLLAbstractVariable(lltype.Ptr(TYPE))
        else:
            vcontainerdef = self.bookkeeper.getvirtualcontainerdef(TYPE)
            return hintmodel.SomeLLAbstractContainer(vcontainerdef)

    def consider_op_keepalive(self, hs_v):
        pass

    def consider_op_debug_log_exc(self, hs_v):
        pass

    def simplify(self):
        RPythonAnnotator.simplify(self, extra_passes=[])

HintAnnotator._registeroperations(hintmodel)
