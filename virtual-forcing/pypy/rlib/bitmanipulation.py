from pypy.rlib import unroll

class BitSplitter(dict):
    def __getitem__(self, lengths):
        if isinstance(lengths, int):
            lengths = (lengths, )
        if lengths in self:
            return dict.__getitem__(self, lengths)
        unrolling_lenghts = unroll.unrolling_iterable(lengths)
        def splitbits(integer):
            result = ()
            sum = 0
            for length in unrolling_lenghts:
                sum += length
                n = integer & ((1<<length) - 1)
                assert n >= 0
                result += (n, )
                integer = integer >> length
            assert sum <= 32
            return result
        splitbits.func_name += "_" + "_".join([str(i) for i in lengths])
        self[lengths] = splitbits
        return splitbits

    def _freeze_(self):
        # as this class is not in __builtin__, we need to explicitly tell
        # the flow space that the object is frozen and the accesses can
        # be constant-folded.
        return True

splitter = BitSplitter()
