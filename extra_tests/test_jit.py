

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

