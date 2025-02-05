

def test_crash():
    # this used to crash but was fixed in 991642901c20
    # see issue #4031
    k = 15
    m = 3
    
    for a in range(k + 1):
        for b in range(k + 1):
            for c in range(min(m, k) + 1):
                for d in range(min(m, k) + 1):
                    continue
    return


def test_property_immutability_bug():
    class A(object):
        @property
        def x(self):
            return 23


    def f():
        res = 0
        for i in range(10000):
            res += A().x
        return res

    res = f()
    assert res == 10000 * 23

    A.x.__init__(lambda self: 24)

    res = f()
    assert res == 10000 * 24

def test_gigantic_trace_limit():
    import pypyjit
    try:
        pypyjit.set_param(trace_limit=100000)
    finally:
        pypyjit.set_param("default")
