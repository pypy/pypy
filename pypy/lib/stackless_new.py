"""
The Stackless module allows you to do multitasking without using threads.
The essential objects are tasklets and channels.
Please refer to their documentation.
"""

import traceback
import sys
try:
    from _stackless import coroutine, greenlet
except ImportError:
    from py.magic import coroutine, greenlet
from collections import deque

__all__ = 'run getcurrent getmain schedule tasklet channel coroutine \
                TaskletExit greenlet'.split()

global_task_id = 0
squeue = None
main_tasklet = None
main_coroutine = None
first_run = False

class TaskletExit(Exception):pass

class channel(object):
    """
    A channel object is used for communication between tasklets.
    By sending on a channel, a tasklet that is waiting to receive
    is resumed. If there is no waiting receiver, the sender is suspended.
    By receiving from a channel, a tasklet that is waiting to send
    is resumed. If there is no waiting sender, the receiver is suspended.
    """

    def __init__(self):
        self.balance = 0
        self.closing = False
        self.queue = deque()

    def __str__(self):
        return 'channel(%s,%s)' % (self.balance, self.queue)

    def close(self):
        """
        channel.close() -- stops the channel from enlarging its queue.
        
        If the channel is not empty, the flag 'closing' becomes true.
        If the channel is empty, the flag 'closed' becomes true.
        """
        self.closing = True

    @property
    def closed(self):
        return self.closing and not self.queue

    def open(self):
        """
        channel.open() -- reopen a channel. See channel.close.
        """
        self.closing = False

    def receive(self):
        """
        channel.receive() -- receive a value over the channel.
        If no other tasklet is already sending on the channel,
        the receiver will be blocked. Otherwise, the receiver will
        continue immediately, and the sender is put at the end of
        the runnables list.
        The above policy can be changed by setting channel flags.
        """
        receiver = getcurrent()
        if self.balance > 0: # somebody is already sending
            self.balance -= 1
            sender = self.queue.popleft()
            #receiver.tempval = sender.tempval
            receiver.tempval = sender.tempval
            squeue.append(sender)
        else: # nobody is waiting
            self.balance -= 1
            squeue.pop()
            self.queue.append(receiver)
        schedule()
        msg = receiver.tempval
        return msg

    def send(self, msg):
        """
        channel.send(value) -- send a value over the channel.
        If no other tasklet is already receiving on the channel,
        the sender will be blocked. Otherwise, the receiver will
        be activated immediately, and the sender is put at the end of
        the runnables list.
        """
        sender = getcurrent()
        sender.tempval = msg
        if self.balance < 0: # somebody is already waiting
            receiver = self.queue.popleft()
            self.balance += 1
            receiver.tempval = msg
            squeue.appendleft(receiver)
            schedule()
        else: # nobody is waiting
            self.queue.append(squeue[-1])
            self.balance += 1
            schedule_remove()

class tasklet(coroutine):
    """
    A tasklet object represents a tiny task in a Python thread.
    At program start, there is always one running main tasklet.
    New tasklets can be created with methods from the stackless
    module.
    """
    def __new__(cls, func=None):
        return super(tasklet,cls).__new__(cls)

    def __init__(self, func=None):
        super(tasklet, self).__init__()
        self._init(func)

    def _init(self, func=None):
        global global_task_id
        self.tempval = func
        self.alive = False
        self.task_id = global_task_id
        global_task_id += 1

    def __str__(self):
        return '<tasklet %s a:%s z:%s>' % \
                (self.task_id, self.is_alive, self.is_zombie)

    __repr__ = __str__

    def __call__(self, *argl, **argd):
        return self.setup(*argl, **argd)

    def bind(self, func):
        """
        Binding a tasklet to a callable object.
        The callable is usually passed in to the constructor.
        In some cases, it makes sense to be able to re-bind a tasklet,
        after it has been run, in order to keep its identity.
        Note that a tasklet can only be bound when it doesn't have a frame.
        """
        if not callable(func):
            raise TypeError('tasklet function must be a callable')
        self.tempval = func

    def kill(self):
        """
        tasklet.kill -- raise a TaskletExit exception for the tasklet.
        Note that this is a regular exception that can be caught.
        The tasklet is immediately activated.
        If the exception passes the toplevel frame of the tasklet,
        the tasklet will silently die.
        """
        if not self.is_zombie:
            coroutine.kill(self)
            self.alive = False

    def setup(self, *argl, **argd):
        """
        supply the parameters for the callable
        """
        if self.tempval is None:
            raise TypeError('cframe function must be callable')
        coroutine.bind(self,self.tempval,*argl,**argd)
        self.tempval = None
        self.alive = True
        squeue.append(self)
        return self

    def __reduce__(self):
        one, two, three = coroutine.__reduce__(self)
        assert one is coroutine
        assert two == ()
        return tasklet, () (three, self.alive, self.tempval)

    def __setstate__(self, (coro_state, alive, tempval)):
        coroutine.__setstate__(self, coro_state)
        self.alive = alive
        self.tempval = tempval

def getmain():
    """
    getmain() -- return the main tasklet.
    """
    return main_tasklet

def getcurrent():
    """
    getcurrent() -- return the currently executing tasklet.
    """

    curr = coroutine.getcurrent()
    if curr is main_coroutine:
        return main_tasklet
    else:
        return curr

def run():
    """
    run_watchdog(timeout) -- run tasklets until they are all
    done, or timeout instructions have passed. Tasklets must
    provide cooperative schedule() calls.
    If the timeout is met, the function returns.
    The calling tasklet is put aside while the tasklets are running.
    It is inserted back after the function stops, right before the
    tasklet that caused a timeout, if any.
    If an exception occours, it will be passed to the main tasklet.

    Please note that the 'timeout' feature is not yet implemented
    """
    schedule_remove()
    
scall = 0

def schedule_remove(retval=None):
    """
    schedule(retval=stackless.current) -- switch to the next runnable tasklet.
    The return value for this call is retval, with the current
    tasklet as default.
    schedule_remove(retval=stackless.current) -- ditto, and remove self.
    """
    global first_run
    if first_run:
        squeue.rotate(-1)
        first_run = False
    t = squeue.pop()
    if t is not getcurrent():
        squeue.appendleft(t)

    schedule()

def schedule(retval=None):
    """
    schedule(retval=stackless.current) -- switch to the next runnable tasklet.
    The return value for this call is retval, with the current
    tasklet as default.
    schedule_remove(retval=stackless.current) -- ditto, and remove self.
    """

    mtask = getmain()
    global first_run
    if first_run:
        squeue.rotate(-1)
        first_run = False

    if squeue:
        task = squeue[0]
        squeue.rotate(-1)
        if task is not getcurrent() and task.is_alive:
            task.switch()
            curr = getcurrent()
            if not task.is_alive:
                if squeue:
                    pt = squeue.pop()
                    if pt.is_alive:
                        squeue.append(pt)
                    else:
                        coroutine.kill(task)
                else:
                    if curr is not mtask:
                        mtask.switch()
                schedule()

def _init():
    global main_tasklet
    global global_task_id
    global first_run
    global squeue
    first_run = True
    global_task_id = 0
    main_tasklet = coroutine.getcurrent()
    try:
        main_tasklet.__class__ = tasklet
    except TypeError: # we are running pypy-c
        class TaskletProxy(object):
            """TaskletProxy is needed to give the main_coroutine tasklet behaviour"""
            def __init__(self, coro):
                self._coro = coro

            def __getattr__(self,attr):
                return getattr(self._coro,attr)

            def __str__(self):
                return '<tasklet %s a:%s z:%s>' % \
                        (self.task_id, self.is_alive, self.is_zombie)

            def __reduce__(self):
                return getmain, ()

            __repr__ = __str__


        global main_coroutine
        main_coroutine = main_tasklet
        main_tasklet = TaskletProxy(main_tasklet)
        assert main_tasklet.is_alive and not main_tasklet.is_zombie
    tasklet._init(main_tasklet)
    squeue = deque()
    squeue.append(main_tasklet)

_init()
