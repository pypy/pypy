"""
For reference, the MRO algorithm of Python 2.3.
"""



def mro(cls):
    order = []
    orderlists = [mro(base) for base in cls.__bases__]
    orderlists.append([cls] + list(cls.__bases__))
    while orderlists:
        for candidatelist in orderlists:
            candidate = candidatelist[0]
            if blockinglist(candidate, orderlists) is None:
                break    # good candidate
        else:
            mro_error(orderlists)  # no candidate found
        assert candidate not in order
        order.append(candidate)
        for i in range(len(orderlists)-1, -1, -1):
            if orderlists[i][0] == candidate:
                del orderlists[i][0]
                if len(orderlists[i]) == 0:
                    del orderlists[i]
    return order

def blockinglist(candidate, orderlists):
    for lst in orderlists:
        if candidate in lst[1:]:
            return lst
    return None  # good candidate

def mro_error(orderlists):
    cycle = []
    candidate = orderlists[0][0]
    while candidate not in cycle:
        cycle.append(candidate)
        nextblockinglist = blockinglist(candidate, orderlists)
        candidate = nextblockinglist[0]
    # avoid the only use of list.index in the PyPy code base:
    i = 0
    for c in cycle:
        if c == candidate:
            break
        i += 1
    del cycle[:i]
    cycle.append(candidate)
    cycle.reverse()
    names = [cls.__name__ for cls in cycle]
    raise TypeError, "Cycle among base classes: " + ' < '.join(names)


def mronames(cls):
    names = [cls.__name__ for cls in mro(cls)]
    return names


if __name__ == '__main__':
    class ex_9:
        #O = object
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
        class ZM(K1,K2,K3): pass
        #print ZM.__mro__

    print 'K1:', mronames(ex_9.K1)
    print 'K2:', mronames(ex_9.K2)
    print 'K3:', mronames(ex_9.K3)
    print mronames(ex_9.ZM)
    print mronames(ex_9.Z)
