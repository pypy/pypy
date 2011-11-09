from pypy.rlib.rarithmetic import ovfcheck


## ------------------------------------------------------------------------
## Lots of code for an adaptive, stable, natural mergesort.  There are many
## pieces to this algorithm; read listsort.txt for overviews and details.
## ------------------------------------------------------------------------
##         Adapted from CPython, original code and algorithms by Tim Peters

def make_timsort_class():

    class TimSort:
        """TimSort(list).sort()

        Sorts the list in-place, using the overridable method lt() for comparison.
        """

        def __init__(self, list, listlength=None):
            self.list = list
            if listlength is None:
                listlength = len(list)
            self.listlength = listlength

        def lt(self, a, b):
            return a < b

        def le(self, a, b):
            return not self.lt(b, a)   # always use self.lt() as the primitive

        # binarysort is the best method for sorting small arrays: it does
        # few compares, but can do data movement quadratic in the number of
        # elements.
        # "a" is a contiguous slice of a list, and is sorted via binary insertion.
        # This sort is stable.
        # On entry, the first "sorted" elements are already sorted.
        # Even in case of error, the output slice will be some permutation of
        # the input (nothing is lost or duplicated).

        def binarysort(self, a, sorted=1):
            for start in xrange(a.base + sorted, a.base + a.len):
                # set l to where list[start] belongs
                l = a.base
                r = start
                pivot = a.list[r]
                # Invariants:
                # pivot >= all in [base, l).
                # pivot  < all in [r, start).
                # The second is vacuously true at the start.
                while l < r:
                    p = l + ((r - l) >> 1)
                    if self.lt(pivot, a.list[p]):
                        r = p
                    else:
                        l = p+1
                assert l == r
                # The invariants still hold, so pivot >= all in [base, l) and
                # pivot < all in [l, start), so pivot belongs at l.  Note
                # that if there are elements equal to pivot, l points to the
                # first slot after them -- that's why this sort is stable.
                # Slide over to make room.
                for p in xrange(start, l, -1):
                    a.list[p] = a.list[p-1]
                a.list[l] = pivot

        # Compute the length of the run in the slice "a".
        # "A run" is the longest ascending sequence, with
        #
        #     a[0] <= a[1] <= a[2] <= ...
        #
        # or the longest descending sequence, with
        #
        #     a[0] > a[1] > a[2] > ...
        #
        # Return (run, descending) where descending is False in the former case,
        # or True in the latter.
        # For its intended use in a stable mergesort, the strictness of the defn of
        # "descending" is needed so that the caller can safely reverse a descending
        # sequence without violating stability (strict > ensures there are no equal
        # elements to get out of order).

        def count_run(self, a):
            if a.len <= 1:
                n = a.len
                descending = False
            else:
                n = 2
                if self.lt(a.list[a.base + 1], a.list[a.base]):
                    descending = True
                    for p in xrange(a.base + 2, a.base + a.len):
                        if self.lt(a.list[p], a.list[p-1]):
                            n += 1
                        else:
                            break
                else:
                    descending = False
                    for p in xrange(a.base + 2, a.base + a.len):
                        if self.lt(a.list[p], a.list[p-1]):
                            break
                        else:
                            n += 1
            return ListSlice(a.list, a.base, n), descending

        # Locate the proper position of key in a sorted vector; if the vector
        # contains an element equal to key, return the position immediately to the
        # left of the leftmost equal element -- or to the right of the rightmost
        # equal element if the flag "rightmost" is set.
        #
        # "hint" is an index at which to begin the search, 0 <= hint < a.len.
        # The closer hint is to the final result, the faster this runs.
        #
        # The return value is the index 0 <= k <= a.len such that
        #
        #     a[k-1] < key <= a[k]      (if rightmost is False)
        #     a[k-1] <= key < a[k]      (if rightmost is True)
        #
        # as long as the indices are in bound.  IOW, key belongs at index k;
        # or, IOW, the first k elements of a should precede key, and the last
        # n-k should follow key.

        def gallop(self, key, a, hint, rightmost):
            assert 0 <= hint < a.len
            if rightmost:
                lower = self.le   # search for the largest k for which a[k] <= key
            else:
                lower = self.lt   # search for the largest k for which a[k] < key

            p = a.base + hint
            lastofs = 0
            ofs = 1
            if lower(a.list[p], key):
                # a[hint] < key -- gallop right, until
                #     a[hint + lastofs] < key <= a[hint + ofs]

                maxofs = a.len - hint     # a[a.len-1] is highest
                while ofs < maxofs:
                    if lower(a.list[p + ofs], key):
                        lastofs = ofs
                        try:
                            ofs = ovfcheck(ofs << 1)
                        except OverflowError:
                            ofs = maxofs
                        else:
                            ofs = ofs + 1
                    else:  # key <= a[hint + ofs]
                        break

                if ofs > maxofs:
                    ofs = maxofs
                # Translate back to offsets relative to a.
                lastofs += hint
                ofs += hint

            else:
                # key <= a[hint] -- gallop left, until
                #     a[hint - ofs] < key <= a[hint - lastofs]
                maxofs = hint + 1   # a[0] is lowest
                while ofs < maxofs:
                    if lower(a.list[p - ofs], key):
                        break
                    else:
                        # key <= a[hint - ofs]
                        lastofs = ofs
                        try:
                            ofs = ovfcheck(ofs << 1)
                        except OverflowError:
                            ofs = maxofs
                        else:
                            ofs = ofs + 1
                if ofs > maxofs:
                    ofs = maxofs
                # Translate back to positive offsets relative to a.
                lastofs, ofs = hint-ofs, hint-lastofs

            assert -1 <= lastofs < ofs <= a.len

            # Now a[lastofs] < key <= a[ofs], so key belongs somewhere to the
            # right of lastofs but no farther right than ofs.  Do a binary
            # search, with invariant a[lastofs-1] < key <= a[ofs].

            lastofs += 1
            while lastofs < ofs:
                m = lastofs + ((ofs - lastofs) >> 1)
                if lower(a.list[a.base + m], key):
                    lastofs = m+1   # a[m] < key
                else:
                    ofs = m         # key <= a[m]

            assert lastofs == ofs         # so a[ofs-1] < key <= a[ofs]
            return ofs

        # hint for the annotator: the argument 'rightmost' is always passed in as
        # a constant (either True or False), so we can specialize the function for
        # the two cases.  (This is actually needed for technical reasons: the
        # variable 'lower' must contain a known method, which is the case in each
        # specialized version but not in the unspecialized one.)
        gallop._annspecialcase_ = "specialize:arg(4)"

        # ____________________________________________________________

        # When we get into galloping mode, we stay there until both runs win less
        # often than MIN_GALLOP consecutive times.  See listsort.txt for more info.
        MIN_GALLOP = 7

        def merge_init(self):
            # This controls when we get *into* galloping mode.  It's initialized
            # to MIN_GALLOP.  merge_lo and merge_hi tend to nudge it higher for
            # random data, and lower for highly structured data.
            self.min_gallop = self.MIN_GALLOP

            # A stack of n pending runs yet to be merged.  Run #i starts at
            # address pending[i].base and extends for pending[i].len elements.
            # It's always true (so long as the indices are in bounds) that
            #
            #     pending[i].base + pending[i].len == pending[i+1].base
            #
            # so we could cut the storage for this, but it's a minor amount,
            # and keeping all the info explicit simplifies the code.
            self.pending = []

        # Merge the slice "a" with the slice "b" in a stable way, in-place.
        # a.len and b.len must be > 0, and a.base + a.len == b.base.
        # Must also have that b.list[b.base] < a.list[a.base], that
        # a.list[a.base+a.len-1] belongs at the end of the merge, and should have
        # a.len <= b.len.  See listsort.txt for more info.

        def merge_lo(self, a, b):
            assert a.len > 0 and b.len > 0 and a.base + a.len == b.base
            min_gallop = self.min_gallop
            dest = a.base
            a = a.copyitems()

            # Invariant: elements in "a" are waiting to be reinserted into the list
            # at "dest".  They should be merged with the elements of "b".
            # b.base == dest + a.len.
            # We use a finally block to ensure that the elements remaining in
            # the copy "a" are reinserted back into self.list in all cases.
            try:
                self.list[dest] = b.popleft()
                dest += 1
                if a.len == 1 or b.len == 0:
                    return

                while True:
                    acount = 0   # number of times A won in a row
                    bcount = 0   # number of times B won in a row

                    # Do the straightforward thing until (if ever) one run
                    # appears to win consistently.
                    while True:
                        if self.lt(b.list[b.base], a.list[a.base]):
                            self.list[dest] = b.popleft()
                            dest += 1
                            if b.len == 0:
                                return
                            bcount += 1
                            acount = 0
                            if bcount >= min_gallop:
                                break
                        else:
                            self.list[dest] = a.popleft()
                            dest += 1
                            if a.len == 1:
                                return
                            acount += 1
                            bcount = 0
                            if acount >= min_gallop:
                                break

                    # One run is winning so consistently that galloping may
                    # be a huge win.  So try that, and continue galloping until
                    # (if ever) neither run appears to be winning consistently
                    # anymore.
                    min_gallop += 1

                    while True:
                        min_gallop -= min_gallop > 1
                        self.min_gallop = min_gallop

                        acount = self.gallop(b.list[b.base], a, hint=0,
                                             rightmost=True)
                        for p in xrange(a.base, a.base + acount):
                            self.list[dest] = a.list[p]
                            dest += 1
                        a.advance(acount)
                        # a.len==0 is impossible now if the comparison
                        # function is consistent, but we can't assume
                        # that it is.
                        if a.len <= 1:
                            return

                        self.list[dest] = b.popleft()
                        dest += 1
                        if b.len == 0:
                            return

                        bcount = self.gallop(a.list[a.base], b, hint=0,
                                             rightmost=False)
                        for p in xrange(b.base, b.base + bcount):
                            self.list[dest] = b.list[p]
                            dest += 1
                        b.advance(bcount)
                        if b.len == 0:
                            return

                        self.list[dest] = a.popleft()
                        dest += 1
                        if a.len == 1:
                            return

                        if acount < self.MIN_GALLOP and bcount < self.MIN_GALLOP:
                            break

                    min_gallop += 1  # penalize it for leaving galloping mode
                    self.min_gallop = min_gallop

            finally:
                # The last element of a belongs at the end of the merge, so we copy
                # the remaining elements of b before the remaining elements of a.
                assert a.len >= 0 and b.len >= 0
                for p in xrange(b.base, b.base + b.len):
                    self.list[dest] = b.list[p]
                    dest += 1
                for p in xrange(a.base, a.base + a.len):
                    self.list[dest] = a.list[p]
                    dest += 1

        # Same as merge_lo(), but should have a.len >= b.len.

        def merge_hi(self, a, b):
            assert a.len > 0 and b.len > 0 and a.base + a.len == b.base
            min_gallop = self.min_gallop
            dest = b.base + b.len
            b = b.copyitems()

            # Invariant: elements in "b" are waiting to be reinserted into the list
            # before "dest".  They should be merged with the elements of "a".
            # a.base + a.len == dest - b.len.
            # We use a finally block to ensure that the elements remaining in
            # the copy "b" are reinserted back into self.list in all cases.
            try:
                dest -= 1
                self.list[dest] = a.popright()
                if a.len == 0 or b.len == 1:
                    return

                while True:
                    acount = 0   # number of times A won in a row
                    bcount = 0   # number of times B won in a row

                    # Do the straightforward thing until (if ever) one run
                    # appears to win consistently.
                    while True:
                        nexta = a.list[a.base + a.len - 1]
                        nextb = b.list[b.base + b.len - 1]
                        if self.lt(nextb, nexta):
                            dest -= 1
                            self.list[dest] = nexta
                            a.len -= 1
                            if a.len == 0:
                                return
                            acount += 1
                            bcount = 0
                            if acount >= min_gallop:
                                break
                        else:
                            dest -= 1
                            self.list[dest] = nextb
                            b.len -= 1
                            if b.len == 1:
                                return
                            bcount += 1
                            acount = 0
                            if bcount >= min_gallop:
                                break

                    # One run is winning so consistently that galloping may
                    # be a huge win.  So try that, and continue galloping until
                    # (if ever) neither run appears to be winning consistently
                    # anymore.
                    min_gallop += 1

                    while True:
                        min_gallop -= min_gallop > 1
                        self.min_gallop = min_gallop

                        nextb = b.list[b.base + b.len - 1]
                        k = self.gallop(nextb, a, hint=a.len-1, rightmost=True)
                        acount = a.len - k
                        for p in xrange(a.base + a.len - 1, a.base + k - 1, -1):
                            dest -= 1
                            self.list[dest] = a.list[p]
                        a.len -= acount
                        if a.len == 0:
                            return

                        dest -= 1
                        self.list[dest] = b.popright()
                        if b.len == 1:
                            return

                        nexta = a.list[a.base + a.len - 1]
                        k = self.gallop(nexta, b, hint=b.len-1, rightmost=False)
                        bcount = b.len - k
                        for p in xrange(b.base + b.len - 1, b.base + k - 1, -1):
                            dest -= 1
                            self.list[dest] = b.list[p]
                        b.len -= bcount
                        # b.len==0 is impossible now if the comparison
                        # function is consistent, but we can't assume
                        # that it is.
                        if b.len <= 1:
                            return

                        dest -= 1
                        self.list[dest] = a.popright()
                        if a.len == 0:
                            return

                        if acount < self.MIN_GALLOP and bcount < self.MIN_GALLOP:
                            break

                    min_gallop += 1  # penalize it for leaving galloping mode
                    self.min_gallop = min_gallop

            finally:
                # The last element of a belongs at the end of the merge, so we copy
                # the remaining elements of a and then the remaining elements of b.
                assert a.len >= 0 and b.len >= 0
                for p in xrange(a.base + a.len - 1, a.base - 1, -1):
                    dest -= 1
                    self.list[dest] = a.list[p]
                for p in xrange(b.base + b.len - 1, b.base - 1, -1):
                    dest -= 1
                    self.list[dest] = b.list[p]

        # Merge the two runs at stack indices i and i+1.

        def merge_at(self, i):
            a = self.pending[i]
            b = self.pending[i+1]
            assert a.len > 0 and b.len > 0
            assert a.base + a.len == b.base

            # Record the length of the combined runs and remove the run b
            self.pending[i] = ListSlice(self.list, a.base, a.len + b.len)
            del self.pending[i+1]

            # Where does b start in a?  Elements in a before that can be
            # ignored (already in place).
            k = self.gallop(b.list[b.base], a, hint=0, rightmost=True)
            a.advance(k)
            if a.len == 0:
                return

            # Where does a end in b?  Elements in b after that can be
            # ignored (already in place).
            b.len = self.gallop(a.list[a.base+a.len-1], b, hint=b.len-1,
                                rightmost=False)
            if b.len == 0:
                return

            # Merge what remains of the runs.  The direction is chosen to
            # minimize the temporary storage needed.
            if a.len <= b.len:
                self.merge_lo(a, b)
            else:
                self.merge_hi(a, b)

        # Examine the stack of runs waiting to be merged, merging adjacent runs
        # until the stack invariants are re-established:
        #
        # 1. len[-3] > len[-2] + len[-1]
        # 2. len[-2] > len[-1]
        #
        # See listsort.txt for more info.

        def merge_collapse(self):
            p = self.pending
            while len(p) > 1:
                if len(p) >= 3 and p[-3].len <= p[-2].len + p[-1].len:
                    if p[-3].len < p[-1].len:
                        self.merge_at(-3)
                    else:
                        self.merge_at(-2)
                elif p[-2].len <= p[-1].len:
                    self.merge_at(-2)
                else:
                    break

        # Regardless of invariants, merge all runs on the stack until only one
        # remains.  This is used at the end of the mergesort.

        def merge_force_collapse(self):
            p = self.pending
            while len(p) > 1:
                if len(p) >= 3 and p[-3].len < p[-1].len:
                    self.merge_at(-3)
                else:
                    self.merge_at(-2)

        # Compute a good value for the minimum run length; natural runs shorter
        # than this are boosted artificially via binary insertion.
        #
        # If n < 64, return n (it's too small to bother with fancy stuff).
        # Else if n is an exact power of 2, return 32.
        # Else return an int k, 32 <= k <= 64, such that n/k is close to, but
        # strictly less than, an exact power of 2.
        #
        # See listsort.txt for more info.

        def merge_compute_minrun(self, n):
            r = 0    # becomes 1 if any 1 bits are shifted off
            while n >= 64:
                r |= n & 1
                n >>= 1
            return n + r

        # ____________________________________________________________
        # Entry point.

        def sort(self):
            remaining = ListSlice(self.list, 0, self.listlength)
            if remaining.len < 2:
                return

            # March over the array once, left to right, finding natural runs,
            # and extending short natural runs to minrun elements.
            self.merge_init()
            minrun = self.merge_compute_minrun(remaining.len)

            while remaining.len > 0:
                # Identify next run.
                run, descending = self.count_run(remaining)
                if descending:
                    run.reverse()
                # If short, extend to min(minrun, nremaining).
                if run.len < minrun:
                    sorted = run.len
                    run.len = min(minrun, remaining.len)
                    self.binarysort(run, sorted)
                # Advance remaining past this run.
                remaining.advance(run.len)
                # Push run onto pending-runs stack, and maybe merge.
                self.pending.append(run)
                self.merge_collapse()

            assert remaining.base == self.listlength

            self.merge_force_collapse()
            assert len(self.pending) == 1
            assert self.pending[0].base == 0
            assert self.pending[0].len == self.listlength


    class ListSlice:
        "A sublist of a list."

        def __init__(self, list, base, len):
            self.list = list
            self.base = base
            self.len  = len

        def copyitems(self):
            "Make a copy of the slice of the original list."
            start = self.base
            stop  = self.base + self.len
            assert 0 <= start <= stop     # annotator hint
            return ListSlice(self.list[start:stop], 0, self.len)

        def advance(self, n):
            self.base += n
            self.len -= n

        def popleft(self):
            result = self.list[self.base]
            self.base += 1
            self.len -= 1
            return result

        def popright(self):
            self.len -= 1
            return self.list[self.base + self.len]

        def reverse(self):
            "Reverse the slice in-place."
            list = self.list
            lo = self.base
            hi = lo + self.len - 1
            while lo < hi:
                list[lo], list[hi] = list[hi], list[lo]
                lo += 1
                hi -= 1
    return TimSort

TimSort = make_timsort_class() #backward compatible interface
