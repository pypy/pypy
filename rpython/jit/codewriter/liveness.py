from rpython.jit.codewriter.flatten import Register, ListOfKind, Label, TLabel
from rpython.jit.codewriter.jitcode import SwitchDictDescr
from rpython.rlib import objectmodel

# Some instructions require liveness information (the ones that can end up
# in generate_guard() in pyjitpl.py).  This is done by putting special
# space operations called '-live-' in the graph.  They turn into '-live-'
# operation in the ssarepr.  Then the present module expands the arguments
# of the '-live-' operations to also include all values that are alive at
# this point (written to before, and read afterwards).  You can also force
# extra variables to be alive by putting them as args of the '-live-'
# operation in the first place.

# For this to work properly, a special operation called '---' must be
# used to mark unreachable places (e.g. just after a 'goto').

# ____________________________________________________________

def compute_liveness(ssarepr):
    label2alive = {}
    while _compute_liveness_must_continue(ssarepr, label2alive):
        pass
    remove_repeated_live(ssarepr)

def _compute_liveness_must_continue(ssarepr, label2alive):
    alive = set()
    must_continue = False

    def follow_label(lbl):
        alive_at_point = label2alive.get(lbl.name, ())
        alive.update(alive_at_point)

    for i in range(len(ssarepr.insns)-1, -1, -1):
        insn = ssarepr.insns[i]

        if isinstance(insn[0], Label):
            alive_at_point = label2alive.setdefault(insn[0].name, set())
            prevlength = len(alive_at_point)
            alive_at_point.update(alive)
            if prevlength != len(alive_at_point):
                must_continue = True
            continue

        if insn[0] == '-live-':
            labels = []
            for x in insn[1:]:
                if isinstance(x, Register):
                    alive.add(x)
                elif isinstance(x, TLabel):
                    follow_label(x)
                    labels.append(x)
            ssarepr.insns[i] = insn[:1] + tuple(alive) + tuple(labels)
            continue

        if insn[0] == '---':
            alive = set()
            continue

        args = insn[1:]
        #
        if len(args) >= 2 and args[-2] == '->':
            reg = args[-1]
            assert isinstance(reg, Register)
            alive.discard(reg)
            args = args[:-2]
        #
        for x in args:
            if isinstance(x, Register):
                alive.add(x)
            elif isinstance(x, ListOfKind):
                for y in x:
                    if isinstance(y, Register):
                        alive.add(y)
            elif isinstance(x, TLabel):
                follow_label(x)
            elif isinstance(x, SwitchDictDescr):
                for key, label in x._labels:
                    follow_label(label)

    return must_continue

def remove_repeated_live(ssarepr):
    last_i_pos = None
    i = 0
    res = []
    while i < len(ssarepr.insns):
        insn = ssarepr.insns[i]
        if insn[0] != '-live-':
            res.append(insn)
            i += 1
            continue
        last_i_pos = i
        i += 1
        labels = []
        lives = [insn]
        # collect lives and labels
        while i < len(ssarepr.insns):
            next = ssarepr.insns[i]
            if next[0] == '-live-':
                lives.append(next)
                i += 1
            elif isinstance(next[0], Label):
                labels.append(next)
                i += 1
            else:
                break
        if len(lives) == 1:
            res.extend(labels)
            res.append(lives[0])
            continue
        liveset = set()
        for live in lives:
            liveset.update(live[1:])
        res.extend(labels)
        res.append(('-live-', ) + tuple(sorted(liveset)))
    ssarepr.insns = res


# ____________________________________________________________
# helper functions for compactly encoding and decoding liveness info

# liveness is encoded as a 2 byte offset into the single string all_liveness
# (which is stored on the metainterp_sd)

OFFSET_SIZE = 2

def encode_offset(pos, code):
    assert OFFSET_SIZE == 2
    code.append(chr(pos & 0xff))
    code.append(chr((pos >> 8) & 0xff))
    assert (pos >> 16) == 0

def decode_offset(jitcode, pc):
    assert OFFSET_SIZE == 2
    return (ord(jitcode[pc]) |
           (ord(jitcode[pc + 1]) << 8))


# within the string of all_liveness, we encode the bitsets of which of the 256
# registers are live as follows: first three byte with the number of set bits
# for each of the categories ints, refs, floats followed by the necessary
# number of bytes to store them (this number of bytes is implicit), for each of
# the categories
# | len live_i | len live_r | len live_f
# | bytes for live_i | bytes for live_r | bytes for live_f

def encode_liveness(live):
    live = sorted(live) # ints in range(256)
    liveness = []
    offset = 0
    char = 0
    i = 0
    while i < len(live):
        x = ord(live[i])
        x -= offset
        if x >= 8:
            liveness.append(chr(char))
            char = 0
            offset += 8
            continue
        char |= 1 << x
        assert 0 <= char < 256
        i += 1
    if char:
        liveness.append(chr(char))
    return "".join(liveness)

#@objectmodel.never_allocate # can't be enabled because of some tests that
# don't optimize
class LivenessIterator(object):
    @objectmodel.always_inline
    def __init__(self, offset, length, all_liveness):
        self.all_liveness = all_liveness
        self.offset = offset
        assert length
        self.length = length
        self.curr_byte = 0
        self.count = 0

    @objectmodel.always_inline
    def __iter__(self):
        return self

    @objectmodel.always_inline
    def next(self):
        if not self.length:
            raise StopIteration
        self.length -= 1
        count = self.count
        all_liveness = self.all_liveness
        curr_byte = self.curr_byte
        # find next bit set
        while 1:
            if (count & 7) == 0:
                curr_byte = self.curr_byte = ord(all_liveness[self.offset])
                self.offset += 1
            if (curr_byte >> (count & 7)) & 1:
                self.count = count + 1
                return count
            count += 1

