from pypy.objspace.std.setobject import W_SetObject
from pypy.objspace.std.setobject import IntegerSetStrategy, ObjectSetStrategy, EmptySetStrategy

class TestW_SetStrategies:

    def wrapped(self, l):
        return [self.space.wrap(x) for x in l]

    def test_from_list(self):
        s = W_SetObject(self.space, self.wrapped([1,2,3,4,5]))
        assert s.strategy is self.space.fromcache(IntegerSetStrategy)

        s = W_SetObject(self.space, self.wrapped([1,"two",3,"four",5]))
        assert s.strategy is self.space.fromcache(ObjectSetStrategy)

        s = W_SetObject(self.space)
        assert s.strategy is self.space.fromcache(EmptySetStrategy)

        s = W_SetObject(self.space, self.wrapped([]))
        assert s.strategy is self.space.fromcache(EmptySetStrategy)

    def test_switch_to_object(self):
        s = W_SetObject(self.space, self.wrapped([1,2,3,4,5]))
        s.add(self.space.wrap("six"))
        assert s.strategy is self.space.fromcache(ObjectSetStrategy)

        s1 = W_SetObject(self.space, self.wrapped([1,2,3,4,5]))
        s2 = W_SetObject(self.space, self.wrapped(["six", "seven"]))
        s1.update(s2)
        assert s1.strategy is self.space.fromcache(ObjectSetStrategy)

    def test_symmetric_difference(self):
        s1 = W_SetObject(self.space, self.wrapped([1,2,3,4,5]))
        s2 = W_SetObject(self.space, self.wrapped(["six", "seven"]))
        s1.symmetric_difference_update(s2)
        assert s1.strategy is self.space.fromcache(ObjectSetStrategy)

    def test_intersection(self):
        s1 = W_SetObject(self.space, self.wrapped([1,2,3,4,5]))
        s2 = W_SetObject(self.space, self.wrapped([4,5, "six", "seven"]))
        s3 = s1.intersect(s2)
        assert s3.strategy is self.space.fromcache(IntegerSetStrategy)

    def test_clear(self):
        s1 = W_SetObject(self.space, self.wrapped([1,2,3,4,5]))
        s1.clear()
        assert s1.strategy is self.space.fromcache(EmptySetStrategy)

    def test_remove(self):
        from pypy.objspace.std.setobject import set_remove__Set_ANY
        s1 = W_SetObject(self.space, self.wrapped([1]))
        set_remove__Set_ANY(self.space, s1, self.space.wrap(1))
        assert s1.strategy is self.space.fromcache(EmptySetStrategy)

