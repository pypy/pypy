
class ResOperation(object):
    """The central ResOperation class, representing one operation."""

    # for 'jump': points to the target loop;
    jump_target = None

    # for 'guard_*'
    suboperations = None
    optimized = None

    # for x86 backend and guards
    inputargs = None

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
        return ResOperation(self.opnum, self.args, self.result, self.descr)

    def __repr__(self):
        return self.repr()

    def repr(self):
        from pypy.rlib.objectmodel import we_are_translated
        # RPython-friendly version
        if self.result is not None:
            sres = '%s = ' % (self.result,)
        else:
            sres = ''
        if self.name:
            prefix = "%s:%s:" % (self.name, self.pc)
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
    'FAIL',
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
    '_GUARD_LAST', # ----- end of guard operations -----

    '_NOSIDEEFFECT_FIRST', # ----- start of no_side_effect operations -----
    '_ALWAYS_PURE_FIRST', # ----- start of always_pure operations -----
    'OOSEND_PURE',    # ootype operation
    'CALL_PURE',
    #
    'CAST_INT_TO_PTR',
    'CAST_PTR_TO_INT',
    'INT_ADD',
    'INT_SUB',
    'INT_MUL',
    'INT_FLOORDIV',
    'INT_MOD',
    'INT_AND',
    'INT_OR',
    'INT_XOR',
    'INT_RSHIFT',
    'INT_LSHIFT',
    'UINT_RSHIFT',
    #
    '_COMPARISON_FIRST',
    'INT_LT',
    'INT_LE',
    'INT_EQ',
    'INT_NE',
    'INT_GT',
    'INT_GE',
    'UINT_LT',
    'UINT_LE',
    'UINT_GT',
    'UINT_GE',
    '_COMPARISON_LAST',
    #
    'INT_IS_TRUE',
    'INT_NEG',
    'INT_INVERT',
    'BOOL_NOT',
    #
    'SAME_AS',      # gets a Const, turns it into a Box
    #
    'OONONNULL',
    'OOISNULL',
    'OOIS',
    'OOISNOT',
    #
    'ARRAYLEN_GC',
    'STRLEN',
    'STRGETITEM',
    'GETFIELD_GC_PURE',
    'GETFIELD_RAW_PURE',
    'GETARRAYITEM_GC_PURE',
    'UNICODELEN',
    'UNICODEGETITEM',
    #
    # ootype operations
    'OOIDENTITYHASH',
    'INSTANCEOF',
    'SUBCLASSOF',
    #
    '_ALWAYS_PURE_LAST',  # ----- end of always_pure operations -----

    'GETARRAYITEM_GC',
    'GETFIELD_GC',
    'GETFIELD_RAW',
    'NEW',
    'NEW_WITH_VTABLE',
    'NEW_ARRAY',
    '_NOSIDEEFFECT_LAST', # ----- end of no_side_effect operations -----

    'SETARRAYITEM_GC',
    'SETFIELD_GC',
    'SETFIELD_RAW',
    'NEWSTR',
    'STRSETITEM',
    'UNICODESETITEM',
    'NEWUNICODE',
    'RUNTIMENEW',     # ootype operation

    '_CANRAISE_FIRST', # ----- start of can_raise operations -----
    'CALL',
    'OOSEND',                     # ootype operation
    #
    '_OVF_FIRST',
    'INT_ADD_OVF',
    'INT_SUB_OVF',
    'INT_MUL_OVF',
    '_OVF_LAST',
    '_CANRAISE_LAST', # ----- end of can_raise operations -----
    '_LAST',     # for the backend to add more internal operations
]

class rop(object):
    pass

i = 0
for opname in _oplist:
    if __name__ == '__main__':
        print '%30s = %d' % (opname, i) # print out the table when run directly
    setattr(rop, opname, i)
    i += 1
del _oplist

opname = {}      # mapping numbers to the original names, for debugging
for _key, _value in rop.__dict__.items():
    if type(_value) is int and _key.isupper() and not _key.startswith('_'):
        assert _value not in opname, "collision! %s and %s" % (
            opname[_value], _key)
        opname[_value] = _key
