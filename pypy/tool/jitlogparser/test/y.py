
def fn_with_bridges(N):
    result = 0
    for x in xrange(N):
        if x % 3 == 0:
            result += 5
        elif x % 5 == 0:
            result += 3
        elif is_prime(x):
            result += x
        elif x == 99:
            result *= 2
    return result


def is_prime(x):
    for y in xrange(2, x):
        if x % y == 0:
            return False
    return True


fn_with_bridges(10000)

