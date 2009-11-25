from sup import run

def w(N, start):
    class A(object):
        def f(self, a, b, *args):
            pass

    a = A()
    f = a.f
    z = (3, 4, 5)

    start()
    i = 0
    while i < N:
        f(1, 2, *z)
        f(1, 2, *z)
        f(1, 2, *z)
        f(1, 2, *z)
        f(1, 2, *z)
        f(1, 2, *z)
        f(1, 2, *z)
        f(1, 2, *z)
        f(1, 2, *z)
        f(1, 2, *z)
        f(1, 2, *z)
        f(1, 2, *z)
        i+=1

run(w, 1000)
