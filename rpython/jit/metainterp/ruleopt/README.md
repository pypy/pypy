# JIT Integer Optimization Peephole Rule DSL

This directory contains the implementation of the DSL for integer rewrites in
optimizeopt. It uses pattern matching to specify how integer operation can be
rewritten. The rules are then compiled to RPython code that executes the
transformations in optimizeopt. The rewrite rules are automatically proven
correct with Z3 as part of the build process.

## Simple transformation rules

The rules specify how integer operation can be transformed into cheaper other
integer operations. A rule always consists of a name, a pattern, and a target. Here's a simple rule:

```
add_zero: int_add(x, 0)
    => x
```

The name of the rule is `add_zero`. It matches operations in the trace of the
form `int_add(x, 0)`, where `x` will match anything and `0` will match only the
constant zero. After the `=>` arrow is the target of the rewrite, i.e. what the
operation is rewritten to, in this case `x`.

The rule language knowns which of the operations are commutative, so `add_zero`
will also optimize `int_add(0, x)` to `x`.

Variables in the pattern can repeat:

```
sub_x_x: int_sub(x, x)
    => 0
```

This rule matches against `int_sub` operations where the two arguments are the
same (either the same box, or the same constant).

Here's a rule with a more complicated pattern:

```
sub_add: int_sub(int_add(x, y), y)
    => x
```

This pattern matches `int_sub` operations, where the first argument was
produced by an `int_add` operation. In addition, one of the arguments of the
addition has to be the same as the second argument of the subtraction.

It is also possible to have a pattern where some arguments needs to be a
constant, without specifying which constant. Those patterns look like this:

```
sub_add_consts: int_sub(int_add(x, C1), C2) # incomplete
    => int_sub(x, C)
```

Variables in the pattern that start with a `C` match against constants only.
However, in current form the rule is incomplete, because `C` is not defined in
the target operation. We will see how to compute it in the next section.

## Computing constants and other intermediate results

Sometimes it is necessary to compute intermediate results that are used in the
target operation. To do that, there can extra assignments between the rule head
and the rule target.

```
sub_add_consts: int_sub(int_add(x, C1), C2) # incomplete
    C = C1 + C1
    => int_sub(x, C)
```

The right hand side of such an assignment is a subset of Python syntax,
supporting arithmetic using `+`, `-`, `*`, and certain helper functions.
However, the syntax allows you to be explicit about unsignedness for some
operations. E.g. `>>u` exists for unsigned right shifts (and I plan to add
`>u`, `>=u`, `<u`, `<=u` exist for comparisons).

## Checks

Some rewrites are only true under certain conditions. For example, `int_eq(x,
1)` can be rewritten to `x`, if `x` is know to store a boolean value. This can
be expressed with *checks*:

```
eq_one: int_eq(x, 1)
    check x.is_bool()
    => x
```

A check is followed by a boolean expression. The variables from the pattern can
be used as `IntBound` instances in checks (and also in assignments) to find out
what the abstract interpretation knows about the value of a trace variable.

Here's another example:

```
mul_lshift: int_mul(x, int_lshift(1, y))
    check y.known_ge_const(0) and y.known_le_const(LONG_BIT)
    => int_lshift(x, y)
```

It expresses that `x * (1 << y)` can be rewritten to `x << y` but checks that
`y` is known to be between `0` and `LONG_BIT`.

Checks and assignments can be repeated and combined with each other:

```
mul_pow2_const: int_mul(x, C)
    check C > 0 and C & (C - 1) == 0
    shift = highest_bit(C)
    => int_lshift(x, shift)
```

In addition to calling methods on `IntBound` instances, it's also possible to
access their attributes, like in this rule:

```
and_x_c_in_range: int_and(x, C)
    check x.lower >= 0 and x.upper <= C & ~(C + 1)
    => x
```

## Proofs

It is very easy to write a peephole rule that is not correct in all corner
cases. Therefore all the rules are proven correct with Z3 before compiled into
actual JIT code. When the proof fails, a (hopefully minimal) counterexample is
printed. The counterexample consists of values for all the inputs that fulfil
the checks, values for the intermediate expressions, and then two *different*
values for the source and the target operations.

E.g. if we try to add the incorrect rule:

```
mul_is_add: int_mul(a, b)
    => int_add(a, b)
```

We get the following counterexample as output:

```
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
```

If we add conditions, they are taken into account:

```
mul_is_add: int_mul(a, b)
    check a.known_gt_const(1) and b.known_gt_const(2)
    => int_add(a, b)
```

This leads to the following counterexample:

```
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
```

Some `IntBound` methods cannot be used in Z3 proofs because they have too
complex control flow. If that is the case, they can have Z3-equivalent
formulations defined, in the `test_z3intbound.Z3IntBound` class.

If that is too hard as well, it's possible to skip the proof of individual
rules by adding `SORRY_Z3` to its body:

```
eq_different_knownbits: int_eq(x, y)
    SORRY_Z3
    check x.known_ne(y)
    => 0
```

