from sup import run

def w(N, start):
    x = range(50)
    class A(object):
        def f1(self, a):
            return False

    x = range(50)
    a = A()
    f1 = a.f1
    flt = filter

    start()
    i = 0
    while i < N:
        flt(f1, x)
        i+=1

run(w, 200)
