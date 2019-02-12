import __builtin__ as builtins
import math
import struct
from fractions import gcd
from _audioop_cffi import ffi, lib


_buffer = memoryview


class error(Exception):
    pass


def _check_size(size):
    if size != 1 and size != 2 and size != 4:
        raise error("Size should be 1, 2 or 4")


def _check_params(length, size):
    _check_size(size)
    if length % size != 0:
        raise error("not a whole number of frames")


def _check_state(state):
    if state is None:
        valpred = 0
        index = 0
    else:
        valpred, index = state
        if not (-0x8000 <= valpred < 0x8000 and 0 <= index < 89):
            raise ValueError("bad state")
    return (valpred, index)


def _sample_count(cp, size):
    return len(cp) // size


def _get_samples(cp, size, signed=True):
    for i in range(_sample_count(cp, size)):
        yield _get_sample(cp, size, i, signed)


def _struct_format(size, signed):
    if size == 1:
        return "b" if signed else "B"
    elif size == 2:
        return "h" if signed else "H"
    elif size == 4:
        return "i" if signed else "I"


def _get_sample(cp, size, i, signed=True):
    fmt = _struct_format(size, signed)
    start = i * size
    end = start + size
    return struct.unpack_from(fmt, _buffer(cp)[start:end])[0]


def _put_sample(cp, size, i, val, signed=True):
    fmt = _struct_format(size, signed)
    struct.pack_into(fmt, cp, i * size, val)


def _get_maxval(size, signed=True):
    if signed and size == 1:
        return 0x7f
    elif size == 1:
        return 0xff
    elif signed and size == 2:
        return 0x7fff
    elif size == 2:
        return 0xffff
    elif signed and size == 4:
        return 0x7fffffff
    elif size == 4:
        return 0xffffffff


def _get_minval(size, signed=True):
    if not signed:
        return 0
    elif size == 1:
        return -0x80
    elif size == 2:
        return -0x8000
    elif size == 4:
        return -0x80000000


def _get_clipfn(size, signed=True):
    maxval = _get_maxval(size, signed)
    minval = _get_minval(size, signed)
    return lambda val: builtins.max(min(val, maxval), minval)


def _overflow(val, size, signed=True):
    minval = _get_minval(size, signed)
    maxval = _get_maxval(size, signed)
    if minval <= val <= maxval:
        return val

    bits = size * 8
    if signed:
        offset = 2**(bits-1)
        return ((val + offset) % (2**bits)) - offset
    else:
        return val % (2**bits)


def getsample(cp, size, i):
    _check_params(len(cp), size)
    if not (0 <= i < len(cp) // size):
        raise error("Index out of range")
    return _get_sample(cp, size, i)


def max(cp, size):
    _check_params(len(cp), size)

    if len(cp) == 0:
        return 0

    return builtins.max(abs(sample) for sample in _get_samples(cp, size))


def minmax(cp, size):
    _check_params(len(cp), size)

    min_sample, max_sample = 0x7fffffff, -0x80000000
    for sample in _get_samples(cp, size):
        max_sample = builtins.max(sample, max_sample)
        min_sample = builtins.min(sample, min_sample)

    return min_sample, max_sample


def avg(cp, size):
    _check_params(len(cp), size)
    sample_count = _sample_count(cp, size)
    if sample_count == 0:
        return 0
    return sum(_get_samples(cp, size)) // sample_count


def rms(cp, size):
    _check_params(len(cp), size)

    sample_count = _sample_count(cp, size)
    if sample_count == 0:
        return 0

    sum_squares = sum(sample**2 for sample in _get_samples(cp, size))
    return int(math.sqrt(sum_squares // sample_count))


def _sum2(cp1, cp2, length):
    size = 2
    return sum(getsample(cp1, size, i) * getsample(cp2, size, i)
               for i in range(length)) + 0.0


def findfit(cp1, cp2):
    size = 2

    if len(cp1) % 2 != 0 or len(cp2) % 2 != 0:
        raise error("Strings should be even-sized")

    if len(cp1) < len(cp2):
        raise error("First sample should be longer")

    len1 = _sample_count(cp1, size)
    len2 = _sample_count(cp2, size)

    sum_ri_2 = _sum2(cp2, cp2, len2)
    sum_aij_2 = _sum2(cp1, cp1, len2)
    sum_aij_ri = _sum2(cp1, cp2, len2)

    result = (sum_ri_2 * sum_aij_2 - sum_aij_ri * sum_aij_ri) / sum_aij_2

    best_result = result
    best_i = 0

    for i in range(1, len1 - len2 + 1):
        aj_m1 = _get_sample(cp1, size, i - 1)
        aj_lm1 = _get_sample(cp1, size, i + len2 - 1)

        sum_aij_2 += aj_lm1**2 - aj_m1**2
        sum_aij_ri = _sum2(_buffer(cp1)[i*size:], cp2, len2)

        result = (sum_ri_2 * sum_aij_2 - sum_aij_ri * sum_aij_ri) / sum_aij_2

        if result < best_result:
            best_result = result
            best_i = i

    factor = _sum2(_buffer(cp1)[best_i*size:], cp2, len2) / sum_ri_2

    return best_i, factor


def findfactor(cp1, cp2):
    size = 2

    if len(cp1) % 2 != 0:
        raise error("Strings should be even-sized")

    if len(cp1) != len(cp2):
        raise error("Samples should be same size")

    sample_count = _sample_count(cp1, size)

    sum_ri_2 = _sum2(cp2, cp2, sample_count)
    sum_aij_ri = _sum2(cp1, cp2, sample_count)

    return sum_aij_ri / sum_ri_2


def findmax(cp, len2):
    size = 2
    sample_count = _sample_count(cp, size)

    if len(cp) % 2 != 0:
        raise error("Strings should be even-sized")

    if len2 < 0 or sample_count < len2:
        raise error("Input sample should be longer")

    if sample_count == 0:
        return 0

    result = _sum2(cp, cp, len2)
    best_result = result
    best_i = 0

    for i in range(1, sample_count - len2 + 1):
        sample_leaving_window = getsample(cp, size, i - 1)
        sample_entering_window = getsample(cp, size, i + len2 - 1)

        result -= sample_leaving_window**2
        result += sample_entering_window**2

        if result > best_result:
            best_result = result
            best_i = i

    return best_i


def avgpp(cp, size):
    _check_params(len(cp), size)
    sample_count = _sample_count(cp, size)
    if sample_count <= 2:
        return 0

    prevextremevalid = False
    prevextreme = None
    avg = 0
    nextreme = 0

    prevval = getsample(cp, size, 0)
    val = getsample(cp, size, 1)

    prevdiff = val - prevval

    for i in range(1, sample_count):
        val = getsample(cp, size, i)
        diff = val - prevval

        if diff * prevdiff < 0:
            if prevextremevalid:
                avg += abs(prevval - prevextreme)
                nextreme += 1

            prevextremevalid = True
            prevextreme = prevval

        prevval = val
        if diff != 0:
            prevdiff = diff

    if nextreme == 0:
        return 0

    return avg // nextreme


def maxpp(cp, size):
    _check_params(len(cp), size)
    sample_count = _sample_count(cp, size)
    if sample_count <= 1:
        return 0

    prevextremevalid = False
    prevextreme = None
    max = 0

    prevval = getsample(cp, size, 0)
    val = getsample(cp, size, 1)

    prevdiff = val - prevval

    for i in range(1, sample_count):
        val = getsample(cp, size, i)
        diff = val - prevval

        if diff * prevdiff < 0:
            if prevextremevalid:
                extremediff = abs(prevval - prevextreme)
                if extremediff > max:
                    max = extremediff
            prevextremevalid = True
            prevextreme = prevval

        prevval = val
        if diff != 0:
            prevdiff = diff

    return max


def cross(cp, size):
    _check_params(len(cp), size)

    crossings = -1
    last_sample = 17
    for sample in _get_samples(cp, size):
        sample = sample < 0
        if sample != last_sample:
            crossings += 1
        last_sample = sample
    return crossings


def mul(cp, size, factor):
    _check_params(len(cp), size)
    clip = _get_clipfn(size)

    rv = ffi.new("unsigned char[]", len(cp))
    result = ffi.buffer(rv)

    for i, sample in enumerate(_get_samples(cp, size)):
        sample = clip(int(sample * factor))
        _put_sample(result, size, i, sample)

    return result[:]


def tomono(cp, size, fac1, fac2):
    _check_params(len(cp), size)
    clip = _get_clipfn(size)

    sample_count = _sample_count(cp, size)

    rv = ffi.new("unsigned char[]", len(cp) // 2)
    result = ffi.buffer(rv)

    for i in range(0, sample_count, 2):
        l_sample = getsample(cp, size, i)
        r_sample = getsample(cp, size, i + 1)

        sample = (l_sample * fac1) + (r_sample * fac2)
        sample = int(clip(sample))

        _put_sample(result, size, i // 2, sample)

    return result[:]


def tostereo(cp, size, fac1, fac2):
    _check_params(len(cp), size)

    sample_count = _sample_count(cp, size)

    rv = ffi.new("char[]", len(cp) * 2)
    lib.tostereo(rv, cp, len(cp), size, fac1, fac2)
    return ffi.buffer(rv)[:]


def add(cp1, cp2, size):
    _check_params(len(cp1), size)

    if len(cp1) != len(cp2):
        raise error("Lengths should be the same")

    rv = ffi.new("char[]", len(cp1))
    lib.add(rv, cp1, cp2, len(cp1), size)
    return ffi.buffer(rv)[:]


def bias(cp, size, bias):
    _check_params(len(cp), size)

    rv = ffi.new("unsigned char[]", len(cp))
    result = ffi.buffer(rv)

    for i, sample in enumerate(_get_samples(cp, size)):
        sample = _overflow(sample + bias, size)
        _put_sample(result, size, i, sample)

    return result[:]


def reverse(cp, size):
    _check_params(len(cp), size)
    sample_count = _sample_count(cp, size)

    rv = ffi.new("unsigned char[]", len(cp))
    result = ffi.buffer(rv)
    for i, sample in enumerate(_get_samples(cp, size)):
        _put_sample(result, size, sample_count - i - 1, sample)

    return result[:]


def lin2lin(cp, size, size2):
    _check_params(len(cp), size)
    _check_size(size2)

    if size == size2:
        return cp

    new_len = (len(cp) // size) * size2
    rv = ffi.new("unsigned char[]", new_len)
    result = ffi.buffer(rv)

    for i in range(_sample_count(cp, size)):
        sample = _get_sample(cp, size, i)
        if size == 1:
            sample <<= 24
        elif size == 2:
            sample <<= 16
        if size2 == 1:
            sample >>= 24
        elif size2 == 2:
            sample >>= 16
        sample = _overflow(sample, size2)
        _put_sample(result, size2, i, sample)

    return result[:]


def ratecv(cp, size, nchannels, inrate, outrate, state, weightA=1, weightB=0):
    _check_params(len(cp), size)
    if nchannels < 1:
        raise error("# of channels should be >= 1")

    bytes_per_frame = size * nchannels
    frame_count = len(cp) // bytes_per_frame

    if bytes_per_frame // nchannels != size:
        raise OverflowError("width * nchannels too big for a C int")

    if weightA < 1 or weightB < 0:
        raise error("weightA should be >= 1, weightB should be >= 0")

    if len(cp) % bytes_per_frame != 0:
        raise error("not a whole number of frames")

    if inrate <= 0 or outrate <= 0:
        raise error("sampling rate not > 0")

    d = gcd(inrate, outrate)
    inrate //= d
    outrate //= d
    d = gcd(weightA, weightB)
    weightA //= d
    weightB //= d

    if state is None:
        d = -outrate
        prev_i = ffi.new('int[]', nchannels)
        cur_i = ffi.new('int[]', nchannels)
    else:
        d, samps = state

        if len(samps) != nchannels:
            raise error("illegal state argument")

        prev_i, cur_i = zip(*samps)
        prev_i = ffi.new('int[]', prev_i)
        cur_i = ffi.new('int[]', cur_i)
    state_d = ffi.new('int[]', (d,))

    q = frame_count // inrate
    ceiling = (q + 1) * outrate
    nbytes = ceiling * bytes_per_frame

    rv = ffi.new("char[]", nbytes)
    trim_index = lib.ratecv(rv, cp, frame_count, size,
                            nchannels, inrate, outrate,
                            state_d, prev_i, cur_i,
                            weightA, weightB)
    result = ffi.buffer(rv)[:trim_index]
    d = state_d[0]
    samps = zip(prev_i, cur_i)
    return (result, (d, tuple(samps)))


def _get_lin_samples(cp, size):
    for sample in _get_samples(cp, size):
        if size == 1:
            yield sample << 8
        elif size == 2:
            yield sample
        elif size == 4:
            yield sample >> 16


def _put_lin_sample(result, size, i, sample):
    if size == 1:
        sample >>= 8
    elif size == 2:
        pass
    elif size == 4:
        sample <<= 16
    _put_sample(result, size, i, sample)


def lin2ulaw(cp, size):
    _check_params(len(cp), size)
    rv = ffi.new("unsigned char[]", _sample_count(cp, size))
    for i, sample in enumerate(_get_lin_samples(cp, size)):
        rv[i] = lib.st_14linear2ulaw(sample)
    return ffi.buffer(rv)[:]


def ulaw2lin(cp, size):
    _check_size(size)
    rv = ffi.new("unsigned char[]", len(cp) * size)
    result = ffi.buffer(rv)
    for i, value in enumerate(cp):
        sample = lib.st_ulaw2linear16(ord(value))
        _put_lin_sample(result, size, i, sample)
    return result[:]


def lin2alaw(cp, size):
    _check_params(len(cp), size)
    rv = ffi.new("unsigned char[]", _sample_count(cp, size))
    for i, sample in enumerate(_get_lin_samples(cp, size)):
        rv[i] = lib.st_linear2alaw(sample)
    return ffi.buffer(rv)[:]


def alaw2lin(cp, size):
    _check_size(size)
    rv = ffi.new("unsigned char[]", len(cp) * size)
    result = ffi.buffer(rv)
    for i, value in enumerate(cp):
        sample = lib.st_alaw2linear16(ord(value))
        _put_lin_sample(result, size, i, sample)
    return result[:]


def lin2adpcm(cp, size, state):
    _check_params(len(cp), size)
    state = _check_state(state)
    rv = ffi.new("unsigned char[]", len(cp) // size // 2)
    state_ptr = ffi.new("int[]", state)
    lib.lin2adcpm(rv, cp, len(cp), size, state_ptr)
    return ffi.buffer(rv)[:], tuple(state_ptr)


def adpcm2lin(cp, size, state):
    _check_size(size)
    state = _check_state(state)
    rv = ffi.new("unsigned char[]", len(cp) * size * 2)
    state_ptr = ffi.new("int[]", state)
    lib.adcpm2lin(rv, cp, len(cp), size, state_ptr)
    return ffi.buffer(rv)[:], tuple(state_ptr)
