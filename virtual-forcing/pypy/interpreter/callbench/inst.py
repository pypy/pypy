from sup import run

def w(N, start):
    class A(object):
        def __init__(self):
            pass

    class B(object):
        def __init__(self, x, y):
            pass

    start()
    i = 0
    while i < N:
        A()
        A()
        A()
        A()
        A()
        B(1, 2)
        B(1, 2)
        B(1, 2)   
        B(1, 2)
        i+=1
    
run(w, 1000)
