..
   @Ronan: This is the old documentation for the flow object space and flow model.
   Please integrate (and edit when needed) this into the new section in the document rpython/doc/translation.rst (section "Building Flow Graphs").


.. _flow-object-space:

The Flow Object Space
---------------------

Introduction
~~~~~~~~~~~~

The task of the FlowObjSpace (the source is at :source:`pypy/objspace/flow/`) is to generate a control-flow graph from a
function.  This graph will also contain a trace of the individual operations, so
that it is actually just an alternate representation for the function.

The FlowObjSpace is an object space, which means that it exports the standard
object space interface and it is driven by the bytecode interpreter.

The basic idea is that if the bytecode interpreter is given a function, e.g.::

  def f(n):
    return 3*n+2

it will do whatever bytecode dispatching and stack-shuffling needed, during
which it issues a sequence of calls to the object space.  The FlowObjSpace
merely records these calls (corresponding to "operations") in a structure called
a basic block.  To track which value goes where, the FlowObjSpace invents
placeholder "wrapped objects" and give them to the interpreter, so that they
appear in some next operation.  This technique is an example of `Abstract
Interpretation`_.

.. _Abstract Interpretation: http://en.wikipedia.org/wiki/Abstract_interpretation

For example, if the placeholder ``v1`` is given as the argument to the above
function, the bytecode interpreter will call ``v2 = space.mul(space.wrap(3),
v1)`` and then ``v3 = space.add(v2, space.wrap(2))`` and return ``v3`` as the
result.  During these calls the FlowObjSpace will record a basic block::

  Block(v1):     # input argument
    v2 = mul(Constant(3), v1)
    v3 = add(v2, Constant(2))


The Flow model
~~~~~~~~~~~~~~

The data structures built up by the flow object space are described in the
:ref:`translation document <rpython:flow-model>`.


How the FlowObjSpace works
~~~~~~~~~~~~~~~~~~~~~~~~~~

The FlowObjSpace works by recording all operations issued by the bytecode
interpreter into basic blocks.  A basic block ends in one of two cases: when
the bytecode interpreters calls ``is_true()``, or when a joinpoint is reached.

* A joinpoint occurs when the next operation is about to be recorded into the
  current block, but there is already another block that records an operation
  for the same bytecode position.  This means that the bytecode interpreter
  has closed a loop and is interpreting already-seen code again.  In this
  situation, we interrupt the bytecode interpreter and we make a link from the
  end of the current block back to the previous block, thus closing the loop
  in the flow graph as well.  (Note that this occurs only when an operation is
  about to be recorded, which allows some amount of constant-folding.)

* If the bytecode interpreter calls ``is_true()``, the FlowObjSpace doesn't
  generally know if the answer should be True or False, so it puts a
  conditional jump and generates two successor blocks for the current basic
  block.  There is some trickery involved so that the bytecode interpreter is
  fooled into thinking that ``is_true()`` first returns False (and the
  subsequent operations are recorded in the first successor block), and later
  the *same* call to ``is_true()`` also returns True (and the subsequent
  operations go this time to the other successor block).

(This section to be extended...)



.. _flow-model:

The Flow Model
--------------

The :ref:`Flow Object Space <flow-object-space>` is described in the `document
describing object spaces`_. Here we describe the data structures produced by it,
which are the basic data structures of the translation
process.

All these types are defined in :source:`rpython/flowspace/model.py` (which is a rather
important module in the PyPy source base, to reinforce the point).

The flow graph of a function is represented by the class ``FunctionGraph``.
It contains a reference to a collection of ``Block``\ s connected by ``Link``\ s.

A ``Block`` contains a list of ``SpaceOperation``\ s.  Each ``SpaceOperation``
has an ``opname`` and a list of ``args`` and ``result``, which are either
``Variable``\ s or ``Constant``\ s.

We have an extremely useful PyGame viewer, which allows you to visually
inspect the graphs at various stages of the translation process (very
useful to try to work out why things are breaking).  It looks like this:

   .. image:: _static/bpnn_update.png

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
                   explicitly raise exceptions.)


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

.. _document describing object spaces: objspace.html
