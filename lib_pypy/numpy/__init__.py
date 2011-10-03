from _numpy import (
        array,
        dtype,
        ufunc,

        zeros,
        empty,
        ones,

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

def __from_buffer_or_datastring(buf_or_str, dt, count, offset=0):
    _dtype = dtype(dt)

    if count > 0:
        length = count * _dtype.itemsize
        if length + offset > len(buf_or_str):
            raise ValueError("length of string (%d) not enough for %d %s" %
                             (len(buf_or_str), count, _dtype))

        buf_or_str = buf_or_str[offset:length+offset]
    else:
        length = len(buf_or_str) - offset
        buf_or_str = buf_or_str[offset:]
        if len(buf_or_str) % _dtype.itemsize != 0:
            raise ValueError("length of string (%d) not evenly dividable by size of dtype (%d)" %
                             (len(buf_or_str), _dtype.itemsize))

    arr = empty(length / _dtype.itemsize, dtype=_dtype)
    arr.data[:length] = buf_or_str

    return arr

def frombuffer(buf, dtype=float, count=-1, offset=0):
    return __from_buffer_or_datastring(buf, dtype, count, offset)

def fromstring(s, dtype=float, count=-1, sep=''):
    if sep:
        import numpy as np
        dtype = np.dtype(dtype)

        parts = s.split(sep)
        clean_parts = [part for part in parts if part]
        if count >= 0:
            clean_parts = clean_parts[:count]

        if dtype.kind == "f":
            cast_func = float
        elif dtype.kind == "i":
            cast_func = int
        else:
            raise TypeError("Can only read int-likes or float-likes from strings.")

        result = empty(len(clean_parts), dtype=dtype)
        for number, value in enumerate(clean_parts):
            result[number] = cast_func(value)

        return result

    return __from_buffer_or_datastring(s, dtype, count)

def fromfile(file, dtype=float, count=-1, sep=''):
    if isinstance(file, basestring):
        file = open(file, "r")
    return fromstring(file.read(), dtype, count, sep)
