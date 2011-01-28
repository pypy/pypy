from pypy.rpython.lltypesystem import lltype
from pypy.translator.unsimplify import varoftype
from pypy.objspace.flow.model import Constant, SpaceOperation

from pypy.jit.codewriter.jtransform import Transformer, NotSupported
from pypy.jit.codewriter.flatten import GraphFlattener
from pypy.jit.codewriter.format import assert_format
from pypy.jit.codewriter.test.test_flatten import fake_regallocs
from pypy.jit.metainterp.history import AbstractDescr

# ____________________________________________________________

FIXEDLIST = lltype.Ptr(lltype.GcArray(lltype.Signed))
VARLIST = lltype.Ptr(lltype.GcStruct('VARLIST',
                                     ('length', lltype.Signed),
                                     ('items', FIXEDLIST),
                                     adtmeths={"ITEM": lltype.Signed}))

class FakeCPU:
    class arraydescrof(AbstractDescr):
        def __init__(self, ARRAY):
            assert ARRAY.OF != lltype.Void
            self.ARRAY = ARRAY
        def __repr__(self):
            return '<ArrayDescr>'
    class fielddescrof(AbstractDescr):
        def __init__(self, STRUCT, fieldname):
            self.STRUCT = STRUCT
            self.fieldname = fieldname
        def __repr__(self):
            return '<FieldDescr %s>' % self.fieldname
    class sizeof(AbstractDescr):
        def __init__(self, STRUCT):
            self.STRUCT = STRUCT
        def __repr__(self):
            return '<SizeDescr>'

class FakeCallControl:
    class getcalldescr(AbstractDescr):
        def __init__(self, op, oopspecindex=0, extraeffect=None):
            self.op = op
            self.oopspecindex = oopspecindex
        def __repr__(self):
            if self.oopspecindex == 0:
                return '<CallDescr>'
            else:
                return '<CallDescrOS%d>' % self.oopspecindex
    def calldescr_canraise(self, calldescr):
        return False

def builtin_test(oopspec_name, args, RESTYPE, expected):
    v_result = varoftype(RESTYPE)
    tr = Transformer(FakeCPU(), FakeCallControl())
    tr.immutable_arrays = {}
    tr.vable_array_vars = {}
    if '/' in oopspec_name:
        oopspec_name, property = oopspec_name.split('/')
        def force_flags(op):
            if property == 'NONNEG':   return True
            if property == 'NEG':      return False
            raise ValueError(property)
        tr._get_list_nonneg_canraise_flags = force_flags
    op = SpaceOperation('direct_call',
                        [Constant("myfunc", lltype.Void)] + args,
                        v_result)
    try:
        oplist = tr._handle_list_call(op, oopspec_name, args)
    except NotSupported:
        assert expected is NotSupported
    else:
        assert expected is not NotSupported
        assert oplist is not None
        flattener = GraphFlattener(None, fake_regallocs())
        if not isinstance(oplist, list):
            oplist = [oplist]
        for op1 in oplist:
            flattener.serialize_op(op1)
        assert_format(flattener.ssarepr, expected)

# ____________________________________________________________
# Fixed lists

def test_newlist():
    builtin_test('newlist', [], FIXEDLIST,
                 """new_array <ArrayDescr>, $0 -> %r0""")
    builtin_test('newlist', [Constant(5, lltype.Signed)], FIXEDLIST,
                 """new_array <ArrayDescr>, $5 -> %r0""")
    builtin_test('newlist', [varoftype(lltype.Signed)], FIXEDLIST,
                 """new_array <ArrayDescr>, %i0 -> %r0""")
    builtin_test('newlist', [Constant(5, lltype.Signed),
                             Constant(0, lltype.Signed)], FIXEDLIST,
                 """new_array <ArrayDescr>, $5 -> %r0""")
    builtin_test('newlist', [Constant(5, lltype.Signed),
                             Constant(1, lltype.Signed)], FIXEDLIST,
                 NotSupported)
    builtin_test('newlist', [Constant(5, lltype.Signed),
                             varoftype(lltype.Signed)], FIXEDLIST,
                 NotSupported)

def test_fixed_ll_arraycopy():
    builtin_test('list.ll_arraycopy',
                 [varoftype(FIXEDLIST),
                  varoftype(FIXEDLIST),
                  varoftype(lltype.Signed), 
                  varoftype(lltype.Signed), 
                  varoftype(lltype.Signed)],
                 lltype.Void, """
                     residual_call_ir_v $'myfunc', <CallDescrOS1>, I[%i0, %i1, %i2], R[%r0, %r1]
                 """)

def test_fixed_getitem():
    builtin_test('list.getitem/NONNEG',
                 [varoftype(FIXEDLIST), varoftype(lltype.Signed)],
                 lltype.Signed, """
                     getarrayitem_gc_i %r0, <ArrayDescr>, %i0 -> %i1
                 """)
    builtin_test('list.getitem/NEG',
                 [varoftype(FIXEDLIST), varoftype(lltype.Signed)],
                 lltype.Signed, """
                     -live-
                     check_neg_index %r0, <ArrayDescr>, %i0 -> %i1
                     getarrayitem_gc_i %r0, <ArrayDescr>, %i1 -> %i2
                 """)

def test_fixed_getitem_foldable():
    builtin_test('list.getitem_foldable/NONNEG',
                 [varoftype(FIXEDLIST), varoftype(lltype.Signed)],
                 lltype.Signed, """
                     getarrayitem_gc_pure_i %r0, <ArrayDescr>, %i0 -> %i1
                 """)
    builtin_test('list.getitem_foldable/NEG',
                 [varoftype(FIXEDLIST), varoftype(lltype.Signed)],
                 lltype.Signed, """
                     -live-
                     check_neg_index %r0, <ArrayDescr>, %i0 -> %i1
                     getarrayitem_gc_pure_i %r0, <ArrayDescr>, %i1 -> %i2
                 """)

def test_fixed_setitem():
    builtin_test('list.setitem/NONNEG', [varoftype(FIXEDLIST),
                                         varoftype(lltype.Signed),
                                         varoftype(lltype.Signed)],
                 lltype.Void, """
                     setarrayitem_gc_i %r0, <ArrayDescr>, %i0, %i1
                 """)
    builtin_test('list.setitem/NEG', [varoftype(FIXEDLIST),
                                      varoftype(lltype.Signed),
                                      varoftype(lltype.Signed)],
                 lltype.Void, """
                     -live-
                     check_neg_index %r0, <ArrayDescr>, %i0 -> %i1
                     setarrayitem_gc_i %r0, <ArrayDescr>, %i1, %i2
                 """)

def test_fixed_len():
    builtin_test('list.len', [varoftype(FIXEDLIST)], lltype.Signed,
                 """arraylen_gc %r0, <ArrayDescr> -> %i0""")

def test_fixed_len_foldable():
    builtin_test('list.len_foldable', [varoftype(FIXEDLIST)], lltype.Signed,
                 """arraylen_gc %r0, <ArrayDescr> -> %i0""")

# ____________________________________________________________
# Resizable lists

def test_resizable_newlist():
    alldescrs = ("<SizeDescr>, <FieldDescr length>,"
                 " <FieldDescr items>, <ArrayDescr>")
    builtin_test('newlist', [], VARLIST,
                 """newlist """+alldescrs+""", $0 -> %r0""")
    builtin_test('newlist', [Constant(5, lltype.Signed)], VARLIST,
                 """newlist """+alldescrs+""", $5 -> %r0""")
    builtin_test('newlist', [varoftype(lltype.Signed)], VARLIST,
                 """newlist """+alldescrs+""", %i0 -> %r0""")
    builtin_test('newlist', [Constant(5, lltype.Signed),
                             Constant(0, lltype.Signed)], VARLIST,
                 """newlist """+alldescrs+""", $5 -> %r0""")
    builtin_test('newlist', [Constant(5, lltype.Signed),
                             Constant(1, lltype.Signed)], VARLIST,
                 NotSupported)
    builtin_test('newlist', [Constant(5, lltype.Signed),
                             varoftype(lltype.Signed)], VARLIST,
                 NotSupported)

def test_resizable_getitem():
    builtin_test('list.getitem/NONNEG',
                 [varoftype(VARLIST), varoftype(lltype.Signed)],
                 lltype.Signed, """
        getlistitem_gc_i %r0, <FieldDescr items>, <ArrayDescr>, %i0 -> %i1
                 """)
    builtin_test('list.getitem/NEG',
                 [varoftype(VARLIST), varoftype(lltype.Signed)],
                 lltype.Signed, """
        -live-
        check_resizable_neg_index %r0, <FieldDescr length>, %i0 -> %i1
        getlistitem_gc_i %r0, <FieldDescr items>, <ArrayDescr>, %i1 -> %i2
                 """)

def test_resizable_setitem():
    builtin_test('list.setitem/NONNEG', [varoftype(VARLIST),
                                         varoftype(lltype.Signed),
                                         varoftype(lltype.Signed)],
                 lltype.Void, """
        setlistitem_gc_i %r0, <FieldDescr items>, <ArrayDescr>, %i0, %i1
                 """)
    builtin_test('list.setitem/NEG', [varoftype(VARLIST),
                                      varoftype(lltype.Signed),
                                      varoftype(lltype.Signed)],
                 lltype.Void, """
        -live-
        check_resizable_neg_index %r0, <FieldDescr length>, %i0 -> %i1
        setlistitem_gc_i %r0, <FieldDescr items>, <ArrayDescr>, %i1, %i2
                 """)

def test_resizable_len():
    builtin_test('list.len', [varoftype(VARLIST)], lltype.Signed,
                 """getfield_gc_i %r0, <FieldDescr length> -> %i0""")

def test_resizable_unsupportedop():
    builtin_test('list.foobar', [varoftype(VARLIST)], lltype.Signed,
                 NotSupported)
