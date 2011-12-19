import math
from pypy.rlib.rarithmetic import r_int64, r_uint
from pypy.rlib.debug import debug_start, debug_print, debug_stop
from pypy.rlib.objectmodel import we_are_translated

#
# Logic to decide which loops are old and not used any more.
#
# All the long-lived references to LoopToken are weakrefs (see JitCell
# in warmstate.py), apart from the 'alive_loops' set in MemoryManager,
# which is the only (long-living) place that keeps them alive.  If a
# loop was not called for long enough, then it is removed from
# 'alive_loops'.  It will soon be freed by the GC.  LoopToken.__del__
# calls the method cpu.free_loop_and_bridges().
#
# The alive_loops set is maintained using the notion of a global
# 'current generation' which is, in practice, the total number of loops
# and bridges produced so far.  A LoopToken is declared "old" if its
# 'generation' field is much smaller than the current generation, and
# removed from the set.
#

class MemoryManager(object):
    NO_NEXT_CHECK = r_int64(2 ** 63 - 1)

    def __init__(self):
        self.check_frequency = -1
        # NB. use of r_int64 to be extremely far on the safe side:
        # this is increasing by one after each loop or bridge is
        # compiled, and it must not overflow.  If the backend implements
        # complete freeing in cpu.free_loop_and_bridges(), then it may
        # be possible to get arbitrary many of them just by waiting long
        # enough.  But in this day and age, you'd still never have the
        # patience of waiting for a slowly-increasing 64-bit number to
        # overflow :-)

        # According to my estimates it's about 5e9 years given 1000 loops
        # per second
        self.current_generation = r_int64(1)
        self.next_check = self.NO_NEXT_CHECK
        self.alive_loops = {}
        self._cleanup_jitcell_dicts = lambda: None

    def set_max_age(self, max_age, check_frequency=0):
        if max_age <= 0:
            self.next_check = self.NO_NEXT_CHECK
        else:
            self.max_age = max_age
            if check_frequency <= 0:
                check_frequency = int(math.sqrt(max_age))
            self.check_frequency = check_frequency
            self.next_check = self.current_generation + 1

    def next_generation(self, do_cleanups_now=True):
        self.current_generation += 1
        if do_cleanups_now and self.current_generation >= self.next_check:
            self._kill_old_loops_now()
            self._cleanup_jitcell_dicts()
            self.next_check = self.current_generation + self.check_frequency

    def keep_loop_alive(self, looptoken):
        if looptoken.generation != self.current_generation:
            looptoken.generation = self.current_generation
            self.alive_loops[looptoken] = None

    def _kill_old_loops_now(self):
        debug_start("jit-mem-collect")
        oldtotal = len(self.alive_loops)
        #print self.alive_loops.keys()
        debug_print("Current generation:", self.current_generation)
        debug_print("Loop tokens before:", oldtotal)
        max_generation = self.current_generation - (self.max_age-1)
        for looptoken in self.alive_loops.keys():
            if (0 <= looptoken.generation < max_generation or
                looptoken.invalidated):
                del self.alive_loops[looptoken]
        newtotal = len(self.alive_loops)
        debug_print("Loop tokens freed: ", oldtotal - newtotal)
        debug_print("Loop tokens left:  ", newtotal)
        #print self.alive_loops.keys()
        if not we_are_translated() and oldtotal != newtotal:
            looptoken = None
            from pypy.rlib import rgc
            # a single one is not enough for all tests :-(
            rgc.collect(); rgc.collect(); rgc.collect()
        debug_stop("jit-mem-collect")

    def get_current_generation_uint(self):
        """Return the current generation, possibly truncated to a uint.
        To use only as an approximation for decaying counters."""
        return r_uint(self.current_generation)

    def record_jitcell_dict(self, callback):
        """NOT_RPYTHON.  The given jitcell_dict is a dict that needs
        occasional clean-ups of old cells.  A cell is old if it never
        reached the threshold, and its counter decayed to a tiny value."""
        # note that the various jitcell_dicts have different RPython types,
        # so we have to make a different function for each one.  These
        # functions are chained to each other: each calls the previous one.
        def cleanup_dict():
            callback()
            cleanup_previous()
        #
        cleanup_previous = self._cleanup_jitcell_dicts
        self._cleanup_jitcell_dicts = cleanup_dict
