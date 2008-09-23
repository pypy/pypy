from sup import run

def w(N, start):
    class A(object):
        def foo(self, x):
            pass

        __add__ = foo

    a = A()
    a1 = A()

    start()
    i = 0
    while i < N:
        a + a1
        a + a1
        a + a1
        a + a1
        a + a1
        a + a1
        a + a1
        a + a1
        a + a1
        a + a1
        a + a1
        a + a1
        a + a1
        a + a1
        a + a1
        a + a1
        a + a1
        a + a1
        i+=1
    
run(w, 1000)
