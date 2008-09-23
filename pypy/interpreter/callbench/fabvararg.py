from sup import run

def w(N, start):
    def f(a, b, *args):
        pass

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
