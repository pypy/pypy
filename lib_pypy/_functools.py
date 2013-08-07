""" Supplies the internal functions for functools.py in the standard library """
try: from __pypy__ import builtinify
except ImportError: builtinify = lambda f: f


sentinel = object()

@builtinify
def reduce(func, sequence, initial=sentinel):
    """reduce(function, sequence[, initial]) -> value

Apply a function of two arguments cumulatively to the items of a sequence,
from left to right, so as to reduce the sequence to a single value.
For example, reduce(lambda x, y: x+y, [1, 2, 3, 4, 5]) calculates
((((1+2)+3)+4)+5).  If initial is present, it is placed before the items
of the sequence in the calculation, and serves as a default when the
sequence is empty."""
    iterator = iter(sequence)
    if initial is sentinel:
        try:
            initial = next(iterator)
        except StopIteration:
            raise TypeError("reduce() of empty sequence with no initial value")
    result = initial
    for item in iterator:
        result = func(result, item)
    return result


class partial(object):
    """
    partial(func, *args, **keywords) - new function with partial application
    of the given arguments and keywords.
    """

    def __init__(self, func, *args, **keywords):
        if not callable(func):
            raise TypeError("the first argument must be callable")
        self.func = func
        self.args = args
        self.keywords = keywords or None

    def __call__(self, *fargs, **fkeywords):
        if self.keywords is not None:
            fkeywords = dict(self.keywords, **fkeywords)
        return self.func(*(self.args + fargs), **fkeywords)

    def __repr__(self):
        cls = type(self)
        if cls is partial:
            name = 'functools.partial'
        else:
            name = cls.__name__
        tmp = [repr(self.func)]
        for arg in self.args:
            tmp.append(repr(arg))
        if self.keywords:
            for k, v in self.keywords.items():
                tmp.append("{}={!r}".format(k, v))
        return "{}({})".format(name, ', '.join(tmp))

    def __reduce__(self):
        d = dict((k, v) for k, v in self.__dict__.items() if k not in
                ('func', 'args', 'keywords'))
        if len(d) == 0:
            d = None
        return (type(self), (self.func,),
                (self.func, self.args, self.keywords, d))

    def __setstate__(self, state):
        self.func, self.args, self.keywords, d = state
        if d is not None:
            self.__dict__.update(d)
