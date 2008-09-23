from sup import run

def w(N, start):
    def f0():
        pass
    def f1(a):
        pass
    def f2(a, b):
        pass
    def f3(a, b, c):
        pass
    def f4(a, b, c, d):
        pass
    def f5(a, b, c, d, e):
        pass

    start()
    i = 0
    while i < N:
        f0()
        f0()
        f0()
        f1(1)
        f1(1)
        f2(1, 2)
        f3(1, 2, 3)
        f4(1, 2, 3, 4)
        f5(1, 2, 3, 4, 5)
        f0()
        f0()
        f0()
        f1(1)
        f1(1)
        f2(1, 2)
        f3(1, 2, 3)
        f4(1, 2, 3, 4)        
        i+=1

run(w, 1000)
