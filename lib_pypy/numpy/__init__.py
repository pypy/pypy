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

__SIGNEDLTR = "i"
__UNSIGNEDLTR = "u"

def bincount(x, weights=None, minlength=None):
    if minlength is not None:
        result = [0 for _ in range(minlength)]
    else:
        result = [0]

    if len(x) == 0:
        raise ValueError("the first argument cannot be empty.")

    x = array(x)
    if x.dtype.kind not in (__SIGNEDLTR, __UNSIGNEDLTR):
        raise TypeError("array cannot be safely cast to required type")


    if len(x.shape) > 1:
        raise ValueError("object too deep for desired array")

    if weights is not None:
        weights = array(weights)
        if weights.shape != x.shape:
            raise ValueError("The weights and list don't have the same length.")

        num_iter = (num_and_weight for num_and_weight in zip(x, weights))

    else:
        num_iter = ((num, 1) for num in x)

    for number, weight in num_iter:
        if number < 0:
            raise ValueError("The first argument of bincount must be non-negative")
        try:
            result[number] += weight
        except IndexError:
            result += [0] * (number - len(result)) + [weight]

    return array(result)

