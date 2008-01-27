from pypy.annotation import model as annmodel
from pypy.annotation.annrpython import RPythonAnnotator, BlockedInference
from pypy.annotation.annrpython import raise_nicer_exception
from pypy.objspace.flow.model import Variable
from pypy.jit.hintannotator import model as hintmodel
from pypy.jit.hintannotator.bookkeeper import HintBookkeeper
from pypy.jit.hintannotator.policy import HintAnnotatorPolicy
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.ootypesystem import ootype
from pypy.translator.simplify import get_funcobj

class HintAnnotator(RPythonAnnotator):

    def __init__(self, translator=None, base_translator=None, policy=None):
        if policy is None:
            policy = HintAnnotatorPolicy()
        self.base_translator = base_translator
        assert base_translator is not None      # None not supported any more
        bookkeeper = HintBookkeeper(self)        
        RPythonAnnotator.__init__(self, translator, policy=policy,
                                  bookkeeper=bookkeeper)
        self.exceptiontransformer = base_translator.getexceptiontransformer()
        
    def build_types(self, origgraph, input_args_hs):
        desc = self.bookkeeper.getdesc(origgraph)
        flowgraph = desc.specialize(input_args_hs)
        return self.build_graph_types(flowgraph, input_args_hs)

    def getuserclassdefinitions(self):
        return []

    def consider_op_new(self, hs_TYPE):
        TYPE = hs_TYPE.const
        if self.policy.novirtualcontainer:
            return hintmodel.SomeLLAbstractVariable(TYPE)
        else:
            # XXX: ootype
            vstructdef = self.bookkeeper.getvirtualcontainerdef(TYPE)
            return hintmodel.SomeLLAbstractContainer(vstructdef)        

    def consider_op_malloc(self, hs_TYPE, hs_flags):
        TYPE = hs_TYPE.const
        flags = hs_flags.const
        assert flags['flavor'] == 'gc'
        if self.policy.novirtualcontainer:
            return hintmodel.SomeLLAbstractVariable(lltype.Ptr(TYPE))
        else:
            vstructdef = self.bookkeeper.getvirtualcontainerdef(TYPE)
            return hintmodel.SomeLLAbstractContainer(vstructdef)

    def consider_op_malloc_varsize(self, hs_TYPE, hs_flags, hs_length):
        TYPE = hs_TYPE.const
        flags = hs_flags.const
        assert flags['flavor'] == 'gc'        
        if self.policy.novirtualcontainer:
            return hintmodel.SomeLLAbstractVariable(lltype.Ptr(TYPE))
        else:
            vcontainerdef = self.bookkeeper.getvirtualcontainerdef(TYPE)
            return hintmodel.SomeLLAbstractContainer(vcontainerdef)

    def consider_op_zero_gc_pointers_inside(self, hs_v):
        pass

    def consider_op_keepalive(self, hs_v):
        pass

    def consider_op_debug_log_exc(self, hs_v):
        pass

    def consider_op_debug_assert(self, hs_v, *args_hs):
        pass

    def consider_op_resume_point(self, hs_v, *args_hs):
        pass

    def consider_op_ts_metacall(self, hs_f1, hs_metadesccls, *args_hs):
        bookkeeper = self.bookkeeper
        fnobj = get_funcobj(hs_f1.const)
        return hintmodel.cannot_follow_call(bookkeeper, fnobj.graph, args_hs,
                                            lltype.typeOf(fnobj).RESULT)

    def consider_op_oosend(self, hs_name, *args_hs):
        assert hs_name.concretetype is ootype.Void
        hs_obj, args_hs = args_hs[0], args_hs[1:]
        return hs_obj.oosend(hs_name, *args_hs)
    
    def simplify(self):
        RPythonAnnotator.simplify(self, extra_passes=[])

    def noreturnvalue(self, op):
        assert op.result.concretetype is lltype.Void, (
            "missing annotation for the return variable of %s" % (op,))
        return hintmodel.s_void

HintAnnotator._registeroperations(hintmodel)
