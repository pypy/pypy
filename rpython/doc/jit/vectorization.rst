
Vectorization
=============

TBA

Features
--------

Currently the following operations can be vectorized if the trace contains parallel operations:

* float32/float64: add, substract, multiply, divide, negate, absolute
* int8/int16/int32/int64 arithmetic: add, substract, multiply, negate, absolute
* int8/int16/int32/int64 logical: and, or, xor

Reduction is implemented:

* sum

Planned reductions:

* all, any, prod, min, max

To find parallel instructions the tracer must provide enough information about
memory load/store operations. They must be adjacent in memory. The requirement for
that is that they use the same index variable and offset can be expressed as a
a linear or affine combination.

Unrolled guards are strengthend on a arithmetical level (See GuardStrengthenOpt).
The resulting vector trace will only have one guard that checks the index.

Calculations on the index variable that are redundant (because of the merged
load/store instructions) are not removed. The backend removes these instructions
while assembling the trace.


Future Work and Limitations
---------------------------

* The only SIMD instruction architecture currently supported is SSE4.1
* Packed mul for int8,int64 (see PMUL_)
* Loop that convert types from int(8|16|32|64) to int(8|16) are not supported in
  the current SSE4.1 assembler implementation.
  The opcode needed spans over multiple instructions. In terms of performance
  there might only be little to non advantage to use SIMD instructions for this
  conversions.

.. _PMUL: http://stackoverflow.com/questions/8866973/can-long-integer-routines-benefit-from-sse/8867025#8867025
