from rpython.jit.metainterp.counter import JitCounter


def test_tick():
    jc = JitCounter()
    incr = jc.compute_threshold(4)
    for i in range(5):
        r = jc.tick(1234567, incr)
        assert r is (i >= 3)
    for i in range(5):
        r = jc.tick(1234568, incr)
        s = jc.tick(1234569, incr)
        assert r is (i >= 3)
        assert s is (i >= 3)
    jc.reset(1234568)
    for i in range(5):
        r = jc.tick(1234568, incr)
        s = jc.tick(1234569, incr)
        assert r is (i >= 3)
        assert s is True

def test_install_new_chain():
    class Dead:
        next = None
        def should_remove_jitcell(self):
            return True
    class Alive:
        next = None
        def should_remove_jitcell(self):
            return False
    #
    jc = JitCounter()
    assert jc.lookup_chain(1234567) is None
    d1 = Dead()
    jc.install_new_cell(1234567, d1)
    assert jc.lookup_chain(1234567) is d1
    d2 = Dead()
    jc.install_new_cell(1234567, d2)
    assert jc.lookup_chain(1234567) is d2
    assert d2.next is None
    #
    d3 = Alive()
    jc.install_new_cell(1234567, d3)
    assert jc.lookup_chain(1234567) is d3
    assert d3.next is None
    d4 = Alive()
    jc.install_new_cell(1234567, d4)
    assert jc.lookup_chain(1234567) is d3
    assert d3.next is d4
    assert d4.next is None
