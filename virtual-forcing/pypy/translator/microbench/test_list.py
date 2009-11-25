
iterations = 500000

d_x = {}
it_range = range(iterations)


def test_list_append():
    l = []
    for x in it_range:
        l.append(x)


def test_list_setitem():
    l = range(iterations / 2)
    idx = iterations / 2 - 200
    for x in it_range:
        l[idx] = x
        l[idx - 300] = x
        l[idx - 42] = x
        l[idx + 3] = x


def test_list_slice():
    l = range(iterations / 2)
    l.append("foo")
    for x in range(500):
        l[42:420]
        l[500:76:-3]

def test_list_getitem():
    l = range(iterations / 2)
    l.append("foo")
    idx = iterations / 43
    for x in it_range:
        l[8]
        l[idx]
        l[3]


def test_list_extend():
    l = range(iterations / 2)
    l.append("foo")
    k = l[:]
    for x in range(50):
        t = l[:]
        t.extend(k)

