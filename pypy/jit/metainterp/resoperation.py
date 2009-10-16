from pypy.rlib.objectmodel import we_are_translated


class ResOperation(object):
    """The central ResOperation class, representing one operation."""

    # for 'jump': points to the target loop;
    jump_target = property(lambda x: crash, lambda x, y: crash)  # XXX temp

    # for 'guard_*'
    suboperations = property(lambda x: crash, lambda x, y: crash)  # XXX temp
    optimized = property(lambda x: crash, lambda x, y: crash)  # XXX temp
    fail_args = None

    # debug
    name = ""
    pc = 0

    def __init__(self, opnum, args, result, descr=None):
        assert isinstance(opnum, int)
        self.opnum = opnum
        self.args = list(args)
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
        op = ResOperation(self.opnum, self.args, self.result, self.descr)
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
        return rop._COMPARISON_FIRST <= self.opnum <= rop._COMPARISON_LAST

    def is_final(self):
        return rop._FINAL_FIRST <= self.opnum <= rop._FINAL_LAST

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
    '_GUARD_FOLDABLE_LAST',
    'GUARD_NO_EXCEPTION',
    'GUARD_EXCEPTION',
    'GUARD_NO_OVERFLOW',
    'GUARD_OVERFLOW',
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
    'FLOAT_IS_TRUE/1',
    'CAST_FLOAT_TO_INT/1',
    'CAST_INT_TO_FLOAT/1',
    #
    '_COMPARISON_FIRST',
    'INT_LT/2',
    'INT_LE/2',
    'INT_EQ/2',
    'INT_NE/2',
    'INT_GT/2',
    'INT_GE/2',
    'UINT_LT/2',
    'UINT_LE/2',
    'UINT_GT/2',
    'UINT_GE/2',
    '_COMPARISON_LAST',
    'FLOAT_LT/2',          # maybe these ones should be comparisons too
    'FLOAT_LE/2',
    'FLOAT_EQ/2',
    'FLOAT_NE/2',
    'FLOAT_GT/2',
    'FLOAT_GE/2',
    #
    'INT_IS_TRUE/1',
    'INT_NEG/1',
    'INT_INVERT/1',
    'BOOL_NOT/1',
    #
    'SAME_AS/1',      # gets a Const, turns it into a Box
    #
    'OONONNULL/1',
    'OOISNULL/1',
    'OOIS/2',
    'OOISNOT/2',
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
    'INSTANCEOF/1d',
    'SUBCLASSOF/2',
    #
    '_ALWAYS_PURE_LAST',  # ----- end of always_pure operations -----

    'GETARRAYITEM_GC/2d',
    'GETFIELD_GC/1d',
    'GETFIELD_RAW/1d',
    'NEW/0d',
    'NEW_WITH_VTABLE/1',
    'NEW_ARRAY/1d',
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
    'COND_CALL_GC_WB',      # [cond, imm_and, if_true_call, args_for_call...]
                            #        => no result       (for the write barrier)
    'COND_CALL_GC_MALLOC',  # [a, b, if_(a<=b)_result, if_(a>b)_call, args...]
                            #        => result          (for mallocs)
    'DEBUG_MERGE_POINT/1',      # debugging only

    '_CANRAISE_FIRST', # ----- start of can_raise operations -----
    'CALL',
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


def setup(debug_print=False):
    for i, name in enumerate(_oplist):
        if debug_print:
            print '%30s = %d' % (name, i)
        if '/' in name:
            name, arity = name.split('/')
            withdescr = arity.endswith('d')
            arity = int(arity.rstrip('d'))
        else:
            arity, withdescr = -1, True       # default
        setattr(rop, name, i)
        if not name.startswith('_'):
            opname[i] = name
        oparity.append(arity)
        opwithdescr.append(withdescr)
    assert len(oparity) == len(opwithdescr) == len(_oplist)

setup(__name__ == '__main__')   # print out the table when run directly
del _oplist
