def receiver(chan, name):
    while 1:
        try:
            data = chan.receive()
        except:
            print name, "** Ouch!!! **"
            raise
        print name, "got:", data
        if data == 42:
            chan.send("%s says bye" % name)
            return

import sys
import stackless
if hasattr(stackless,'coroutine'):
    import stackless_ as stackless

chan = stackless.channel()
t1 = stackless.tasklet(receiver)(chan, "inky")
t2 = stackless.tasklet(receiver)(chan, "dinky")
stackless.run()
try:
    for i in 2,3,5,7, 42:
        print "sending", i
        chan.send(i)
        chan.send(i)
        #if i==7:
        #    print "sending Exception"
        #    chan.send_exception(ValueError, i)
except ValueError:
    e, v, t = sys.exc_info()
    print e, v
    del e, v, t
print "main done."
#
# trying to clean up things, until we have a real
# channel deallocator:
print "trying cleanup:"
while chan.balance:
    if chan.balance < 0:
        chan.send(42)
    else:
        print chan.receive()
