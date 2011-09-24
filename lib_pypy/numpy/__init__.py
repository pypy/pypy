from _numpy import (
        array,
        dtype,
        ufunc,

        zeros,
        empty,
        ones,
        fromstring,

        abs,
        absolute,
        add,
        arccos,
        arcsin,
        arctan,
        copysign,
        cos,
        divide,
        equal,
        exp,
        fabs,
        floor,
        greater,
        greater_equal,
        less,
        less_equal,
        maximum,
        minimum,
        multiply,
        negative,
        not_equal,
        reciprocal,
        sign,
        sin,
        subtract,
        tan,
    )

def average(a):
    # This implements a weighted average, for now we don't implement the
    # weighting, just the average part!
    return mean(a)

def mean(a):
    if not hasattr(a, "mean"):
        a = array(a)
    return a.mean()
