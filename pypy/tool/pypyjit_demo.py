
def g(i):
    k = 0
    while k < 3:
        k += 1
    return i + 1

def f(x):
    for i in range(10000):
        t = (1, 2, i)
        i = g(i)
        x == t



try:
    f((1, 2, 3))

except Exception, e:
    print "Exception: ", type(e)
    print e

