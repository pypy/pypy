from stackless_ import *

def f(outchan):
    for i in range(10):
        print 'f send',i
        outchan.send(i)
    outchan.send(-1)

def g(inchan):
    while 1:
        val = inchan.receive()
        if val == -1:
            break
        print 'g received',val

ch = channel()
t1 = tasklet(f)(ch)
t2 = tasklet(g)(ch)

t1.run()
