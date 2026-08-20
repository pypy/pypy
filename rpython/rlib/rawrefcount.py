#
#  See documentation in pypy/doc/discussion/rawrefcount.rst
#
#  This is meant for pypy's cpyext module, but is a generally
#  useful interface over our GC.  XXX "pypy" should be removed here
#
import sys, weakref, py
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.rlib.objectmodel import we_are_translated, specialize, not_rpython
from rpython.rtyper.extregistry import ExtRegistryEntry
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.rlib import rgc
from rpython.rlib.rarithmetic import UINT_MAX

# Immortality lives in the LOW bits of ob_refcnt, orthogonal to the
# REFCNT_FROM_PYPY "has prefix" tag in the high bits (see the table in
# pypy/doc/discussion/rawrefcount.rst).  _Py_IMMORTAL_REFCNT is CPython 3.12's
# value on both widths (UINT_MAX on 64-bit, UINT_MAX >> 2 on 32-bit); the tag
# is placed above the immortal field so that an immortalized owned object,
# ob_refcnt = REFCNT_FROM_PYPY + _Py_IMMORTAL_REFCNT, keeps both patterns
# intact.  On 32-bit the immortal field is 30 bits wide, which forces
# REFCNT_FROM_PYPY up to bit 30 and squeezes REFCNT_FROM_PYPY_LIGHT (a region
# never actually created in pypy3, only exercised by rawrefcount's own tests).
# Prefix-less immortals (bare statics) carry exactly _Py_IMMORTAL_REFCNT and
# are mapped out-of-band (cpyext State.static_py2w/static_w2py).
# Py_INCREF/Py_DECREF and the interp-level incref/decref no-op on immortals,
# so the value never drifts.
if sys.maxint > 2**32:
    REFCNT_FROM_PYPY       = sys.maxint // 4 + 1
    REFCNT_FROM_PYPY_LIGHT = REFCNT_FROM_PYPY + (sys.maxint // 2 + 1)
    _Py_IMMORTAL_REFCNT    = rffi.cast(lltype.Signed, UINT_MAX)
    def refcnt_is_immortal(rc):
        # CPython's 64-bit check: bit 31 (the sign of the low 32 bits) is set
        return (rc & (1 << 31)) != 0
else:
    REFCNT_FROM_PYPY       = 0x40000000
    REFCNT_FROM_PYPY_LIGHT = 0x70000000
    _Py_IMMORTAL_REFCNT    = rffi.cast(lltype.Signed, UINT_MAX >> 2)
    def refcnt_is_immortal(rc):
        # mask-equality instead of CPython's plain equality, so the check also
        # catches REFCNT_FROM_PYPY-tagged immortals; identical to CPython for
        # untagged (foreign) objects
        return (rc & _Py_IMMORTAL_REFCNT) == _Py_IMMORTAL_REFCNT

RAWREFCOUNT_DEALLOC_TRIGGER = lltype.Ptr(lltype.FuncType([], lltype.Void))


# Keep in sync with pypy/goal/targetpypystandalone.py and
# rpython/config/translationoption.py's rawrefcount_link_prefix.
RRC_LINK_PREFIX = True

_LINK_OFFSET = rffi.sizeof(lltype.Signed)   # bytes back from body to ob_pypy_link
_LINK_PREFIX = 16   # padded to 16 so body (ob_refcnt) keeps malloc's 16-byte alignment

if RRC_LINK_PREFIX:
    def _ob_link_get(ob):
        base = rffi.ptradd(rffi.cast(rffi.CCHARP, ob), -_LINK_OFFSET)
        return rffi.cast(rffi.CArrayPtr(lltype.Signed), base)[0]

    def _ob_link_set(ob, value):
        base = rffi.ptradd(rffi.cast(rffi.CCHARP, ob), -_LINK_OFFSET)
        rffi.cast(rffi.CArrayPtr(lltype.Signed), base)[0] = value

    def _ob_free(ob, track_allocation=True):
        # free the whole allocation, which starts at the hidden prefix.  Address
        # arithmetic (not ptradd) so ll2ctypes maps the base back to the malloc.
        base = rffi.cast(rffi.VOIDP, rffi.cast(lltype.Signed, ob) - _LINK_PREFIX)
        lltype.free(base, flavor='raw', track_allocation=track_allocation)

    # Canonical test PyObject: the visible CPython header.  ob_pypy_link is NOT a
    # field here -- it lives in the hidden prefix reserved by _pyobject_alloc,
    # reached at ob-8.
    PyObjectS = lltype.Struct('PyObjectS',
                              ('c_ob_refcnt', lltype.Signed),
                              ('c_ob_type', lltype.Signed))
    PyObject = lltype.Ptr(PyObjectS)

    # Allocation layout: padding, then the hidden link word, then the visible
    # PyObjectS.  Handing back a pointer to .body reserves the prefix at
    # body-_LINK_PREFIX, matching pyobj_raw_alloc.
    _PyObjectPrefixedS = lltype.Struct('_PyObjectPrefixedS',
                                       ('pad', lltype.Signed),
                                       ('ob_pypy_link', lltype.Signed),
                                       ('body', PyObjectS))

    def _pyobject_alloc(track_allocation=True, immortal=False):
        "Allocate a PyObjectS with the hidden link prefix reserved (see pyobj_raw_alloc)."
        full = lltype.malloc(_PyObjectPrefixedS, flavor='raw', zero=True,
                             immortal=immortal,
                             track_allocation=track_allocation and not immortal)
        return rffi.cast(PyObject, rffi.cast(lltype.Signed, full) + _LINK_PREFIX)

else:
    def _ob_link_get(ob):
        return ob.c_ob_pypy_link

    def _ob_link_set(ob, value):
        ob.c_ob_pypy_link = value

    def _ob_free(ob, track_allocation=True):
        lltype.free(ob, flavor='raw', track_allocation=track_allocation)

    # Canonical test PyObject: ob_pypy_link is a plain header field, PyPy's
    # traditional (pre-abi3) layout -- no hidden prefix.
    PyObjectS = lltype.Struct('PyObjectS',
                              ('c_ob_refcnt', lltype.Signed),
                              ('c_ob_pypy_link', lltype.Signed))
    PyObject = lltype.Ptr(PyObjectS)

    def _pyobject_alloc(track_allocation=True, immortal=False):
        "Allocate a PyObjectS; ob_pypy_link is just a field, no hidden prefix."
        return lltype.malloc(PyObjectS, flavor='raw', zero=True,
                             immortal=immortal,
                             track_allocation=track_allocation and not immortal)


def _build_pypy_link(p):
    res = len(_adr2pypy)
    _adr2pypy.append(p)
    return res


@not_rpython
def init(dealloc_trigger_callback=None):
    """set up rawrefcount with the GC.  This is only used
    for tests; it should not be called at all during translation.
    """
    global _p_list, _o_list, _adr2pypy, _pypy2ob, _pypy2ob_rev
    global _d_list, _dealloc_trigger_callback
    _p_list = []
    _o_list = []
    _adr2pypy = [None]
    _pypy2ob = {}
    _pypy2ob_rev = {}
    _d_list = []
    _d_marker = None
    _dealloc_trigger_callback = dealloc_trigger_callback

@not_rpython
def create_link_pypy(p, ob):
    "a link where the PyPy object contains some or all the data"
    #print 'create_link_pypy\n\t%s\n\t%s' % (p, ob)
    assert p not in _pypy2ob
    assert ob._obj not in _pypy2ob_rev
    assert not _ob_link_get(ob)
    _ob_link_set(ob, _build_pypy_link(p))
    _pypy2ob[p] = ob
    _pypy2ob_rev[ob._obj] = p
    _p_list.append(ob)

@not_rpython
def create_link_pyobj(p, ob):
    """a link where the PyObject contains all the data.
       from_obj() will not work on this 'p'."""
    #print 'create_link_pyobj\n\t%s\n\t%s' % (p, ob)
    assert p not in _pypy2ob
    assert ob._obj not in _pypy2ob_rev
    assert not _ob_link_get(ob)
    _ob_link_set(ob, _build_pypy_link(p))
    _o_list.append(ob)

@not_rpython
def mark_deallocating(marker, ob):
    """mark the PyObject as deallocating, by storing 'marker'
    inside its ob_pypy_link field"""
    assert ob._obj not in _pypy2ob_rev
    assert not _ob_link_get(ob)
    _ob_link_set(ob, _build_pypy_link(marker))

@not_rpython
def from_obj(OB_PTR_TYPE, p):
    ob = _pypy2ob.get(p)
    if ob is None:
        return lltype.nullptr(OB_PTR_TYPE.TO)
    assert lltype.typeOf(ob) == OB_PTR_TYPE
    assert _pypy2ob_rev[ob._obj] is p
    return ob

@not_rpython
def to_obj(Class, ob):
    link = _ob_link_get(ob)
    if link == 0:
        return None
    p = _adr2pypy[link]
    assert isinstance(p, Class)
    return p

@not_rpython
def next_dead(OB_PTR_TYPE):
    """When the GC runs, it finds some pyobjs to be dead
    but cannot immediately dispose of them (it doesn't know how to call
    e.g. tp_dealloc(), and anyway calling it immediately would cause all
    sorts of bugs).  So instead, it stores them in an internal list,
    initially with refcnt == REFCNT_FROM_PYPY + 1.  This pops the next item off
    this list.
    """
    if len(_d_list) == 0:
        return lltype.nullptr(OB_PTR_TYPE.TO)
    ob = _d_list.pop()
    assert lltype.typeOf(ob) == OB_PTR_TYPE
    return ob

@not_rpython
def _collect(track_allocation=True):
    """for tests only.  Emulates a GC collection.
    Will invoke dealloc_trigger_callback() once if there are objects
    whose _Py_Dealloc() should be called.
    """
    def detach(ob, wr_list):
        assert ob.c_ob_refcnt >= REFCNT_FROM_PYPY
        assert _ob_link_get(ob)
        p = _adr2pypy[_ob_link_get(ob)]
        assert p is not None
        _adr2pypy[_ob_link_get(ob)] = None
        wr_list.append((ob, weakref.ref(p)))
        return p

    global _p_list, _o_list
    wr_p_list = []
    new_p_list = []
    for ob in reversed(_p_list):
        if refcnt_is_immortal(ob.c_ob_refcnt):
            new_p_list.append(ob)   # immortal: never dies
        elif ob.c_ob_refcnt not in (REFCNT_FROM_PYPY, REFCNT_FROM_PYPY_LIGHT):
            new_p_list.append(ob)
        else:
            p = detach(ob, wr_p_list)
            ob_test = _pypy2ob.pop(p)
            p_test = _pypy2ob_rev.pop(ob_test._obj)
            assert p_test is p
            del p, p_test
        ob = None
    _p_list = Ellipsis

    wr_o_list = []
    new_o_list = []
    for ob in reversed(_o_list):
        if refcnt_is_immortal(ob.c_ob_refcnt):
            new_o_list.append(ob)   # immortal: never dies
        else:
            detach(ob, wr_o_list)
    _o_list = Ellipsis

    rgc.collect()  # forces the cycles to be resolved and the weakrefs to die
    rgc.collect()
    rgc.collect()

    def attach(ob, wr, final_list):
        assert ob.c_ob_refcnt >= REFCNT_FROM_PYPY
        p = wr()
        if p is not None:
            assert _ob_link_get(ob)
            _adr2pypy[_ob_link_get(ob)] = p
            final_list.append(ob)
            return p
        else:
            _ob_link_set(ob, 0)
            if ob.c_ob_refcnt >= REFCNT_FROM_PYPY_LIGHT:
                ob.c_ob_refcnt -= REFCNT_FROM_PYPY_LIGHT
                if ob.c_ob_refcnt == 0:
                    _ob_free(ob, track_allocation=track_allocation)
            else:
                assert ob.c_ob_refcnt >= REFCNT_FROM_PYPY
                assert ob.c_ob_refcnt < int(REFCNT_FROM_PYPY_LIGHT * 0.99)
                if ob.c_ob_refcnt == REFCNT_FROM_PYPY:
                    ob.c_ob_refcnt += 1
                    _d_list.append(ob)
            return None

    _p_list = new_p_list
    for ob, wr in wr_p_list:
        p = attach(ob, wr, _p_list)
        if p is not None:
            _pypy2ob[p] = ob
    _pypy2ob_rev.clear()       # rebuild this dict from scratch
    for p, ob in _pypy2ob.items():
        assert ob._obj not in _pypy2ob_rev
        _pypy2ob_rev[ob._obj] = p
    _o_list = new_o_list
    for ob, wr in wr_o_list:
        attach(ob, wr, _o_list)

    if _d_list:
        res = _dealloc_trigger_callback()
        if res == "RETRY":
            _collect(track_allocation=track_allocation)

_keepalive_forever = set()
def _dont_free_any_more():
    "Make sure that any object still referenced won't be freed any more."
    for ob in _p_list + _o_list:
        _keepalive_forever.add(to_obj(object, ob))
    del _d_list[:]

# ____________________________________________________________


def _unspec_p(hop, v_p):
    assert isinstance(v_p.concretetype, lltype.Ptr)
    assert v_p.concretetype.TO._gckind == 'gc'
    return hop.genop('cast_opaque_ptr', [v_p], resulttype=llmemory.GCREF)

def _unspec_ob(hop, v_ob):
    assert isinstance(v_ob.concretetype, lltype.Ptr)
    assert v_ob.concretetype.TO._gckind == 'raw'
    return hop.genop('cast_ptr_to_adr', [v_ob], resulttype=llmemory.Address)

def _spec_p(hop, v_p):
    assert v_p.concretetype == llmemory.GCREF
    return hop.genop('cast_opaque_ptr', [v_p],
                     resulttype=hop.r_result.lowleveltype)

def _spec_ob(hop, v_ob):
    assert v_ob.concretetype == llmemory.Address
    return hop.genop('cast_adr_to_ptr', [v_ob],
                     resulttype=hop.r_result.lowleveltype)


class Entry(ExtRegistryEntry):
    _about_ = init

    def compute_result_annotation(self, s_dealloc_callback):
        from rpython.rtyper.llannotation import SomePtr
        assert isinstance(s_dealloc_callback, SomePtr)   # ll-ptr-to-function

    def specialize_call(self, hop):
        hop.exception_cannot_occur()
        [v_dealloc_callback] = hop.inputargs(hop.args_r[0])
        hop.genop('gc_rawrefcount_init', [v_dealloc_callback])


class Entry(ExtRegistryEntry):
    _about_ = (create_link_pypy, create_link_pyobj, mark_deallocating)

    def compute_result_annotation(self, s_p, s_ob):
        pass

    def specialize_call(self, hop):
        if self.instance is create_link_pypy:
            name = 'gc_rawrefcount_create_link_pypy'
        elif self.instance is create_link_pyobj:
            name = 'gc_rawrefcount_create_link_pyobj'
        elif self.instance is mark_deallocating:
            name = 'gc_rawrefcount_mark_deallocating'
        v_p, v_ob = hop.inputargs(*hop.args_r)
        hop.exception_cannot_occur()
        hop.genop(name, [_unspec_p(hop, v_p), _unspec_ob(hop, v_ob)])
        #
        if hop.rtyper.annotator.translator.config.translation.gc == "boehm":
            c_func = hop.inputconst(lltype.typeOf(func_boehm_eci),
                                    func_boehm_eci)
            hop.genop('direct_call', [c_func])


class Entry(ExtRegistryEntry):
    _about_ = from_obj

    def compute_result_annotation(self, s_OB_PTR_TYPE, s_p):
        from rpython.annotator import model as annmodel
        from rpython.rtyper.llannotation import lltype_to_annotation
        assert (isinstance(s_p, annmodel.SomeInstance) or
                    annmodel.s_None.contains(s_p))
        assert s_OB_PTR_TYPE.is_constant()
        return lltype_to_annotation(s_OB_PTR_TYPE.const)

    def specialize_call(self, hop):
        hop.exception_cannot_occur()
        v_p = hop.inputarg(hop.args_r[1], arg=1)
        v_ob = hop.genop('gc_rawrefcount_from_obj', [_unspec_p(hop, v_p)],
                         resulttype = llmemory.Address)
        return _spec_ob(hop, v_ob)

class Entry(ExtRegistryEntry):
    _about_ = to_obj

    def compute_result_annotation(self, s_Class, s_ob):
        from rpython.annotator import model as annmodel
        from rpython.rtyper.llannotation import SomePtr
        assert isinstance(s_ob, SomePtr)
        assert s_Class.is_constant()
        classdef = self.bookkeeper.getuniqueclassdef(s_Class.const)
        return annmodel.SomeInstance(classdef, can_be_None=True)

    def specialize_call(self, hop):
        hop.exception_cannot_occur()
        v_ob = hop.inputarg(hop.args_r[1], arg=1)
        v_p = hop.genop('gc_rawrefcount_to_obj', [_unspec_ob(hop, v_ob)],
                        resulttype = llmemory.GCREF)
        return _spec_p(hop, v_p)

class Entry(ExtRegistryEntry):
    _about_ = next_dead

    def compute_result_annotation(self, s_OB_PTR_TYPE):
        from rpython.annotator import model as annmodel
        from rpython.rtyper.llannotation import lltype_to_annotation
        assert s_OB_PTR_TYPE.is_constant()
        return lltype_to_annotation(s_OB_PTR_TYPE.const)

    def specialize_call(self, hop):
        hop.exception_cannot_occur()
        v_ob = hop.genop('gc_rawrefcount_next_dead', [],
                         resulttype = llmemory.Address)
        return _spec_ob(hop, v_ob)

src_dir = py.path.local(__file__).dirpath() / 'src'
boehm_eci = ExternalCompilationInfo(
    pre_include_bits       = ['#define RRC_LINK_PREFIX %d' % int(RRC_LINK_PREFIX)],
    post_include_bits     = [(src_dir / 'boehm-rawrefcount.h').read()],
    separate_module_files = [(src_dir / 'boehm-rawrefcount.c')],
)
func_boehm_eci = rffi.llexternal_use_eci(boehm_eci)
