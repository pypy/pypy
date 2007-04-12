"""
The Stackless module allows you to do multitasking without using threads.
The essential objects are tasklets and channels.
Please refer to their documentation.
"""

import traceback
import sys
try:
    from _stackless import coroutine, greenlet
except ImportError: # we are running from CPython
    from py.magic import greenlet
    try:
        from functools import partial
    except ImportError: # we are not running python 2.5
        class partial(object):
            # just enough of 'partial' to be usefull
            def __init__(self, func, *argl, **argd):
                self.func = func
                self.argl = argl
                self.argd = argd

            def __call__(self):
                return self.func(*self.argl, **self.argd)

    class GWrap(greenlet):
        """This is just a wrapper around greenlets to allow
           to stick additional attributes to a greenlet.
           To be more concrete, we need a backreference to
           the coroutine object"""

    class MWrap(object):
        def __init__(self,something):
            self.something = something

        def __getattr__(self, attr):
            return getattr(self.something, attr)

    class coroutine(object):
        "we can't have greenlet as a base, because greenlets can't be rebound"

        def __init__(self):
            self._frame = None
            self.is_zombie = False

        def __getattr__(self, attr):
            return getattr(self._frame, attr)

        def __del__(self):
            self.is_zombie = True
            del self._frame
            self._frame = None

        def bind(self, func, *argl, **argd):
            """coro.bind(f, *argl, **argd) -> None.
               binds function f to coro. f will be called with
               arguments *argl, **argd
            """
            if self._frame is None or self._frame.dead:
                self._frame = frame = GWrap()
                frame.coro = self
            if hasattr(self._frame, 'run') and self._frame.run:
                raise ValueError("cannot bind a bound coroutine")
            self._frame.run = partial(func, *argl, **argd)

        def switch(self):
            """coro.switch() -> returnvalue
               switches to coroutine coro. If the bound function
               f finishes, the returnvalue is that of f, otherwise
               None is returned
            """
            try:
                return greenlet.switch(self._frame)
            except TypeError, exp: # self._frame is the main coroutine
                return greenlet.switch(self._frame.something)

        def kill(self):
            """coro.kill() : kill coroutine coro"""
            self._frame.throw()

        def _is_alive(self):
            if self._frame is None:
                return False
            return not self._frame.dead
        is_alive = property(_is_alive)
        del _is_alive

        def getcurrent():
            """coroutine.getcurrent() -> the currently running coroutine"""
            try:
                return greenlet.getcurrent().coro
            except AttributeError:
                return _maincoro
        getcurrent = staticmethod(getcurrent)

    _maincoro = coroutine()
    maingreenlet = greenlet.getcurrent()
    _maincoro._frame = frame = MWrap(maingreenlet)
    frame.coro = _maincoro
    del frame
    del maingreenlet

from collections import deque

import operator
__all__ = 'run getcurrent getmain schedule tasklet channel coroutine \
                TaskletExit greenlet'.split()

_global_task_id = 0
_squeue = None
_main_tasklet = None
_main_coroutine = None
_last_task = None
_channel_callback = None
_schedule_callback = None

def _scheduler_remove(value):
    try:
        del _squeue[operator.indexOf(_squeue, value)]
    except ValueError:pass

def _scheduler_append(value, normal=True):
    if normal:
        _squeue.append(value)
    else:
        _squeue.rotate(-1)
        _squeue.appendleft(value)
        _squeue.rotate(1)

def _scheduler_contains(value):
    try:
        operator.indexOf(_squeue, value)
        return True
    except ValueError:
        return False

def _scheduler_switch(current, next):
    global _last_task
    prev = _last_task
    if (_schedule_callback is not None and
        prev is not next):
        _schedule_callback(prev, next)
    _last_task = next
    assert not next.blocked
    if next is not current:
        next.switch()
    return current


class TaskletExit(Exception):pass

def set_schedule_callback(callback):
    global _schedule_callback
    _schedule_callback = callback

def set_channel_callback(callback):
    global _channel_callback
    _channel_callback = callback

def getruncount():
    return len(_squeue)

class bomb(object):
    def __init__(self, exp_type=None, exp_value=None, exp_traceback=None):
        self.type = exp_type
        self.value = exp_value
        self.traceback = exp_traceback

    def raise_(self):
        raise self.type, self.value, self.traceback

class channel(object):
    """
    A channel object is used for communication between tasklets.
    By sending on a channel, a tasklet that is waiting to receive
    is resumed. If there is no waiting receiver, the sender is suspended.
    By receiving from a channel, a tasklet that is waiting to send
    is resumed. If there is no waiting sender, the receiver is suspended.
    """

    def __init__(self, label=''):
        self.balance = 0
        self.closing = False
        self.queue = deque()
        self.label = label

    def __str__(self):
        return 'channel[%s](%s,%s)' % (self.label, self.balance, self.queue)

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
        willblock = not self.balance > 0
        if _channel_callback is not None:
            _channel_callback(self, receiver, 0, willblock)
        if self.balance > 0: # somebody is already sending
            self.balance -= 1
            sender = self.queue.popleft()
            sender.blocked = False
            receiver.tempval = sender.tempval
            _scheduler_append(sender)
        else: # nobody is waiting
            self.balance -= 1
            self.queue.append(receiver)
            receiver.blocked = True
            _scheduler_remove(getcurrent())
            schedule()
            assert not receiver.blocked
            
        msg = receiver.tempval
        if isinstance(msg, bomb):
            msg.raise_()
        return msg

    def send_exception(self, exp_type, msg):
        self.send(bomb(exp_type, exp_type(msg)))

    def send_sequence(self, iterable):
        for item in iterable:
            self.send(item)

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
        willblock = not self.balance < 0
        if _channel_callback is not None:
            _channel_callback(self, sender, 1, willblock)
        if self.balance < 0: # somebody is already waiting
            receiver = self.queue.popleft()
            receiver.blocked = False
            self.balance += 1
            receiver.tempval = msg
            _scheduler_append(receiver, False)
            schedule()
        else: # nobody is waiting
            self.queue.append(sender)
            sender.blocked = True
            self.balance += 1
            _scheduler_remove(getcurrent())
            schedule()
            assert not sender.blocked
            
class tasklet(coroutine):
    """
    A tasklet object represents a tiny task in a Python thread.
    At program start, there is always one running main tasklet.
    New tasklets can be created with methods from the stackless
    module.
    """
    tempval = None
    def __new__(cls, func=None, label=''):
        return super(tasklet,cls).__new__(cls)

    def __init__(self, func=None, label=''):
        super(tasklet, self).__init__()
        self._init(func, label)

    def _init(self, func=None, label=''):
        global _global_task_id
        self.func = func
        self.alive = False
        self.blocked = False
        self._task_id = _global_task_id
        self.label = label
        _global_task_id += 1

    def __str__(self):
        return '<tasklet[%s, %s]>' % (self.label,self._task_id)

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
        self.func = func

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
            _scheduler_remove(self)
            self.alive = False

    def setup(self, *argl, **argd):
        """
        supply the parameters for the callable
        """
        if self.func is None:
            raise TypeError('cframe function must be callable')
        func = self.func
        def _func():
            try:
                try:
                    func(*argl, **argd)
                except TaskletExit:
                    pass
            finally:
                _scheduler_remove(self)
                self.alive = False

        self.func = None
        coroutine.bind(self, _func)
        self.alive = True
        _scheduler_append(self)
        return self

    def run(self):
        if _scheduler_contains(self):
            return
        else:
            _scheduler_append(self)

    def __reduce__(self):
        one, two, three = coroutine.__reduce__(self)
        assert one is coroutine
        assert two == ()
        return tasklet, (), (three, self.alive, self.tempval)

    def __setstate__(self, (coro_state, alive, tempval)):
        coroutine.__setstate__(self, coro_state)
        self.alive = alive
        self.tempval = tempval

def getmain():
    """
    getmain() -- return the main tasklet.
    """
    return _main_tasklet

def getcurrent():
    """
    getcurrent() -- return the currently executing tasklet.
    """

    curr = coroutine.getcurrent()
    if curr is _main_coroutine:
        return _main_tasklet
    else:
        return curr

_run_calls = []
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
    curr = getcurrent()
    _run_calls.append(curr)
    _scheduler_remove(curr)
    try:
        schedule()
        assert not _squeue
    finally:
        _scheduler_append(curr)
    
def schedule_remove(retval=None):
    """
    schedule(retval=stackless.current) -- switch to the next runnable tasklet.
    The return value for this call is retval, with the current
    tasklet as default.
    schedule_remove(retval=stackless.current) -- ditto, and remove self.
    """
    _scheduler_remove(getcurrent())
    r = schedule(retval)
    return r


def schedule(retval=None):
    """
    schedule(retval=stackless.current) -- switch to the next runnable tasklet.
    The return value for this call is retval, with the current
    tasklet as default.
    schedule_remove(retval=stackless.current) -- ditto, and remove self.
    """
    mtask = getmain()
    curr = getcurrent()
    if retval is None:
        retval = curr
    while True:
        if _squeue:
            if _squeue[0] is curr:
                # If the current is at the head, skip it.
                _squeue.rotate(-1)
                
            task = _squeue[0]
            #_squeue.rotate(-1)
        elif _run_calls:
            task = _run_calls.pop()
        else:
            raise RuntimeError('No runnable tasklets left.')
        _scheduler_switch(curr, task)
        if curr is _last_task:
            # We are in the tasklet we want to resume at this point.
            return retval

def _init():
    global _main_tasklet
    global _global_task_id
    global _squeue
    global _last_task
    _global_task_id = 0
    _main_tasklet = coroutine.getcurrent()
    try:
        _main_tasklet.__class__ = tasklet
    except TypeError: # we are running pypy-c
        class TaskletProxy(object):
            """TaskletProxy is needed to give the _main_coroutine tasklet behaviour"""
            def __init__(self, coro):
                self._coro = coro

            def __getattr__(self,attr):
                return getattr(self._coro,attr)

            def __str__(self):
                return '<tasklet %s a:%s>' % (self._task_id, self.is_alive)

            def __reduce__(self):
                return getmain, ()

            __repr__ = __str__


        global _main_coroutine
        _main_coroutine = _main_tasklet
        _main_tasklet = TaskletProxy(_main_tasklet)
        assert _main_tasklet.is_alive and not _main_tasklet.is_zombie
    _last_task = _main_tasklet
    tasklet._init.im_func(_main_tasklet, label='main')
    _squeue = deque()
    _scheduler_append(_main_tasklet)

_init()
