'''Toy Language'''

import py
import time
from rpython.rlib.jit import JitDriver, dont_look_inside, promote, set_param
from rpython.jit.backend.hlinfo import highleveljitinfo

driver = JitDriver(greens=['values', 'do_promote', 'vals'], reds='auto')


def run(n, values, do_promote):
    vals = [i for i in range(values)]
    c = n
    result = 0
    while c > 0:
        driver.jit_merge_point(values=values, do_promote=do_promote, vals=vals)

        val = vals[c % values]
        if do_promote:
            # produce a chain of guard_values:
            val = promote(val)

        # 'val' may be promoted.
        # do something "expensive" with 'val'
        result += (val + val * val - val * val / (val + 1) + val * val * val /
                   (val + 1) - val * val * val * val / (val + 1) +
                   val * val * val * val * val / (val + 1) -
                   val * val * val / (val + 1) * val * val / (val + 1) +
                   val * val * val * val / (val + 1) * val * val / (val + 1))

        c -= 1
    return result


def entry_point(args):
    """Main entry point of the stand-alone executable:
    """
    # store args[0] in a place where the JIT log can find it (used by
    # viewcode.py to know the executable whose symbols it should display)
    highleveljitinfo.sys_executable = args[0]
    if len(args) < 5:
        print "Arguments expected: N num_values guard_chain_cutoff do_promote"
        return 2

    n = int(args[1])
    values = int(args[2])
    cutoff = int(args[3])
    do_promote = bool(int(args[4]))

    set_param(driver, 'guard_value_limit', cutoff)

    # compile EVERYTHING:
    set_param(driver, 'threshold', 1)
    set_param(driver, 'trace_eagerness', 1)

    print "Warmup..."
    # there are two guards to warm up: one in the unrolled loop-preamble, one
    # in the loop itself. Hence, we create 2 chains of 'values' guards. To be
    # safe, warm up multiple times 'values'.
    t = time.time()
    run(values * 100, values, do_promote)
    print "Warmup done. Time: %s s" % (time.time() - t)

    print "Run!"
    t = time.time()
    run(n, values, do_promote)
    print "Run done. Time: %s s" % (time.time() - t)

    return 0


def target(driver, args):
    return entry_point, None
