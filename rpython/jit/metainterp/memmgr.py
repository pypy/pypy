import math
from rpython.rlib.rarithmetic import r_int64
from rpython.rlib.debug import debug_start, debug_print, debug_stop
from rpython.rlib.objectmodel import we_are_translated, stm_ignored
from rpython.rlib.rgc import stm_is_enabled
from rpython.rtyper import annlowlevel
from rpython.rlib import rstm

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

from rpython.rtyper.lltypesystem import lltype, llmemory
TOKENGEN = lltype.GcStruct('TokenGen',
                           ('token', llmemory.GCREF),
                           ('generation', lltype.Signed))
PTOKENGEN = lltype.Ptr(TOKENGEN)

class MemoryManager(object):

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
        self.next_check = r_int64(-1)

        # We can't use stm_is_enabled() here, because we have only one
        # instance of MemoryManager built before translation.
        # For the non-stm case, we'll use this:
        self.alive_loops = {}

        # For the stm case, we'll use this:
        # * hash table mapping integers to (looptoken, generation)
        self.stm_alive_loops = rstm.NULL_HASHTABLE
        # * lowest integer key used in stm_alive_loops
        self.stm_lowest_key = 0


    def set_max_age(self, max_age, check_frequency=0):
        if max_age <= 0:
            self.next_check = r_int64(-1)
        else:
            self.max_age = max_age
            if check_frequency <= 0:
                check_frequency = int(math.sqrt(max_age))
            self.check_frequency = check_frequency
            self.next_check = self.current_generation + 1

    def next_generation(self):
        self.current_generation += 1
        if self.current_generation == self.next_check:
            self._kill_old_loops_now()
            self.next_check = self.current_generation + self.check_frequency

    def keep_loop_alive(self, looptoken):
        if looptoken.generation != self.current_generation:
            # STM: never produce conflicts from this function
            # (except possibly the first time it is called)
            if not stm_is_enabled():
                looptoken.generation = self.current_generation
                self.alive_loops[looptoken] = None
            else:
                next_key = rstm.stm_count()
                tokgen = lltype.malloc(TOKENGEN)
                tokgen.token = annlowlevel.cast_instance_to_gcref(looptoken)
                tokgen.generation = self.current_generation
                if not self.stm_alive_loops:
                    self.stm_alive_loops = rstm.create_hashtable()

                gcref = lltype.cast_opaque_ptr(llmemory.GCREF, tokgen)
                self.stm_alive_loops.set(next_key, gcref)

    def _kill_old_loops_now(self):
        debug_start("jit-mem-collect")
        #print self.alive_loops.keys()
        debug_print("Current generation:", self.current_generation)
        max_generation = self.current_generation - (self.max_age-1)
        #
        if not stm_is_enabled():
            oldtotal = len(self.alive_loops)
            for looptoken in self.alive_loops.keys():
                if not self._must_keep_loop(looptoken, max_generation):
                    del self.alive_loops[looptoken]
            newtotal = len(self.alive_loops)
        else:
            # this logic assumes that we are more or less the only running
            # thread.  Even if there are possible corner cases, they should
            # not have worse results than a possibly early or late freeing
            # of one loop, and only in corner cases.
            from rpython.jit.metainterp.history import JitCellToken
            stm_alive_loops = self.stm_alive_loops
            keep_loops = {}
            #
            # all keys in 'stm_alive_loops' should be in the following range
            old_count = self.stm_lowest_key
            new_count = rstm.stm_count()
            oldtotal = 0
            if stm_alive_loops:
                for key in range(old_count, new_count):
                    gcref = stm_alive_loops.get(key)
                    if not gcref:
                        continue
                    # make 'stm_alive_loops' empty, and add the loops that we
                    # must keep in the set 'keep_loops'
                    stm_alive_loops.set(key, rstm.NULL_GCREF)
                    oldtotal += 1

                    tokgen = lltype.cast_opaque_ptr(PTOKENGEN, gcref)
                    looptoken = annlowlevel.cast_gcref_to_instance(JitCellToken,
                                                                   tokgen.token)
                    #if self._must_keep_loop(looptoken, max_generation):
                    if not (0 <= tokgen.generation < max_generation or
                            looptoken.invalidated):
                        keep_loops[looptoken] = tokgen
            newtotal = len(keep_loops)
            #
            # now re-add loops with key numbers that *end* at 'new_count'
            for looptoken, tokgen in keep_loops.items():
                gcref = lltype.cast_opaque_ptr(llmemory.GCREF, tokgen)
                stm_alive_loops.set(new_count, gcref)
                new_count -= 1
            self.stm_lowest_key = new_count + 1    # lowest used key number
        #
        debug_print("Loop tokens before:", oldtotal)
        debug_print("Loop tokens freed: ", oldtotal - newtotal)
        debug_print("Loop tokens left:  ", newtotal)
        #print self.alive_loops.keys()
        if not we_are_translated() and oldtotal != newtotal:
            looptoken = None
            from rpython.rlib import rgc
            # a single one is not enough for all tests :-(
            rgc.collect(); rgc.collect(); rgc.collect()
        debug_stop("jit-mem-collect")

    def _must_keep_loop(self, looptoken, max_generation):
        assert not stm_is_enabled()
        return not (0 <= looptoken.generation < max_generation or
                    looptoken.invalidated)
