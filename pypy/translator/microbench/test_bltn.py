N = int(2**19 - 1)

#
def test_call_sin():
    from math import sin
    
    x = 1.0
    c = 0
    n = N
    while c < n:
        x = sin(x)
        c += 1
