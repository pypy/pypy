from sup import run

def w(N, start):
    def f1(a):
        return False
    x = range(50)

    start()
    i = 0
    while i < N:
        filter(f1, x)
        i+=1
    
run(w, 200)
