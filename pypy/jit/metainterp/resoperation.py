from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.debug import make_sure_not_resized

class ResOperation(object):
    """The central ResOperation class, representing one operation."""

    # for 'guard_*'
    fail_args = None

    # debug
    name = ""
    pc = 0

    def __init__(self, opnum, args, result, descr=None):
        make_sure_not_resized(args)
        assert isinstance(opnum, int)
        self.opnum = opnum
        self.args = list(args)
        make_sure_not_resized(self.args)
        assert not isinstance(result, list)
        self.result = result
        self.setdescr(descr)

    def setdescr(self, descr):
        # for 'call', 'new', 'getfield_gc'...: the descr is a number provided
        # by the backend holding details about the type of the operation --
        # actually an instance of a class, typically Descr, that inherits
        # from AbstractDescr
        from pypy.jit.metainterp.history import check_descr
        check_descr(descr)
        self.descr = descr

    def clone(self):
        descr = self.descr
        if descr is not None:
            descr = descr._clone_if_mutable()
        op = ResOperation(self.opnum, self.args, self.result, descr)
        op.fail_args = self.fail_args
        if not we_are_translated():
            op.name = self.name
            op.pc = self.pc
        return op

    def __repr__(self):
        return self.repr()

    def repr(self):
        # RPython-friendly version
        if self.result is not None:
            sres = '%s = ' % (self.result,)
        else:
            sres = ''
        if self.name:
            prefix = "%s:%s   " % (self.name, self.pc)
        else:
            prefix = ""
        if self.descr is None or we_are_translated():
            return '%s%s%s(%s)' % (prefix, sres, self.getopname(),
                                 ', '.join([str(a) for a in self.args]))
        else:
            return '%s%s%s(%s, descr=%r)' % (prefix, sres, self.getopname(),
                            ', '.join([str(a) for a in self.args]), self.descr)

    def getopname(self):
        try:
            return opname[self.opnum].lower()
        except KeyError:
            return '<%d>' % self.opnum

    def is_guard(self):
        return rop._GUARD_FIRST <= self.opnum <= rop._GUARD_LAST

    def is_foldable_guard(self):
        return rop._GUARD_FOLDABLE_FIRST <= self.opnum <= rop._GUARD_FOLDABLE_LAST

    def is_guard_exception(self):
        return (self.opnum == rop.GUARD_EXCEPTION or
                self.opnum == rop.GUARD_NO_EXCEPTION)

    def is_guard_overflow(self):
        return (self.opnum == rop.GUARD_OVERFLOW or
                self.opnum == rop.GUARD_NO_OVERFLOW)

    def is_always_pure(self):
        return rop._ALWAYS_PURE_FIRST <= self.opnum <= rop._ALWAYS_PURE_LAST

    def has_no_side_effect(self):
        return rop._NOSIDEEFFECT_FIRST <= self.opnum <= rop._NOSIDEEFFECT_LAST

    def can_raise(self):
        return rop._CANRAISE_FIRST <= self.opnum <= rop._CANRAISE_LAST

    def is_ovf(self):
        return rop._OVF_FIRST <= self.opnum <= rop._OVF_LAST

    def is_comparison(self):
        return self.is_always_pure() and self.returns_bool_result()

    def is_final(self):
        return rop._FINAL_FIRST <= self.opnum <= rop._FINAL_LAST

    def returns_bool_result(self):
        opnum = self.opnum
        if we_are_translated():
            assert opnum >= 0
        elif opnum < 0:
            return False     # for tests
        return opboolresult[opnum]

# ____________________________________________________________

_oplist = [
    '_FINAL_FIRST',
    'JUMP',
    'FINISH',
    '_FINAL_LAST',

    '_GUARD_FIRST',
    '_GUARD_FOLDABLE_FIRST',
    'GUARD_TRUE',
    'GUARD_FALSE',
    'GUARD_VALUE',
    'GUARD_CLASS',
    'GUARD_NONNULL',
    'GUARD_ISNULL',
    'GUARD_NONNULL_CLASS',
    '_GUARD_FOLDABLE_LAST',
    'GUARD_NO_EXCEPTION',
    'GUARD_EXCEPTION',
    'GUARD_NO_OVERFLOW',
    'GUARD_OVERFLOW',
    'GUARD_NOT_FORCED',
    '_GUARD_LAST', # ----- end of guard operations -----

    '_NOSIDEEFFECT_FIRST', # ----- start of no_side_effect operations -----
    '_ALWAYS_PURE_FIRST', # ----- start of always_pure operations -----
    'OOSEND_PURE',    # ootype operation
    'CALL_PURE',
    #
    'CAST_PTR_TO_INT/1',
    'INT_ADD/2',
    'INT_SUB/2',
    'INT_MUL/2',
    'INT_FLOORDIV/2',
    'INT_MOD/2',
    'INT_AND/2',
    'INT_OR/2',
    'INT_XOR/2',
    'INT_RSHIFT/2',
    'INT_LSHIFT/2',
    'UINT_RSHIFT/2',
    'FLOAT_ADD/2',
    'FLOAT_SUB/2',
    'FLOAT_MUL/2',
    'FLOAT_TRUEDIV/2',
    'FLOAT_NEG/1',
    'FLOAT_ABS/1',
    'FLOAT_IS_TRUE/1b',
    'CAST_FLOAT_TO_INT/1',
    'CAST_INT_TO_FLOAT/1',
    #
    'INT_LT/2b',
    'INT_LE/2b',
    'INT_EQ/2b',
    'INT_NE/2b',
    'INT_GT/2b',
    'INT_GE/2b',
    'UINT_LT/2b',
    'UINT_LE/2b',
    'UINT_GT/2b',
    'UINT_GE/2b',
    'FLOAT_LT/2b',
    'FLOAT_LE/2b',
    'FLOAT_EQ/2b',
    'FLOAT_NE/2b',
    'FLOAT_GT/2b',
    'FLOAT_GE/2b',
    #
    'INT_IS_TRUE/1b',
    'INT_NEG/1',
    'INT_INVERT/1',
    'BOOL_NOT/1b',
    #
    'SAME_AS/1',      # gets a Const or a Box, turns it into another Box
    #
    'OOIS/2b',
    'OOISNOT/2b',
    #
    'ARRAYLEN_GC/1d',
    'STRLEN/1',
    'STRGETITEM/2',
    'GETFIELD_GC_PURE/1d',
    'GETFIELD_RAW_PURE/1d',
    'GETARRAYITEM_GC_PURE/2d',
    'UNICODELEN/1',
    'UNICODEGETITEM/2',
    #
    # ootype operations
    'INSTANCEOF/1db',
    'SUBCLASSOF/2b',
    #
    '_ALWAYS_PURE_LAST',  # ----- end of always_pure operations -----

    'GETARRAYITEM_GC/2d',
    'GETFIELD_GC/1d',
    'GETFIELD_RAW/1d',
    'NEW/0d',
    'NEW_WITH_VTABLE/1',
    'NEW_ARRAY/1d',
    'FORCE_TOKEN/0',
    'VIRTUAL_REF/2',
    '_NOSIDEEFFECT_LAST', # ----- end of no_side_effect operations -----

    'SETARRAYITEM_GC/3d',
    'SETARRAYITEM_RAW/3d',#only added by backend.llsupport.gc.rewrite_assembler
    'SETFIELD_GC/2d',
    'SETFIELD_RAW/2d',
    'NEWSTR/1',
    'STRSETITEM/3',
    'UNICODESETITEM/3',
    'NEWUNICODE/1',
    'RUNTIMENEW/1',     # ootype operation
    'COND_CALL_GC_WB',  # [objptr, newvalue]   (for the write barrier)
    'DEBUG_MERGE_POINT/1',      # debugging only
    'VIRTUAL_REF_FINISH/2',

    '_CANRAISE_FIRST', # ----- start of can_raise operations -----
    'CALL',
    'CALL_ASSEMBLER',
    'CALL_MAY_FORCE',
    'CALL_LOOPINVARIANT',
    'OOSEND',                     # ootype operation
    '_CANRAISE_LAST', # ----- end of can_raise operations -----

    '_OVF_FIRST', # ----- start of is_ovf operations -----
    'INT_ADD_OVF/2',
    'INT_SUB_OVF/2',
    'INT_MUL_OVF/2',
    '_OVF_LAST', # ----- end of is_ovf operations -----
    '_LAST',     # for the backend to add more internal operations
]

# ____________________________________________________________

class rop(object):
    pass

opname = {}      # mapping numbers to the original names, for debugging
oparity = []     # mapping numbers to the arity of the operation or -1
opwithdescr = [] # mapping numbers to a flag "takes a descr"
opboolresult= [] # mapping numbers to a flag "returns a boolean"


def setup(debug_print=False):
    for i, name in enumerate(_oplist):
        if debug_print:
            print '%30s = %d' % (name, i)
        if '/' in name:
            name, arity = name.split('/')
            withdescr = 'd' in arity
            boolresult = 'b' in arity
            arity = int(arity.rstrip('db'))
        else:
            arity, withdescr, boolresult = -1, True, False       # default
        setattr(rop, name, i)
        if not name.startswith('_'):
            opname[i] = name
        oparity.append(arity)
        opwithdescr.append(withdescr)
        opboolresult.append(boolresult)
    assert len(oparity)==len(opwithdescr)==len(opboolresult)==len(_oplist)

setup(__name__ == '__main__')   # print out the table when run directly
del _oplist
