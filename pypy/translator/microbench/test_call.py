N = int(2**19 - 1)

def f1(x):
    return x + 1

def test_call_1():
    c = 0
    n = N
    while c < n:
        c = f1(c)

def f2(x, y):
    return x + y

def test_call_2():
    c = 0
    n = N
    while c < n:
        c = f2(c, 1)


def f3(x, y, z):
    return x + y * z

def test_call_3():
    c = 0
    n = N
    while c < n:
        c = f3(c, 1, 1)


def f4(w, x, y, z):
    return x + y * z / w

def test_call_4():
    c = 0
    n = N
    while c < n:
        c = f4(1, c, 1, 1)

# __________________________________________


def d4(x, y=1, z=1, w=1):
    return x + y * z / w

def test_call_default_1():
    c = 0
    n = N
    while c < n:
        c = d4(c)

def test_call_default_2():
    c = 0
    n = N
    while c < n:
        c = d4(c, 1)


# __________________________________________


def test_call_keyword_1():
    c = 0
    n = N
    while c < n:
        c = d4(c, z=1)

def test_call_keyword_2():
    c = 0
    n = N
    while c < n:
        c = d4(c, z=1, w=1)

def test_call_keyword_3():
    c = 0
    n = N
    while c < n:
        c = d4(c, z=1, w=1, y=1)
