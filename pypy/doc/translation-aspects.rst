.. include:: throwaway.rst

==========================================================================================
Memory management and threading models as translation aspects -- solutions and challenges
==========================================================================================

.. contents::


Introduction
=============

One of the goals of the PyPy project is to have the memory and concurrency
models flexible and changeable without having to reimplement the
interpreter manually. In fact, PyPy, by the time of the 0.8 release contains code for memory
management and concurrency models which allows experimentation without
requiring early design decisions.  This document describes many of the more
technical details of the current state of the implementation of the memory
object model, automatic memory management and concurrency models and describes
possible future developments.


The low level object model
===========================

One important part of the translation process is *rtyping* [DLT]_, [TR]_.
Before that step all objects in our flow graphs are annotated with types at the
level of the RPython type system which is still quite high-level and
target-independent.  During rtyping they are transformed into objects that
match the model of the specific target platform. For C or C-like targets this
model consists of a set of C-like types like structures, arrays and functions
in addition to primitive types (integers, characters, floating point numbers).
This multi-stage approach gives a lot of flexibility in how a given object is
represented at the target's level. The RPython process can decide what
representation to use based on the type annotation and on the way the object is
used.

In the following the structures used to represent RPython classes are described.
There is one "vtable" per RPython class, with the following structure: The root
class "object" has a vtable of the following type (expressed in a C-like 
syntax)::

    struct object_vtable {
        struct object_vtable* parenttypeptr;
        RuntimeTypeInfo * rtti;
        Signed subclassrange_min;
        Signed subclassrange_max;
        array { char } * name;
        struct object * instantiate();
    }

The structure members ``subclassrange_min`` and ``subclassrange_max`` are used
for subclass checking (see below). Every other class X, with parent Y, has the
structure::

    struct vtable_X {
        struct vtable_Y super;   // inlined
        ...                      // extra class attributes
    }

The extra class attributes usually contain function pointers to the methods
of that class, although the data class attributes (which are supported by the
RPython object model) are stored there.

The type of the instances is::

   struct object {       // for instances of the root class
       struct object_vtable* typeptr;
   }

   struct X {            // for instances of every other class
       struct Y super;   // inlined
       ...               // extra instance attributes
   }

The extra instance attributes are all the attributes of an instance.

These structure layouts are quite similar to how classes are usually
implemented in C++.

Subclass checking
-----------------

The way we do subclass checking is a good example of the flexibility provided
by our approach: in the beginning we were using a naive linear lookup
algorithm. Since subclass checking is quite a common operation (it is also used
to check whether an object is an instance of a certain class), we wanted to
replace it with the more efficient relative numbering algorithm (see [PVE]_ for
an overview of techniques). This was a matter of changing just the appropriate
code of the rtyping process to calculate the class-ids during rtyping and
insert the necessary fields into the class structure. It would be similarly
easy to switch to another implementation.

Identity hashes
---------------

In the RPython type system, class instances can be used as dictionary keys using
a default hash implementation based on identity, which in practice is
implemented using the memory address. This is similar to CPython's behavior
when no user-defined hash function is present. The annotator keeps track of the
classes for which this hashing is ever used.

One of the peculiarities of PyPy's approach is that live objects are analyzed
by our translation toolchain. This leads to the presence of instances of RPython
classes that were built before the translation started. These are called
"pre-built constants" (PBCs for short). During rtyping, these instances must be
converted to the low level model. One of the problems with doing this is that
the standard hash implementation of Python is to take the id of an object, which

is just the memory address. If the RPython program explicitly captures the
hash of a PBC by storing it (for example in the implementation of a data
structure) then the stored hash value will not match the value of the object's
address after translation.

To prevent this the following strategy is used: for every class whose instances
are hashed somewhere in the program (either when storing them in a
dictionary or by calling the hash function) an extra field is introduced in the
structure used for the instances of that class. For PBCs of such a class this
field is used to store the memory address of the original object and new objects
have this field initialized to zero. The hash function for instances of such a
class stores the object's memory address in this field if it is zero. The
return value of the hash function is the content of the field. This means that
instances of such a class that are converted PBCs retain the hash values they
had before the conversion whereas new objects of the class have their memory
address as hash values. A strategy along these lines would in any case have been
required if we ever switch to using a copying garbage collector.

Cached functions with PBC arguments
------------------------------------

As explained in [DLT]_ the annotated code can contain
functions from a finite set of PBCs to something else. The set itself has to be
finite but its content does not need to be provided explicitly but is discovered
as the annotation of the input argument by the annotator itself. This kind of
function is translated by recording the input-result relationship by calling
the function concretely at annotation time, and adding a field to the PBCs in
the set and emitting code reading that field instead of the function call.  

Changing the representation of an object
----------------------------------------

One example of the flexibility the RTyper provides is how we deal with lists.
Based on information gathered by the annotator the RTyper chooses between two
different list implementations. If a list never changes its size after creation,
a low-level array is used directly. For lists which might be resized, a
representation consisting of a structure with a pointer to an array is used,
together with over-allocation.

We plan to use similar techniques to use tagged pointers instead of using boxing
to represent builtin types of the PyPy interpreter such as integers. This would
require attaching explicit hints to the involved classes. Field access would
then be translated to the corresponding masking operations.


Automatic Memory Management Implementations
============================================

The whole implementation of the PyPy interpreter assumes automatic memory
management, e.g. automatic reclamation of memory that is no longer used. The
whole analysis toolchain also assumes that memory management is being taken
care of -- only the backends have to concern themselves with that issue. For
backends that target environments that have their own garbage collector, like
.NET or Java, this is not an issue. For other targets like C
the backend has to produce code that uses some sort of garbage collection.

This approach has several advantages. It makes it possible to target different
platforms, with and without integrated garbage collection. Furthermore, the
interpreter implementation is not complicated by the need to do explicit memory
management everywhere. Even more important the backend can optimize the memory
handling to fit a certain situation (like a machine with very restricted
memory) or completely replace the memory management technique or memory model
with a different one without the need to change source code. Additionally,
the backend can use information that was inferred by the rest of the toolchain
to improve the quality of memory management. 

Using the Boehm garbage collector
-----------------------------------

Currently there are two different garbage collectors implemented in the C
backend (which is the most complete backend right now). One of them uses the
existing Boehm-Demers-Weiser garbage collector [BOEHM]_. For every memory
allocating operation in a low level flow graph the C backend introduces a call
to a function of the boehm collector which returns a suitable amount of memory.
Since the C backend has a lot of information available about the data structure
being allocated it can choose the memory allocation function out of the Boehm
API that fits best. For example, for objects that do not contain references to
other objects (e.g. strings) there is a special allocation function which
signals to the collector that it does not need to consider this memory when
tracing pointers.

Using the Boehm collector has disadvantages as well. The problems stem from the
fact that the Boehm collector is conservative which means that it has to
consider every word in memory as a potential pointer. Since PyPy's toolchain
has complete knowledge of the placement of data in memory we can generate an
exact garbage collector that considers only genuine pointers.

Using a simple reference counting garbage collector
-----------------------------------------------------

The other implemented garbage collector is a simple reference counting scheme.
The C backend inserts a reference count field into every structure that has to be
handled by the garbage collector and puts increment and decrement operations
for this reference count into suitable places in the resulting C code. After
every reference decrement operations a check is performed whether the reference
count has dropped to zero. If this is the case the memory of the object will be
reclaimed after the references counts of the objects the original object
refers to are decremented as well.

The current placement of reference counter updates is far from optimal: The
reference counts are updated much more often than theoretically necessary (e.g.
sometimes a counter is increased and then immediately decreased again).
Objects passed into a function as arguments can almost always use a "trusted reference",
because the call-site is responsible to create a valid reference.
Furthermore some more analysis could show that some objects don't need a
reference counter at all because they either have a very short, foreseeable
life-time or because they live exactly as long as another object.

Another drawback of the current reference counting implementation is that it
cannot deal with circular references, which is a fundamental flaw of reference
counting memory management schemes in general. CPython solves this problem by
having special code that handles circular garbage which PyPy lacks at the
moment. This problem has to be addressed in the future to make the reference
counting scheme a viable garbage collector. Since reference counting is quite
successfully used by CPython it will be interesting to see how far it can be
optimized for PyPy.

Simple escape analysis to remove memory allocation
---------------------------------------------------

We also implemented a technique to reduce the amount of memory allocation.
Sometimes it is possible to deduce from the flow graphs that an object lives
exactly as long as the stack frame of the function it is allocated in.
This happens if no pointer to the object is stored into another object and if
no pointer to the object is returned from the function. If this is the case and
if the size of the object is known in advance the object can be allocated on
the stack. To achieve this, the object is "exploded", that means that for every
element of the structure a new variable is generated that is handed around in
the graph. Reads from elements of the structure are removed and just replaced
by one of the variables, writes by assignments to same.

Since quite a lot of objects are allocated in small helper functions, this
simple approach which does not track objects across function boundaries only
works well in the presence of function inlining.

A general garbage collection framework
--------------------------------------

In addition to the garbage collectors implemented in the C backend we have also
started writing a more general toolkit for implementing exact garbage
collectors in Python. The general idea is to express the garbage collection
algorithms in Python as well and translate them as part of the translation
process to C code (or whatever the intended platform is).

To be able to access memory in a low level manner there are special ``Address``
objects that behave like pointers to memory and can be manipulated accordingly:
it is possible to read/write to the location they point to a variety of data
types and to do pointer arithmetic.  These objects are translated to real
pointers and the appropriate operations. When run on top of CPython there is a
*memory simulator* that makes the address objects behave like they were
accessing real memory. In addition the memory simulator contains a number of
consistency checks that expose common memory handling errors like dangling
pointers, uninitialized memory, etc.

At the moment we have three simple garbage collectors implemented for this
framework: a simple copying collector, a mark-and-sweep collector and a
deferred reference counting collector. These garbage collectors are work when run on
top of the memory simulator, but at the moment it is not yet possible to translate
PyPy to C with them. This is because it is not easy to
find the root pointers that reside on the C stack -- both because the C stack layout is
heavily platform dependent, and also due to the possibility of roots that are not
only on the stack but also hiding in registers (which would give a problem for *moving
garbage collectors*).

There are several possible solutions for this problem: One
of them is to not use C compilers to generate machine code, so that the stack
frame layout gets into our control. This is one of the tasks that need to be
tackled in phase 2, as directly generating assembly is needed anyway for a
just-in-time compiler. The other possibility (which would be much easier to
implement) is to move all the data away from the stack to the heap
before collecting garbage, as described in section "Stackless C code"  below.

Concurrency Model Implementations
============================================

At the moment we have implemented two different concurrency models, and the
option to not support concurrency at all 
(another proof of the modularity of our approach):
threading with a global interpreter lock and a "stackless" model.

No threading
-------------

By default, multi-threading is not supported at all, which gives some small
benefits for single-threaded applications since even in the single-threaded
case there is some overhead if threading capabilities are built into
the interpreter.

Threading with a Global Interpreter Lock
------------------------------------------

Right now, there is one non-trivial threading model implemented. It follows
the threading implementation of CPython and thus uses a global interpreter
lock. This lock prevents any two threads from interpreting python code at
the same time. The global interpreter lock is released around calls to blocking I/O
functions. This approach has a number of advantages: it gives very little
runtime penalty for single-threaded applications, makes many of the common uses
for threading possible, and it is relatively easy to implement and maintain. It has
the disadvantage that multiple threads cannot be distributed across multiple
processors. 

To make this threading-model usable for I/O-bound applications, the global
interpreter lock should be released around blocking external function calls
(which is also what CPython does). This has been partially implemented.


Stackless C code
-----------------

"Stackless" C code is C code that only uses a bounded amount of
space in the C stack, and that can generally obtain explicit
control of its own stack.  This is commonly known as "continuations",
or "continuation-passing style" code, although in our case we will limit
ourselves to single-shot continuations, i.e. continuations that are
captured and subsequently will be resumed exactly once.

The technique we have implemented is based on the recurring idea
of emulating this style via exceptions: a specific program point can
generate a pseudo-exception whose purpose is to unwind the whole C stack
in a restartable way.  More precisely, the "unwind" exception causes 
the C stack to be saved into the heap in a compact and explicit
format, as described below.  It is then possible to resume only the
innermost (most recent) frame of the saved stack -- allowing unlimited
recursion on OSes that limit the size of the C stack -- or to resume a
different previously-saved C stack altogether, thus implementing
coroutines or light-weight threads.

In our case, exception handling is always explicit in the generated code:
the C backend puts a cheap check
after each call site to detect if the callee exited
normally or generated an exception.  So when compiling functions in
stackless mode, the generated exception handling code special-cases the
new "unwind" exception.  This exception causes the current function to
respond by saving its local variables to a heap structure (a linked list
of records, one per stack frame) and then propagating the exception
outwards.  Eventually, at the end of the frame chain, the outermost
function is a manually-written dispatcher that catches the "unwind"
exception.

At this point, the whole C stack is stored away in the heap.  This is a
very interesting state in itself, because precisely there is no C stack
below the dispatcher
left.  It is this which will allow us to write all the algorithms 
in a portable way, that
normally require machine-specific code to inspect the stack,
in particular garbage collectors.

To continue execution, the dispatcher can resume either the freshly saved or a
completely different stack.  Moreover, it can resume directly the innermost
(most recent) saved frame in the heap chain, without having to resume all
intermediate frames first.  This not only makes stack switches fast, but it
also allows the frame to continue to run on top of a clean C stack.  When that
frame eventually exits normally, it returns to the dispatcher, which then
invokes the previous (parent) saved frame, and so on. We insert stack checks
before calls that can lead to recursion by detecting cycles in the call graph.
These stack checks copy the stack to the heap (by raising the special
exception) if it is about to grow deeper than a certain level.
As a different point of view, the C stack can also be considered as a cache
for the heap-based saved frames in this model.  When we run out
of C stack space, we flush the cache.  When the cache is empty, we fill it with
the next item from the heap.

To give the translated program some amount of control over the
heap-based stack structures and over the top-level dispatcher that jumps
between them, there are a few "external" functions directly implemented
in C.  These functions provide an elementary interface, on top of which
useful abstractions can be implemented, like:

* coroutines: explicitly switching code, similar to Greenlets [GREENLET]_.

* "tasklets": cooperatively-scheduled microthreads, as introduced in
  Stackless Python [STK]_.

* implicitly-scheduled (preemptive) microthreads, also known as green threads.

An important property of the changes in all the generated C functions is
that they are written in a way that does only minimally degrade their performance in
the non-exceptional case.  Most optimizations performed by C compilers,
like register allocation, continue to work...

The following picture shows a graph function together with the modifications
necessary for the stackless style: the check whether the stack is too big and
should be unwound, the check whether we are in the process of currently storing
away the stack and the check whether the call to the function is not a regular
call but a reentry call.

.. graphviz:: image/stackless_informal.dot
   :scale: 70


Future work
================

open challenges for phase 2:

Garbage collection
------------------

One of the biggest missing features of our current garbage collectors is
finalization. At present finalizers are simply not invoked if an object is
freed by the garbage collector. Along the same lines weak references are not
supported yet. It should be possible to implement these with a reasonable
amount of effort for reference counting as well as the Boehm collector (which
provides the necessary hooks). 

Integrating the now simulated-only GC framework into the rtyping process and
the code generation will require considerable effort. It requires being able to
keep track of the GC roots which is hard to do with portable C code. One
solution would be to use the "stackless" code since it can move the stack 
completely to the heap. We expect that we can implement GC read and write 
barriers as function calls and rely on inlining to make them more efficient.

We may also spend some time on improving the existing reference counting
implementation by removing unnecessary incref-decref pairs and identifying
trustworthy references. A bigger task would
be to add support for detecting circular references.


Threading model
---------------

One of the interesting possibilities that stackless offers is to implement *green
threading*. This would involve writing a scheduler and some preemption logic. 

We should also investigate other threading models based on operating system
threads with various granularities of locking for access of shared objects.

Object model
------------

We also might want to experiment with more sophisticated structure inlining.
Sometimes it is possible to find out that one structure object
allocated on the heap lives exactly as long as another structure object on the
heap pointing to it. If this is the case it is possible to inline the first
object into the second. This saves the space of one pointer and avoids
pointer-chasing.


Conclusion
===========

As concretely shown with various detailed examples, our approach gives us
flexibility and lets us choose various aspects at translation time instead
of encoding them into the implementation itself.

References
===========

.. [BOEHM] `Boehm-Demers-Weiser garbage collector`_, a garbage collector
           for C and C++, Hans Boehm, 1988-2004
.. _`Boehm-Demers-Weiser garbage collector`: http://www.hpl.hp.com/personal/Hans_Boehm/gc/

.. [GREENLET] `Lightweight concurrent programming`_, py-lib Documentation 2003-2005
.. _`Lightweight concurrent programming`: http://codespeak.net/svn/greenlet/trunk/doc/greenlet.txt

.. [STK] `Stackless Python`_, a Python implementation that does not use
         the C stack, Christian Tismer, 1999-2004
.. _`Stackless Python`: http://www.stackless.com

.. [TR] `Translation`_, PyPy documentation, 2003-2005
.. _`Translation`: translation.html

.. [LE] `Encapsulating low-level implementation aspects`_,
        PyPy documentation (and EU deliverable D05.4), 2005
.. _`Encapsulating low-level implementation aspects`: low-level-encapsulation.html

.. [DLT] `Compiling dynamic language implementations`_,
         PyPy documentation (and EU deliverable D05.1), 2005
.. _`Compiling dynamic language implementations`: https://bitbucket.org/pypy/extradoc/raw/tip/eu-report/D05.1_Publish_on_translating_a_very-high-level_description.pdf

.. [PVE] `Simple and Efficient Subclass Tests`_, Jonathan Bachrach, Draft submission to ECOOP-02, 2001
.. _`Simple and Efficient Subclass Tests`: http://people.csail.mit.edu/jrb/pve/pve.pdf
