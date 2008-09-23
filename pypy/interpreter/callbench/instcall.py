from sup import run

def w(N, start):
    class A(object):
        def __call__(self):
            pass

    a = A()

    start()
    i = 0
    while i < N:
        a()
        a()
        a()
        a()
        a()
        a()
        a()
        a()
        a()
        a()
        a()
        a()
        a()
        a()
        a()
        a()
        a()
        a()        
        a()
        a()
        i+=1
    
run(w, 1000)
