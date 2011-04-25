=====================
 PyPy - Translation
=====================

.. contents::


This document describes the tool chain that we have developed to analyze
and "compile" RPython_ programs (like PyPy itself) to various target
platforms.

.. _RPython: coding-guide.html#restricted-python

It consists of three broad sections: a slightly simplified overview, a
brief introduction to each of the major components of our tool chain and
then a more comprehensive section describing how the pieces fit together.
If you are reading this document for the first time, the Overview_ is
likely to be most useful, if you are trying to refresh your PyPy memory
then the `How It Fits Together`_ is probably what you want.

Overview
========

The job of translation tool chain is to translate RPython_ programs into an
efficient version of that program for one of various target platforms,
generally one that is considerably lower-level than Python.  It divides
this task into several steps, and the purpose of this document is to
introduce them.

As of the 1.2 release, RPython_ programs can be translated into the following
languages/platforms: C/POSIX, CLI/.NET
and Java/JVM (in addition, there's `a backend`_ that translates
`application-level`_ into `interpreter-level`_ code, but this is a special
case in several ways).

.. _`a backend`: geninterp.html
.. _`application-level`: coding-guide.html#application-level
.. _`interpreter-level`: coding-guide.html#interpreter-level

The choice of the target platform affects the process somewhat, but to
start with we describe the process of translating an RPython_ program into
C (which is the default and original target).

.. _`initialization time`:

The translation tool chain never sees Python source code or syntax
trees, but rather starts with the *code objects* that define the
behaviour of the function objects one gives it as input.  The
`bytecode evaluator`_ and the `Flow Object Space`_ work through these
code objects using `abstract interpretation`_ to produce a control
flow graph (one per function): yet another representation of the
source program, but one which is suitable for applying type inference
and translation techniques and which is the fundamental data structure
most of the translation steps operate on.

It is helpful to consider translation as being made up of the following
steps (see also the figure below):

1. The complete program is imported, at which time arbitrary run-time
   initialization can be performed.  Once this is done, the program must
   be present in memory as a form that is "static enough" in the sense of
   RPython_.

2. The Annotator_ performs a global analysis starting from an specified
   entry point to deduce type and other information about what each
   variable can contain at run-time, building flow graphs using the `Flow
   Object Space`_ as it encounters them.

3. The `RPython Typer`_ (or RTyper) uses the high-level information
   inferred by the Annotator to turn the operations in the control flow
   graphs into low-level operations.

4. After RTyping there are two, rather different, `optional
   transformations`_ which can be applied -- the "backend
   optimizations" which are intended to make the resulting program go
   faster, and the "stackless transform" which transforms the program
   into a form of continuation passing style which allows the
   implementation of coroutines and other forms of non-standard
   control flow.

5. The next step is `preparing the graphs for source generation`_, which
   involves computing the names that the various functions and types in
   the program will have in the final source and applying transformations
   which insert explicit exception handling and memory management
   operations.

6. The `C backend`_ (colloquially known as "GenC") produces a number of C
   source files (as noted above, we are ignoring the other backends for
   now).

7. These source files are compiled to produce an executable.

(although these steps are not quite as distinct as you might think from
this presentation).

There is an `interactive interface`_ called `translatorshell.py`_ to the
translation process which allows you to interactively work through these
stages.

The following figure gives a simplified overview (`PDF color version`_):

    .. image:: image/translation-greyscale-small.png


.. _`PDF color version`: image/translation.pdf
.. _`bytecode evaluator`: interpreter.html
.. _`abstract interpretation`: http://en.wikipedia.org/wiki/Abstract_interpretation
.. _`Flow Object Space`: objspace.html#the-flow-object-space
.. _`interactive interface`: getting-started-dev.html#try-out-the-translator
.. _`translatorshell.py`: ../../../../pypy/bin/translatorshell.py

.. _`flow model`:
.. _`control flow graphs`: 

The Flow Model
==============

The `Flow Object Space`_ is described in the `document
describing object spaces`_. Here we describe the data structures produced by it,
which are the basic data structures of the translation
process.

All these types are defined in `pypy.objspace.flow.model`_ (which is a rather
important module in the PyPy source base, to reinforce the point).

The flow graph of a function is represented by the class ``FunctionGraph``.
It contains a reference to a collection of ``Block``\ s connected by ``Link``\ s.

A ``Block`` contains a list of ``SpaceOperation``\ s.  Each ``SpaceOperation``
has an ``opname`` and a list of ``args`` and ``result``, which are either
``Variable``\ s or ``Constant``\ s.

We have an extremely useful PyGame viewer, which allows you to visually
inspect the graphs at various stages of the translation process (very
useful to try to work out why things are breaking).  It looks like this:

   .. image:: image/bpnn_update.png

It is recommended to play with ``python bin/translatorshell.py`` on a few
examples to get an idea of the structure of flow graphs. The following describes
the types and their attributes in some detail:


``FunctionGraph``
    A container for one graph (corresponding to one function).

    :startblock:   the first block.  It is where the control goes when the
                   function is called.  The input arguments of the startblock
                   are the function's arguments.  If the function takes a
                   ``*args`` argument, the ``args`` tuple is given as the last
                   input argument of the startblock.

    :returnblock:  the (unique) block that performs a function return.  It is
                   empty, not actually containing any ``return`` operation; the
                   return is implicit.  The returned value is the unique input
                   variable of the returnblock.

    :exceptblock:  the (unique) block that raises an exception out of the
                   function.  The two input variables are the exception class
                   and the exception value, respectively.  (No other block will
                   actually link to the exceptblock if the function does not
                   explicitely raise exceptions.)


``Block``
    A basic block, containing a list of operations and ending in jumps to other
    basic blocks.  All the values that are "live" during the execution of the
    block are stored in Variables.  Each basic block uses its own distinct
    Variables.

    :inputargs:   list of fresh, distinct Variables that represent all the
                  values that can enter this block from any of the previous
                  blocks.

    :operations:  list of SpaceOperations.
    :exitswitch:  see below

    :exits:       list of Links representing possible jumps from the end of this
                  basic block to the beginning of other basic blocks.

    Each Block ends in one of the following ways:

    * unconditional jump: exitswitch is None, exits contains a single Link.

    * conditional jump: exitswitch is one of the Variables that appear in the
      Block, and exits contains one or more Links (usually 2).  Each Link's
      exitcase gives a concrete value.  This is the equivalent of a "switch":
      the control follows the Link whose exitcase matches the run-time value of
      the exitswitch Variable.  It is a run-time error if the Variable doesn't
      match any exitcase.

    * exception catching: exitswitch is ``Constant(last_exception)``.  The first
      Link has exitcase set to None and represents the non-exceptional path.
      The next Links have exitcase set to a subclass of Exception, and are taken
      when the *last* operation of the basic block raises a matching exception.
      (Thus the basic block must not be empty, and only the last operation is
      protected by the handler.)

    * return or except: the returnblock and the exceptblock have operations set
      to an empty tuple, exitswitch to None, and exits empty.


``Link``
    A link from one basic block to another.

    :prevblock:  the Block that this Link is an exit of.
    
    :target:     the target Block to which this Link points to.

    :args:       a list of Variables and Constants, of the same size as the
                 target Block's inputargs, which gives all the values passed
                 into the next block.  (Note that each Variable used in the
                 prevblock may appear zero, one or more times in the ``args``
                 list.)

    :exitcase:   see above.

    :last_exception: None or a Variable; see below.

    :last_exc_value: None or a Variable; see below.

    Note that ``args`` uses Variables from the prevblock, which are matched to
    the target block's ``inputargs`` by position, as in a tuple assignment or
    function call would do.

    If the link is an exception-catching one, the ``last_exception`` and
    ``last_exc_value`` are set to two fresh Variables that are considered to be
    created when the link is entered; at run-time, they will hold the exception
    class and value, respectively.  These two new variables can only be used in
    the same link's ``args`` list, to be passed to the next block (as usual,
    they may actually not appear at all, or appear several times in ``args``).


``SpaceOperation``
    A recorded (or otherwise generated) basic operation.

    :opname:  the name of the operation. The Flow Space produces only operations
              from the list in ``pypy.interpreter.baseobjspace``, but later the
              names can be changed arbitrarily.

    :args:    list of arguments.  Each one is a Constant or a Variable seen
              previously in the basic block.

    :result:  a *new* Variable into which the result is to be stored.

    Note that operations usually cannot implicitly raise exceptions at run-time;
    so for example, code generators can assume that a ``getitem`` operation on a
    list is safe and can be performed without bound checking.  The exceptions to
    this rule are: (1) if the operation is the last in the block, which ends
    with ``exitswitch == Constant(last_exception)``, then the implicit
    exceptions must be checked for, generated, and caught appropriately; (2)
    calls to other functions, as per ``simple_call`` or ``call_args``, can
    always raise whatever the called function can raise --- and such exceptions
    must be passed through to the parent unless they are caught as above.


``Variable``
    A placeholder for a run-time value.  There is mostly debugging stuff here.

    :name:  it is good style to use the Variable object itself instead of its
            ``name`` attribute to reference a value, although the ``name`` is
            guaranteed unique.


``Constant``
    A constant value used as argument to a SpaceOperation, or as value to pass
    across a Link to initialize an input Variable in the target Block.

    :value:  the concrete value represented by this Constant.
    :key:    a hashable object representing the value.

    A Constant can occasionally store a mutable Python object.  It represents a
    static, pre-initialized, read-only version of that object.  The flow graph
    should not attempt to actually mutate such Constants.

.. _`document describing object spaces`: objspace.html
.. _`pypy.objspace.flow.model`: ../../../../pypy/objspace/flow/model.py


.. _Annotator:

The Annotation Pass
===================

We describe briefly below how a control flow graph can be "annotated" to
discover the types of the objects.  This annotation pass is a form of type
inference.  It operates on the control flow graphs built by the Flow
Object Space.

For a more comprehensive description of the annotation process, see the
corresponding section of our `EU report about translation`_.

The major goal of the annotator is to "annotate" each variable that
appears in a flow graph.  An "annotation" describes all the possible
Python objects that this variable could contain at run-time, based on a
whole-program analysis of all the flow graphs -- one per function.

An "annotation" is an instance of a subclass of ``SomeObject``.  Each
subclass that represents a specific family of objects.

Here is an overview (see ``pypy.annotation.model``):

* ``SomeObject`` is the base class.  An instance of ``SomeObject()``
  represents any Python object, and as such usually means that the input
  program was not fully RPython.

* ``SomeInteger()`` represents any integer.  ``SomeInteger(nonneg=True)``
  represent a non-negative integer (``>=0``).

* ``SomeString()`` represents any string; ``SomeChar()`` a string of
  length 1.

* ``SomeTuple([s1,s2,..,sn])`` represents a tuple of length ``n``.  The
  elements in this tuple are themselves constrained by the given list of
  annotations.  For example, ``SomeTuple([SomeInteger(), SomeString()])``
  represents a tuple with two items: an integer and a string.


The result of the annotation pass is essentially a large dictionary
mapping ``Variable``\ s to annotations.

All the ``SomeXxx`` instances are immutable.  If the annotator needs to
revise its belief about what a Variable can contain, it does so creating a
new annotation, not mutating the existing one.


Mutable Values and Containers
------------------------------

Mutable objects need special treatment during annotation, because
the annotation of contained values needs to be possibly updated to account
for mutation operations, and consequently the annotation information
reflown through the relevant parts of the flow the graphs.

* ``SomeList`` stands for a list of homogeneous type (i.e. all the
  elements of the list are represented by a single common ``SomeXxx``
  annotation).

* ``SomeDict`` stands for a homogeneous dictionary (i.e. all keys have
  the same ``SomeXxx`` annotation, and so have all values).

User-defined Classes and Instances
-----------------------------------

``SomeInstance`` stands for an instance of the given class or any
subclass of it.  For each user-defined class seen by the annotator, we
maintain a ClassDef (``pypy.annotation.classdef``) describing the
attributes of the instances of the class; essentially, a ClassDef gives
the set of all class-level and instance-level attributes, and for each
one, a corresponding ``SomeXxx`` annotation.

Instance-level attributes are discovered progressively as the annotation
progresses.  Assignments like::

   inst.attr = value

update the ClassDef of the given instance to record that the given
attribute exists and can be as general as the given value.

For every attribute, the ClassDef also records all the positions where
the attribute is *read*.  If, at some later time, we discover an
assignment that forces the annotation about the attribute to be
generalized, then all the places that read the attribute so far are
marked as invalid and the annotator will restart its analysis
from there.

The distinction between instance-level and class-level attributes is
thin; class-level attributes are essentially considered as initial
values for instance-level attributes.  Methods are not special in this
respect, except that they are bound to the instance (i.e. ``self =
SomeInstance(cls)``) when considered as the initial value for the
instance.

The inheritance rules are as follows: the union of two ``SomeInstance``
annotations is the ``SomeInstance`` of the most precise common base
class.  If an attribute is considered (i.e. read or written) through a
``SomeInstance`` of a parent class, then we assume that all subclasses
also have the same attribute, and that the same annotation applies to
them all (so code like ``return self.x`` in a method of a parent class
forces the parent class and all its subclasses to have an attribute
``x``, whose annotation is general enough to contain all the values that
all the subclasses might want to store in ``x``).  However, distinct
subclasses can have attributes of the same names with different,
unrelated annotations if they are not used in a general way through the
parent class.


.. _`RPython typer`:

The RPython Typer
=================

http://codespeak.net/pypy/trunk/pypy/rpython/

The RTyper is the first place where the choice of backend makes a
difference; as outlined above we are assuming that ANSI C is the target.

The RPython Typer is the bridge between the Annotator_ and the code
generator.  The information computed by the annotator is high-level, in
the sense that it describe RPython types like lists or instances of
user-defined classes.

To emit code we need to represent these high-level annotations in the
low-level model of the target language; for C, this means structures and
pointers and arrays.  The Typer both determines the appropriate low-level type
for each annotation and replaces each high-level operation in the control flow
graphs with one or a few low-level operations.  Just like low-level types,
there is only a fairly restricted set of low-level operations, along the lines
of reading or writing from or to a field of a structure.

In theory, this step is optional; a code generator might be able to read
directly the high-level types.  Our experience, however, suggests that this is
very unlikely to be practical.  "Compiling" high-level types into low-level
ones is rather more messy than one would expect and this was the motivation
for making this step explicit and isolated in a single place.  After RTyping,
the graphs only contain operations that already live on the level of the
target language, which makes the job of the code generators much simpler.

For more detailed information, see the `documentation for the RTyper`_.

.. _`documentation for the RTyper`: rtyper.html

Example: Integer operations
---------------------------

Integer operations are make an easy example.  Assume a graph containing the
following operation::

    v3 = add(v1, v2)

annotated::

    v1 -> SomeInteger()
    v2 -> SomeInteger()
    v3 -> SomeInteger()

then obviously we want to type it and replace it with::

    v3 = int_add(v1, v2)

where -- in C notation -- all three variables v1, v2 and v3 are typed ``int``.
This is done by attaching an attribute ``concretetype`` to v1, v2 and v3
(which might be instances of Variable or possibly Constant).  In our model,
this ``concretetype`` is ``pypy.rpython.lltypesystem.lltype.Signed``.  Of
course, the purpose of replacing the operation called ``add`` with
``int_add`` is that code generators no longer have to worry about what kind
of addition (or concatenation maybe?) it means.

.. _`optional transformations`:

The Optional Transformations
============================

Between RTyping and C source generation there are two optional transforms:
the "backend optimizations" and the "stackless transform". See also
`D07.1 Massive Parallelism and Translation Aspects`_ for further details.

.. _`Technical report`: 
.. _`D07.1 Massive Parallelism and Translation Aspects`: http://codespeak.net/pypy/extradoc/eu-report/D07.1_Massive_Parallelism_and_Translation_Aspects-2007-02-28.pdf

Backend Optimizations
---------------------

The point of the backend optimizations are to make the compiled program run
faster.  Compared to many parts of the PyPy translator, which are very unlike
a traditional compiler, most of these will be fairly familiar to people who
know how compilers work.

Function Inlining
+++++++++++++++++

To reduce the overhead of the many function calls that occur when running the
PyPy interpreter we implemented function inlining. This is an optimization
which takes a flow graph and a callsite and inserts a copy of the flow graph
into the graph of the calling function, renaming occurring variables as
appropriate. This leads to problems if the original function was surrounded by
a ``try: ... except: ...`` guard. In this case inlining is not always
possible.  If the called function is not directly raising an exception (but an
exception is potentially raised by further called functions) inlining is safe,
though.

In addition we also implemented heuristics which function to inline where. For
this purpose we assign every function a "size". This size should roughly
correspond to the increase in code-size which is to be expected should the
function be inlined somewhere. This estimate is the sum of two numbers: for
one every operations is assigned a specific weight, the default being a weight
of one. Some operations are considered to be more effort than others,
e.g. memory allocation and calls; others are considered to be no effort at all
(casts...). The size estimate is for one the sum of the weights of all
operations occurring in the graph. This is called the "static instruction
count". The other part of the size estimate of a graph is the "median
execution cost". This is again the sum of the weight of all operations in the
graph, but this time weighted with a guess how often the operation is
executed. To arrive at this guess we assume that at every branch we take both
paths equally often, except for branches that are the end of loops, where the
jump back to the end of the loop is considered more likely.  This leads to a
system of equations which can be solved to get approximate weights for all
operations.

After the size estimate for all function has been determined, functions are
being inlined into their callsites, starting from the smallest functions. Every
time a function is being inlined into another function, the size of the outer
function is recalculated. This is done until the remaining functions all have a
size greater than a predefined limit.

Malloc Removal
++++++++++++++

Since RPython is a garbage collected language there is a lot of heap memory
allocation going on all the time, which would either not occur at all in a more
traditional explicitely managed language or results in an object which dies at
a time known in advance and can thus be explicitely deallocated. For example a
loop of the following form::

    for i in range(n):
        ...

which simply iterates over all numbers from 0 to n - 1 is equivalent to the
following in Python::

    l = range(n)
    iterator = iter(l)
    try:
        while 1:
            i = iterator.next()
            ...
    except StopIteration:
        pass

Which means that three memory allocations are executed: The range object, the
iterator for the range object and the StopIteration instance, which ends the
loop.

After a small bit of inlining all these three objects are never even passed as
arguments to another function and are also not stored into a globally reachable
position. In such a situation the object can be removed (since it would die
anyway after the function returns) and can be replaced by its contained values.

This pattern (an allocated object never leaves the current function and thus
dies after the function returns) occurs quite often, especially after some
inlining has happened. Therefore we implemented an optimization which
"explodes" objects and thus saves one allocation in this simple (but quite
common) situation.


Escape Analysis and Stack Allocation
++++++++++++++++++++++++++++++++++++

Another technique to reduce the memory allocation penalty is to use stack
allocation for objects that can be proved not to life longer than the stack
frame they have been allocated in.  This proved not to really gain us any
speed, so over time it was removed again.


The Stackless Transform
-----------------------

The stackless transform converts functions into a form that knows how
to save the execution point and active variables into a heap structure
and resume execution at that point.  This is used to implement
coroutines as an RPython-level feature, which in turn are used to
implement `coroutines, greenlets and tasklets`_ as an application
level feature for the Standard Interpreter.

Enable the stackless transformation with :config:`translation.stackless`.

.. _`coroutines, greenlets and tasklets`: stackless.html

.. _`preparing the graphs for source generation`:

Preparation for Source Generation
=================================

This, perhaps slightly vaguely named, stage is the most recent to appear as a
separate step.  Its job is to make the final implementation decisions before
source generation -- experience has shown that you really don't want to be
doing *any* thinking at the same time as actually generating source code.  For
the C backend, this step does three things:

 - inserts explicit exception handling,

 - inserts explicit memory management operations,

 - decides on the names functions and types will have in the final
   source (this mapping of objects to names is sometimes referred to as
   the "low-level database").

Making Exception Handling Explicit
----------------------------------

RPython code is free to use exceptions in much the same way as unrestricted
Python, but the final result is a C program, and C has no concept of
exceptions.  The exception transformer implements exception handling in a
similar way to CPython: exceptions are indicated by special return values and
the current exception is stored in a global data structure.

In a sense the input to the exception transformer is a program in terms of the
lltypesystem_ with exceptions and the output is a program in terms of the bare
lltypesystem.

.. _lltypesystem: glossary.html#lltypesystem

Memory Management Details
-------------------------

As well as featuring exceptions, RPython is a garbage collected language;
again, C is not.  To square this circle, decisions about memory management
must be made.  In keeping with PyPy's approach to flexibility, there is
freedom to change how to do it.  There are three approaches implemented today:

 - reference counting (deprecated, too slow)
 - using the `Boehm-Demers-Weiser conservative garbage collector`_
 - using one of our custom `exact GCs implemented in RPython`_

.. _`Boehm-Demers-Weiser conservative garbage collector`: http://www.hpl.hp.com/personal/Hans_Boehm/gc/
.. _`exact GCs implemented in RPython`: garbage_collection.html

Almost all application-level Python code allocates objects at a very fast
rate; this means that the memory management implementation is critical to the
performance of the PyPy interpreter.

You can choose which garbage collection strategy to use with
:config:`translation.gc`.


.. _C:
.. _GenC:
.. _`c backend`:

The C Back-End
==============

http://codespeak.net/pypy/trunk/pypy/translator/c/

GenC is not really documented at the moment.  The basic principle of creating
code from flow graphs is similar to the `Python back-end`_.  See also
"Generating C code" in our `EU report about translation`_.

GenC is usually the most actively maintained backend -- everyone working on
PyPy has a C compiler, for one thing -- and is usually where new features are
implemented first.

.. _`EU report about translation`: http://codespeak.net/svn/pypy/extradoc/eu-report/D05.1_Publish_on_translating_a_very-high-level_description.pdf


A Historical Note
=================

As this document has shown, the translation step is divided into more
steps than one might at first expect.  It is certainly divided into more
steps than we expected when the project started; the very first version of
GenC operated on the high-level flow graphs and the output of the
annotator, and even the concept of the RTyper didn't exist yet.  More
recently, the fact that preparing the graphs for source generation
("databasing") and actually generating the source are best considered
separately has become clear.


Other backends
==============

Use the :config:`translation.backend` option to choose which backend to use.



The Object-Oriented Backends
----------------------------

The Object-Oriented backends target platforms that are less C-like and support
classes, instance etc. If such a platform is targeted, the `OO type system` is
used while rtyping. Of the OO backends, both gencli and genjava can translate
the full Python interpreter.

.. _`oo type system`: rtyper.html#oo-type

.. mention that pretty much all these backends are done by volunteers?

GenCLI
++++++

GenCLI_ targets the `Common Language Infrastructure`_, the most famous
implementations of which are Microsoft's `.NET`_ and Mono_.

It is the most advanced of the object oriented backends -- it can
compile the PyPy interpreter as well as our two standard benchmarks,
RPyStone (CPython's PyStone benchmark modified slightly to be RPython)
and a RPython version of the common Richards benchmark.

It is almost entirely the work of Antonio Cuni, who started this
backend as part of his `Master's thesis`_, the Google's Summer of Code
2006 program and the Summer of PyPy program.

.. _`Common Language Infrastructure`: http://www.ecma-international.org/publications/standards/Ecma-335.htm
.. _`.NET`: http://www.microsoft.com/net/
.. _Mono: http://www.mono-project.com/
.. _`Master's thesis`: http://codespeak.net/~antocuni/Implementing%20Python%20in%20.NET.pdf
.. _GenCLI: cli-backend.html

GenJVM
++++++

GenJVM targets the Java Virtual Machine: it translates RPython
programs directly into Java bytecode, similarly to what GenCLI does.

So far it is the second most mature high level backend after GenCLI:
it still can't translate the full Standard Interpreter, but after the
Leysin sprint we were able to compile and run the rpytstone and
richards benchmarks.

GenJVM is almost entirely the work of Niko Matsakis, who worked on it
also as part of the Summer of PyPy program.

.. _`Python again`:
.. _`Python back-end`:

The Interpreter-Level backend
-----------------------------

http://codespeak.net/pypy/trunk/pypy/translator/geninterplevel.py

Above, this backend was described as a "special case in several ways".  One of
these ways is that the job it does is specific to PyPy's standard interpreter,
and the other is that it does not even use the annotator -- it works directly
the graphs produced by the Flow Object Space.

See `geninterp's documentation <geninterp.html>`__.

.. _extfunccalls:

External Function Calls
=======================

External function call approach is described in `rffi`_ documentation.

.. _`rffi`: rffi.html

How It Fits Together
====================

As should be clear by now, the translation tool chain of PyPy is a flexible
and complicated beast, formed from many separate components.

The following image summarizes the various parts of the tool chain as of the
0.9 release, with the default translation to C highlighted:

.. image:: image/pypy-translation-0.9.png
   :align: center

A detail that has not yet been emphasized is the interaction of the
various components.  It makes for a nice presentation to say that
after the annotator has finished the RTyper processes the graphs and
then the exception handling is made explicit and so on, but it's not
entirely true.  For example, the RTyper inserts calls to many
`low-level helpers`_ which must first be annotated, and the GC
transformer can use inlining (one of the `backend optimizations`_) of
some of its small helper functions to improve performance.  The
following picture attempts to summarize the components involved in
performing each step of the default translation process:

.. image:: image/translation-detail-0.9.png
   :align: center

.. _`low-level helpers`: glossary.html#low-level-helper

A component not mentioned before is the "MixLevelAnnotator"; it
provides a convenient interface for a "late" (after RTyping)
translation step to declare that it needs to be able to call each of a
collection of functions (which may refer to each other in a mutually
recursive fashion) and annotate and rtype them all at once.

.. include:: _ref.rst
