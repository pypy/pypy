import stackless
if hasattr(stackless,'coroutine'):
    import stackless_ as stackless

def f(outchan):
    for i in range(10):
        #print 'f: outchan before:',str(outchan)
        print 'f: sending',i
        outchan.send(i)
        #print 'f: outchan after:',str(outchan)
    outchan.send(-1)

def g(inchan):
    while 1:
        #print 'g: inchan before:',str(inchan)
        val = inchan.receive()
        print 'g: received',val
        #print 'g: inchan after:',str(inchan)
        if val == -1:
            break

ch = stackless.channel()
t1 = stackless.tasklet(f)(ch)
t2 = stackless.tasklet(g)(ch)

t1.run()
