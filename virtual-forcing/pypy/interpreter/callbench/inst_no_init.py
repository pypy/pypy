from sup import run

def w(N, start):
    class A(object):
        pass

    start()
    i = 0
    while i < N:
        A()
        A()
        A()
        A()
        A()
        A()
        A()
        A()
        A()
        A()
        i+=1
    
run(w, 1000)
