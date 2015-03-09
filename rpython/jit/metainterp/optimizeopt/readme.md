PyPy optimzier module
===

After finding any trace in a user program, the generated interpreter records the instructions until it encounters a backwards jump. The allow operations found in a trace can be found in `rpython/metainterp/resoperation.py`. An example trace could look like this (syntax is the same as used in the test suit):

    [p0,i0]
    i1 = int_add(i0)
    i2 = int_le(i1, 100)
    guard_true(i2)
    jump(p0, i1)

The first operation is called a label, the last is the backwards jump. Before the jit backend transforms any trace into a machine code, it tries to transform the trace into an equivalent trace that executes faster. The method `optimize_trace` in `rpython/jit/metainterp/optimizeopt/__init__.py` is the main entry point.

Optimizations are applied in a sequence one after another and the base sequence is as follows:

    intbounds:rewrite:virtualize:string:earlyforce:pure:heap:unroll

Each of the colon separated name has a class attached that is later instantiated as a subclass of `Optimization`. The second class is the `Optimizer` that is derives from the `Optimization` class as well. Most of the optimizations only require a single forward pass. The trace is 'propagated' in to each optimization in the method `propagate_forward`. Instruction by instruction then flows from the first optimization to the last optimization. The method `emit_operation` is called for every operation that is passed to the next optimizer.

A frequently encountered pattern
---

One pattern that is often used in the optimizer is the binding of operation to a method. `make_dispatcher_method` associates methods with instructions.

    class OptX(Optimization):
        def prefix_JUMP(self, op):
            pass # emit, transform, ...

   dispatch_opt = make_dispatcher_method(OptX, 'prefix_', default=OptSimplify.emit_operation)
   OptX.propagate_forward = dispatch_opt
   

This ensures that whenever a jump operation is encountered it is routed to the method `prefix_JUMP`.

Rewrite
---

The second optimization is called 'rewrite' an is commonly also known as strength reduction. A simple example would be that an integer multiplied by 2 is equivalent to the bits shifted to the left once (e.g. x * 2 == x << 1). Not only strength reduction is done in this optimization but also boolean or arithmetic simplifications. Examples would be: x & 0 == 0, x - 0 == x, ... 

Whenever such an operation is encountered (e.g. x & 0), no operation is emitted. Instead the variable of x is made equal to 0 (= `make_equal_to(op.result, 0)`). The variables found in a trace are instances of Box classes that can be found in `rpython/jit/metainterp/history.py`. `OptValue` wraps those variables again and maps the boxes to the optimization values in the optimizer. When a value is made equal, the box in the opt. value. This renders a new value to any further access.

As a result the optimizer must provide the means to access the OptValue instances. Thus it must use methods such as `make_args_key` to retrive the OptValue instances.

OptPure
---

Is interwoven into the basic optimizer. It saves operations, results, arguments to be known to have pure semantics.

(What does pure really mean? as far as I can tell:) Pure is free of side effects and it is referentially transparent (the operation can be replaced with its value without changing the program semantics). The operations marked as ALWAYS_PURE in `resoperation.py` is a subset of the SIDEEFFECT free operations. Operations such as new, new array, getfield_(raw/gc) are marked of sideeffect free but not as pure.

This can be seen as memoization technique. Once an operation proved to be 'pure' it is saved and should not be recomputed later.

Unroll
---

A detailed description can be found the paper (see references below). This optimization does not fall into the traditional scheme of one forward pass only. In a nutshell it unrolls the trace _once_, connects the two traces (by inserting parameters into the jump and label of the peeled trace) and uses information to iron out allocations, propagate constants and do any other optimization currently present in the 'optimizeopt' module.

It is prepended all optimizations and thus extends the Optimizer class and unrolls the loop once before it proceeds.

Further references
---

* Loop-Aware Optimizations in PyPy’s Tracing JIT
  Link: http://www2.maths.lth.se/matematiklth/vision/publdb/reports/pdf/ardo-bolz-etal-dls-12.pdf

* Allocation Removal by Partial Evaluation in a Tracing JIT
  Link: - http://www.stups.uni-duesseldorf.de/mediawiki/images/b/b0/Pub-BoCuFiLePeRi2011.pdf
