from pypy.module.transaction.fifo import Fifo

class Item:
    def __init__(self, value):
        self.value = value

def test_one_item():
    f = Fifo()
    assert f.is_empty()
    f.append(Item(123))
    assert not f.is_empty()
    item = f.popleft()
    assert f.is_empty()
    assert item.value == 123

def test_three_items():
    f = Fifo()
    for i in [10, 20, 30]:
        f.append(Item(i))
        assert not f.is_empty()
    for i in [10, 20, 30]:
        assert not f.is_empty()
        item = f.popleft()
        assert item.value == i
    assert f.is_empty()

def test_steal():
    for n1 in range(3):
        for n2 in range(3):
            f1 = Fifo()
            f2 = Fifo()
            for i in range(n1): f1.append(Item(10 + i))
            for i in range(n2): f2.append(Item(20 + i))
            f1.steal(f2)
            assert f2.is_empty()
            for x in range(10, 10+n1) + range(20, 20+n2):
                assert not f1.is_empty()
                item = f1.popleft()
                assert item.value == x
            assert f1.is_empty()
