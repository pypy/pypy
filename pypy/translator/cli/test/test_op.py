from pypy.translator.cli.test.runtest import check

def test_op():
    for name, func in globals().iteritems():
        if name.startswith('op_'):
            yield check, func, [int, int], (3, 4)


def op_neg(x, y):
    return -x

def op_less_equal(x, y):
    return x<=y

def op_and_not(x, y):
    return x and (not y)

def op_shift(x, y):
    return x<<3 + y>>4

def op_bit_and_or_not_xor(x, y):
    return (x&y) | ~(x^y)

def op_operations(x, y):
    return (x*y) / (x-y) +(-x)
