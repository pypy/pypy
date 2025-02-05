import pytest
import gc
import weakref

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

def test_gc_stats_sum_is_correct():
    def extract_mb(line):
        if '(' in line:
            line = line[:line.index('(')].strip()
        assert line.endswith("MB")
        return float(line[:-2].rsplit(' ', 1)[-1])

    l1 = [str(i) for i in range(100000)]
    l2 = [str(i) for i in range(100000)]
    l1[:] = []
    gc.collect()
    for with_memory_pressure in [0, 1]:
        stats = str(gc.get_stats(with_memory_pressure))
        first_half, second_half = stats.split("Total memory allocated")
        for half in first_half, second_half:
            lines = half.splitlines()
            total = extract_mb(lines[1])
            summed = extract_mb(lines[2]) + extract_mb(lines[3]) + extract_mb(lines[4])
            assert 0.9 < summed / total < 1.1

def test_args_passed_are_eligible_for_gc():
    class A:
        pass

    def other(a):
        # delete the only remaining ref to a and replace with a weakref
        a = weakref.ref(a)

        for _ in range(5):
            gc.collect()

        assert a() is None


    # move our reference to the instance of A into other
    other(A())
    # also works with kwargs (which uses a different code path)
    other(a=A())

if __name__ == "__main__":
    sys.exit(main())
