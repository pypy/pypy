from rpython.rlib.rarithmetic import r_uint
from pypy.module.gc.hook import LowLevelGcHooks
from pypy.interpreter.baseobjspace import ObjSpace
from pypy.interpreter.gateway import interp2app, unwrap_spec

class AppTestGcHooks(object):

    def setup_class(cls):
        space = cls.space
        gchooks = space.fromcache(LowLevelGcHooks)

        @unwrap_spec(ObjSpace, r_uint, int)
        def fire_gc_minor(space, total_memory_used, pinned_objects):
            gchooks.fire_gc_minor(total_memory_used, pinned_objects)

        @unwrap_spec(ObjSpace, int, int)
        def fire_gc_collect_step(space, oldstate, newstate):
            gchooks.fire_gc_collect_step(oldstate, newstate)

        @unwrap_spec(ObjSpace, int, int, int, r_uint, r_uint, r_uint)
        def fire_gc_collect(space, a, b, c, d, e, f):
            gchooks.fire_gc_collect(a, b, c, d, e, f)

        @unwrap_spec(ObjSpace)
        def fire_many(space):
            gchooks.fire_gc_minor(0, 0)
            gchooks.fire_gc_collect_step(0, 0)
            gchooks.fire_gc_collect(1, 2, 3, 4, 5, 6)

        cls.w_fire_gc_minor = space.wrap(interp2app(fire_gc_minor))
        cls.w_fire_gc_collect_step = space.wrap(interp2app(fire_gc_collect_step))
        cls.w_fire_gc_collect = space.wrap(interp2app(fire_gc_collect))
        cls.w_fire_many = space.wrap(interp2app(fire_many))

    def test_on_gc_minor(self):
        import gc
        lst = []
        def on_gc_minor(stats):
            lst.append((stats.total_memory_used, stats.pinned_objects))
        gc.set_hooks(on_gc_minor=on_gc_minor)
        self.fire_gc_minor(10, 20)
        self.fire_gc_minor(30, 40)
        assert lst == [
            (10, 20),
            (30, 40),
            ]
        #
        gc.set_hooks(on_gc_minor=None)
        self.fire_gc_minor(50, 60)  # won't fire because the hooks is disabled
        assert lst == [
            (10, 20),
            (30, 40),
            ]

    def test_on_gc_collect_step(self):
        import gc
        lst = []
        def on_gc_collect_step(stats):
            lst.append((stats.oldstate, stats.newstate))
        gc.set_hooks(on_gc_collect_step=on_gc_collect_step)
        self.fire_gc_collect_step(10, 20)
        self.fire_gc_collect_step(30, 40)
        assert lst == [
            (10, 20),
            (30, 40),
            ]
        #
        gc.set_hooks(on_gc_collect_step=None)
        self.fire_gc_collect_step(50, 60)  # won't fire
        assert lst == [
            (10, 20),
            (30, 40),
            ]

    def test_on_gc_collect(self):
        import gc
        lst = []
        def on_gc_collect(stats):
            lst.append((stats.count,
                        stats.arenas_count_before,
                        stats.arenas_count_after,
                        stats.arenas_bytes,
                        stats.rawmalloc_bytes_before,
                        stats.rawmalloc_bytes_after))
        gc.set_hooks(on_gc_collect=on_gc_collect)
        self.fire_gc_collect(1, 2, 3, 4, 5, 6)
        self.fire_gc_collect(7, 8, 9, 10, 11, 12)
        assert lst == [
            (1, 2, 3, 4, 5, 6),
            (7, 8, 9, 10, 11, 12),
            ]
        #
        gc.set_hooks(on_gc_collect=None)
        self.fire_gc_collect(42, 42, 42, 42, 42, 42)  # won't fire
        assert lst == [
            (1, 2, 3, 4, 5, 6),
            (7, 8, 9, 10, 11, 12),
            ]

    def test_consts(self):
        import gc
        S = gc.GcCollectStepStats
        assert S.STATE_SCANNING == 0
        assert S.STATE_MARKING == 1
        assert S.STATE_SWEEPING == 2
        assert S.STATE_FINALIZING == 3
        assert S.GC_STATES == ('SCANNING', 'MARKING', 'SWEEPING', 'FINALIZING')

    def test_clear_queue(self):
        import gc
        lst = []
        def on_gc_minor(stats):        lst.append('minor')
        def on_gc_collect_step(stats): lst.append('step')
        def on_gc_collect(stats):      lst.append('collect')
        gc.set_hooks(on_gc_minor=on_gc_minor,
                     on_gc_collect_step=on_gc_collect_step,
                     on_gc_collect=on_gc_collect)
        #
        self.fire_many()
        assert lst == ['minor', 'step', 'collect']
        lst[:] = []
        self.fire_gc_minor(0, 0)
        assert lst == ['minor']
