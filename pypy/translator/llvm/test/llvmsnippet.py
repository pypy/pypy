import autopath

def simple1():
    return 1

def simple2():
    return False

def simple3():
    c = "Hello, Stars!"
    return c

def simple4():
    return 3 + simple1()

def simple5(b):
    if b:
        x = 12
    else:
        x = 13
    return x

def simple6():
    simple4()
    return 1

def ackermann(n, m):
    if n == 0:
        return m + 1
    if m == 0:
        return ackermann(n - 1, 1)
    return ackermann(n - 1, ackermann(n, m - 1))


def arraytestsimple():
    a = [42]
    return a[0]

def arraytestsimple1():
    a = [43]
    return a[-1]

def arraytestsetitem(i):
    a = [43]
    a[0] = i * 2
    return a[-1]

