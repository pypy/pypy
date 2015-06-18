

class AppTestHashtable:
    spaceconfig = dict(usemodules=['pypystm'])

    def test_simple(self):
        import pypystm
        q = pypystm.queue()
        obj = []
        q.put(obj)
        obj1 = q.get()
        assert obj1 is obj
        raises(pypystm.Empty, q.get, block=False)
        raises(pypystm.Empty, q.get, timeout=0.01)
        q.put(obj)
        obj1 = q.get(block=False)
        assert obj1 is obj
        q.put(obj)
        obj1 = q.get(timeout=0.01)
        assert obj1 is obj
