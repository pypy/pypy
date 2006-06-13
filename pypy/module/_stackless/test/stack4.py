"""
this test shows what happens, when trying to use an already closed channel
"""

import sys
import stackless
if hasattr(stackless,'coroutine'):
    import stackless_ as stackless

def f(outchan):
    v = 1
    print 'f sending',v
    outchan.send(v)
    print 'f has successfully sent',v
    v = 2
    print 'f sending',v
    try:
        outchan.send(v)
        print 'f has successfully sent',v
    except StopIteration:
        print 'f got StopIteration'


def g(inchan):
    print 'g before receiving'
    v = inchan.receive()
    print 'g received (just before closing)', v
    inchan.close()
    print 'g after closing channel'
    try:
        print 'g before receiving'
        v = inchan.receive()
    except StopIteration:
        print 'g got StopIteration from receiving'


chan = stackless.channel()
t1 = stackless.tasklet(f)(chan)
t2 = stackless.tasklet(g)(chan)
stackless.run()
