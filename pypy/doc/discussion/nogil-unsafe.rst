===========================================================
Explicitly removing the GIL (and letting the program crash)
===========================================================


Idea
----

Python programs normally run with the GIL, meaning only one thread at a
time can be running Python code.  Of course, threads are still useful in
Python for various reasons: notably, while a thread is waiting in any
system call, it releases the GIL, allowing another thread to run Python
code.

If we allowed unrestricted removal of the GIL, the Python interpreter
would either crash, or we would need a lot of extra work: either adding
careful locking everywhere like Jython/IronPython, or use STM.  Both
options impose an additional runtime overhead everywhere.

The nogil-unsafe branch explores a different approach: the Python
interpreter is allowed to crash, but the user (i.e. the Python
programmer) needs to identify parts of the program that are safe to run
on multiple threads.  The idea so far is that it makes sense to say
"this code here can run on multiple threads because I carefully checked
that it is safe".  Such a safety does not automatically extend to other
parts of the program: it is by default *never* safe to run two threads
in parallel, *unless* the user says that this particular piece of code
code can really be run by multiple threads in parallel.  Even if the
program contains, in two unrelated parts, two pieces of code that are
each parallelizable, it does not automatically mean that we can run a
thread in one piece of code in parallel with a thread in the other.

So the model is that every thread runs under a configurable "color", and
threads can only run together if they are of the same color.  By
default, all threads have no color at all, and cannot run in parallel
with any other thread at all (colored or not).  On the other hand,
several colored threads can run in parallel if the color is the same.
The idea is that the user identifies a piece of code that can be
parallelized, creates a color for it, and uses a "with" statement to
change the color of threads entering and leaving that piece of code.

What can be done in such parallelizable pieces of code?  "Simple enough"
operations---the details of which should be researched and well
documented.  Moreover, we can tweak a few parts of the standard library
to support this general approach, too: for example, when pdb is called,
it would switch the thread back to colorless (or maybe the Python
interpreter should do so whenever it calls tracing hooks, or invokves a
signal handler).


Implementation
--------------

Here is in more details how the GIL works in PyPy.  There are parts that
are heuristically determined, but it seems to work quite well enough
nowadays:

- A thread must acquire the GIL to run Python code.

- When a thread does a system call, it releases the GIL in such a way
  that if the system call completes quickly, it will re-acquire the GIL
  immediately afterwards, with high probability.  If the system call
  does not complete quickly, another thread will acquire the GIL and
  continue.

- When a thread exhausts its "time slice", measured in number of
  bytecodes run, then it releases the GIL in a different way that
  explicitly puts this thread at the back of the queue.

The GIL release and re-acquire operations around a system call work like
this.  First, we pick another thread, more precisely the one that is
scheduled to run after this one, and call it the "stealer thread".  In
the stealer thread, instead of purely sleeping, we regularly "poll" the
value of a boolean global variable.  When the running thread releases
the GIL it just writes a 0 in this global variable; when it re-acquires
the GIL it tries to replace it with a 1 again.  So if the running thread
does only short-running system calls, the global variable will mostly be
seen as 1 from the stealer thread.  However, if the stealer thread sees
it as 0, it tries to replace it with 1, and if that succeeds, then the
GIL was really stolen.

The plan for the nogil-unsafe branch is to keep this logic, but extend
it for the case where the running thread is colored.  To simplify, let's
say for now that colored threads don't participate in the "time slice"
system.  The idea is to replace the boolean global variable with a full
integer variable, divided in two halves: the higher 48 bits contain the
color of the running thread (colorless threads all use a different
unique value); the lower 16 bits contain the number of threads of that
color currently running.

Logic to release the GIL before a system call:

- in the default branch: ``global_variable = 0;``

- in the nogil-unsafe branch: ``atomically_decrement(integer_variable);``

Logic to acquire the GIL after a system call:

- in the default branch::

     if (xchg(global_variable, 1) != 0)
         slow_path();

- in the nogil-unsafe branch::

     n = integer_variable + 1;
     if ((n >> 16) != thread_color || !compare_and_swap(integer_variable, n))
         slow_path();

This change should come with a minimal performance impact (I guess).

Logic of the stealer thread:

- in the default branch::

     while (xchg(global_variable, 1) != 0) {
         sleep for 0.1 ms
     }

- in the nogil-unsafe branch::

     while ((old_value & 0xffff) != 0 ||
            !compare_and_swap(integer_variable, old_value, (new_color<<16) + 1))
         sleep for 0.1 ms
     }

Similar too.  We need however to add logic such that when several
threads with the same color enter the waiting state, only the first one
moves on to the queue (where it can become the stealer).  All the other
ones should instead be suspended, e.g. on an OS "condition variable".
When the stealing succeeds, it sends a signal on this condition variable
to wake them all up.  With a simple tweak we could count in advance how
many such threads there are, and immediately set the integer variable to
``(new_color << 16) + count``; this avoids the thundering herd effect
caused by all the threads woken up at the same time, each trying to
increase the integer variable by one.
