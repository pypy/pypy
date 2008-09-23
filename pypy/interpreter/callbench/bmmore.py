from sup import run

def w(N, start):
    class A(object):
        def f4(self, a, b, c, d):
            pass
        def f5(self, a, b, c, d, e):
            pass
    a = A()
    f4 = a.f4
    f5 = a.f5

    start()
    i = 0
    while i < N:
        f4(1, 2, 3, 4)
        f4(1, 2, 3, 4)
        f4(1, 2, 3, 4)    
        f5(1, 2, 3, 4, 5)
        f5(1, 2, 3, 4, 5)
        f5(1, 2, 3, 4, 5)
        f4(1, 2, 3, 4)
        f4(1, 2, 3, 4)
        f4(1, 2, 3, 4)    
        f5(1, 2, 3, 4, 5)
        f5(1, 2, 3, 4, 5)
        f5(1, 2, 3, 4, 5)        
        i+=1
    
run(w, 1000)
