"""
For reference, the MRO algorithm of Python 2.3.
"""


def MRO(cls):

    def register(cls):
        try:
            blocklist = blocking[cls]
        except KeyError:
            blocklist = blocking[cls] = [0]
            prevlist = blocklist
            for base in cls.__bases__:
                prevlist.append(base)
                prevlist = register(base)
        blocklist[0] += 1
        return blocklist

    order = []
    blocking = {}
    register(cls)
    
    unblock = [cls]
    while unblock:
        cls = unblock.pop()
        blocklist = blocking[cls]
        assert blocklist[0] > 0
        blocklist[0] -= 1
        if blocklist[0] == 0:
            order.append(cls)
            unblock += blocklist[:0:-1]

    if len(order) < len(blocking):
        mro_error(blocking)
    return order


def mro_error(blocking):
    # look for a cycle

    def find_cycle(cls):
        path.append(cls)
        blocklist = blocking[cls]   # raise KeyError when we complete the path
        if blocklist[0] > 0:
            del blocking[cls]
            for cls2 in blocklist[1:]:
                find_cycle(cls2)
            blocking[cls] = blocklist
        del path[-1]

    #import pprint; pprint.pprint(blocking)
    path = []
    try:
        for cls in blocking.keys():
            find_cycle(cls)
    except KeyError:
        i = path.index(path[-1])
        names = [cls.__name__ for cls in path[i:]]
        raise TypeError, "Cycle among base classes: " + ' < '.join(names)
    else:
        # should not occur
        raise TypeError, "Cannot create a consistent method resolution order (MRO)"


if __name__ == '__main__':
    class ex_9:
        class O: pass
        class A(O): pass
        class B(O): pass
        class C(O): pass
        class D(O): pass
        class E(O): pass
        class F(O): pass
        class K1(A,B,C): pass
        class K2(D,F,B,E): pass
        class K3(D,A): pass
        class Z(K1,K2,F,K3): pass

    print MRO(ex_9.Z)
