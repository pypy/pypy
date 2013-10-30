from rpython.jit.metainterp.counter import JitCounter


def test_get_index():
    jc = JitCounter(size=128)    # 7 bits
    for i in range(10):
        hash = 400000001 * i
        index = jc.get_index(hash)
        assert index == (hash >> (32 - 7))

def test_fetch_next_index():
    jc = JitCounter(size=4)
    lst = [jc.fetch_next_index() for i in range(10)]
    assert lst == [0, 1, 2, 3, 0, 1, 2, 3, 0, 1]

def test_tick():
    jc = JitCounter()
    incr = jc.compute_threshold(4)
    for i in range(5):
        r = jc.tick(104, incr)
        assert r is (i >= 3)
    for i in range(5):
        r = jc.tick(108, incr)
        s = jc.tick(109, incr)
        assert r is (i >= 3)
        assert s is (i >= 3)
    jc.reset(108)
    for i in range(5):
        r = jc.tick(108, incr)
        s = jc.tick(109, incr)
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
    assert jc.lookup_chain(104) is None
    d1 = Dead() 
    jc.install_new_cell(104, d1)
    assert jc.lookup_chain(104) is d1
    d2 = Dead()
    jc.install_new_cell(104, d2)
    assert jc.lookup_chain(104) is d2
    assert d2.next is None
    #
    d3 = Alive()
    jc.install_new_cell(104, d3)
    assert jc.lookup_chain(104) is d3
    assert d3.next is None
    d4 = Alive()
    jc.install_new_cell(104, d4)
    assert jc.lookup_chain(104) is d3
    assert d3.next is d4
    assert d4.next is None
