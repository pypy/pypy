import sys
from pypy.rpython.lltypesystem import lltype, rclass, rffi
from pypy.rpython.ootypesystem import ootype
from pypy.rpython import rlist
from pypy.rpython.lltypesystem import rstr as ll_rstr, rdict as ll_rdict
from pypy.rpython.lltypesystem import rlist as lltypesystem_rlist
from pypy.rpython.lltypesystem.module import ll_math
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.ootypesystem import rdict as oo_rdict
from pypy.rpython.llinterp import LLInterpreter
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.annlowlevel import cast_base_ptr_to_instance
from pypy.translator.simplify import get_funcobj
from pypy.translator.unsimplify import split_block
from pypy.objspace.flow.model import Constant
from pypy import conftest
from pypy.translator.translator import TranslationContext
from pypy.annotation.policy import AnnotatorPolicy
from pypy.annotation import model as annmodel
from pypy.rpython.annlowlevel import MixLevelHelperAnnotator
from pypy.jit.metainterp.typesystem import deref
from pypy.rlib import rgc
from pypy.rlib.rarithmetic import r_longlong, r_ulonglong, r_uint, intmask

def getargtypes(annotator, values):
    if values is None:    # for backend tests producing stand-alone exe's
        from pypy.annotation.listdef import s_list_of_strings
        return [s_list_of_strings]
    return [_annotation(annotator, x) for x in values]

def _annotation(a, x):
    T = lltype.typeOf(x)
    if T == lltype.Ptr(ll_rstr.STR):
        t = str
    else:
        t = annmodel.lltype_to_annotation(T)
    return a.typeannotation(t)

def annotate(func, values, inline=None, backendoptimize=True,
             type_system="lltype", listcomp=False):
    # build the normal ll graphs for ll_function
    t = TranslationContext(list_comprehension_operations=listcomp)
    annpolicy = AnnotatorPolicy()
    annpolicy.allow_someobjects = False
    a = t.buildannotator(policy=annpolicy)
    argtypes = getargtypes(a, values)
    a.build_types(func, argtypes, main_entry_point=True)
    rtyper = t.buildrtyper(type_system = type_system)
    rtyper.specialize()
    if inline:
        auto_inlining(t, threshold=inline)
    if backendoptimize:
        from pypy.translator.backendopt.all import backend_optimizations
        backend_optimizations(t, inline_threshold=inline or 0,
                remove_asserts=True, really_remove_asserts=True)

    #if conftest.option.view:
    #    t.view()
    return rtyper

def getgraph(func, values):
    rtyper = annotate(func, values)
    return rtyper.annotator.translator.graphs[0]

def split_before_jit_merge_point(graph, portalblock, portalopindex):
    """Split the block just before the 'jit_merge_point',
    making sure the input args are in the canonical order.
    """
    # split the block just before the jit_merge_point()
    if portalopindex > 0:
        link = split_block(None, portalblock, portalopindex)
        portalblock = link.target
    portalop = portalblock.operations[0]
    # split again, this time enforcing the order of the live vars
    # specified by decode_hp_hint_args().
    assert portalop.opname == 'jit_marker'
    assert portalop.args[0].value == 'jit_merge_point'
    greens_v, reds_v = decode_hp_hint_args(portalop)
    link = split_block(None, portalblock, 0, greens_v + reds_v)
    return link.target

def decode_hp_hint_args(op):
    # Returns (list-of-green-vars, list-of-red-vars) without Voids.
    # Both lists must be sorted: first INT, then REF, then FLOAT.
    assert op.opname == 'jit_marker'
    jitdriver = op.args[1].value
    numgreens = len(jitdriver.greens)
    numreds = len(jitdriver.reds)
    greens_v = op.args[2:2+numgreens]
    reds_v = op.args[2+numgreens:]
    assert len(reds_v) == numreds
    #
    def _sort(args_v):
        from pypy.jit.metainterp.history import getkind
        lst = [v for v in args_v if v.concretetype is not lltype.Void]
        _kind2count = {'int': 1, 'ref': 2, 'float': 3}
        lst2 = sorted(lst, key=lambda v: _kind2count[getkind(v.concretetype)])
        # a crash here means that you have to reorder the variable named in
        # the JitDriver.  Indeed, greens and reds must both be sorted: first
        # all INTs, followed by all REFs, followed by all FLOATs.
        assert lst == lst2
        return lst
    #
    return (_sort(greens_v), _sort(reds_v))

def maybe_on_top_of_llinterp(rtyper, fnptr):
    # Run a generated graph on top of the llinterp for testing.
    # When translated, this just returns the fnptr.
    funcobj = get_funcobj(fnptr)
    if hasattr(funcobj, 'graph'):
        llinterp = LLInterpreter(rtyper)  #, exc_data_ptr=exc_data_ptr)
        def on_top_of_llinterp(*args):
            return llinterp.eval_graph(funcobj.graph, list(args))
    else:
        assert hasattr(funcobj, '_callable')
        def on_top_of_llinterp(*args):
            return funcobj._callable(*args)
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
def _ll_2_list_delitem(l, index):
    rlist.ll_delitem(rlist.dum_checkidx, l, index)
def _ll_1_list_pop(l):
    return rlist.ll_pop_default(rlist.dum_checkidx, l)
def _ll_2_list_pop(l, index):
    return rlist.ll_pop(rlist.dum_checkidx, l, index)
_ll_2_list_append = rlist.ll_append
_ll_2_list_extend = rlist.ll_extend
_ll_3_list_insert = rlist.ll_insert_nonneg
_ll_4_list_setslice = rlist.ll_listsetslice
_ll_2_list_delslice_startonly = rlist.ll_listdelslice_startonly
_ll_3_list_delslice_startstop = rlist.ll_listdelslice_startstop
_ll_1_list_list2fixed = lltypesystem_rlist.ll_list2fixed
_ll_2_list_inplace_mul = rlist.ll_inplace_mul

_ll_2_list_getitem_foldable = _ll_2_list_getitem
_ll_1_list_len_foldable     = _ll_1_list_len

_ll_5_list_ll_arraycopy = rgc.ll_arraycopy

def _ll_1_gc_identityhash(x):
    return lltype.identityhash(x)

def _ll_1_gc_id(ptr):
    return llop.gc_id(lltype.Signed, ptr)

def _ll_1_jit_force_virtual(inst):
    return llop.jit_force_virtual(lltype.typeOf(inst), inst)


def _ll_2_int_floordiv_ovf_zer(x, y):
    if y == 0:
        raise ZeroDivisionError
    if x == -sys.maxint - 1 and y == -1:
        raise OverflowError
    return llop.int_floordiv(lltype.Signed, x, y)

def _ll_2_int_floordiv_ovf(x, y):
    if x == -sys.maxint - 1 and y == -1:        
        raise OverflowError
    return llop.int_floordiv(lltype.Signed, x, y)

def _ll_2_int_floordiv_zer(x, y):
    if y == 0:
        raise ZeroDivisionError
    return llop.int_floordiv(lltype.Signed, x, y)

def _ll_2_int_mod_ovf_zer(x, y):
    if y == 0:
        raise ZeroDivisionError
    if x == -sys.maxint - 1 and y == -1:
        raise OverflowError
    return llop.int_mod(lltype.Signed, x, y)

def _ll_2_int_mod_ovf(x, y):
    if x == -sys.maxint - 1 and y == -1:
        raise OverflowError
    return llop.int_mod(lltype.Signed, x, y)

def _ll_2_int_mod_zer(x, y):
    if y == 0:
        raise ZeroDivisionError
    return llop.int_mod(lltype.Signed, x, y)

def _ll_2_int_lshift_ovf(x, y):
    result = x << y
    if (result >> y) != x:
        raise OverflowError
    return result

def _ll_1_int_abs(x):
    if x < 0:
        return -x
    else:
        return x
        
# math support
# ------------

_ll_1_ll_math_ll_math_sqrt = ll_math.ll_math_sqrt


# long long support
# -----------------

def u_to_longlong(x):
    return rffi.cast(lltype.SignedLongLong, x)

def _ll_1_llong_invert(xll):
    y = ~r_ulonglong(xll)
    return u_to_longlong(y)

def _ll_2_llong_lt(xll, yll):
    return xll < yll

def _ll_2_llong_le(xll, yll):
    return xll <= yll

def _ll_2_llong_eq(xll, yll):
    return xll == yll

def _ll_2_llong_ne(xll, yll):
    return xll != yll

def _ll_2_llong_gt(xll, yll):
    return xll > yll

def _ll_2_llong_ge(xll, yll):
    return xll >= yll

def _ll_2_llong_ult(xull, yull):
    return xull < yull

def _ll_2_llong_ule(xull, yull):
    return xull <= yull

def _ll_2_llong_ugt(xull, yull):
    return xull > yull

def _ll_2_llong_uge(xull, yull):
    return xull >= yull

def _ll_2_llong_add(xll, yll):
    z = r_ulonglong(xll) + r_ulonglong(yll)
    return u_to_longlong(z)

def _ll_2_llong_sub(xll, yll):
    z = r_ulonglong(xll) - r_ulonglong(yll)
    return u_to_longlong(z)

def _ll_2_llong_mul(xll, yll):
    z = r_ulonglong(xll) * r_ulonglong(yll)
    return u_to_longlong(z)

def _ll_2_llong_and(xll, yll):
    z = r_ulonglong(xll) & r_ulonglong(yll)
    return u_to_longlong(z)

def _ll_2_llong_or(xll, yll):
    z = r_ulonglong(xll) | r_ulonglong(yll)
    return u_to_longlong(z)

def _ll_2_llong_xor(xll, yll):
    z = r_ulonglong(xll) ^ r_ulonglong(yll)
    return u_to_longlong(z)

def _ll_2_llong_lshift(xll, y):
    z = r_ulonglong(xll) << y
    return u_to_longlong(z)

def _ll_2_llong_rshift(xll, y):
    return xll >> y

def _ll_2_llong_urshift(xull, y):
    return xull >> y

def _ll_1_llong_from_int(x):
    return r_longlong(intmask(x))

def _ll_1_llong_from_uint(x):
    return r_longlong(r_uint(x))

def _ll_1_llong_to_int(xll):
    return intmask(xll)

def _ll_1_llong_from_float(xf):
    return r_longlong(xf)

def _ll_1_llong_to_float(xll):
    return float(rffi.cast(lltype.SignedLongLong, xll))


def _ll_1_llong_abs(xll):
    if xll < 0:
        return -xll
    else:
        return xll

def _ll_2_llong_floordiv(xll, yll):
    return llop.llong_floordiv(lltype.SignedLongLong, xll, yll)

def _ll_2_llong_floordiv_zer(xll, yll):
    if yll == 0:
        raise ZeroDivisionError
    return llop.llong_floordiv(lltype.SignedLongLong, xll, yll)

def _ll_2_llong_mod(xll, yll):
    return llop.llong_mod(lltype.SignedLongLong, xll, yll)

def _ll_2_llong_mod_zer(xll, yll):
    if yll == 0:
        raise ZeroDivisionError
    return llop.llong_mod(lltype.SignedLongLong, xll, yll)

def _ll_2_ullong_floordiv(xll, yll):
    return llop.ullong_floordiv(lltype.SignedLongLong, xll, yll)

def _ll_2_ullong_floordiv_zer(xll, yll):
    if yll == 0:
        raise ZeroDivisionError
    return llop.ullong_floordiv(lltype.SignedLongLong, xll, yll)

def _ll_2_ullong_mod(xll, yll):
    return llop.ullong_mod(lltype.SignedLongLong, xll, yll)

def _ll_2_ullong_mod_zer(xll, yll):
    if yll == 0:
        raise ZeroDivisionError
    return llop.ullong_mod(lltype.SignedLongLong, xll, yll)


# libffi support
# --------------

def func(llfunc):
    from pypy.rlib.libffi import Func
    return cast_base_ptr_to_instance(Func, llfunc)

def _ll_1_libffi_prepare_call(llfunc):
    return func(llfunc)._prepare()

def _ll_4_libffi_push_int(llfunc, value, ll_args, i):
    return func(llfunc)._push_int(value, ll_args, i)

def _ll_4_libffi_push_float(llfunc, value, ll_args, i):
    return func(llfunc)._push_float(value, ll_args, i)

def _ll_3_libffi_call_int(llfunc, funcsym, ll_args):
    return func(llfunc)._do_call(funcsym, ll_args, rffi.LONG)

def _ll_3_libffi_call_float(llfunc, funcsym, ll_args):
    return func(llfunc)._do_call(funcsym, ll_args, rffi.DOUBLE)

def _ll_3_libffi_call_void(llfunc, funcsym, ll_args):
    return func(llfunc)._do_call(funcsym, ll_args, lltype.Void)


# in the following calls to builtins, the JIT is allowed to look inside:
inline_calls_to = [
    ('int_floordiv_ovf_zer', [lltype.Signed, lltype.Signed], lltype.Signed),
    ('int_floordiv_ovf',     [lltype.Signed, lltype.Signed], lltype.Signed),
    ('int_floordiv_zer',     [lltype.Signed, lltype.Signed], lltype.Signed),
    ('int_mod_ovf_zer',      [lltype.Signed, lltype.Signed], lltype.Signed),
    ('int_mod_ovf',          [lltype.Signed, lltype.Signed], lltype.Signed),
    ('int_mod_zer',          [lltype.Signed, lltype.Signed], lltype.Signed),
    ('int_lshift_ovf',       [lltype.Signed, lltype.Signed], lltype.Signed),
    ('int_abs',              [lltype.Signed],                lltype.Signed),
    ('ll_math.ll_math_sqrt', [lltype.Float],                 lltype.Float),
    ]


class LLtypeHelpers:

    # ---------- dict ----------

    def _ll_0_newdict(DICT):
        return ll_rdict.ll_newdict(DICT)
    _ll_0_newdict.need_result_type = True

    _ll_2_dict_delitem = ll_rdict.ll_dict_delitem
    _ll_1_dict_copy = ll_rdict.ll_copy
    _ll_1_dict_clear = ll_rdict.ll_clear
    _ll_2_dict_update = ll_rdict.ll_update

    # ---------- dict keys(), values(), items(), iter ----------

    _ll_1_dict_keys   = ll_rdict.ll_dict_keys
    _ll_1_dict_values = ll_rdict.ll_dict_values
    _ll_1_dict_items  = ll_rdict.ll_dict_items
    _ll_1_dict_keys  .need_result_type = True
    _ll_1_dict_values.need_result_type = True
    _ll_1_dict_items .need_result_type = True

    def _ll_1_newdictiter(ITER, d):
        return ll_rdict.ll_dictiter(lltype.Ptr(ITER), d)
    _ll_1_newdictiter.need_result_type = True

    _dictnext_keys   = staticmethod(ll_rdict.ll_dictnext_group['keys'])
    _dictnext_values = staticmethod(ll_rdict.ll_dictnext_group['values'])
    _dictnext_items  = staticmethod(ll_rdict.ll_dictnext_group['items'])

    def _ll_1_dictiter_nextkeys(iter):
        return LLtypeHelpers._dictnext_keys(None, iter)
    def _ll_1_dictiter_nextvalues(iter):
        return LLtypeHelpers._dictnext_values(None, iter)
    def _ll_1_dictiter_nextitems(RES, iter):
        return LLtypeHelpers._dictnext_items(lltype.Ptr(RES), iter)
    _ll_1_dictiter_nextitems.need_result_type = True

    # ---------- strings and unicode ----------

    _ll_1_str_str2unicode = ll_rstr.LLHelpers.ll_str2unicode

    def _ll_4_str_eq_slice_checknull(s1, start, length, s2):
        """str1[start : start + length] == str2."""
        if not s2:
            return 0
        chars2 = s2.chars
        if len(chars2) != length:
            return 0
        j = 0
        chars1 = s1.chars
        while j < length:
            if chars1[start + j] != chars2[j]:
                return 0
            j += 1
        return 1

    def _ll_4_str_eq_slice_nonnull(s1, start, length, s2):
        """str1[start : start + length] == str2, assuming str2 != NULL."""
        chars2 = s2.chars
        if len(chars2) != length:
            return 0
        j = 0
        chars1 = s1.chars
        while j < length:
            if chars1[start + j] != chars2[j]:
                return 0
            j += 1
        return 1

    def _ll_4_str_eq_slice_char(s1, start, length, c2):
        """str1[start : start + length] == c2."""
        if length != 1:
            return 0
        if s1.chars[start] != c2:
            return 0
        return 1

    def _ll_2_str_eq_nonnull(s1, s2):
        len1 = len(s1.chars)
        len2 = len(s2.chars)
        if len1 != len2:
            return 0
        j = 0
        chars1 = s1.chars
        chars2 = s2.chars
        while j < len1:
            if chars1[j] != chars2[j]:
                return 0
            j += 1
        return 1

    def _ll_2_str_eq_nonnull_char(s1, c2):
        chars = s1.chars
        if len(chars) != 1:
            return 0
        if chars[0] != c2:
            return 0
        return 1

    def _ll_2_str_eq_checknull_char(s1, c2):
        if not s1:
            return 0
        chars = s1.chars
        if len(chars) != 1:
            return 0
        if chars[0] != c2:
            return 0
        return 1

    def _ll_2_str_eq_lengthok(s1, s2):
        j = 0
        chars1 = s1.chars
        chars2 = s2.chars
        len1 = len(chars1)
        while j < len1:
            if chars1[j] != chars2[j]:
                return 0
            j += 1
        return 1

    # ---------- malloc with del ----------

    def _ll_2_raw_malloc(TP, size):
        return lltype.malloc(TP, size, flavor='raw')

    def build_ll_0_alloc_with_del(RESULT, vtable):
        def _ll_0_alloc_with_del():
            p = lltype.malloc(RESULT.TO)
            lltype.cast_pointer(rclass.OBJECTPTR, p).typeptr = vtable
            return p
        return _ll_0_alloc_with_del

    def build_ll_1_raw_malloc(ARRAY):
        def _ll_1_raw_malloc(n):
            return lltype.malloc(ARRAY, n, flavor='raw')
        return _ll_1_raw_malloc

    def build_ll_1_raw_free(ARRAY):
        def _ll_1_raw_free(p):
            lltype.free(p, flavor='raw')
        return _ll_1_raw_free

class OOtypeHelpers:

    # ---------- dict ----------

    def _ll_0_newdict(DICT):
        return oo_rdict.ll_newdict(DICT)
    _ll_0_newdict.need_result_type = True

    def _ll_3_dict_setitem(d, key, value):
        d.ll_set(key, value)

    def _ll_2_dict_contains(d, key):
        return d.ll_contains(key)

    def _ll_1_dict_clear(d):
        d.ll_clear()

    _ll_2_dict_getitem = oo_rdict.ll_dict_getitem
    _ll_2_dict_delitem = oo_rdict.ll_dict_delitem
    _ll_3_dict_setdefault = oo_rdict.ll_dict_setdefault
    _ll_3_dict_get = oo_rdict.ll_dict_get
    _ll_1_dict_copy = oo_rdict.ll_dict_copy
    _ll_2_dict_update = oo_rdict.ll_dict_update

    # ---------- dict keys(), values(), items(), iter ----------

    _ll_1_dict_keys   = oo_rdict.ll_dict_keys
    _ll_1_dict_values = oo_rdict.ll_dict_values
    _ll_1_dict_items  = oo_rdict.ll_dict_items
    _ll_1_dict_keys  .need_result_type = True
    _ll_1_dict_values.need_result_type = True
    _ll_1_dict_items .need_result_type = True

    def _ll_1_newdictiter(ITER, d):
        return oo_rdict.ll_dictiter(ITER, d)
    _ll_1_newdictiter.need_result_type = True

    _dictnext_keys   = staticmethod(oo_rdict.ll_dictnext_group['keys'])
    _dictnext_values = staticmethod(oo_rdict.ll_dictnext_group['values'])
    _dictnext_items  = staticmethod(oo_rdict.ll_dictnext_group['items'])

    def _ll_1_dictiter_nextkeys(iter):
        return OOtypeHelpers._dictnext_keys(None, iter)
    def _ll_1_dictiter_nextvalues(iter):
        return OOtypeHelpers._dictnext_values(None, iter)
    def _ll_1_dictiter_nextitems(RES, iter):
        return OOtypeHelpers._dictnext_items(RES, iter)
    _ll_1_dictiter_nextitems.need_result_type = True

    # --------------- oostring and oounicode ----------------

    def _ll_2_oostring_signed_foldable(n, base):
        return ootype.oostring(n, base)

    def _ll_1_oostring_char_foldable(ch):
        return ootype.oostring(ch, -1)

    def _ll_1_oostring_unsigned_foldable(n):
        return ootype.oostring(n, -1)

    def _ll_1_oostring_string_foldable(s):
        return ootype.oostring(s, -1)

    def _ll_1_oostring_root_foldable(s):
        return ootype.oostring(s, -1)

    def _ll_2_oounicode_signed_foldable(n, base):
        return ootype.oounicode(n, base)

    def _ll_1_oounicode_unichar_foldable(ch):
        return ootype.oounicode(ch, -1)

    def _ll_1_oounicode_string_foldable(s):
        return ootype.oounicode(s, -1)

# -------------------------------------------------------

def setup_extra_builtin(rtyper, oopspec_name, nb_args, extra=None):
    name = '_ll_%d_%s' % (nb_args, oopspec_name.replace('.', '_'))
    if extra is not None:
        name = 'build' + name
    try:
        wrapper = globals()[name]
    except KeyError:
        if rtyper.type_system.name == 'lltypesystem':
            Helpers = LLtypeHelpers
        else:
            Helpers = OOtypeHelpers
        wrapper = getattr(Helpers, name).im_func
    if extra is not None:
        wrapper = wrapper(*extra)
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

def get_oostring_oopspec(op):
    T = op.args[0].concretetype
    if T is not ootype.Signed:
        args = op.args[:-1]
    else:
        args = op.args
    if isinstance(T, ootype.Instance):
        T = ootype.ROOT
    return '%s_%s_foldable' % (op.opname, T._name.lower()), args

def get_identityhash_oopspec(op):
    return 'gc_identityhash', op.args

def get_gcid_oopspec(op):
    return 'gc_id', op.args


RENAMED_ADT_NAME = {
    'list': {
        'll_getitem_fast': 'getitem',
        'll_setitem_fast': 'setitem',
        'll_length':       'len',
        },
    }

def get_send_oopspec(SELFTYPE, name):
    oopspec_name = SELFTYPE.oopspec_name
    assert oopspec_name is not None
    renamed = RENAMED_ADT_NAME.get(oopspec_name, {})
    pubname = renamed.get(name, name)
    oopspec = '%s.%s' % (oopspec_name, pubname)
    return oopspec


def decode_builtin_call(op):
    if op.opname == 'oosend':
        SELFTYPE, name, opargs = decompose_oosend(op)
        return get_send_oopspec(SELFTYPE, name), opargs
    elif op.opname == 'direct_call':
        fnobj = get_funcobj(op.args[0].value)
        opargs = op.args[1:]
        return get_call_oopspec_opargs(fnobj, opargs)
    elif op.opname in ('oostring', 'oounicode'):
        return get_oostring_oopspec(op)
    elif op.opname == 'gc_identityhash':
        return get_identityhash_oopspec(op)
    elif op.opname == 'gc_id':
        return get_gcid_oopspec(op)
    else:
        raise ValueError(op.opname)

def builtin_func_for_spec(rtyper, oopspec_name, ll_args, ll_res,
                          extra=None, extrakey=None):
    assert (extra is None) == (extrakey is None)
    key = (oopspec_name, tuple(ll_args), ll_res, extrakey)
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
    impl = setup_extra_builtin(rtyper, oopspec_name, len(args_s), extra)
    if getattr(impl, 'need_result_type', False):
        bk = rtyper.annotator.bookkeeper
        args_s.insert(0, annmodel.SomePBC([bk.getdesc(deref(ll_res))]))
    #
    if hasattr(rtyper, 'annotator'):  # regular case
        mixlevelann = MixLevelHelperAnnotator(rtyper)
        c_func = mixlevelann.constfunc(impl, args_s, s_result)
        mixlevelann.finish()
    else:
        # for testing only
        c_func = Constant(oopspec_name,
                          lltype.Ptr(lltype.FuncType(ll_args, ll_res)))
    #
    if not hasattr(rtyper, '_builtin_func_for_spec_cache'):
        rtyper._builtin_func_for_spec_cache = {}
    rtyper._builtin_func_for_spec_cache[key] = (c_func, LIST_OR_DICT)
    #
    return c_func, LIST_OR_DICT


def decompose_oosend(op):
    name = op.args[0].value
    opargs = op.args[1:]
    SELFTYPE = opargs[0].concretetype
    return SELFTYPE, name, opargs

def lookup_oosend_method(op):
    SELFTYPE, methname, args_v = decompose_oosend(op)
    _, meth = SELFTYPE._lookup(methname)
    return SELFTYPE, methname, meth
