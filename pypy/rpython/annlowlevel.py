"""
The code needed to flow and annotate low-level helpers -- the ll_*() functions
"""

import types
from pypy.tool.sourcetools import valid_identifier
from pypy.annotation import model as annmodel
from pypy.annotation.policy import AnnotatorPolicy
from pypy.rpython.lltypesystem import lltype
from pypy.rpython import extfunctable, extregistry
from pypy.objspace.flow.model import Constant

def not_const(s_obj): # xxx move it somewhere else
    if s_obj.is_constant():
        new_s_obj = annmodel.SomeObject()
        new_s_obj.__class__ = s_obj.__class__
        new_s_obj.__dict__ = s_obj.__dict__.copy()
        del new_s_obj.const
        s_obj = new_s_obj
    return s_obj


class KeyComp(object):
    def __init__(self, val):
        self.val = val
    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.val == other.val
    def __ne__(self, other):
        return not (self == other)
    def __hash__(self):
        return hash(self.val)
    def __str__(self):
        val = self.val
        if isinstance(val, lltype.LowLevelType):
            return val._short_name() + 'LlT'
        s = getattr(val, '__name__', None)
        if s is None:
            compact = getattr(val, 'compact_repr', None)
            if compact is None:
                s = repr(val)
            else:
                s = compact()        
        return s + 'Const'

class LowLevelAnnotatorPolicy(AnnotatorPolicy):
    allow_someobjects = False
    # if this exists and is boolean, then it always wins:
    override_do_imports_immediately = True

    def __init__(pol, rtyper=None):
        pol.rtyper = rtyper

    def default_specialize(funcdesc, args_s):
        key = []
        new_args_s = []
        for s_obj in args_s:
            if isinstance(s_obj, annmodel.SomePBC):
                assert s_obj.is_constant(), "ambiguous low-level helper specialization"
                key.append(KeyComp(s_obj.const))
                new_args_s.append(s_obj)
            else:
                new_args_s.append(not_const(s_obj))
                try:
                    key.append(annmodel.annotation_to_lltype(s_obj))
                except ValueError:
                    # passing non-low-level types to a ll_* function is allowed
                    # for module/ll_*
                    key.append(s_obj.__class__)
        flowgraph = funcdesc.cachedgraph(tuple(key))
        args_s[:] = new_args_s
        return flowgraph
    default_specialize = staticmethod(default_specialize)

    def override__init_opaque_object(pol, s_opaqueptr, s_value):
        assert isinstance(s_opaqueptr, annmodel.SomePtr)
        assert isinstance(s_opaqueptr.ll_ptrtype.TO, lltype.OpaqueType)
        assert isinstance(s_value, annmodel.SomeExternalObject)
        exttypeinfo = extfunctable.typetable[s_value.knowntype]
        assert s_opaqueptr.ll_ptrtype.TO._exttypeinfo == exttypeinfo
        return annmodel.SomeExternalObject(exttypeinfo.typ)

    def override__from_opaque_object(pol, s_opaqueptr):
        assert isinstance(s_opaqueptr, annmodel.SomePtr)
        assert isinstance(s_opaqueptr.ll_ptrtype.TO, lltype.OpaqueType)
        exttypeinfo = s_opaqueptr.ll_ptrtype.TO._exttypeinfo
        return annmodel.SomeExternalObject(exttypeinfo.typ)

    def override__to_opaque_object(pol, s_value):
        assert isinstance(s_value, annmodel.SomeExternalObject)
        exttypeinfo = extfunctable.typetable[s_value.knowntype]
        return annmodel.SomePtr(lltype.Ptr(exttypeinfo.get_lltype()))

    def specialize__ts(pol, funcdesc, args_s, ref):
        ts = pol.rtyper.type_system
        ref = ref.split('.')
        x = ts
        for part in ref:
            x = getattr(x, part)
        bk = pol.rtyper.annotator.bookkeeper
        funcdesc2 = bk.getdesc(x)
        return pol.default_specialize(funcdesc2, args_s)

    specialize__ll = default_specialize

def annotate_lowlevel_helper(annotator, ll_function, args_s, policy=None):
    if policy is None:
        policy= LowLevelAnnotatorPolicy()
    return annotator.annotate_helper(ll_function, args_s, policy)

# ___________________________________________________________________
# Mix-level helpers: combining RPython and ll-level

class MixLevelAnnotatorPolicy(LowLevelAnnotatorPolicy):

    def __init__(pol, rtyper):
        pol.rtyper = rtyper

    def default_specialize(pol, funcdesc, args_s):
        name = funcdesc.name
        if name.startswith('ll_') or name.startswith('_ll_'): # xxx can we do better?
            return super(MixLevelAnnotatorPolicy, pol).default_specialize(
                funcdesc, args_s)
        else:
            return funcdesc.cachedgraph(None)

    def specialize__arglltype(pol, funcdesc, args_s, i):
        key = pol.rtyper.getrepr(args_s[i]).lowleveltype
        alt_name = funcdesc.name+"__for_%sLlT" % key._short_name()
        return funcdesc.cachedgraph(key, alt_name=valid_identifier(alt_name))        


class MixLevelHelperAnnotator:

    def __init__(self, rtyper):
        self.rtyper = rtyper
        self.policy = MixLevelAnnotatorPolicy(rtyper)
        self.pending = []     # list of (ll_function, graph, args_s, s_result)
        self.delayedreprs = []
        self.delayedconsts = []
        self.delayedfuncs = []
        self.original_graph_count = len(rtyper.annotator.translator.graphs)

    def getgraph(self, ll_function, args_s, s_result):
        # get the graph of the mix-level helper ll_function and prepare it for
        # being annotated.  Annotation and RTyping should be done in a single shot
        # at the end with finish().
        graph = self.rtyper.annotator.annotate_helper(ll_function, args_s,
                                                      policy = self.policy,
                                                      complete_now = False)
        for v_arg, s_arg in zip(graph.getargs(), args_s):
            self.rtyper.annotator.setbinding(v_arg, s_arg)
        self.rtyper.annotator.setbinding(graph.getreturnvar(), s_result)
        self.pending.append((ll_function, graph, args_s, s_result))
        return graph

    def delayedfunction(self, ll_function, args_s, s_result):
        # get a delayed pointer to the low-level function, annotated as
        # specified.  The pointer is only valid after finish() was called.
        graph = self.getgraph(ll_function, args_s, s_result)
        return self.graph2delayed(graph)

    def constfunc(self, ll_function, args_s, s_result):
        p = self.delayedfunction(ll_function, args_s, s_result)
        return Constant(p, lltype.typeOf(p))

    def graph2delayed(self, graph):
        FUNCTYPE = lltype.ForwardReference()
        # obscure hack: embed the name of the function in the string, so
        # that the genc database can get it even before the delayedptr
        # is really computed
        name = "delayed!%s" % (graph.name,)
        delayedptr = lltype._ptr(lltype.Ptr(FUNCTYPE), name, solid=True)
        self.delayedfuncs.append((delayedptr, graph))
        return delayedptr

    def graph2const(self, graph):
        p = self.graph2delayed(graph)
        return Constant(p, lltype.typeOf(p))

    def getdelayedrepr(self, s_value):
        """Like rtyper.getrepr(), but the resulting repr will not be setup() at
        all before finish() is called.
        """
        r = self.rtyper.getrepr(s_value)
        r.set_setup_delayed(True)
        self.delayedreprs.append(r)
        return r

    def s_r_instanceof(self, cls, can_be_None=True):
        classdesc = self.rtyper.annotator.bookkeeper.getdesc(cls)
        classdef = classdesc.getuniqueclassdef()
        s_instance = annmodel.SomeInstance(classdef, can_be_None)
        r_instance = self.getdelayedrepr(s_instance)
        return s_instance, r_instance

    def delayedconst(self, repr, obj):
        if repr.is_setup_delayed():
            # record the existence of this 'obj' for the bookkeeper - e.g.
            # if 'obj' is an instance, this will populate the classdef with
            # the prebuilt attribute values of the instance
            bk = self.rtyper.annotator.bookkeeper
            bk.immutablevalue(obj)

            delayedptr = lltype._ptr(repr.lowleveltype, "delayed!")
            self.delayedconsts.append((delayedptr, repr, obj))
            return delayedptr
        else:
            return repr.convert_const(obj)

    def finish(self):
        self.finish_annotate()
        self.finish_rtype()

    def finish_annotate(self):
        # push all the graphs into the annotator's pending blocks dict at once
        rtyper = self.rtyper
        ann = rtyper.annotator
        bk = ann.bookkeeper
        for ll_function, graph, args_s, s_result in self.pending:
            # mark the return block as already annotated, because the return var
            # annotation was forced in getgraph() above.  This prevents temporary
            # less general values reaching the return block from crashing the
            # annotator (on the assert-that-new-binding-is-not-less-general).
            ann.annotated[graph.returnblock] = graph
            s_function = bk.immutablevalue(ll_function)
            bk.emulate_pbc_call(graph, s_function, args_s)
        ann.complete_helpers(self.policy)
        for ll_function, graph, args_s, s_result in self.pending:
            s_real_result = ann.binding(graph.getreturnvar())
            if s_real_result != s_result:
                raise Exception("wrong annotation for the result of %r:\n"
                                "originally specified: %r\n"
                                " found by annotating: %r" %
                                (graph, s_result, s_real_result))
        del self.pending[:]

    def finish_rtype(self):
        rtyper = self.rtyper
        rtyper.type_system.perform_normalizations(rtyper)
        for r in self.delayedreprs:
            r.set_setup_delayed(False)
        for p, repr, obj in self.delayedconsts:
            p._become(repr.convert_const(obj))
        for p, graph in self.delayedfuncs:
            real_p = rtyper.getcallable(graph)
            lltype.typeOf(p).TO.become(lltype.typeOf(real_p).TO)
            p._become(real_p)
        rtyper.specialize_more_blocks()
        del self.delayedreprs[:]
        del self.delayedconsts[:]
        del self.delayedfuncs[:]

    def backend_optimize(self, **flags):
        # only optimize the newly created graphs
        from pypy.translator.backendopt.all import backend_optimizations
        translator = self.rtyper.annotator.translator
        newgraphs = translator.graphs[self.original_graph_count:]
        self.original_graph_count = len(translator.graphs)
        backend_optimizations(translator, newgraphs, **flags)

# ____________________________________________________________

class PseudoHighLevelCallable(object):
    """A gateway to a low-level function pointer.  To high-level RPython
    code it looks like a normal function, taking high-level arguments
    and returning a high-level result.
    """
    def __init__(self, llfnptr, args_s, s_result):
        self.llfnptr = llfnptr
        self.args_s = args_s
        self.s_result = s_result

    def __call__(self, *args):
        raise Exception("PseudoHighLevelCallable objects are not really "
                        "callable directly")

class Entry(extregistry.ExtRegistryEntry):
    _type_ = PseudoHighLevelCallable

    def compute_result_annotation(self, *args_s):
        return self.instance.s_result

    def specialize_call(self, hop):
        args_r = [hop.rtyper.getrepr(s) for s in self.instance.args_s]
        r_res = hop.rtyper.getrepr(self.instance.s_result)
        vlist = hop.inputargs(*args_r)
        p = self.instance.llfnptr
        TYPE = lltype.typeOf(p)
        c_func = Constant(p, TYPE)
        for r_arg, ARGTYPE in zip(args_r, TYPE.TO.ARGS):
            assert r_arg.lowleveltype == ARGTYPE
        assert r_res.lowleveltype == TYPE.TO.RESULT
        hop.exception_is_here()
        return hop.genop('direct_call', [c_func] + vlist, resulttype = r_res)
