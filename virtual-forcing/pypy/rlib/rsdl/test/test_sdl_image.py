import py, os
import autopath
from pypy.rlib.rsdl import RSDL, RIMG, RSDL_helper
from pypy.rpython.lltypesystem import lltype, rffi


def test_load_image():
    for filename in ["demo.jpg", "demo.png"]:
        image = RIMG.Load(os.path.join(autopath.this_dir, filename))
        assert image
        assert rffi.getintfield(image, 'c_w') == 17
        assert rffi.getintfield(image, 'c_h') == 23
        RSDL.FreeSurface(image)

def test_image_pixels():
    for filename in ["demo.jpg", "demo.png"]:
        image = RIMG.Load(os.path.join(autopath.this_dir, filename))
        assert image
        assert rffi.getintfield(image.c_format, 'c_BytesPerPixel') in (3, 4)
        RSDL.LockSurface(image)
        result = {}
        try:
            rgb = lltype.malloc(rffi.CArray(RSDL.Uint8), 3, flavor='raw')
            try:
                for y in range(23):
                    for x in range(y % 13, 17, 13):
                        color = RSDL_helper.get_pixel(image, x, y)
                        RSDL.GetRGB(color,
                                    image.c_format,
                                    rffi.ptradd(rgb, 0),
                                    rffi.ptradd(rgb, 1),
                                    rffi.ptradd(rgb, 2))
                        r = rffi.cast(lltype.Signed, rgb[0])
                        g = rffi.cast(lltype.Signed, rgb[1])
                        b = rffi.cast(lltype.Signed, rgb[2])
                        result[x, y] = r, g, b
            finally:
                lltype.free(rgb, flavor='raw')
        finally:
            RSDL.UnlockSurface(image)
        RSDL.FreeSurface(image)
        for x, y in result:
            f = (x*17 + y*23) / float(17*17+23*23)
            expected_r = int(255.0 * (1.0-f))
            expected_g = 0
            expected_b = int(255.0 * f)
            r, g, b = result[x, y]
            assert abs(r-expected_r) < 10
            assert abs(g-expected_g) < 10
            assert abs(b-expected_b) < 10
