===========================================
JIT Integer Optimization Peephole Rule DSL
===========================================

For integer peephole optimizations in the JIT we use a domain specific language
based on pattern matching that specifies how (sequences of) integer operations
should be simplified. It is implemented in the directory
``jit/metainterp/optimizeopt``. This directory contains the implementation of
the DSL for integer rewrites in optimizeopt. The rules are then compiled to
RPython code that executes the transformations in optimizeopt. The rewrite
rules are automatically proven correct with Z3 as part of the build process.
This page is an introduction to how that DSL works and how to use it.

Simple transformation rules
============================

The rules in the DSL specify how integer operation can be transformed into
cheaper other integer operations. A rule always consists of a name, a pattern,
and a target. Here's a simple rule::

    add_zero: int_add(x, 0)
        => x

The name of the rule is ``add_zero``. It matches operations in the trace of the
form ``int_add(x, 0)``, where ``x`` will match anything and ``0`` will match only the
constant zero. After the ``=>`` arrow is the target of the rewrite, i.e. what the
operation is rewritten to, in this case ``x``.

The rule language knowns which of the operations are commutative, so ``add_zero``
will also optimize ``int_add(0, x)`` to ``x``.

Variables in the pattern can repeat::

    sub_x_x: int_sub(x, x)
        => 0

This rule matches against ``int_sub`` operations where the two arguments are the
same (either the same box, or the same constant).

Here's a rule with a more complicated pattern::

    sub_add: int_sub(int_add(x, y), y)
        => x

This pattern matches ``int_sub`` operations, where the first argument was
produced by an ``int_add`` operation. In addition, one of the arguments of the
addition has to be the same as the second argument of the subtraction.

The constants ``MININT``, ``MAXINT`` and ``LONG_BIT`` (which is either 32 or 64) can
be used in rules, they behave like writing numbers but allow
bit-width-independent formulations::

    is_true_and_minint: int_is_true(int_and(x, MININT))
        => int_lt(x, 0)

It is also possible to have a pattern where some arguments needs to be a
constant, without specifying which constant. Those patterns look like this::

    sub_add_consts: int_sub(int_add(x, C1), C2) # incomplete
        # more goes here
        => int_sub(x, C)

Variables in the pattern that start with a ``C`` match against constants only.
However, in this current form the rule is incomplete, because ``C`` is not
defined in the target operation. We will see how to compute it in the next
section.

Computing constants and other intermediate results
===================================================

Sometimes it is necessary to compute intermediate results that are used in the
target operation. To do that, there can extra assignments between the rule head
and the rule target.::

    sub_add_consts: int_sub(int_add(x, C1), C2) # incomplete
        C = C1 + C1
        => int_sub(x, C)

The right hand side of such an assignment is a subset of Python syntax,
supporting arithmetic using ``+``, ``-``, ``*``, and certain helper functions.
However, the syntax allows you to be explicit about unsignedness for some
operations. E.g. ``>>u`` exists for unsigned right shifts (and I plan to add
`>u``, ``>=u``, ``<u``, ``<=u`` for comparisons).

Checks
===================================================

Some rewrites are only true under certain conditions. For example,
``int_eq(x, 1)`` can be rewritten to ``x``, if ``x`` is know to store a boolean value. This can
be expressed with *checks*::

    eq_one: int_eq(x, 1)
        check x.is_bool()
        => x

A check is followed by a boolean expression. The variables from the pattern can
be used as ``IntBound`` instances in checks (and also in assignments) to find out
what the abstract interpretation knows about the value of a trace variable.

Here's another example::

    mul_lshift: int_mul(x, int_lshift(1, y))
        check y.known_ge_const(0) and y.known_le_const(LONG_BIT)
        => int_lshift(x, y)

It expresses that ``x * (1 << y)`` can be rewritten to ``x << y`` but checks that
``y`` is known to be between ``0`` and ``LONG_BIT``.

Checks and assignments can be repeated and combined with each other::

    mul_pow2_const: int_mul(x, C)
        check C > 0 and C & (C - 1) == 0
        shift = highest_bit(C)
        => int_lshift(x, shift)

In addition to calling methods on ``IntBound`` instances, it's also possible to
access their attributes, like in this rule::

    and_x_c_in_range: int_and(x, C)
        check x.lower >= 0 and x.upper <= C & ~(C + 1)
        => x



Rule Ordering and Liveness
===================================================

The generated optimizer code will give preference to applying rules that
produce a constant or a variable as a rewrite result. Only if none of those
match do rules that produce new result operations get applied. For example, the
rules ``sub_x_x`` and ``sub_add`` are tried before trying ``sub_add_consts``,
because the former two rules optimize to a constant and a variable
respectively, while the latter produces a new operation as the result.

The rule ``sub_add_consts`` has a possible problem, which is that if the
intermediate result of the ``int_add`` operation in the rule head is used by
some other operations, then the ``sub_add_consts`` rule does not actually
reduce the number of operations (and might actually make things slightly worse
due to increased register pressure). However, currently it would be extremely
hard to take that kind of information into account in the optimization pass of
the JIT, so we optimistically apply the rules anyway.

Checking rule coverage
===================================================

Every rewrite rule should have at least one unit test where it triggers. To
ensure this, the tests in file ``test_optimizeintbound.py`` have an assert at the
end of a test run, that every rule fired at least once (this check can
somethings trigger as a false positive, for example when running individual
tests with ``-k``).

Printing rule statistics
===================================================

The JIT can print statistics about which rule fired how often in the
``jit-intbounds-stats`` :doc:`logging <../logging>` category. For example, to
print it to stdout at the end of program execution, run PyPy like this::

    PYPYLOG=jit-intbounds-stats:- pypy ...

The output of that will look something like this::

    int_add
        add_reassoc_consts 2514
        add_zero 107008
    int_sub
        sub_zero 31519
        sub_from_zero 523
        sub_x_x 3153
        sub_add_consts 159
        sub_add 55
        sub_sub_x_c_c 1752
        sub_sub_c_x_c 0
        sub_xor_x_y_y 0
        sub_or_x_y_y 0
    int_mul
        mul_zero 0
        mul_one 110
        mul_minus_one 0
        mul_pow2_const 1456
        mul_lshift 0
    ...

Proofs
===================================================

It is very easy to write a peephole rule that is not correct in all corner
cases. Therefore all the rules are proven correct with Z3 before compiled into
actual JIT code, by default. When the proof fails, a (hopefully minimal)
counterexample is printed. The counterexample consists of values for all the
inputs that fulfil the checks, values for the intermediate expressions, and
then two *different* values for the source and the target operations.

E.g. if we try to add the incorrect rule::

    mul_is_add: int_mul(a, b)
        => int_add(a, b)

We get the following counterexample as output::

    Could not prove correctness of rule 'mul_is_add'
    in line 1
    counterexample given by Z3:
    counterexample values:
    a: 0
    b: 1
    operation int_mul(a, b) with Z3 formula a*b
    has counterexample result vale: 0
    BUT
    target expression: int_add(a, b) with Z3 formula a + b
    has counterexample value: 1

If we add conditions, they are taken into account::

    mul_is_add: int_mul(a, b)
        check a.known_gt_const(1) and b.known_gt_const(2)
        => int_add(a, b)

This leads to the following counterexample::

    Could not prove correctness of rule 'mul_is_add'
    in line 46
    counterexample given by Z3:
    counterexample values:
    a: 2
    b: 3
    operation int_mul(a, b) with Z3 formula a*b
    has counterexample result vale: 6
    BUT
    target expression: int_add(a, b) with Z3 formula a + b
    has counterexample value: 5

Some ``IntBound`` methods cannot be used in Z3 proofs because they have `too
complex control flow`__ If that is the case, they can have Z3-equivalent
formulations defined, in the ``test_z3intbound.Z3IntBound`` class (in every
case this is done, it's a potential proof hole if the Z3 friendly reformulation
and the real implementation differ from each other, therefore extra care is
required to make very sure they are equivalent).

.. __: https://pypy.org/posts/2024/08/toy-knownbits.html#cases-where-this-style-of-z3-proof-doesnt-work).

If that is too hard as well, it's possible to skip the proof of individual
rules by adding ``SORRY_Z3`` to its body (but we should try not to do that too
often)::

    eq_different_knownbits: int_eq(x, y)
        SORRY_Z3
        check x.known_ne(y)
        => 0

Checking for satisfiability
===================================================

In addition to checking whether the rule yields a correct optimization, we also
check whether the rule can ever apply. This ensures that there are *some*
runtime values that would fulfil all the checks in a rule. Here's an example of
a rule violating this::

    never_applies: int_is_true(x)
        check x.known_lt_const(0) and x.known_gt_const(0) # impossible condition, always False
        => x

Right now the error messages are not completely easy to understand, I hope to
improve this later::

    Rule 'never_applies' cannot ever apply
    in line 1
    Z3 did not manage to find values for variables x such that the following condition becomes True:
    And(x <= x_upper,
        x_lower <= x,
        If(x_upper < 0, x_lower > 0, x_upper < 0))

Adding new rules
===================================================

To add new rules (ideally motivated by `observed problems in real traces`__),
the following steps should be performed:

.. __: https://pypy.org/posts/2024/07/mining-jit-traces-missing-optimizations-z3.html

- Add a failing test to ``test_optimizeintbound.py``.
- Add the rule to ``real.rules``.
- Regenerate the Python code by running ``pypy ruleopt/generate.py`` (you need
  the ``z3-solver`` and ``rply`` packages installed for that).
- Check that ``test_optimizeintbound.py`` passes, then run the other
  ``optimizeopt/`` tests (in particular ``optimizeopt/test/test_z3checktests.py``
  checks that the operations and expected outputs `are sensible`__).

.. __: https://pypy.org/posts/2022/12/jit-bug-finding-smt-fuzzing.html


DSL Implementation Notes
================================

The implementation of the DSL is done in a relatively ad-hoc manner. It is
parsed using `rply`__, there's a small type checker that tries to find common
problems in how the rules are written. Z3 is used via the Python API. The
pattern matching RPython code is generated using an approach inspired by Luc
Maranget's paper `Compiling Pattern Matching to Good Decision Trees`__, see
`this blog post`__ for an approachable introduction.

.. __: https://rply.readthedocs.io/
.. __: http://moscova.inria.fr/~maranget/papers/ml05e-maranget.pdf
.. __: https://compiler.club/compiling-pattern-matching/




