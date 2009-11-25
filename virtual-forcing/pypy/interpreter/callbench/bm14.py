from sup import run

def w(N, start):
    class A(object):
        def f0(self):
            pass
        def f1(self, a):
            pass
        def f2(self, a, b):
            pass
        def f3(self, a, b, c):
            pass
        def f4(self, a, b, c, d):
            pass

    a = A()
    f0 = a.f0
    f1 = a.f1
    f2 = a.f2
    f3 = a.f3
    f4 = a.f4

    start()
    i = 0
    while i < N:
        f0()
        f0()
        f0()
        f0()
        f1(1)
        f1(1)
        f1(1)
        f1(1)
        f2(1, 2)
        f2(1, 2)
        f2(1, 2)
        f3(1, 2, 3)
        f3(1, 2, 3)
        f4(1, 2, 3, 4)

        f0()
        f0()
        f0()
        f1(1)
        f1(1)
        f1(1)
        f2(1, 2)
        
        i+=1

run(w, 1000)
