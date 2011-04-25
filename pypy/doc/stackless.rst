==========================================================
         Application-level Stackless features
==========================================================



Introduction
================

PyPy can expose to its user language features similar to the ones
present in `Stackless Python`_: **no recursion depth limit**, and the
ability to write code in a **massively concurrent style**.  It actually
exposes three different paradigms to choose from:

* `Tasklets and channels`_;

* Greenlets_;

* Plain coroutines_.

All of them are extremely light-weight, which means that PyPy should be
able to handle programs containing large amounts of coroutines, tasklets
and greenlets.


Requirements
++++++++++++++++

If you are running py.py on top of CPython, then you need to enable
the _stackless module by running it as follows::

    py.py --withmod-_stackless

This is implemented internally using greenlets, so it only works on a
platform where `greenlets`_ are supported.  A few features do
not work this way, though, and really require a translated
``pypy-c``.

To obtain a translated version of ``pypy-c`` that includes Stackless
support, run translate.py as follows::

    cd pypy/translator/goal
    python translate.py --stackless


Application level interface
=============================

A stackless PyPy contains a module called ``stackless``.  The interface
exposed by this module have not been refined much, so it should be
considered in-flux (as of 2007).

So far, PyPy does not provide support for ``stackless`` in a threaded
environment.  This limitation is not fundamental, as previous experience
has shown, so supporting this would probably be reasonably easy.

An interesting point is that the same ``stackless`` module can provide
a number of different concurrency paradigms at the same time.  From a
theoretical point of view, none of above-mentioned existing three
paradigms considered on its own is new: two of them are from previous
Python work, and the third one is a variant of the classical coroutine.
The new part is that the PyPy implementation manages to provide all of
them and let the user implement more.  Moreover - and this might be an
important theoretical contribution of this work - we manage to provide
these concurrency concepts in a "composable" way.  In other words, it
is possible to naturally mix in a single application multiple
concurrency paradigms, and multiple unrelated usages of the same
paradigm.  This is discussed in the Composability_ section below.


Infinite recursion
++++++++++++++++++

Any stackless PyPy executable natively supports recursion that is only
limited by the available memory.  As in normal Python, though, there is
an initial recursion limit (which is 5000 in all pypy-c's, and 1000 in
CPython).  It can be changed with ``sys.setrecursionlimit()``.  With a
stackless PyPy, any value is acceptable - use ``sys.maxint`` for
unlimited.

In some cases, you can write Python code that causes interpreter-level
infinite recursion -- i.e. infinite recursion without going via
application-level function calls.  It is possible to limit that too,
with ``_stackless.set_stack_depth_limit()``, or to unlimit it completely
by setting it to ``sys.maxint``.


Coroutines
++++++++++

A Coroutine is similar to a very small thread, with no preemptive scheduling.
Within a family of coroutines, the flow of execution is explicitly
transferred from one to another by the programmer.  When execution is
transferred to a coroutine, it begins to execute some Python code.  When
it transfers execution away from itself it is temporarily suspended, and
when execution returns to it it resumes its execution from the
point where it was suspended.  Conceptually, only one coroutine is
actively running at any given time (but see Composability_ below).

The ``stackless.coroutine`` class is instantiated with no argument.
It provides the following methods and attributes:

* ``stackless.coroutine.getcurrent()``

    Static method returning the currently running coroutine.  There is a
    so-called "main" coroutine object that represents the "outer"
    execution context, where your main program started and where it runs
    as long as it does not switch to another coroutine.

* ``coro.bind(callable, *args, **kwds)``

    Bind the coroutine so that it will execute ``callable(*args,
    **kwds)``.  The call is not performed immediately, but only the
    first time we call the ``coro.switch()`` method.  A coroutine must
    be bound before it is switched to.  When the coroutine finishes
    (because the call to the callable returns), the coroutine exits and
    implicitly switches back to another coroutine (its "parent"); after
    this point, it is possible to bind it again and switch to it again.
    (Which coroutine is the parent of which is not documented, as it is
    likely to change when the interface is refined.)

* ``coro.switch()``

    Suspend the current (caller) coroutine, and resume execution in the
    target coroutine ``coro``.

* ``coro.kill()``

    Kill ``coro`` by sending a CoroutineExit exception and switching
    execution immediately to it. This exception can be caught in the 
    coroutine itself and can be raised from any call to ``coro.switch()``. 
    This exception isn't propagated to the parent coroutine.

* ``coro.throw(type, value)``

    Insert an exception in ``coro`` an resume switches execution
    immediately to it. In the coroutine itself, this exception
    will come from any call to ``coro.switch()`` and can be caught. If the
    exception isn't caught, it will be propagated to the parent coroutine.

Example
~~~~~~~

Here is a classical producer/consumer example: an algorithm computes a
sequence of values, while another consumes them.  For our purposes we
assume that the producer can generate several values at once, and the
consumer can process up to 3 values in a batch - it can also process
batches with fewer than 3 values without waiting for the producer (which
would be messy to express with a classical Python generator). ::

    def producer(lst):
        while True:
            ...compute some more values...
            lst.extend(new_values)
            coro_consumer.switch()

    def consumer(lst):
        while True:
            # First ask the producer for more values if needed
            while len(lst) == 0:
                coro_producer.switch()
            # Process the available values in a batch, but at most 3
            batch = lst[:3]
            del lst[:3]
            ...process batch...

    # Initialize two coroutines with a shared list as argument
    exchangelst = []
    coro_producer = coroutine()
    coro_producer.bind(producer, exchangelst)
    coro_consumer = coroutine()
    coro_consumer.bind(consumer, exchangelst)

    # Start running the consumer coroutine
    coro_consumer.switch()


Tasklets and channels
+++++++++++++++++++++

The ``stackless`` module also provides an interface that is roughly
compatible with the interface of the ``stackless`` module in `Stackless
Python`_: it contains ``stackless.tasklet`` and ``stackless.channel``
classes.  Tasklets are also similar to microthreads, but (like coroutines)
they don't actually run in parallel with other microthreads; instead,
they synchronize and exchange data with each other over Channels, and
these exchanges determine which Tasklet runs next.

For usage reference, see the documentation on the `Stackless Python`_
website.

Note that Tasklets and Channels are implemented at application-level in
`lib_pypy/stackless.py`_ on top of coroutines_.  You can refer to this
module for more details and API documentation.

The stackless.py code tries to resemble the stackless C code as much
as possible. This makes the code somewhat unpythonic.

Bird's eye view of tasklets and channels
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Tasklets are a bit like threads: they encapsulate a function in such a way that
they can be suspended/restarted any time. Unlike threads, they won't
run concurrently, but must be cooperative. When using stackless
features, it is vitally important that no action is performed that blocks
everything else.  In particular, blocking input/output should be centralized
to a single tasklet.

Communication between tasklets is done via channels. 
There are three ways for a tasklet to give up control:

1. call ``stackless.schedule()``
2. send something over a channel
3. receive something from a channel

A (live) tasklet can either be running, waiting to get scheduled, or be
blocked by a channel.

Scheduling is done in strictly round-robin manner. A blocked tasklet
is removed from the scheduling queue and will be reinserted when it
becomes unblocked.

Example
~~~~~~~

Here is a many-producers many-consumers example, where any consumer can
process the result of any producer.  For this situation we set up a
single channel where all producer send, and on which all consumers
wait::

    def producer(chan):
        while True:
            chan.send(...next value...)

    def consumer(chan):
        while True:
            x = chan.receive()
            ...do something with x...

    # Set up the N producer and M consumer tasklets
    common_channel = stackless.channel()
    for i in range(N):
        stackless.tasklet(producer, common_channel)()
    for i in range(M):
        stackless.tasklet(consumer, common_channel)()

    # Run it all
    stackless.run()

Each item sent over the channel is received by one of the waiting
consumers; which one is not specified.  The producers block until their
item is consumed: the channel is not a queue, but rather a meeting point
which causes tasklets to block until both a consumer and a producer are
ready.  In practice, the reason for having several consumers receiving
on a single channel is that some of the consumers can be busy in other
ways part of the time.  For example, each consumer might receive a
database request, process it, and send the result to a further channel
before it asks for the next request.  In this situation, further
requests can still be received by other consumers.


Greenlets
+++++++++

A Greenlet is a kind of primitive Tasklet with a lower-level interface
and with exact control over the execution order.  Greenlets are similar
to Coroutines, with a slightly different interface: greenlets put more
emphasis on a tree structure.  The various greenlets of a program form a
precise tree, which fully determines their order of execution.

For usage reference, see the `documentation of the greenlets`_.
The PyPy interface is identical.  You should use ``greenlet.greenlet``
instead of ``stackless.greenlet`` directly, because the greenlet library
can give you the latter when you ask for the former on top of PyPy.

PyPy's greenlets do not suffer from the cyclic GC limitation that the
CPython greenlets have: greenlets referencing each other via local
variables tend to leak on top of CPython (where it is mostly impossible
to do the right thing).  It works correctly on top of PyPy.


Coroutine Pickling
++++++++++++++++++

Coroutines and tasklets can be pickled and unpickled, i.e. serialized to
a string of bytes for the purpose of storage or transmission.  This
allows "live" coroutines or tasklets to be made persistent, moved to
other machines, or cloned in any way.  The standard ``pickle`` module
works with coroutines and tasklets (at least in a translated ``pypy-c``;
unpickling live coroutines or tasklets cannot be easily implemented on
top of CPython).

To be able to achieve this result, we have to consider many objects that
are not normally pickleable in CPython.  Here again, the `Stackless
Python`_ implementation has paved the way, and we follow the same
general design decisions: simple internal objects like bound method
objects and various kinds of iterators are supported; frame objects can
be fully pickled and unpickled
(by serializing a reference to the bytecode they are
running in addition to all the local variables).  References to globals
and modules are pickled by name, similarly to references to functions
and classes in the traditional CPython ``pickle``.

The "magic" part of this process is the implementation of the unpickling
of a chain of frames.  The Python interpreter of PyPy uses
interpreter-level recursion to represent application-level calls.  The
reason for this is that it tremendously simplifies the implementation of
the interpreter itself.  Indeed, in Python, almost any operation can
potentially result in a non-tail-recursive call to another Python
function.  This makes writing a non-recursive interpreter extremely
tedious; instead, we rely on lower-level transformations during the
translation process to control this recursion.  This is the `Stackless
Transform`_, which is at the heart of PyPy's support for stackless-style
concurrency.

At any point in time, a chain of Python-level frames corresponds to a
chain of interpreter-level frames (e.g. C frames in pypy-c), where each
single Python-level frame corresponds to one or a few interpreter-level
frames - depending on the length of the interpreter-level call chain
from one bytecode evaluation loop to the next (recursively invoked) one.

This means that it is not sufficient to simply create a chain of Python
frame objects in the heap of a process before we can resume execution of
these newly built frames.  We must recreate a corresponding chain of
interpreter-level frames.  To this end, we have inserted a few *named
resume points* (see 3.2.4, in `D07.1 Massive Parallelism and Translation Aspects`_) in the Python interpreter of PyPy.  This is the
motivation for implementing the interpreter-level primitives
``resume_state_create()`` and ``resume_state_invoke()``, the powerful
interface that allows an RPython program to artificially rebuild a chain
of calls in a reflective way, completely from scratch, and jump to it.

.. _`D07.1 Massive Parallelism and Translation Aspects`: http://codespeak.net/pypy/extradoc/eu-report/D07.1_Massive_Parallelism_and_Translation_Aspects-2007-02-28.pdf

Example
~~~~~~~

(See `demo/pickle_coroutine.py`_ for the complete source of this demo.)

Consider a program which contains a part performing a long-running
computation::

    def ackermann(x, y):
        if x == 0:
            return y + 1
        if y == 0:
            return ackermann(x - 1, 1)
        return ackermann(x - 1, ackermann(x, y - 1))

By using pickling, we can save the state of the computation while it is
running, for the purpose of restoring it later and continuing the
computation at another time or on a different machine.  However,
pickling does not produce a whole-program dump: it can only pickle
individual coroutines.  This means that the computation should be
started in its own coroutine::

    # Make a coroutine that will run 'ackermann(3, 8)'
    coro = coroutine()
    coro.bind(ackermann, 3, 8)

    # Now start running the coroutine
    result = coro.switch()

The coroutine itself must switch back to the main program when it needs
to be interrupted (we can only pickle suspended coroutines).  Due to
current limitations this requires an explicit check in the
``ackermann()`` function::

    def ackermann(x, y):
        if interrupt_flag:      # test a global flag
            main.switch()       # and switch back to 'main' if it is set
        if x == 0:
            return y + 1
        if y == 0:
            return ackermann(x - 1, 1)
        return ackermann(x - 1, ackermann(x, y - 1))

The global ``interrupt_flag`` would be set for example by a timeout, or
by a signal handler reacting to Ctrl-C, etc.  It causes the coroutine to
transfer control back to the main program.  The execution comes back
just after the line ``coro.switch()``, where we can pickle the coroutine
if necessary::

    if not coro.is_alive:
        print "finished; the result is:", result
    else:
        # save the state of the suspended coroutine
        f = open('demo.pickle', 'w')
        pickle.dump(coro, f)
        f.close()

The process can then stop.  At any later time, or on another machine,
we can reload the file and restart the coroutine with::

    f = open('demo.pickle', 'r')
    coro = pickle.load(f)
    f.close()
    result = coro.switch()

Limitations
~~~~~~~~~~~

Coroutine pickling is subject to some limitations.  First of all, it is
not a whole-program "memory dump".  It means that only the "local" state
of a coroutine is saved.  The local state is defined to include the
chain of calls and the local variables, but not for example the value of
any global variable.

As in normal Python, the pickle will not include any function object's
code, any class definition, etc., but only references to functions and
classes.  Unlike normal Python, the pickle contains frames.  A pickled
frame stores a bytecode index, representing the current execution
position.  This means that the user program cannot be modified *at all*
between pickling and unpickling!

On the other hand, the pickled data is fairly independent from the
platform and from the PyPy version.

Pickling/unpickling fails if the coroutine is suspended in a state that
involves Python frames which were *indirectly* called.  To define this
more precisely, a Python function can issue a regular function or method
call to invoke another Python function - this is a *direct* call and can
be pickled and unpickled.  But there are many ways to invoke a Python
function indirectly.  For example, most operators can invoke a special
method ``__xyz__()`` on a class, various built-in functions can call
back Python functions, signals can invoke signal handlers, and so on.
These cases are not supported yet.


Composability
+++++++++++++

Although the concept of coroutines is far from new, they have not been
generally integrated into mainstream languages, or only in limited form
(like generators in Python and iterators in C#).  We can argue that a
possible reason for that is that they do not scale well when a program's
complexity increases: they look attractive in small examples, but the
models that require explicit switching, by naming the target coroutine,
do not compose naturally.  This means that a program that uses
coroutines for two unrelated purposes may run into conflicts caused by
unexpected interactions.

To illustrate the problem, consider the following example (simplified
code; see the full source in
`pypy/module/_stackless/test/test_composable_coroutine.py`_).  First, a
simple usage of coroutine::

    main_coro = coroutine.getcurrent()    # the main (outer) coroutine
    data = []

    def data_producer():
        for i in range(10):
            # add some numbers to the list 'data' ...
            data.append(i)
            data.append(i * 5)
            data.append(i * 25)
            # and then switch back to main to continue processing
            main_coro.switch()

    producer_coro = coroutine()
    producer_coro.bind(data_producer)

    def grab_next_value():
        if not data:
            # put some more numbers in the 'data' list if needed
            producer_coro.switch()
        # then grab the next value from the list
        return data.pop(0)

Every call to grab_next_value() returns a single value, but if necessary
it switches into the producer function (and back) to give it a chance to
put some more numbers in it.

Now consider a simple reimplementation of Python's generators in term of
coroutines::

    def generator(f):
        """Wrap a function 'f' so that it behaves like a generator."""
        def wrappedfunc(*args, **kwds):
            g = generator_iterator()
            g.bind(f, *args, **kwds)
            return g
        return wrappedfunc

    class generator_iterator(coroutine):
        def __iter__(self):
            return self
        def next(self):
            self.caller = coroutine.getcurrent()
            self.switch()
            return self.answer

    def Yield(value):
        """Yield the value from the current generator."""
        g = coroutine.getcurrent()
        g.answer = value
        g.caller.switch()

    def squares(n):
        """Demo generator, producing square numbers."""
        for i in range(n):
            Yield(i * i)
    squares = generator(squares)

    for x in squares(5):
        print x       # this prints 0, 1, 4, 9, 16

Both these examples are attractively elegant.  However, they cannot be
composed.  If we try to write the following generator::

    def grab_values(n):
        for i in range(n):
            Yield(grab_next_value())
    grab_values = generator(grab_values)

then the program does not behave as expected.  The reason is the
following.  The generator coroutine that executes ``grab_values()``
calls ``grab_next_value()``, which may switch to the ``producer_coro``
coroutine.  This works so far, but the switching back from
``data_producer()`` to ``main_coro`` lands in the wrong coroutine: it
resumes execution in the main coroutine, which is not the one from which
it comes.  We expect ``data_producer()`` to switch back to the
``grab_next_values()`` call, but the latter lives in the generator
coroutine ``g`` created in ``wrappedfunc``, which is totally unknown to
the ``data_producer()`` code.  Instead, we really switch back to the
main coroutine, which confuses the ``generator_iterator.next()`` method
(it gets resumed, but not as a result of a call to ``Yield()``).

As part of trying to combine multiple different paradigms into a single
application-level module, we have built a way to solve this problem.
The idea is to avoid the notion of a single, global "main" coroutine (or
a single main greenlet, or a single main tasklet).  Instead, each
conceptually separated user of one of these concurrency interfaces can
create its own "view" on what the main coroutine/greenlet/tasklet is,
which other coroutine/greenlet/tasklets there are, and which of these is
the currently running one.  Each "view" is orthogonal to the others.  In
particular, each view has one (and exactly one) "current"
coroutine/greenlet/tasklet at any point in time.  When the user switches
to a coroutine/greenlet/tasklet, it implicitly means that he wants to
switch away from the current coroutine/greenlet/tasklet *that belongs to
the same view as the target*.

The precise application-level interface has not been fixed yet; so far,
"views" in the above sense are objects of the type
``stackless.usercostate``.  The above two examples can be rewritten in
the following way::

    producer_view = stackless.usercostate()   # a local view
    main_coro = producer_view.getcurrent()    # the main (outer) coroutine
    ...
    producer_coro = producer_view.newcoroutine()
    ...

and::

    generators_view = stackless.usercostate()

    def generator(f):
        def wrappedfunc(*args, **kwds):
            g = generators_view.newcoroutine(generator_iterator)
            ...

            ...generators_view.getcurrent()...

Then the composition ``grab_values()`` works as expected, because the
two views are independent.  The coroutine captured as ``self.caller`` in
the ``generator_iterator.next()`` method is the main coroutine of the
``generators_view``.  It is no longer the same object as the main
coroutine of the ``producer_view``, so when ``data_producer()`` issues
the following command::

    main_coro.switch()

the control flow cannot accidentally jump back to
``generator_iterator.next()``.  In other words, from the point of view
of ``producer_view``, the function ``grab_next_value()`` always runs in
its main coroutine ``main_coro`` and the function ``data_producer`` in
its coroutine ``producer_coro``.  This is the case independently of
which ``generators_view``-based coroutine is the current one when
``grab_next_value()`` is called.

Only code that has explicit access to the ``producer_view`` or its
coroutine objects can perform switches that are relevant for the
generator code.  If the view object and the coroutine objects that share
this view are all properly encapsulated inside the generator logic, no
external code can accidentally temper with the expected control flow any
longer.

In conclusion: we will probably change the app-level interface of PyPy's
stackless module in the future to not expose coroutines and greenlets at
all, but only views.  They are not much more difficult to use, and they
scale automatically to larger programs.


.. _`Stackless Python`: http://www.stackless.com
.. _`documentation of the greenlets`: http://codespeak.net/svn/greenlet/trunk/doc/greenlet.txt
.. _`Stackless Transform`: translation.html#the-stackless-transform

.. include:: _ref.rst
