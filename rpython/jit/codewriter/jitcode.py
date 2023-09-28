from rpython.jit.metainterp.history import AbstractDescr, ConstInt
from rpython.jit.metainterp.support import adr2int
from rpython.rlib.objectmodel import we_are_translated, specialize
from rpython.rlib.rarithmetic import base_int


class JitCode(AbstractDescr):
    _empty_i = []
    _empty_r = []
    _empty_f = []

    def __init__(self, name, fnaddr=None, calldescr=None, called_from=None):
        self.name = name
        self.fnaddr = fnaddr
        self.calldescr = calldescr
        self.jitdriver_sd = None # None for non-portals
        self._called_from = called_from   # debugging
        self._ssarepr     = None          # debugging

    def setup(self, code='', constants_i=[], constants_r=[], constants_f=[],
              num_regs_i=255, num_regs_r=255, num_regs_f=255,
              startpoints=None, alllabels=None,
              resulttypes=None):
        self.code = code
        for x in constants_i:
            assert not isinstance(x, base_int), (
                "found constant %r of type %r, must not appear in "
                "JitCode.constants_i" % (x, type(x)))
        # if the following lists are empty, use a single shared empty list
        self.constants_i = constants_i or self._empty_i
        self.constants_r = constants_r or self._empty_r
        self.constants_f = constants_f or self._empty_f
        # encode the three num_regs into a single char each
        assert num_regs_i < 256 and num_regs_r < 256 and num_regs_f < 256
        self.c_num_regs_i = chr(num_regs_i)
        self.c_num_regs_r = chr(num_regs_r)
        self.c_num_regs_f = chr(num_regs_f)
        self._startpoints = startpoints   # debugging
        self._alllabels = alllabels       # debugging
        self._resulttypes = resulttypes   # debugging

    def get_fnaddr_as_int(self):
        return adr2int(self.fnaddr)

    def num_regs_i(self):
        return ord(self.c_num_regs_i)

    def num_regs_r(self):
        return ord(self.c_num_regs_r)

    def num_regs_f(self):
        return ord(self.c_num_regs_f)

    def num_regs_and_consts_i(self):
        return ord(self.c_num_regs_i) + len(self.constants_i)

    def num_regs_and_consts_r(self):
        return ord(self.c_num_regs_r) + len(self.constants_r)

    def num_regs_and_consts_f(self):
        return ord(self.c_num_regs_f) + len(self.constants_f)


    def _live_vars(self, pc, all_liveness, op_live):
        from rpython.jit.codewriter.liveness import LivenessIterator
        # for testing only
        if ord(self.code[pc]) != op_live:
            self._missing_liveness(pc)
        offset = self.get_live_vars_info(pc, op_live)
        lst_i = []
        lst_r = []
        lst_f = []
        enumerate_vars(offset, all_liveness,
                lambda index: lst_i.append("%%i%d" % (index, )),
                lambda index: lst_r.append("%%r%d" % (index, )),
                lambda index: lst_f.append("%%f%d" % (index, )),
                None)
        return ' '.join(lst_i + lst_r + lst_f)

    def get_live_vars_info(self, pc, op_live):
        from rpython.jit.codewriter.liveness import decode_offset, OFFSET_SIZE
        # either this, or the previous instruction must be -live-
        if not we_are_translated():
            assert pc in self._startpoints
        if ord(self.code[pc]) != op_live:
            pc -= OFFSET_SIZE + 1
            if not we_are_translated():
                assert pc in self._startpoints
            if ord(self.code[pc]) != op_live:
                self._missing_liveness(pc)
        return decode_offset(self.code, pc + 1)

    def _missing_liveness(self, pc):
        msg = "missing liveness[%d] in %s" % (pc, self.name)
        if we_are_translated():
            print msg
            raise AssertionError
        raise MissingLiveness("%s\n%s" % (msg, self.dump()))

    def follow_jump(self, position):
        """Assuming that 'position' points just after a bytecode
        instruction that ends with a label, follow that label."""
        code = self.code
        position -= 2
        assert position >= 0
        if not we_are_translated():
            assert position in self._alllabels
        labelvalue = ord(code[position]) | (ord(code[position+1])<<8)
        assert labelvalue < len(code)
        return labelvalue

    def dump(self):
        if self._ssarepr is None:
            return '<no dump available for %r>' % (self.name,)
        else:
            from rpython.jit.codewriter.format import format_assembler
            return format_assembler(self._ssarepr)

    def __repr__(self):
        return '<JitCode %r>' % self.name

    def _clone_if_mutable(self):
        raise NotImplementedError

class MissingLiveness(Exception):
    pass


class SwitchDictDescr(AbstractDescr):
    "Get a 'dict' attribute mapping integer values to bytecode positions."

    def attach(self, as_dict):
        self.dict = as_dict
        self.const_keys_in_order = map(ConstInt, sorted(as_dict.keys()))

    def __repr__(self):
        dict = getattr(self, 'dict', '?')
        return '<SwitchDictDescr %s>' % (dict,)

    def _clone_if_mutable(self):
        raise NotImplementedError


@specialize.arg(5)
def enumerate_vars(offset, all_liveness, callback_i, callback_r, callback_f, spec):
    from rpython.jit.codewriter.liveness import LivenessIterator
    length_i = ord(all_liveness[offset])
    length_r = ord(all_liveness[offset + 1])
    length_f = ord(all_liveness[offset + 2])
    offset += 3
    if length_i:
        it = LivenessIterator(offset, length_i, all_liveness)
        for index in it:
            callback_i(index)
        offset = it.offset
    if length_r:
        it = LivenessIterator(offset, length_r, all_liveness)
        for index in it:
            callback_r(index)
        offset = it.offset
    if length_f:
        it = LivenessIterator(offset, length_f, all_liveness)
        for index in it:
            callback_f(index)
