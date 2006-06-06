import stackless
if hasattr(stackless,'coroutine'):
    import stackless_ as stackless

DEBUG = False

def print_sched(prev, next):
    try:
        print 'before scheduling. prev: %s, next: %s' % (prev, next)
    except Exception, e:
        print 'Exception in print_sched', e
        print '\tprev:', type(prev)
        print '\tnext:', type(next)
    print

def print_chan(chan, task, sending, willblock):
    print 'channel_action:', chan, task, 's:', sending, ' wb:',
    print willblock
    print

if DEBUG:
    stackless.set_schedule_callback(print_sched)
    stackless.set_channel_callback(print_chan)

def f(outchan):
    for i in range(10):
        print 'f: sending',i
        print
        outchan.send(i)
    outchan.send(-1)

def g(inchan):
    while 1:
        val = inchan.receive()
        print 'g: received',val
        print
        if val == -1:
            break

ch = stackless.channel()
t1 = stackless.tasklet(f)(ch)
t2 = stackless.tasklet(g)(ch)

stackless.run()
