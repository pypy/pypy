from rpython.rlib.rarithmetic import r_singlefloat, intmask, r_uint
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.translator.tool.cbuild import ExternalCompilationInfo


r_uint32 = rffi.r_uint
assert r_uint32.BITS == 32
UINT32MAX = 2 ** 32 - 1


class JitCounter:
    DEFAULT_SIZE = 4096

    def __init__(self, size=DEFAULT_SIZE):
        "NOT_RPYTHON"
        self.size = size
        self.shift = 1
        while (UINT32MAX >> self.shift) != size - 1:
            self.shift += 1
            assert self.shift < 999, "size is not a power of two <= 2**31"
        self.timetable = lltype.malloc(rffi.CArray(rffi.FLOAT), size,
                                       flavor='raw', zero=True,
                                       track_allocation=False)
        self.celltable = [None] * size
        self._nextindex = 0

    def compute_threshold(self, threshold):
        """Return the 'increment' value corresponding to the given number."""
        if threshold <= 0:
            return 0.0   # no increment, never reach 1.0
        return 1.0 / (threshold - 0.001)

    def get_index(self, hash):
        """Return the index (< self.size) from a hash value.  This keeps
        the *high* bits of hash!  Be sure that hash is computed correctly."""
        return intmask(r_uint32(r_uint(hash) >> self.shift))
    get_index._always_inline_ = True

    def fetch_next_index(self):
        result = self._nextindex
        self._nextindex = (result + 1) & self.get_index(-1)
        return result

    def tick(self, index, increment):
        counter = float(self.timetable[index]) + increment
        if counter < 1.0:
            self.timetable[index] = r_singlefloat(counter)
            return False
        else:
            # when the bound is reached, we immediately reset the value to 0.0
            self.reset(index)
            return True
    tick._always_inline_ = True

    def reset(self, index):
        self.timetable[index] = r_singlefloat(0.0)

    def lookup_chain(self, index):
        return self.celltable[index]

    def cleanup_chain(self, index):
        self.reset(index)
        self.install_new_cell(index, None)

    def install_new_cell(self, index, newcell):
        cell = self.celltable[index]
        keep = newcell
        while cell is not None:
            remove_me = cell.should_remove_jitcell()
            nextcell = cell.next
            if not remove_me:
                cell.next = keep
                keep = cell
            cell = nextcell
        self.celltable[index] = keep

    def set_decay(self, decay):
        """Set the decay, from 0 (none) to 1000 (max)."""
        if decay < 0:
            decay = 0
        elif decay > 1000:
            decay = 1000
        self.decay_by_mult = 1.0 - (decay * 0.001)

    def decay_all_counters(self):
        # Called during a minor collection by the GC, to gradually decay
        # counters that didn't reach their maximum.  Thus if a counter
        # is incremented very slowly, it will never reach the maximum.
        # This avoids altogether the JIT compilation of rare paths.
        # We also call this function when any maximum bound is reached,
        # to avoid sudden bursts of JIT-compilation (the next one will
        # not reach the maximum bound immmediately after).  This is
        # important in corner cases where we would suddenly compile more
        # than one loop because all counters reach the bound at the same
        # time, but where compiling all but the first one is pointless.
        size = self.size
        pypy__decay_jit_counters(self.timetable, self.decay_by_mult, size)


# this function is written directly in C; gcc will optimize it using SSE
eci = ExternalCompilationInfo(post_include_bits=["""
static void pypy__decay_jit_counters(float table[], double f1, long size1) {
    float f = (float)f1;
    int i, size = (int)size1;
    for (i=0; i<size; i++)
        table[i] *= f;
}
"""])

pypy__decay_jit_counters = rffi.llexternal(
    "pypy__decay_jit_counters", [rffi.FLOATP, lltype.Float, lltype.Signed],
    lltype.Void, compilation_info=eci, _nowrapper=True, sandboxsafe=True)


# ____________________________________________________________
#
# A non-RPython version that avoids issues with rare random collisions,
# which make all tests brittle

class DeterministicJitCounter(JitCounter):
    def __init__(self):
        from collections import defaultdict
        JitCounter.__init__(self, size=8)
        zero = r_singlefloat(0.0)
        self.timetable = defaultdict(lambda: zero)
        self.celltable = defaultdict(lambda: None)

    def get_index(self, hash):
        "NOT_RPYTHON"
        return hash
