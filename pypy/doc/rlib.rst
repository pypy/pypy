=================================================
Generally Useful RPython Modules 
=================================================

.. _Python: http://www.python.org/dev/doc/maint24/ref/ref.html

.. contents::


This page lists some of the modules in `pypy/rlib`_ together with some hints
for what they can be used for. The modules here will make up some general
library useful for RPython programs (since most of the standard library modules
are not RPython). Most of these modules are somewhat rough still and are likely
to change at some point.  Usually it is useful to look at the tests in
`pypy/rlib/test`_ to get an impression of how to use a module.


``listsort``
============

The `pypy/rlib/listsort.py`_ module contains an implementation of the timsort sorting algorithm
(the sort method of lists is not RPython). To use it, subclass from the
``listsort.TimSort`` class and override the ``lt`` method to change the
comparison behaviour. The constructor of ``TimSort`` takes a list as an
argument, which will be sorted in place when the ``sort`` method of the
``TimSort`` instance is called. **Warning:** currently only one type of list can
be sorted using the ``listsort`` module in one program, otherwise the annotator
will be confused.

``nonconst``
============

The `pypy/rlib/nonconst.py`_ module is useful mostly for tests. The `flow object space`_ and
the `annotator`_ do quite some constant folding, which is sometimes not desired
in a test. To prevent constant folding on a certain value, use the ``NonConst``
class. The constructor of ``NonConst`` takes an arbitrary value. The instance of
``NonConst`` will behave during annotation like that value, but no constant
folding will happen.

.. _`flow object space`: objspace.html#the-flow-object-space
.. _`annotator`: translation.html#the-annotation-pass


``objectmodel``
===============

The `pypy/rlib/objectmodel.py`_ module is a mixed bag of various functionality. Some of the
more useful ones are:

``ComputedIntSymbolic``:
    Instances of ``ComputedIntSymbolic`` are treated like integers of unknown
    value by the annotator. The value is determined by a no-argument function
    (which needs to be passed into the constructor of the class). When the
    backend emits code, the function is called to determine the value.

``CDefinedIntSymbolic``:
    Instances of ``ComputedIntSymbolic`` are also treated like integers of
    unknown value by the annotator. When C code is emitted they will be
    represented by the attribute ``expr`` of the symbolic (which is also the
    first argument of the constructor).

``r_dict``:
    An RPython dict-like object. The constructor of r_dict takes two functions:
    ``key_eq`` and ``key_hash`` which are used for comparing and hashing the
    entries in the dictionary.

``instantiate(cls)``:
    Instantiate class ``cls`` without calling ``__init__``.

``we_are_translated()``:
    This function returns ``False`` when run on top of CPython, but the
    annotator thinks its return value is ``True``. Therefore it can be used to
    do different things on top of CPython than after translation. This should be
    used extremely sparingly (mostly for optimizations or debug code).

``cast_object_to_weakaddress(obj)``:
    Returns a sort of "weak reference" to obj, just without any convenience. The
    weak address that it returns is not invalidated if the object dies, so you
    need to take care yourself to know when the object dies. Use with extreme
    care.

``cast_weakadress_to_object(obj)``:
    Inverse of the previous function. If the object died then a segfault will
    ensue.

``UnboxedValue``:
    This is a class which should be used as a base class for a class which
    carries exactly one integer field. The class should have ``__slots__``
    with exactly one entry defined. After translation, instances of this class
    won't be allocated but represented by *tagged pointers**, that is pointers
    that have the lowest bit set.


``rarithmetic``
===============

The `pypy/rlib/rarithmetic.py`_ module contains functionality to handle the small differences
in the behaviour of arithmetic code in regular Python and RPython code. Most of
them are already described in the `coding guide`_

.. _`coding guide`: coding-guide.html


``rbigint``
===========

The `pypy/rlib/rbigint.py`_ module contains a full RPython implementation of the Python ``long``
type (which itself is not supported in RPython). The ``rbigint`` class contains
that implementation. To construct ``rbigint`` instances use the static methods
``fromint``, ``frombool``, ``fromfloat`` and ``fromdecimalstr``. To convert back
to other types use the methods ``toint``, ``tobool``, ``touint`` and
``tofloat``. Since RPython does not support operator overloading, all the
special methods of ``rbigint`` that would normally start and end with "__" have
these underscores left out for better readability (so ``a.add(b)`` can be used
to add two rbigint instances).


``rrandom``
===========

The `pypy/rlib/rrandom.py`_ module contains an implementation of the mersenne twister random
number generator. It contains one class ``Random`` which most importantly has a
``random`` method which returns a pseudo-random floating point number between
0.0 and 1.0.

``rsocket``
===========

The `pypy/rlib/rsocket.py`_ module contains an RPython implementation of the functionality of
the socket standard library with a slightly different interface.  The
difficulty with the Python socket API is that addresses are not "well-typed"
objects: depending on the address family they are tuples, or strings, and
so on, which is not suitable for RPython.  Instead, ``rsocket`` contains
a hierarchy of Address classes, in a typical static-OO-programming style.


``rstack``
==========

The `pypy/rlib/rstack.py`_ module allows an RPython program to control its own execution stack.
This is only useful if the program is translated using stackless. An old
description of the exposed functions is below.

We introduce an RPython type ``frame_stack_top`` and a built-in function
``yield_current_frame_to_caller()`` that work as follows (see example below):

* The built-in function ``yield_current_frame_to_caller()`` causes the current
  function's state to be captured in a new ``frame_stack_top`` object that is
  returned to the parent.  Only one frame, the current one, is captured this
  way.  The current frame is suspended and the caller continues to run.  Note
  that the caller is only resumed once: when
  ``yield_current_frame_to_caller()`` is called.  See below.

* A ``frame_stack_top`` object can be jumped to by calling its ``switch()``
  method with no argument.

* ``yield_current_frame_to_caller()`` and ``switch()`` themselves return a new
  ``frame_stack_top`` object: the freshly captured state of the caller of the
  source ``switch()`` that was just executed, or None in the case described
  below.

* the function that called ``yield_current_frame_to_caller()`` also has a
  normal return statement, like all functions.  This statement must return
  another ``frame_stack_top`` object.  The latter is *not* returned to the
  original caller; there is no way to return several times to the caller.
  Instead, it designates the place to which the execution must jump, as if by
  a ``switch()``.  The place to which we jump this way will see a None as the
  source frame stack top.

* every frame stack top must be resumed once and only once.  Not resuming
  it at all causes a leak.  Resuming it several times causes a crash.

* a function that called ``yield_current_frame_to_caller()`` should not raise.
  It would have no implicit parent frame to propagate the exception to.  That
  would be a crashingly bad idea.

The following example would print the numbers from 1 to 7 in order::

    def g():
        print 2
        frametop_before_5 = yield_current_frame_to_caller()
        print 4
        frametop_before_7 = frametop_before_5.switch()
        print 6
        return frametop_before_7

    def f():
        print 1
        frametop_before_4 = g()
        print 3
        frametop_before_6 = frametop_before_4.switch()
        print 5
        frametop_after_return = frametop_before_6.switch()
        print 7
        assert frametop_after_return is None

    f()


``streamio``
============

The `pypy/rlib/streamio.py`_ contains an RPython stream I/O implementation (which was started
by Guido van Rossum as `sio.py`_ in the CPython sandbox as a prototype for the
upcoming new file implementation in Python 3000).

.. _`sio.py`: http://svn.python.org/view/sandbox/trunk/sio/sio.py

``unroll``
==========

The `pypy/rlib/unroll.py`_ module most importantly contains the function ``unrolling_iterable``
which wraps an iterator. Looping over the iterator in RPython code will not
produce a loop in the resulting flow graph but will unroll the loop instead.


``parsing``
===========

The `pypy/rlib/parsing/`_ module is a still in-development module to generate tokenizers and
parsers in RPython. It is still highly experimental and only really used by the
`Prolog interpreter`_ (although in slightly non-standard ways). The easiest way
to specify a tokenizer/grammar is to write it down using regular expressions and
simple EBNF format. 

The regular expressions are implemented using finite automatons. The parsing
engine uses `packrat parsing`_, which has O(n) parsing time but is more
powerful than LL(n) and LR(n) grammars.

.. _`packrat parsing`: http://pdos.csail.mit.edu/~baford/packrat/

Regular Expressions
-------------------

The regular expression syntax is mostly a subset of the syntax of the `re`_
module. By default, non-special characters match themselves. If you concatenate
regular expressions the result will match the concatenation of strings matched
by the single regular expressions.

``|``
    ``R|S`` matches any string that *either* matches R or matches S.

``*``
    ``R*`` matches 0 or more repetitions of R.

``+``
    ``R+`` matches 1 or more repetitions of R.

``?``
    ``R?`` matches 0 or 1 repetition of R.

``(...)``
    Parenthesis can be used to group regular expressions (note that in contrast
    to Python's re module you cannot later match the content of this group).

``{m}``
    ``R{m}`` matches exactly m repetitions of R.

``{m, n}``
    ``R{m, n}`` matches between m and n repetitions of R (including m and n).

``[]``
    Matches a set of characters. The characters to be matched can be listed
    sequentially. A range of characters can be specified using ``-``. For
    examples ``[ac-eg]`` matches the characters a, c, d, e and g.
    The whole set can be inverted by starting it with ``^``. So [^a] matches
    anything except a.

To parse a regular expression and to get a matcher for it, you can use the
function ``make_runner(s)`` in the ``pypy.rlib.parsing.regexparse`` module.  It
returns a object with a ``recognize(input)`` method that returns True or False
depending on whether ``input`` matches the string or not.

.. _`re`: http://docs.python.org/library/re.html

EBNF
----

To describe a tokenizer and a grammar the ``pypy.rlib.parsing.ebnfparse``
defines a syntax for doing that.

The syntax file contains a sequence or rules. Every rule either describes a
regular expression or a grammar rule.

Regular expressions rules have the form::

    NAME: "regex";

NAME is the name of the token that the regular expression
produces (it has to consist of upper-case letters), ``regex`` is a regular
expression with the syntax described above. One token name is special-cased: a
token called ``IGNORE`` will be filtered out of the token stream before being
passed on to the parser and can thus be used to match comments or
non-significant whitespace.

Grammar rules have the form::
    
    name: expansion_1 | expansion_2 | ... | expansion_n;

Where ``expansion_i`` is a sequence of nonterminal or token names::

    symbol_1 symbol_2 symbol_3 ... symbol_n

This means that the nonterminal symbol ``name`` (which has to consist of
lower-case letters) can be expanded into any of the expansions. The expansions
can consist of a sequence of token names, nonterminal names or literals, which
are strings in quotes that are matched literally.

An example to make this clearer::
    
    IGNORE: " ";
    DECIMAL: "0|[1-9][0-9]*";
    additive: multitive "+" additive |
              multitive;
    multitive: primary "*" multitive |
               primary;
    primary: "(" additive ")" | DECIMAL;

This grammar describes the syntax of arithmetic impressions involving addition
and multiplication. The tokenizer
produces a stream of either DECIMAL tokens or tokens that have matched one of
the literals "+", "*", "(" or ")". Any space will be ignored. The grammar
produces a syntax tree that follows the precedence of the operators. For example
the expression ``12 + 4 * 5`` is parsed into the following tree:

.. graphviz:: image/parsing_example1.dot

Parse Trees
-----------

The parsing process builds up a tree consisting of instances of ``Symbol`` and
``Nonterminal``, the former corresponding to tokens, the latter to nonterminal
symbols. Both classes live in the `pypy/rlib/parsing/tree.py`_ module. You can use
the ``view()`` method ``Nonterminal`` instances to get a pygame view of the
parse tree.

``Symbol`` instances have the following attributes: ``symbol``, which is the
name of the token and ``additional_info`` which is the matched source.

``Nonterminal`` instances have the following attributes: ``symbol`` is the name
of the nonterminal and ``children`` which is a list of the children attributes.


Visitors
++++++++

To write tree visitors for the parse trees that are RPython, there is a special
baseclass ``RPythonVisitor`` in `pypy/rlib/parsing/tree.py`_ to use. If your
class uses this, it will grow a ``dispatch(node)`` method, that calls an
appropriate ``visit_<symbol>`` method, depending on the ``node`` argument. Here
the <symbol> is replaced by the ``symbol`` attribute of the visited node.

For the visitor to be RPython, the return values of all the visit methods need
to be of the same type.


Tree Transformations
--------------------

As the tree of arithmetic example above shows, by default the parse tree
contains a lot of nodes that are not really conveying useful information.
To get rid of some of them, there is some support in the grammar format to
automatically create a visitor that transforms the tree to remove the additional
nodes. The simplest such transformation just removes nodes, but there are
more complex ones.

The syntax for these transformations is to enclose symbols in expansions of a
nonterminal by [...], <...> or >...<.

[symbol_1 symbol_2 ... symbol_n]
++++++++++++++++++++++++++++++++

This will produce a transformer that completely removes the enclosed symbols
from the tree.

Example::

    IGNORE: " ";
    n: "A" [","] n | "A";

Parsing the string "A, A, A" gives the tree:

.. graphviz:: image/parsing_example2.dot

After transformation the tree has the "," nodes removed:

.. graphviz:: image/parsing_example3.dot

<symbol>
++++++++

This will replace the parent with symbol. Every expansion can contain at most
one symbol that is enclosed by <...>, because the parent can only be replaced
once, obviously.

Example::

    IGNORE: " ";
    n: "a" "b" "c" m;
    m: "(" <n> ")" | "d";

Parsing the string "a b c (a b c d)" gives the tree:

.. graphviz:: image/parsing_example4.dot

After transformation the tree looks like this:

.. graphviz:: image/parsing_example5.dot


>nonterminal_1 nonterminal_2 ... nonterminal_n<
+++++++++++++++++++++++++++++++++++++++++++++++

This replaces the nodes nonterminal_1 to nonterminal_n by their children.

Example::

    IGNORE: " ";
    DECIMAL: "0|[1-9][0-9]*";
    list: DECIMAL >list< | DECIMAL;

Parsing the string "1 2" gives the tree:

.. graphviz:: image/parsing_example6.dot
    
after the transformation the tree looks like:

.. graphviz:: image/parsing_example7.dot

Note that the transformation works recursively. That means that the following
also works: if the string "1 2 3 4 5" is parsed the tree at first looks like
this:

.. graphviz:: image/parsing_example8.dot

But after transformation the whole thing collapses to one node with a lot of
children:

.. graphviz:: image/parsing_example9.dot


Extensions to the EBNF grammar format
-------------------------------------

There are some extensions to the EBNF grammar format that are really only
syntactic sugar but make writing grammars less tedious. These are:

``symbol?``:
    matches 0 or 1 repetitions of symbol

``symbol*``:
    matches 0 or more repetitions of symbol. After the tree transformation all
    these repetitions are children of the current symbol.

``symbol+``:
    matches 1 or more repetitions of symbol. After the tree transformation all
    these repetitions are children of the current symbol.

These are implemented by adding some more rules to the grammar in the correct
way. Examples: the grammar::

    s: a b? c;

is transformed to look like this::

    s: a >_maybe_symbol_0_< c | a c;
    _maybe_symbol_0_: b;

The grammar::

    s: a b* c;

is transformed to look like this::

    s: a >_star_symbol_0< c | a c;
    _star_symbol_0: b >_symbol_star_0< | b;

The grammar::

    s: a b+ c;

is transformed to look like this::

    s: a >_plus_symbol_0< c;
    _plus_symbol_0: b >_plus_symbol_0< | b;


Full Example
------------

A semi-complete parser for the `json format`_::

    STRING: "\\"[^\\\\"]*\\"";
    NUMBER: "\-?(0|[1-9][0-9]*)(\.[0-9]+)?([eE][\+\-]?[0-9]+)?";
    IGNORE: " |\n";
    value: <STRING> | <NUMBER> | <object> | <array> | <"null"> |
           <"true"> | <"false">;
    object: ["{"] (entry [","])* entry ["}"];
    array: ["["] (value [","])* value ["]"];
    entry: STRING [":"] value;


The resulting tree for parsing the string::

    {"a": "5", "b": [1, null, 3, true, {"f": "g", "h": 6}]}

looks like this:

.. graphviz:: image/parsing_example10.dot



.. _`Prolog interpreter`: https://bitbucket.org/cfbolz/pyrolog/
.. _`json format`: http://www.json.org

.. include:: _ref.rst
