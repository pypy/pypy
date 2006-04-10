from pypy.translator.cli.test.runtest import check

def test_list():
    for name, func in globals().iteritems():
        if not name.startswith('list_'):
            continue

        yield check, func, [int, int], (42, 13)


def create(x, y):
    return [x, y, x+y, x*y]

def sum_(lst):
    total = 0
    i = 0
    while i < len(lst):
        total += lst[i]
        i += 1

    return total    

def list_sum(x, y):
    return sum_(create(x, y))

def list_setitem(x, y):
    lst = create(x, y)
    lst[0] = 0
    lst[1] = 0
    return sum_(lst)
