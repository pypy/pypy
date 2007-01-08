from pypy.jit.timeshifter.test.test_portal import PortalTest, P_NOVIRTUAL
from pypy.rpython.lltypesystem import lltype

import py

class TestVirtualizable(PortalTest):

    def test_simple_explicit(self):
        XY = lltype.GcForwardReference()
        GETTER = lltype.Ptr(lltype.FuncType([lltype.Ptr(XY)], lltype.Signed))
        SETTER = lltype.Ptr(lltype.FuncType([lltype.Ptr(XY), lltype.Signed],
                                            lltype.Void))
        XY_ACCESS = lltype.Struct('xy',
                                  ('get_x', GETTER),
                                  ('set_x', SETTER),
                                  ('get_y', GETTER),
                                  ('set_y', SETTER),
                                  hints = {'immutable': True},
                                  )
        
        XY.become(lltype.GcStruct('xy',
                                  ('access', lltype.Ptr(XY_ACCESS)),
                                  ('x', lltype.Signed),
                                  ('y', lltype.Signed),
                                  hints = {'virtualizable': True}
                      ))
        
        def f(xy):
            xy_access = xy.access
            if xy_access:
                x = xy_access.get_x(xy)
            else:
                x = xy.x
            xy_access = xy.access
            if xy_access:
                y = xy_access.get_y(xy)
            else:
                y = xy.y
            return x+y

        def main(x, y):
            xy = lltype.malloc(XY)
            xy.access = lltype.nullptr(XY_ACCESS)
            xy.x = x
            xy.y = y
            return f(xy)

        res = self.timeshift_from_portal(main, f, [20, 22], policy=P_NOVIRTUAL)
        assert res == 42
        self.check_insns(getfield=0) # maybe?
