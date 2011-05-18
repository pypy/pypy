
from pypy.interpreter.mixedmodule import MixedModule 

class Module(MixedModule):
    """Functional tools for creating and using iterators.

    Infinite iterators:
    count([n]) --> n, n+1, n+2, ...
    cycle(p) --> p0, p1, ... plast, p0, p1, ...
    repeat(elem [,n]) --> elem, elem, elem, ... endlessly or up to n times

    Iterators terminating on the shortest input sequence:
    izip(p, q, ...) --> (p[0], q[0]), (p[1], q[1]), ... 
    ifilter(pred, seq) --> elements of seq where pred(elem) is True
    ifilterfalse(pred, seq) --> elements of seq where pred(elem) is False
    islice(seq, [start,] stop [, step]) --> elements from
           seq[start:stop:step]
    imap(fun, p, q, ...) --> fun(p0, q0), fun(p1, q1), ...
    starmap(fun, seq) --> fun(*seq[0]), fun(*seq[1]), ...
    tee(it, n=2) --> (it1, it2 , ... itn) splits one iterator into n
    chain(p, q, ...) --> p0, p1, ... plast, q0, q1, ... 
    takewhile(pred, seq) --> seq[0], seq[1], until pred fails
    dropwhile(pred, seq) --> seq[n], seq[n+1], starting when pred fails
    groupby(iterable[, keyfunc]) --> sub-iterators grouped by value of keyfunc(v)
    """

    interpleveldefs = {
        'chain'         : 'interp_itertools.W_Chain',
        'combinations'  : 'interp_itertools.W_Combinations',
        'combinations_with_replacement' : 'interp_itertools.W_CombinationsWithReplacement',
        'compress'      : 'interp_itertools.W_Compress',
        'count'         : 'interp_itertools.W_Count',
        'cycle'         : 'interp_itertools.W_Cycle',
        'dropwhile'     : 'interp_itertools.W_DropWhile',
        'groupby'       : 'interp_itertools.W_GroupBy',
        'ifilter'       : 'interp_itertools.W_IFilter',
        'ifilterfalse'  : 'interp_itertools.W_IFilterFalse',
        'imap'          : 'interp_itertools.W_IMap',
        'islice'        : 'interp_itertools.W_ISlice',
        'izip'          : 'interp_itertools.W_IZip',
        'izip_longest'  : 'interp_itertools.W_IZipLongest',
        'permutations'  : 'interp_itertools.W_Permutations',
        'product'       : 'interp_itertools.W_Product',
        'repeat'        : 'interp_itertools.W_Repeat',
        'starmap'       : 'interp_itertools.W_StarMap',
        'takewhile'     : 'interp_itertools.W_TakeWhile',
        'tee'           : 'interp_itertools.tee',
    }

    appleveldefs = {
    }
