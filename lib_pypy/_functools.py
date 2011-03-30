""" Supplies the internal functions for functools.py in the standard library """

# reduce() has moved to _functools in Python 2.6+.
reduce = reduce

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
        self.keywords = keywords

    def __call__(self, *fargs, **fkeywords):
        newkeywords = self.keywords.copy()
        newkeywords.update(fkeywords)
        return self.func(*(self.args + fargs), **newkeywords)

