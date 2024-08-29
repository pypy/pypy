import gc

def test_memory_doesnt_jump_during_sweeping():
    memory = []
    def on_gc_collect_step(stats):
        memory.append((stats.GC_STATES[stats.oldstate], gc.get_stats()._s.total_arena_memory))

    gc.hooks.on_gc_collect_step = on_gc_collect_step

    l1 = [str(i) for i in range(100000)]
    l2 = [str(i) for i in range(100000)]
    l1[:] = []
    memory[:] = []
    for i in range(100):
        gc.collect_step()
    minimum = min(x[1] for x in memory)
    maximum = max(x[1] for x in memory)
    assert minimum != 0
    assert minimum >= maximum // 2

    gc.hooks.on_gc_collect_step = lambda stats: None
