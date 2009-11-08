from pypy.rpython.lltypesystem import lltype, rffi
from pypy.jit.backend.llsupport.descr import *
from pypy.jit.backend.llsupport import symbolic
from pypy.rlib.objectmodel import Symbolic


def test_get_size_descr():
    c0 = GcCache(False)
    c1 = GcCache(True)
    T = lltype.GcStruct('T')
    S = lltype.GcStruct('S', ('x', lltype.Char),
                             ('y', lltype.Ptr(T)))
    descr_s = get_size_descr(c0, S)
    descr_t = get_size_descr(c0, T)
    assert descr_s.size == symbolic.get_size(S, False)
    assert descr_t.size == symbolic.get_size(T, False)
    assert descr_s == get_size_descr(c0, S)
    assert descr_s != get_size_descr(c1, S)
    #
    descr_s = get_size_descr(c1, S)
    assert isinstance(descr_s.size, Symbolic)


def test_get_field_descr():
    U = lltype.Struct('U')
    T = lltype.GcStruct('T')
    S = lltype.GcStruct('S', ('x', lltype.Char),
                             ('y', lltype.Ptr(T)),
                             ('z', lltype.Ptr(U)),
                             ('f', lltype.Float))
    assert getFieldDescrClass(lltype.Ptr(T)) is GcPtrFieldDescr
    assert getFieldDescrClass(lltype.Ptr(U)) is NonGcPtrFieldDescr
    cls = getFieldDescrClass(lltype.Char)
    assert cls != getFieldDescrClass(lltype.Signed)
    assert cls == getFieldDescrClass(lltype.Char)
    clsf = getFieldDescrClass(lltype.Float)
    assert clsf != cls
    assert clsf == getFieldDescrClass(lltype.Float)
    #
    c0 = GcCache(False)
    c1 = GcCache(True)
    assert get_field_descr(c0, S, 'y') == get_field_descr(c0, S, 'y')
    assert get_field_descr(c0, S, 'y') != get_field_descr(c1, S, 'y')
    for tsc in [False, True]:
        c2 = GcCache(tsc)
        descr_x = get_field_descr(c2, S, 'x')
        descr_y = get_field_descr(c2, S, 'y')
        descr_z = get_field_descr(c2, S, 'z')
        descr_f = get_field_descr(c2, S, 'f')
        assert descr_x.__class__ is cls
        assert descr_y.__class__ is GcPtrFieldDescr
        assert descr_z.__class__ is NonGcPtrFieldDescr
        assert descr_f.__class__ is clsf
        if not tsc:
            assert descr_x.offset < descr_y.offset < descr_z.offset
            assert descr_x.sort_key() < descr_y.sort_key() < descr_z.sort_key()
            assert descr_x.get_field_size(False) == rffi.sizeof(lltype.Char)
            assert descr_y.get_field_size(False) == rffi.sizeof(lltype.Ptr(T))
            assert descr_z.get_field_size(False) == rffi.sizeof(lltype.Ptr(U))
            assert descr_f.get_field_size(False) == rffi.sizeof(lltype.Float)
        else:
            assert isinstance(descr_x.offset, Symbolic)
            assert isinstance(descr_y.offset, Symbolic)
            assert isinstance(descr_z.offset, Symbolic)
            assert isinstance(descr_f.offset, Symbolic)
            assert isinstance(descr_x.get_field_size(True), Symbolic)
            assert isinstance(descr_y.get_field_size(True), Symbolic)
            assert isinstance(descr_z.get_field_size(True), Symbolic)
            assert isinstance(descr_f.get_field_size(True), Symbolic)
        assert not descr_x.is_pointer_field()
        assert     descr_y.is_pointer_field()
        assert not descr_z.is_pointer_field()
        assert not descr_f.is_pointer_field()
        assert not descr_x.is_float_field()
        assert not descr_y.is_float_field()
        assert not descr_z.is_float_field()
        assert     descr_f.is_float_field()


def test_get_array_descr():
    U = lltype.Struct('U')
    T = lltype.GcStruct('T')
    A1 = lltype.GcArray(lltype.Char)
    A2 = lltype.GcArray(lltype.Ptr(T))
    A3 = lltype.GcArray(lltype.Ptr(U))
    A4 = lltype.GcArray(lltype.Float)
    assert getArrayDescrClass(A2) is GcPtrArrayDescr
    assert getArrayDescrClass(A3) is NonGcPtrArrayDescr
    cls = getArrayDescrClass(A1)
    assert cls != getArrayDescrClass(lltype.GcArray(lltype.Signed))
    assert cls == getArrayDescrClass(lltype.GcArray(lltype.Char))
    clsf = getArrayDescrClass(A4)
    assert clsf != cls
    assert clsf == getArrayDescrClass(lltype.GcArray(lltype.Float))
    #
    c0 = GcCache(False)
    descr1 = get_array_descr(c0, A1)
    descr2 = get_array_descr(c0, A2)
    descr3 = get_array_descr(c0, A3)
    descr4 = get_array_descr(c0, A4)
    assert descr1.__class__ is cls
    assert descr2.__class__ is GcPtrArrayDescr
    assert descr3.__class__ is NonGcPtrArrayDescr
    assert descr4.__class__ is clsf
    assert descr1 == get_array_descr(c0, lltype.GcArray(lltype.Char))
    assert not descr1.is_array_of_pointers()
    assert     descr2.is_array_of_pointers()
    assert not descr3.is_array_of_pointers()
    assert not descr4.is_array_of_pointers()
    assert not descr1.is_array_of_floats()
    assert not descr2.is_array_of_floats()
    assert not descr3.is_array_of_floats()
    assert     descr4.is_array_of_floats()
    #
    WORD = rffi.sizeof(lltype.Signed)
    assert descr1.get_base_size(False) == WORD
    assert descr2.get_base_size(False) == WORD
    assert descr3.get_base_size(False) == WORD
    assert descr4.get_base_size(False) == WORD
    assert descr1.get_ofs_length(False) == 0
    assert descr2.get_ofs_length(False) == 0
    assert descr3.get_ofs_length(False) == 0
    assert descr4.get_ofs_length(False) == 0
    assert descr1.get_item_size(False) == rffi.sizeof(lltype.Char)
    assert descr2.get_item_size(False) == rffi.sizeof(lltype.Ptr(T))
    assert descr3.get_item_size(False) == rffi.sizeof(lltype.Ptr(U))
    assert descr4.get_item_size(False) == rffi.sizeof(lltype.Float)
    #
    assert isinstance(descr1.get_base_size(True), Symbolic)
    assert isinstance(descr2.get_base_size(True), Symbolic)
    assert isinstance(descr3.get_base_size(True), Symbolic)
    assert isinstance(descr4.get_base_size(True), Symbolic)
    assert isinstance(descr1.get_ofs_length(True), Symbolic)
    assert isinstance(descr2.get_ofs_length(True), Symbolic)
    assert isinstance(descr3.get_ofs_length(True), Symbolic)
    assert isinstance(descr4.get_ofs_length(True), Symbolic)
    assert isinstance(descr1.get_item_size(True), Symbolic)
    assert isinstance(descr2.get_item_size(True), Symbolic)
    assert isinstance(descr3.get_item_size(True), Symbolic)
    assert isinstance(descr4.get_item_size(True), Symbolic)


def test_get_call_descr_not_translated():
    c0 = GcCache(False)
    descr1 = get_call_descr(c0, [lltype.Char, lltype.Signed], lltype.Char)
    assert descr1.get_result_size(False) == rffi.sizeof(lltype.Char)
    assert not descr1.returns_a_pointer()
    assert not descr1.returns_a_float()
    assert descr1.arg_classes == "ii"
    #
    T = lltype.GcStruct('T')
    descr2 = get_call_descr(c0, [lltype.Ptr(T)], lltype.Ptr(T))
    assert descr2.get_result_size(False) == rffi.sizeof(lltype.Ptr(T))
    assert descr2.returns_a_pointer()
    assert not descr2.returns_a_float()
    assert descr2.arg_classes == "r"
    #
    U = lltype.GcStruct('U', ('x', lltype.Signed))
    assert descr2 == get_call_descr(c0, [lltype.Ptr(U)], lltype.Ptr(U))
    #
    descr4 = get_call_descr(c0, [lltype.Float, lltype.Float], lltype.Float)
    assert descr4.get_result_size(False) == rffi.sizeof(lltype.Float)
    assert not descr4.returns_a_pointer()
    assert descr4.returns_a_float()
    assert descr4.arg_classes == "ff"

def test_get_call_descr_translated():
    c1 = GcCache(True)
    T = lltype.GcStruct('T')
    U = lltype.GcStruct('U', ('x', lltype.Signed))
    descr3 = get_call_descr(c1, [lltype.Ptr(T)], lltype.Ptr(U))
    assert isinstance(descr3.get_result_size(True), Symbolic)
    assert descr3.returns_a_pointer()
    assert not descr3.returns_a_float()
    assert descr3.arg_classes == "r"
    #
    descr4 = get_call_descr(c1, [lltype.Float, lltype.Float], lltype.Float)
    assert isinstance(descr4.get_result_size(True), Symbolic)
    assert not descr4.returns_a_pointer()
    assert descr4.returns_a_float()
    assert descr4.arg_classes == "ff"

def test_call_descr_extra_info():
    c1 = GcCache(True)
    T = lltype.GcStruct('T')
    U = lltype.GcStruct('U', ('x', lltype.Signed))
    descr1 = get_call_descr(c1, [lltype.Ptr(T)], lltype.Ptr(U), "hello")
    extrainfo = descr1.get_extra_info()
    assert extrainfo == "hello"
    descr2 = get_call_descr(c1, [lltype.Ptr(T)], lltype.Ptr(U), "hello")
    assert descr1 is descr2
    descr3 = get_call_descr(c1, [lltype.Ptr(T)], lltype.Ptr(U))
    extrainfo = descr3.get_extra_info()
    assert extrainfo is None


def test_repr_of_descr():
    c0 = GcCache(False)
    T = lltype.GcStruct('T')
    S = lltype.GcStruct('S', ('x', lltype.Char),
                             ('y', lltype.Ptr(T)),
                             ('z', lltype.Ptr(T)))
    descr1 = get_size_descr(c0, S)
    s = symbolic.get_size(S, False)
    assert descr1.repr_of_descr() == '<SizeDescr %d>' % s
    #
    descr2 = get_field_descr(c0, S, 'y')
    o, _ = symbolic.get_field_token(S, 'y', False)
    assert descr2.repr_of_descr() == '<GcPtrFieldDescr %d>' % o
    #
    descr2i = get_field_descr(c0, S, 'x')
    o, _ = symbolic.get_field_token(S, 'x', False)
    assert descr2i.repr_of_descr() == '<CharFieldDescr %d>' % o
    #
    descr3 = get_array_descr(c0, lltype.GcArray(lltype.Ptr(S)))
    assert descr3.repr_of_descr() == '<GcPtrArrayDescr>'
    #
    descr3i = get_array_descr(c0, lltype.GcArray(lltype.Char))
    assert descr3i.repr_of_descr() == '<CharArrayDescr>'
    #
    cache = {}
    descr4 = get_call_descr(c0, [lltype.Char, lltype.Ptr(S)], lltype.Ptr(S))
    assert 'GcPtrCallDescr' in descr4.repr_of_descr()
    #
    descr4i = get_call_descr(c0, [lltype.Char, lltype.Ptr(S)], lltype.Char)
    assert 'CharCallDescr' in descr4i.repr_of_descr()
    #
    descr4f = get_call_descr(c0, [lltype.Char, lltype.Ptr(S)], lltype.Float)
    assert 'FloatCallDescr' in descr4f.repr_of_descr()
