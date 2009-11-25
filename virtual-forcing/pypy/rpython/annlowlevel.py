"""
The code needed to flow and annotate low-level helpers -- the ll_*() functions
"""

import types
from pypy.tool.sourcetools import valid_identifier
from pypy.annotation import model as annmodel
from pypy.annotation.policy import AnnotatorPolicy, Sig
from pypy.annotation.specialize import flatten_star_args
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.ootypesystem import ootype
from pypy.rpython import extregistry
from pypy.objspace.flow.model import Constant
from pypy.translator.simplify import get_functype

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

    def __init__(pol, rtyper=None):
        pol.rtyper = rtyper

    def lowlevelspecialize(funcdesc, args_s, key_for_args):
        args_s, key1, builder = flatten_star_args(funcdesc, args_s)
        key = []
        new_args_s = []
        for i, s_obj in enumerate(args_s):
            if i in key_for_args:
                key.append(key_for_args[i])
                new_args_s.append(s_obj)
            elif isinstance(s_obj, annmodel.SomePBC):
                assert s_obj.is_constant(), "ambiguous low-level helper specialization"
                key.append(KeyComp(s_obj.const))
                new_args_s.append(s_obj)
            else:
                new_args_s.append(annmodel.not_const(s_obj))
                try:
                    key.append(annmodel.annotation_to_lltype(s_obj))
                except ValueError:
                    # passing non-low-level types to a ll_* function is allowed
                    # for module/ll_*
                    key.append(s_obj.__class__)
        key = (tuple(key),)
        if key1 is not None:
            key += (key1,)
        flowgraph = funcdesc.cachedgraph(key, builder=builder)
        args_s[:] = new_args_s
        return flowgraph
    lowlevelspecialize = staticmethod(lowlevelspecialize)

    def default_specialize(funcdesc, args_s):
        return LowLevelAnnotatorPolicy.lowlevelspecialize(funcdesc, args_s, {})
    default_specialize = staticmethod(default_specialize)

    def specialize__ts(pol, funcdesc, args_s, ref):
        ts = pol.rtyper.type_system
        ref = ref.split('.')
        x = ts
        for part in ref:
            x = getattr(x, part)
        bk = pol.rtyper.annotator.bookkeeper
        funcdesc2 = bk.getdesc(x)
        return pol.default_specialize(funcdesc2, args_s)

    def specialize__semierased(funcdesc, args_s):
        a2l = annmodel.annotation_to_lltype
        l2a = annmodel.lltype_to_annotation
        args_s[:] = [l2a(a2l(s)) for s in args_s]
        return LowLevelAnnotatorPolicy.default_specialize(funcdesc, args_s)
    specialize__semierased = staticmethod(specialize__semierased)
    
    specialize__ll = default_specialize

    def specialize__ll_and_arg(funcdesc, args_s, *argindices):
        keys = {}
        for i in argindices:
            keys[i] = args_s[i].const
        return LowLevelAnnotatorPolicy.lowlevelspecialize(funcdesc, args_s,
                                                          keys)
    specialize__ll_and_arg = staticmethod(specialize__ll_and_arg)

def annotate_lowlevel_helper(annotator, ll_function, args_s, policy=None):
    if policy is None:
        policy= LowLevelAnnotatorPolicy()
    return annotator.annotate_helper(ll_function, args_s, policy)

# ___________________________________________________________________
# Mix-level helpers: combining RPython and ll-level

class MixLevelAnnotatorPolicy(LowLevelAnnotatorPolicy):

    def __init__(pol, annhelper):
        pol.annhelper = annhelper
        pol.rtyper = annhelper.rtyper

    def default_specialize(pol, funcdesc, args_s):
        name = funcdesc.name
        if name.startswith('ll_') or name.startswith('_ll_'): # xxx can we do better?
            return super(MixLevelAnnotatorPolicy, pol).default_specialize(
                funcdesc, args_s)
        else:
            return AnnotatorPolicy.default_specialize(funcdesc, args_s)

    def specialize__arglltype(pol, funcdesc, args_s, i):
        key = pol.rtyper.getrepr(args_s[i]).lowleveltype
        alt_name = funcdesc.name+"__for_%sLlT" % key._short_name()
        return funcdesc.cachedgraph(key, alt_name=valid_identifier(alt_name))

    def specialize__genconst(pol, funcdesc, args_s, i):
        # XXX this is specific to the JIT
        TYPE = annmodel.annotation_to_lltype(args_s[i], 'genconst')
        args_s[i] = annmodel.lltype_to_annotation(TYPE)
        alt_name = funcdesc.name + "__%s" % (TYPE._short_name(),)
        return funcdesc.cachedgraph(TYPE, alt_name=valid_identifier(alt_name))


class MixLevelHelperAnnotator:

    def __init__(self, rtyper):
        self.rtyper = rtyper
        self.policy = MixLevelAnnotatorPolicy(self)
        self.pending = []     # list of (ll_function, graph, args_s, s_result)
        self.delayedreprs = {}
        self.delayedconsts = []
        self.delayedfuncs = []
        self.newgraphs = {}

    def getgraph(self, ll_function, args_s, s_result):
        # get the graph of the mix-level helper ll_function and prepare it for
        # being annotated.  Annotation and RTyping should be done in a single shot
        # at the end with finish().
        graph, args_s = self.rtyper.annotator.get_call_parameters(
            ll_function, args_s, policy = self.policy)
        for v_arg, s_arg in zip(graph.getargs(), args_s):
            self.rtyper.annotator.setbinding(v_arg, s_arg)
        self.rtyper.annotator.setbinding(graph.getreturnvar(), s_result)
        #self.rtyper.annotator.annotated[graph.returnblock] = graph
        self.pending.append((ll_function, graph, args_s, s_result))
        return graph

    def delayedfunction(self, ll_function, args_s, s_result, needtype=False):
        # get a delayed pointer to the low-level function, annotated as
        # specified.  The pointer is only valid after finish() was called.
        graph = self.getgraph(ll_function, args_s, s_result)
        if needtype:
            ARGS = [self.getdelayedrepr(s_arg, False).lowleveltype
                    for s_arg in args_s]
            RESULT = self.getdelayedrepr(s_result, False).lowleveltype
            FUNCTYPE = lltype.FuncType(ARGS, RESULT)
        else:
            FUNCTYPE = None
        return self.graph2delayed(graph, FUNCTYPE)

    def constfunc(self, ll_function, args_s, s_result):
        p = self.delayedfunction(ll_function, args_s, s_result)
        return Constant(p, lltype.typeOf(p))

    def graph2delayed(self, graph, FUNCTYPE=None):
        if self.rtyper.type_system.name == 'lltypesystem':
            if FUNCTYPE is None:
                FUNCTYPE = lltype.ForwardReference()
            # obscure hack: embed the name of the function in the string, so
            # that the genc database can get it even before the delayedptr
            # is really computed
            name = "delayed!%s" % (graph.name,)
            delayedptr = lltype._ptr(lltype.Ptr(FUNCTYPE), name, solid=True)
        else:
            if FUNCTYPE is None:
                FUNCTYPE = ootype.ForwardReference()
            name = "delayed!%s" % (graph.name,)
            delayedptr = ootype._forward_static_meth(FUNCTYPE, _name=name)
        self.delayedfuncs.append((delayedptr, graph))
        return delayedptr

    def graph2const(self, graph):
        p = self.graph2delayed(graph)
        return Constant(p, lltype.typeOf(p))

    def getdelayedrepr(self, s_value, check_never_seen=True):
        """Like rtyper.getrepr(), but the resulting repr will not be setup() at
        all before finish() is called.
        """
        r = self.rtyper.getrepr(s_value)
        if check_never_seen:
            r.set_setup_delayed(True)
            delayed = True
        else:
            delayed = r.set_setup_maybe_delayed()
        if delayed:
            self.delayedreprs[r] = True
        return r

    def s_r_instanceof(self, cls, can_be_None=True, check_never_seen=True):
        classdesc = self.rtyper.annotator.bookkeeper.getdesc(cls)
        classdef = classdesc.getuniqueclassdef()
        s_instance = annmodel.SomeInstance(classdef, can_be_None)
        r_instance = self.getdelayedrepr(s_instance, check_never_seen)
        return s_instance, r_instance

    def delayedconst(self, repr, obj):
        if repr.is_setup_delayed():
            # record the existence of this 'obj' for the bookkeeper - e.g.
            # if 'obj' is an instance, this will populate the classdef with
            # the prebuilt attribute values of the instance
            bk = self.rtyper.annotator.bookkeeper
            bk.immutablevalue(obj)

            if self.rtyper.type_system.name == 'lltypesystem':
                delayedptr = lltype._ptr(repr.lowleveltype, "delayed!")
            else:
                delayedptr = ootype.make_instance(repr.lowleveltype)
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
        translator = ann.translator
        original_graph_count = len(translator.graphs)
        for ll_function, graph, args_s, s_result in self.pending:
            # mark the return block as already annotated, because the return var
            # annotation was forced in getgraph() above.  This prevents temporary
            # less general values reaching the return block from crashing the
            # annotator (on the assert-that-new-binding-is-not-less-general).
            ann.annotated[graph.returnblock] = graph
            s_function = bk.immutablevalue(ll_function)
            bk.emulate_pbc_call(graph, s_function, args_s)
            self.newgraphs[graph] = True
        ann.complete_helpers(self.policy)
        for ll_function, graph, args_s, s_result in self.pending:
            s_real_result = ann.binding(graph.getreturnvar())
            if s_real_result != s_result:
                raise Exception("wrong annotation for the result of %r:\n"
                                "originally specified: %r\n"
                                " found by annotating: %r" %
                                (graph, s_result, s_real_result))
        del self.pending[:]
        for graph in translator.graphs[original_graph_count:]:
            self.newgraphs[graph] = True

    def finish_rtype(self):
        rtyper = self.rtyper
        translator = rtyper.annotator.translator
        original_graph_count = len(translator.graphs)
        rtyper.type_system.perform_normalizations(rtyper)
        for r in self.delayedreprs:
            r.set_setup_delayed(False)
        rtyper.call_all_setups()
        for p, repr, obj in self.delayedconsts:
            p._become(repr.convert_const(obj))
        rtyper.call_all_setups()
        for p, graph in self.delayedfuncs:
            self.newgraphs[graph] = True
            real_p = rtyper.getcallable(graph)
            REAL = get_functype(lltype.typeOf(real_p))
            FUNCTYPE = get_functype(lltype.typeOf(p))
            if isinstance(FUNCTYPE, (lltype.ForwardReference, ootype.ForwardReference)):
                FUNCTYPE.become(REAL)
            assert FUNCTYPE == REAL
            p._become(real_p)
        rtyper.specialize_more_blocks()
        self.delayedreprs.clear()
        del self.delayedconsts[:]
        del self.delayedfuncs[:]
        for graph in translator.graphs[original_graph_count:]:
            self.newgraphs[graph] = True

    def backend_optimize(self, **flags):
        # only optimize the newly created graphs
        from pypy.translator.backendopt.all import backend_optimizations
        translator = self.rtyper.annotator.translator
        newgraphs = self.newgraphs.keys()
        backend_optimizations(translator, newgraphs, secondary=True, **flags)
        self.newgraphs.clear()

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

class PseudoHighLevelCallableEntry(extregistry.ExtRegistryEntry):
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
        FUNCTYPE = get_functype(TYPE)
        for r_arg, ARGTYPE in zip(args_r, FUNCTYPE.ARGS):
            assert r_arg.lowleveltype == ARGTYPE
        assert r_res.lowleveltype == FUNCTYPE.RESULT
        hop.exception_is_here()
        return hop.genop('direct_call', [c_func] + vlist, resulttype = r_res)

# ____________________________________________________________


def llhelper(F, f):
    """Gives a low-level function pointer of type F which, when called,
    invokes the RPython function f().
    """
    # Example - the following code can be either run or translated:
    #
    #   def my_rpython_code():
    #       g = llhelper(F, my_other_rpython_function)
    #       assert typeOf(g) == F
    #       ...
    #       g()
    #
    # however the following doesn't translate (xxx could be fixed with hacks):
    #
    #   prebuilt_g = llhelper(F, f)
    #   def my_rpython_code():
    #       prebuilt_g()

    # the next line is the implementation for the purpose of direct running
    if isinstance(F, ootype.OOType):
        return ootype.static_meth(F, f.func_name, _callable=f)
    else:
        return lltype.functionptr(F.TO, f.func_name, _callable=f)


class LLHelperEntry(extregistry.ExtRegistryEntry):
    _about_ = llhelper

    def compute_result_annotation(self, s_F, s_callable):
        assert s_F.is_constant()
        assert s_callable.is_constant()
        F = s_F.const
        if isinstance(F, ootype.OOType):
            FUNC = F
            resultcls = annmodel.SomeOOStaticMeth
        else:
            FUNC = F.TO
            resultcls = annmodel.SomePtr
        
        args_s = [annmodel.lltype_to_annotation(T) for T in FUNC.ARGS]
        key = (llhelper, s_callable.const)
        s_res = self.bookkeeper.emulate_pbc_call(key, s_callable, args_s)
        assert annmodel.lltype_to_annotation(FUNC.RESULT).contains(s_res)
        return resultcls(F)

    def specialize_call(self, hop):
        hop.exception_cannot_occur()
        return hop.args_r[1].get_unique_llfn()

# ____________________________________________________________

def make_string_entries(strtype):
    assert strtype in (str, unicode)

    def hlstr(ll_s):
        if hasattr(ll_s, 'chars'):
            if strtype is str:
                return ''.join(ll_s.chars)
            else:
                return u''.join(ll_s.chars)
        else:
            return ll_s._str

    class HLStrEntry(extregistry.ExtRegistryEntry):
        _about_ = hlstr

        def compute_result_annotation(self, s_ll_str):
            if strtype is str:
                return annmodel.SomeString()
            else:
                return annmodel.SomeUnicodeString()

        def specialize_call(self, hop):
            hop.exception_cannot_occur()
            assert hop.args_r[0].lowleveltype == hop.r_result.lowleveltype
            v_ll_str, = hop.inputargs(*hop.args_r)
            return hop.genop('same_as', [v_ll_str],
                             resulttype = hop.r_result.lowleveltype)

    def llstr(s):
        from pypy.rpython.lltypesystem.rstr import mallocstr, mallocunicode
        if strtype is str:
            ll_s = mallocstr(len(s))
        else:
            ll_s = mallocunicode(len(s))
        for i, c in enumerate(s):
            ll_s.chars[i] = c
        return ll_s

    def oostr(s):
        if strtype is str:
            return ootype.make_string(s)
        else:
            return ootype.make_unicode(s)

    class LLStrEntry(extregistry.ExtRegistryEntry):
        _about_ = llstr

        def compute_result_annotation(self, s_str):
            from pypy.rpython.lltypesystem.rstr import STR, UNICODE
            if strtype is str:
                return annmodel.lltype_to_annotation(lltype.Ptr(STR))
            else:
                return annmodel.lltype_to_annotation(lltype.Ptr(UNICODE))

        def specialize_call(self, hop):
            hop.exception_cannot_occur()
            assert hop.args_r[0].lowleveltype == hop.r_result.lowleveltype
            v_ll_str, = hop.inputargs(*hop.args_r)
            return hop.genop('same_as', [v_ll_str],
                             resulttype = hop.r_result.lowleveltype)

    class OOStrEntry(extregistry.ExtRegistryEntry):
        _about_ = oostr

        def compute_result_annotation(self, s_str):
            if strtype is str:
                return annmodel.lltype_to_annotation(ootype.String)
            else:
                return annmodel.lltype_to_annotation(ootype.Unicode)

        specialize_call = LLStrEntry.specialize_call.im_func

    return hlstr, llstr, oostr

hlstr,     llstr,     oostr     = make_string_entries(str)
hlunicode, llunicode, oounicode = make_string_entries(unicode)

# ____________________________________________________________

def cast_object_to_ptr(PTR, object):
    raise NotImplementedError("cast_object_to_ptr")

def cast_instance_to_base_ptr(instance):
    return cast_object_to_ptr(base_ptr_lltype(), instance)
cast_instance_to_base_ptr._annspecialcase_ = 'specialize:argtype(0)'

def cast_instance_to_base_obj(instance):
    return cast_object_to_ptr(base_obj_ootype(), instance)
cast_instance_to_base_obj._annspecialcase_ = 'specialize:argtype(0)'

def base_ptr_lltype():
    from pypy.rpython.lltypesystem.rclass import OBJECTPTR
    return OBJECTPTR

def base_obj_ootype():
    from pypy.rpython.ootypesystem.rclass import OBJECT
    return OBJECT

class CastObjectToPtrEntry(extregistry.ExtRegistryEntry):
    _about_ = cast_object_to_ptr

    def compute_result_annotation(self, s_PTR, s_object):
        assert s_PTR.is_constant()
        if isinstance(s_PTR.const, lltype.Ptr):
            return annmodel.SomePtr(s_PTR.const)
        elif isinstance(s_PTR.const, ootype.Instance):
            return annmodel.SomeOOInstance(s_PTR.const)
        else:
            assert False

    def specialize_call(self, hop):
        from pypy.rpython import rpbc
        PTR = hop.r_result.lowleveltype
        if isinstance(PTR, lltype.Ptr):
            T = lltype.Ptr
            opname = 'cast_pointer'
            null = lltype.nullptr(PTR.TO)
        elif isinstance(PTR, ootype.Instance):
            T = ootype.Instance
            opname = 'ooupcast'
            null = ootype.null(PTR)
        else:
            assert False

        if isinstance(hop.args_r[1], rpbc.NoneFrozenPBCRepr):
            return hop.inputconst(PTR, null)
        v_arg = hop.inputarg(hop.args_r[1], arg=1)
        assert isinstance(v_arg.concretetype, T)
        hop.exception_cannot_occur()
        return hop.genop(opname, [v_arg], resulttype = PTR)


# ____________________________________________________________

def cast_base_ptr_to_instance(Class, ptr):
    raise NotImplementedError("cast_base_ptr_to_instance")

class CastBasePtrToInstanceEntry(extregistry.ExtRegistryEntry):
    _about_ = cast_base_ptr_to_instance

    def compute_result_annotation(self, s_Class, s_ptr):
        assert s_Class.is_constant()
        classdef = self.bookkeeper.getuniqueclassdef(s_Class.const)
        return annmodel.SomeInstance(classdef, can_be_None=True)

    def specialize_call(self, hop):
        # XXX: check if there is any test to port from oo-jit/
        v_arg = hop.inputarg(hop.args_r[1], arg=1)
        if isinstance(v_arg.concretetype, lltype.Ptr):
            opname = 'cast_pointer'
        elif isinstance(v_arg.concretetype, ootype.Instance):
            opname = 'oodowncast'
        else:
            assert False
        hop.exception_cannot_occur()
        return hop.genop(opname, [v_arg],
                         resulttype = hop.r_result.lowleveltype)

# ____________________________________________________________


def placeholder_sigarg(s):
    if s == "self":
        def expand(s_self, *args_s):
            assert isinstance(s_self, annmodel.SomePtr)
            return s_self
    elif s == "SELF":
        raise NotImplementedError
    else:
        assert s.islower()
        def expand(s_self, *args_s):
            assert isinstance(s_self, annmodel.SomePtr)
            return getattr(s_self.ll_ptrtype.TO, s.upper()) 
    return expand

def typemeth_placeholder_sigarg(s):
    if s == "SELF":
        def expand(s_TYPE, *args_s):
            assert isinstance(s_TYPE, annmodel.SomePBC)
            assert s_TYPE.is_constant()
            return s_TYPE
    elif s == "self":
        def expand(s_TYPE, *args_s):
            assert isinstance(s_TYPE, annmodel.SomePBC)
            assert s_TYPE.is_constant()
            return lltype.Ptr(s_TYPE.const)
    else:
        assert s.islower()
        def expand(s_TYPE, *args_s):
            assert isinstance(s_TYPE, annmodel.SomePBC)
            assert s_TYPE.is_constant()
            return getattr(s_TYPE.const, s.upper()) 
    return expand

            
class ADTInterface(object):

    def __init__(self, base, sigtemplates):
        self.sigtemplates = sigtemplates
        self.base = base
        sigs = {}
        if base is not None:
            sigs.update(base.sigs)
        for name, template in sigtemplates.items():
            args, result = template
            if args[0] == "self":
                make_expand = placeholder_sigarg
            elif args[0] == "SELF":
                make_expand = typemeth_placeholder_sigarg
            else:
                assert False, ("ADTInterface signature should start with"
                               " 'SELF' or 'self'")
            sigargs = []
            for arg in args:
                if isinstance(arg, str):
                    arg = make_expand(arg)
                sigargs.append(arg)
            sigs[name] = Sig(*sigargs)
        self.sigs = sigs

    def __call__(self, adtmeths):
        for name, sig in self.sigs.items():
            meth = adtmeths[name]
            prevsig = getattr(meth, '_annenforceargs_', None)
            if prevsig:
                assert prevsig is sig
            else:
                meth._annenforceargs_ = sig
        return adtmeths

# ____________________________________________________________

class cachedtype(type):
    """Metaclass for classes that should only have one instance per
    tuple of arguments given to the constructor."""

    def __init__(selfcls, name, bases, dict):
        super(cachedtype, selfcls).__init__(name, bases, dict)
        selfcls._instancecache = {}

    def __call__(selfcls, *args):
        d = selfcls._instancecache
        try:
            return d[args]
        except KeyError:
            instance = d[args] = selfcls.__new__(selfcls, *args)
            try:
                instance.__init__(*args)
            except:
                # If __init__ fails, remove the 'instance' from d.
                # That's a "best effort" attempt, it's not really enough
                # in theory because some other place might have grabbed
                # a reference to the same broken 'instance' in the meantime
                del d[args]
                raise
            return instance
