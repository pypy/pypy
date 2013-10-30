from rpython.rlib.rarithmetic import r_singlefloat
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.translator.tool.cbuild import ExternalCompilationInfo


class JitCounter:
    DEFAULT_SIZE = 4096

    def __init__(self, size=DEFAULT_SIZE):
        assert size >= 1 and (size & (size - 1)) == 0     # a power of two
        self.mask = size - 1
        self.timetable = lltype.malloc(rffi.CArray(rffi.FLOAT), size,
                                       flavor='raw', zero=True,
                                       track_allocation=False)
        self.celltable = [None] * size

    def compute_threshold(self, threshold):
        """Return the 'increment' value corresponding to the given number."""
        if threshold <= 0:
            return 0.0   # no increment, never reach 1.0
        if threshold < 2:
            threshold = 2
        return 1.0 / threshold   # the number is at most 0.5

    def tick(self, hash, increment):
        hash &= self.mask
        counter = float(self.timetable[hash]) + increment
        if counter < 1.0:
            self.timetable[hash] = r_singlefloat(counter)
            return False
        else:
            return True
    tick._always_inline_ = True

    def reset(self, hash):
        hash &= self.mask
        self.timetable[hash] = r_singlefloat(0.0)

    def lookup_chain(self, hash):
        hash &= self.mask
        return self.celltable[hash]

    def cleanup_chain(self, hash):
        self.install_new_cell(hash, None)

    def install_new_cell(self, hash, newcell):
        hash &= self.mask
        cell = self.celltable[hash]
        keep = newcell
        while cell is not None:
            remove_me = cell.should_remove_jitcell()
            nextcell = cell.next
            if not remove_me:
                cell.next = keep
                keep = cell
            cell = nextcell
        self.celltable[hash] = keep

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
        size = self.mask + 1
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
