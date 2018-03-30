from rpython.translator.goal import gcbench
from rpython.memory.test.test_transformed_gc import MyGcHooks, GC_HOOKS_STATS

# _____ Define and setup target ___

def entry_point(argv):
    GC_HOOKS_STATS.fix_annotation()
    ret = gcbench.entry_point(argv)
    minors = GC_HOOKS_STATS.minors
    steps = GC_HOOKS_STATS.steps
    collects = GC_HOOKS_STATS.collects
    print 'GC hooks statistics'
    print '    gc-minor:        ', minors
    print '    gc-collect-step: ', steps
    print '    gc-collect:      ', collects
    return ret

gchooks = MyGcHooks()

def target(*args):
    gcbench.ENABLE_THREADS = False    # not RPython
    return entry_point, None

