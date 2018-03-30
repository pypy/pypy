from pypy.module.gc.hook import gchooks
from pypy.interpreter.baseobjspace import ObjSpace
from pypy.interpreter.gateway import interp2app, unwrap_spec

class AppTestGcHooks(object):

    def setup_class(cls):
        space = cls.space

        @unwrap_spec(ObjSpace, int, int)
        def fire_gc_minor(space, total_memory_used, pinned_objects):
            gchooks.fire_gc_minor(total_memory_used, pinned_objects)
        cls.w_fire_gc_minor = space.wrap(interp2app(fire_gc_minor))

    def test_on_gc_minor(self):
        import gc
        lst = []
        def on_gc_minor(total_memory_used, pinned_objects):
            lst.append((total_memory_used, pinned_objects))
        gc.set_hooks(on_gc_minor=on_gc_minor)
        self.fire_gc_minor(10, 20)
        self.fire_gc_minor(30, 40)
        assert lst == [
            (10, 20),
            (30, 40),
            ]
