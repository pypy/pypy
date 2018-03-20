#
#  See documentation in pypy/doc/discussion/rawrefcount.rst
#
#  This is meant for pypy's cpyext module, but is a generally
#  useful interface over our GC.  XXX "pypy" should be removed here
#
import sys, weakref, py, math
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.rlib.objectmodel import we_are_translated, specialize, not_rpython
from rpython.rtyper.extregistry import ExtRegistryEntry
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.rlib import rgc, objectmodel
from pypy.interpreter.baseobjspace import W_Root


MAX_BIT = int(math.log(sys.maxint, 2))

# Flags
REFCNT_FROM_PYPY = 1 << MAX_BIT - 2                             # Reference from a pypy object
REFCNT_FROM_PYPY_LIGHT = (1 << MAX_BIT - 1) + REFCNT_FROM_PYPY  # Light reference from a pypy object
REFCNT_CYCLE_BUFFERED = 1 << MAX_BIT - 3                        # Object in roots buffer (for potential cycles)
REFCNT_IN_WAVEFRONT = 1 << MAX_BIT - 4                          # Object in any wavefront

# Offsets and sizes
REFCNT_CLR_OFFS = MAX_BIT - 7
REFCNT_CRC_OFFS = REFCNT_CLR_OFFS / 2
REFCNT_BITS = REFCNT_CRC_OFFS - 1

# Concurrent cycle collection colors
REFCNT_CLR_BLACK = 0 << REFCNT_CLR_OFFS   # In use or free (default)
REFCNT_CLR_GRAY = 1 << REFCNT_CLR_OFFS    # Possible member of cycle
REFCNT_CLR_YELLOW = 2 << REFCNT_CLR_OFFS  # Member of garbage cycle
REFCNT_CLR_PURPLE = 3 << REFCNT_CLR_OFFS  # Possible root of cycle
REFCNT_CLR_GREEN = 4 << REFCNT_CLR_OFFS   # Acyclic
REFCNT_CLR_ORANGE = 5 << REFCNT_CLR_OFFS  # In orange wavefront (might change to YELLOW + IN_WAVEFRONT + phase = 3)
REFCNT_CLR_MASK = 7 << REFCNT_CLR_OFFS

# Cyclic reference count with overflow bit
REFCNT_CRC_OVERFLOW = 1 << REFCNT_CRC_OFFS + REFCNT_BITS
REFCNT_CRC_MASK = (1 << REFCNT_CRC_OFFS + REFCNT_BITS + 1) - 1
REFCNT_CRC = 1 < REFCNT_CRC_OFFS

# True reference count with overflow bit
REFCNT_OVERFLOW = 1 << REFCNT_BITS
REFCNT_MASK = (1 << REFCNT_BITS + 1) - 1


RAWREFCOUNT_DEALLOC_TRIGGER = lltype.Ptr(lltype.FuncType([], lltype.Void))
W_MARKER_DEALLOCATING = W_Root()


def _build_pypy_link(p):
    res = len(_adr2pypy)
    _adr2pypy.append(p)
    return res

def incref(pyobj):
    if pyobj.c_ob_refcnt & REFCNT_OVERFLOW == 0:
        pyobj.c_ob_refcnt += 1
    else:
        if pyobj.c_ob_refcnt & REFCNT_MASK == REFCNT_OVERFLOW:
            pyobj.c_ob_refcnt += 1
            overflow_new(pyobj)
        else:
            overflow_add(pyobj)

def decref(pyobj):
    if pyobj.c_ob_refcnt & REFCNT_OVERFLOW == 0:
        pyobj.c_ob_refcnt -= 1
    else:
        if pyobj.c_ob_refcnt & REFCNT_MASK == REFCNT_OVERFLOW:
            pyobj.c_ob_refcnt -= 1
        elif overflow_sub(pyobj):
            pyobj.c_ob_refcnt -= 1

_refcount_overflow = dict()

def overflow_new(obj):
    _refcount_overflow[objectmodel.current_object_addr_as_int(obj)] = 0

def overflow_add(obj):
    _refcount_overflow[objectmodel.current_object_addr_as_int(obj)] += 1

def overflow_sub(obj):
    addr = objectmodel.current_object_addr_as_int(obj)
    c = _refcount_overflow[addr]
    if c > 0:
        _refcount_overflow[addr] = c - 1
        return False
    else:
        _refcount_overflow.pop(addr)
        return True

def overflow_get(obj):
    return _refcount_overflow[objectmodel.current_object_addr_as_int(obj)]

# TODO: _cyclic_refcount_overflow = dict()

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

# def init_traverse(traverse_cpy_call):
#     global _traverse_cpy_call
#     _traverse_cpy_call = traverse_cpy_call
#
# def traverse_cpy_call(pyobj, visitproc_ptr, arg):
#     global _traverse_cpy_call
#     _traverse_cpy_call(pyobj.c_ob_type.c_tp_traverse, pyobj,
#                        visitproc_ptr, arg)

@not_rpython
def create_link_pypy(p, ob):
    "a link where the PyPy object contains some or all the data"
    #print 'create_link_pypy\n\t%s\n\t%s' % (p, ob)
    assert p not in _pypy2ob
    assert ob._obj not in _pypy2ob_rev
    assert not ob.c_ob_pypy_link
    ob.c_ob_pypy_link = _build_pypy_link(p)
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
    assert not ob.c_ob_pypy_link
    ob.c_ob_pypy_link = _build_pypy_link(p)
    _o_list.append(ob)

@not_rpython
def mark_deallocating(marker, ob):
    """mark the PyObject as deallocating, by storing 'marker'
    inside its ob_pypy_link field"""
    assert ob._obj not in _pypy2ob_rev
    assert not ob.c_ob_pypy_link
    ob.c_ob_pypy_link = _build_pypy_link(marker)

@not_rpython
def buffer_pyobj(ob):
    pass  # TODO: implement?

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
    link = ob.c_ob_pypy_link
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
    initially with refcnt == 1.  This pops the next item off this list.
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
        assert ob.c_ob_pypy_link
        p = _adr2pypy[ob.c_ob_pypy_link]
        assert p is not None
        _adr2pypy[ob.c_ob_pypy_link] = None
        wr_list.append((ob, weakref.ref(p)))
        return p

    global _p_list, _o_list
    wr_p_list = []
    new_p_list = []
    for ob in reversed(_p_list):
        if ob.c_ob_refcnt & REFCNT_MASK > 0 \
           or ob.c_ob_refcnt & REFCNT_FROM_PYPY == 0:
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
    for ob in reversed(_o_list):
        detach(ob, wr_o_list)
    _o_list = Ellipsis

    rgc.collect()  # forces the cycles to be resolved and the weakrefs to die
    rgc.collect()
    rgc.collect()

    def attach(ob, wr, final_list):
        assert ob.c_ob_refcnt >= REFCNT_FROM_PYPY
        p = wr()
        if p is not None:
            assert ob.c_ob_pypy_link
            _adr2pypy[ob.c_ob_pypy_link] = p
            final_list.append(ob)
            return p
        else:
            ob.c_ob_pypy_link = 0
            if ob.c_ob_refcnt >= REFCNT_FROM_PYPY_LIGHT:
                ob.c_ob_refcnt -= REFCNT_FROM_PYPY_LIGHT
                ob.c_ob_pypy_link = 0
                if ob.c_ob_refcnt & REFCNT_MASK == 0 \
                   and ob.c_ob_refcnt < REFCNT_FROM_PYPY:
                    lltype.free(ob, flavor='raw',
                                track_allocation=track_allocation)
            else:
                assert ob.c_ob_refcnt >= REFCNT_FROM_PYPY
                assert ob.c_ob_refcnt < int(REFCNT_FROM_PYPY_LIGHT * 0.99)
                ob.c_ob_refcnt -= REFCNT_FROM_PYPY
                ob.c_ob_pypy_link = 0
                if ob.c_ob_refcnt & REFCNT_MASK == 0 \
                   and ob.c_ob_refcnt < REFCNT_FROM_PYPY:
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
    _o_list = []
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
    _about_ = buffer_pyobj

    def compute_result_annotation(self, s_ob):
        pass

    def specialize_call(self, hop):
        name = 'gc_rawrefcount_buffer_pyobj'
        hop.exception_cannot_occur()
        v_ob = hop.inputarg(hop.args_r[0], arg=0)
        hop.genop(name, [_unspec_ob(hop, v_ob)])

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
    post_include_bits     = [(src_dir / 'boehm-rawrefcount.h').read()],
    separate_module_files = [(src_dir / 'boehm-rawrefcount.c')],
)
func_boehm_eci = rffi.llexternal_use_eci(boehm_eci)
