N = int(2**19 - 1)

def test_loop():
    x = 0
    n = N
    while x < n:
        x = x + 1

#
def plus1(x):
    return x + 1

def test_call_function():
    x = 0
    n = N
    while x < n:
        x = plus1(x) 

#
