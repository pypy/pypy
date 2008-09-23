import sys, time

def ref(N, start):
    start()
    i = 0
    while i < N:
        i+=1


def run(func, n):
    n *= int(sys.argv[1])
    st = [None]
    t = time.time

    def start():
        st[0] = t()

    ref(n, start)
    elapsed_ref1 = t() - st[0]
    ref(n, start)
    elapsed_ref2 = t() - st[0]
    ref(n, start)
    elapsed_ref3 = t() - st[0]    
    elapsed_ref = min(elapsed_ref1, elapsed_ref2, elapsed_ref3)

    func(n, start)
    elapsed1 = t() - st[0]
    func(n, start)
    elapsed2 = t() - st[0]
    func(n, start)
    elapsed3 = t() - st[0]
    elapsed = min(elapsed1, elapsed2, elapsed3)    

    #if elapsed < elapsed_ref*10:
    #    print "not enough meat", elapsed, elapsed_ref

    print sys.argv[0].replace('.py', ''), elapsed-elapsed_ref
    

