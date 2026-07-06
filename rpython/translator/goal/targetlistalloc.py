"""
Benchmark target for list allocation cost, driven by argv[1]:

  0  (default) -- [None] * size   GcPtr list; zero_gc_pointers_inside pre-clears
  1            -- [0]   * size   Signed list; no pre-clearing; GCC vectorizes loop
  2            -- [obj] * size   GcPtr list filled with a live object; write
                                  barriers in _ll_alloc_and_set_nojit loop block GCC
                                  auto-vectorization, adding per-element overhead
  3            -- loop setitem    lst[i] = obj in a while-loop on an existing list;
                                  demonstrates the path where write barriers ARE
                                  needed (list may be old; optimization must not
                                  remove barriers from this path)

Translate with:
  pypy2.7 rpython/bin/rpython -O2 --gc=incminimark rpython/translator/goal/targetlistalloc.py

Measure with callgrind:
  valgrind --tool=callgrind --callgrind-out-file=cg.out ./targetlistalloc-c <mode>
  callgrind_annotate cg.out | grep -A5 "alloc_and\|arrayclear\|memset\|writebarrier"
"""
import os

SIZES = [100, 1000, 10000]
REPEAT = 500


class PtrHolder(object):
    pass

class IntHolder(object):
    pass


_ptr_holder = PtrHolder()
_ptr_holder.lst = [_ptr_holder]  # seed: items typed as Ptr(PtrHolder), not Void
_ptr_holder.obj = _ptr_holder    # live object for mode 2/3

_int_holder = IntHolder()
_int_holder.lst = [0]            # seed: items typed as Signed


def bench_none(repeat):
    i = 0
    while i < repeat:
        j = 0
        while j < len(SIZES):
            size = SIZES[j]
            a = [None] * size
            _ptr_holder.lst = a
            j += 1
        i += 1
    return len(_ptr_holder.lst)


def bench_zero(repeat):
    i = 0
    while i < repeat:
        j = 0
        while j < len(SIZES):
            size = SIZES[j]
            a = [0] * size
            _int_holder.lst = a
            j += 1
        i += 1
    return len(_int_holder.lst)


def bench_obj(repeat):
    # [obj] * size: _ll_alloc_and_set_nojit loops with ll_setitem_fast.
    # The fresh list is always young so write barriers never fire, but the
    # tid-flag check per element blocks GCC auto-vectorization.
    obj = _ptr_holder.obj
    i = 0
    while i < repeat:
        j = 0
        while j < len(SIZES):
            size = SIZES[j]
            a = [obj] * size
            _ptr_holder.lst = a
            j += 1
        i += 1
    return len(_ptr_holder.lst)


def bench_setitem(repeat):
    # loop setitem on an existing list: lst[i] = obj goes through ll_setitem_fast
    # on a list that may be in the old generation -- write barriers are required
    # for correctness and must remain even after any _ll_alloc_and_set_nojit opt.
    obj = _ptr_holder.obj
    size = SIZES[2]
    a = [obj] * size
    _ptr_holder.lst = a          # keep alive across GC cycles
    i = 0
    while i < repeat:
        k = 0
        while k < size:
            _ptr_holder.lst[k] = obj
            k += 1
        i += 1
    return len(_ptr_holder.lst)


def entry_point(argv):
    mode = 0
    if len(argv) > 1:
        s = argv[1]
        if s == '1':
            mode = 1
        elif s == '2':
            mode = 2
        elif s == '3':
            mode = 3
    if mode == 1:
        result = bench_zero(REPEAT)
    elif mode == 2:
        result = bench_obj(REPEAT)
    elif mode == 3:
        result = bench_setitem(REPEAT)
    else:
        result = bench_none(REPEAT)
    os.write(1, str(result) + "\n")
    return 0


def target(*args):
    return entry_point, None
