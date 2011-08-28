from pypy.translator.stackless.test.test_transform import \
     llinterp_stackless_function, run_stackless_function
from pypy.rlib import rstack


def test_simple():
    import py; py.test.skip("to be rewritten with gc_x_clone")
    def g(lst):
        lst.append(1)
        parent = rstack.yield_current_frame_to_caller()
        # compute a bit
        lst.append(3)
        # switch back for the fork
        parent = parent.switch()
        lst.append(6)   # we are here twice!
        return parent

    def f():
        lst = []
        c = g(lst)
        lst.append(2)
        c1 = c.switch()
        lst.append(4)
        c2 = c1.clone()      # clone() here
        lst.append(5)
        end1 = c1.switch()
        lst.append(7)
        end2 = c2.switch()
        lst.append(8)
        assert not end1
        assert not end2
        n = 0
        for i in lst:
            n = n*10 + i
        return n

    data = llinterp_stackless_function(f)
    assert data == 123456768

    res = run_stackless_function(f)
    assert res == 123456768
