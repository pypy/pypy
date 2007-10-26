from pypy.rlib import unroll

# terrible hack to make the annotator think this is a real dict
__name__ = '__builtin__'

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
        
splitter = BitSplitter()
