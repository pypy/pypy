Some rough notes about the Oz threading model
=============================================

(almost verbatim from CTM)

Scheduling
----------

Fair scheduling through round-robin.

With priority levels : three queues exist, which manage high, medium,
low priority threads. The time slice ratio for these is
100:10:1. Threads inherit the priority of their parent.

Mozart uses an external timer approach to implement thread preemption.

Thread ops
----------

All these ops are defined in a Thread namespace/module.

this()               -> current thread's name (*not* another thread's name)
state(t)             -> return state of t in {runnable, blocked, terminated}
suspend(t)            : suspend t
resume(t)             : resume execution of t
preempt(t)            : preempt t
terminate(t)          : terminate t immediately
injectException(t, e) : raise exception e in t
setPriority(t, p)     : set t's priority to p

Interestingly, coroutines can be build upon this thread
API. Coroutines have two ops : spawn and resume.

spawn(p)             -> creates a coroutine with procedure p, returns pid
resume(c)             : transfers control from current coroutine to c

The implementation of these ops in terms of the threads API is as
follows :

def spawn(p):
    in_thread:
        pid = Thread.this()
        Thread.suspend(pid)
        p()

def resume(cid):
    Thread.resume cid
    Thread.suspend(Thread.this())

