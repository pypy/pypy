from pypy.rpython.lltypesystem import lltype, rclass
from pypy.rpython.ootypesystem import ootype
from pypy.rpython import rlist
from pypy.rpython.lltypesystem import rdict, rstr
from pypy.rpython.llinterp import LLInterpreter
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.translator.simplify import get_funcobj
from pypy.translator.unsimplify import split_block
from pypy.objspace.flow.model import Constant
from pypy import conftest
from pypy.translator.translator import TranslationContext
from pypy.annotation.policy import AnnotatorPolicy
from pypy.annotation import model as annmodel
from pypy.rpython.annlowlevel import MixLevelHelperAnnotator
from pypy.rpython.extregistry import ExtRegistryEntry

def getargtypes(annotator, values):
    if values is None:    # for backend tests producing stand-alone exe's
        from pypy.annotation.listdef import s_list_of_strings
        return [s_list_of_strings]
    return [_annotation(annotator, x) for x in values]

def _annotation(a, x):
    T = lltype.typeOf(x)
    if T == lltype.Ptr(rstr.STR):
        t = str
    else:
        t = annmodel.lltype_to_annotation(T)
    return a.typeannotation(t)

def annotate(func, values, inline=None, backendoptimize=True,
             type_system="lltype"):
    # build the normal ll graphs for ll_function
    t = TranslationContext()
    annpolicy = AnnotatorPolicy()
    annpolicy.allow_someobjects = False
    a = t.buildannotator(policy=annpolicy)
    argtypes = getargtypes(a, values)
    a.build_types(func, argtypes)
    rtyper = t.buildrtyper(type_system = type_system)
    rtyper.specialize()
    if inline:
        auto_inlining(t, threshold=inline)
    if backendoptimize:
        from pypy.translator.backendopt.all import backend_optimizations
        backend_optimizations(t, inline_threshold=inline or 0)

    #if conftest.option.view:
    #    t.view()
    return rtyper

def split_before_jit_merge_point(graph, portalblock, portalopindex):
    """Find the block with 'jit_merge_point' and split just before,
    making sure the input args are in the canonical order.
    """
    # split the block just before the jit_merge_point()
    if portalopindex > 0:
        link = split_block(None, portalblock, portalopindex)
        portalblock = link.target
    portalop = portalblock.operations[0]
    # split again, this time enforcing the order of the live vars
    # specified by the user in the jit_merge_point() call
    assert portalop.opname == 'jit_marker'
    assert portalop.args[0].value == 'jit_merge_point'
    livevars = [v for v in portalop.args[2:]
                  if v.concretetype is not lltype.Void]
    link = split_block(None, portalblock, 0, livevars)
    return link.target

def maybe_on_top_of_llinterp(rtyper, fnptr):
    # Run a generated graph on top of the llinterp for testing.
    # When translated, this just returns the fnptr.
    llinterp = LLInterpreter(rtyper)  #, exc_data_ptr=exc_data_ptr)
    funcobj = get_funcobj(fnptr)
    if hasattr(funcobj, 'graph'):
        def on_top_of_llinterp(*args):
            return llinterp.eval_graph(funcobj.graph, list(args))
    else:
        assert isinstance(fnptr, ootype._meth)
        assert hasattr(fnptr, '_callable')
        def on_top_of_llinterp(*args):
            return fnptr._callable(*args)
    return on_top_of_llinterp

class Entry(ExtRegistryEntry):
    _about_ = maybe_on_top_of_llinterp
    def compute_result_annotation(self, s_rtyper, s_fnptr):
        return s_fnptr
    def specialize_call(self, hop):
        hop.exception_cannot_occur()
        return hop.inputarg(hop.args_r[1], arg=1)

# ____________________________________________________________
#
# Manually map oopspec'ed operations back to their ll implementation
# coming from modules like pypy.rpython.rlist.  The following
# functions are fished from the globals() by setup_extra_builtin().

def _ll_0_newlist(LIST):
    return LIST.ll_newlist(0)
def _ll_1_newlist(LIST, count):
    return LIST.ll_newlist(count)
def _ll_2_newlist(LIST, count, item):
    return rlist.ll_alloc_and_set(LIST, count, item)
_ll_0_newlist.need_result_type = True
_ll_1_newlist.need_result_type = True
_ll_2_newlist.need_result_type = True

def _ll_1_list_len(l):
    return l.ll_length()
def _ll_2_list_getitem(l, index):
    return rlist.ll_getitem(rlist.dum_checkidx, l, index)
def _ll_3_list_setitem(l, index, newitem):
    rlist.ll_setitem(rlist.dum_checkidx, l, index, newitem)
def _ll_1_list_pop(l):
    return rlist.ll_pop_default(rlist.dum_checkidx, l)
def _ll_2_list_pop(l, index):
    return rlist.ll_pop(rlist.dum_checkidx, l, index)
_ll_2_list_append = rlist.ll_append
_ll_2_list_extend = rlist.ll_extend
_ll_3_list_insert = rlist.ll_insert_nonneg

_ll_2_list_getitem_foldable = _ll_2_list_getitem
_ll_1_list_len_foldable     = _ll_1_list_len

def _ll_0_newdict(DICT):
    from pypy.rpython.lltypesystem.rdict import ll_newdict
    return ll_newdict(DICT)
_ll_0_newdict.need_result_type = True

_ll_2_dict_getitem = rdict.ll_dict_getitem
_ll_3_dict_setitem = rdict.ll_dict_setitem
_ll_2_dict_contains = rdict.ll_contains

_ll_5_string_copy_contents = rstr.copy_string_contents

def setup_extra_builtin(oopspec_name, nb_args):
    name = '_ll_%d_%s' % (nb_args, oopspec_name.replace('.', '_'))
##    try:
    wrapper = globals()[name]
##    except KeyError:
##        if '.' not in oopspec_name:
##            raise
##        if not isinstance(SELFTYPE, ootype.BuiltinADTType):
##            raise
##        _, meth = SELFTYPE._lookup(oopspec_name.split('.')[1])
##        if not meth:
##            raise
##        wrapper = ootype.build_unbound_method_wrapper(meth)
    return wrapper

# # ____________________________________________________________

class Index:
    def __init__(self, n):
        self.n = n

def parse_oopspec(fnobj):
    FUNCTYPE = lltype.typeOf(fnobj)
    ll_func = fnobj._callable
    nb_args = len(FUNCTYPE.ARGS)
    argnames = ll_func.func_code.co_varnames[:nb_args]
    # parse the oopspec and fill in the arguments
    operation_name, args = ll_func.oopspec.split('(', 1)
    assert args.endswith(')')
    args = args[:-1] + ','     # trailing comma to force tuple syntax
    if args.strip() == ',':
        args = '()'
    nb_args = len(argnames)
    argname2index = dict(zip(argnames, [Index(n) for n in range(nb_args)]))
    argtuple = eval(args, argname2index)
    return operation_name, argtuple

def normalize_opargs(argtuple, opargs):
    result = []
    for obj in argtuple:
        if isinstance(obj, Index):
            result.append(opargs[obj.n])
        else:
            result.append(Constant(obj, lltype.typeOf(obj)))
    return result

def get_call_oopspec_opargs(fnobj, opargs):
    oopspec, argtuple = parse_oopspec(fnobj)
    normalized_opargs = normalize_opargs(argtuple, opargs)
    return oopspec, normalized_opargs

def decode_builtin_call(op):
    if op.opname == 'oosend':
        SELFTYPE, name, opargs = decompose_oosend(op)
        return get_send_oopspec(SELFTYPE, name), opargs
    elif op.opname == 'direct_call':
        fnobj = get_funcobj(op.args[0].value)
        opargs = op.args[1:]
        return get_call_oopspec_opargs(fnobj, opargs)
    else:
        raise ValueError(op.opname)

def builtin_func_for_spec(rtyper, oopspec_name, ll_args, ll_res):
    key = (oopspec_name, tuple(ll_args), ll_res)
    try:
        return rtyper._builtin_func_for_spec_cache[key]
    except (KeyError, AttributeError):
        pass
    args_s = [annmodel.lltype_to_annotation(v) for v in ll_args]
    if '.' not in oopspec_name:    # 'newxxx' operations
        LIST_OR_DICT = ll_res
    else:
        LIST_OR_DICT = ll_args[0]
    s_result = annmodel.lltype_to_annotation(ll_res)
    impl = setup_extra_builtin(oopspec_name, len(args_s))
    if getattr(impl, 'need_result_type', False):
        bk = rtyper.annotator.bookkeeper
        args_s.insert(0, annmodel.SomePBC([bk.getdesc(ll_res.TO)]))
    #
    mixlevelann = MixLevelHelperAnnotator(rtyper)
    c_func = mixlevelann.constfunc(impl, args_s, s_result)
    mixlevelann.finish()
    #
    if not hasattr(rtyper, '_builtin_func_for_spec_cache'):
        rtyper._builtin_func_for_spec_cache = {}
    rtyper._builtin_func_for_spec_cache[key] = (c_func, LIST_OR_DICT)
    #
    return c_func, LIST_OR_DICT

def raise_exc_value(tp, value):
    from pypy.rpython.llinterp import LLException
    raise LLException(tp, value)

class Entry(ExtRegistryEntry):
    _about_ = raise_exc_value

    def compute_result_annotation(self, s_tp, s_value):
        return annmodel.s_ImpossibleValue

    def specialize_call(self, hop):
        v_list = [hop.inputarg(hop.args_r[0], arg=0),
                  hop.inputarg(hop.args_r[1], arg=1)]
        hop.has_implicit_exception(Exception)
        hop.exception_is_here()
        return hop.genop('raise_exc_value', v_list)
