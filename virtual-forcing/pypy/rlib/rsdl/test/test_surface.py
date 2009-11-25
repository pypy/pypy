import py, sys
from pypy.rlib.rsdl import RSDL, RSDL_helper
from pypy.rlib.rarithmetic import r_uint
from pypy.rpython.lltypesystem import lltype, rffi

class TestSurface:

    def setup_method(self, meth):
        self.dst_surf = RSDL.CreateRGBSurface(0, 300, 300, 32,
                                        r_uint(0x000000FF),
                                        r_uint(0x0000FF00),
                                        r_uint(0x00FF0000),
                                        r_uint(0x00000000))
        self.src_surf = RSDL.CreateRGBSurface(0, 50, 50, 32,
                                        r_uint(0x000000FF),
                                        r_uint(0x0000FF00),
                                        r_uint(0x00FF0000),
                                        r_uint(0x00000000))
        fmt = self.src_surf.c_format
        self.black = RSDL.MapRGB(fmt, 0, 0, 0)
        self.red = RSDL.MapRGB(fmt, 255, 0, 0)
        self.blue = RSDL.MapRGB(fmt, 0, 0, 255)
        RSDL.FillRect(self.src_surf, lltype.nullptr(RSDL.Rect), self.red)

    def test_simple(self):
        pass   # only checks that creating the surfaces works

    def test_set_alpha(self):
        # prepare
        assert RSDL.SetAlpha(self.src_surf, RSDL.SRCALPHA, 128) == 0

        # draw
        RSDL_helper.blit_complete_surface(
            self.src_surf,
            self.dst_surf,
            10, 10)
        RSDL_helper.blit_complete_surface(
            self.src_surf,
            self.dst_surf,
            20, 20)

        # check
        for position, color in (
                (( 0, 0), (  0,0,0)), # no rect
                ((10,10), (127,0,0)), # one rect
                ((20,20), (191,0,0))  # two overlapping rects
            ):
            fetched_color = RSDL_helper.get_pixel(self.dst_surf, position[0], position[1])
            assert RSDL_helper.get_rgb(fetched_color, self.dst_surf.c_format) == color 

    def test_set_color_key(self):
        # prepare
        fillrect = RSDL_helper.mallocrect(10, 10, 30, 30)
        RSDL.FillRect(self.src_surf, fillrect, self.blue)
        lltype.free(fillrect, flavor='raw')
        assert RSDL.SetColorKey(self.src_surf, RSDL.SRCCOLORKEY, self.blue) == 0

        # draw
        RSDL_helper.blit_complete_surface(self.src_surf, self.dst_surf, 0, 0)

        # check
        for position, color in (
                (( 0, 0), self.red),
                ((10,10), self.black),
                ((20,20), self.black),
                ((40,40), self.red)
            ):
            fetched_color = RSDL_helper.get_pixel(self.dst_surf, position[0], position[1])
            assert fetched_color == color

    def teardown_method(self, meth):
        RSDL.FreeSurface(self.src_surf)
        RSDL.FreeSurface(self.dst_surf)
        RSDL.Quit()

