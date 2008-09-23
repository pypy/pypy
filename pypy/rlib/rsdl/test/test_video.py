
import py, sys
from pypy.rlib.rsdl import RSDL, RSDL_helper
from pypy.rlib.rarithmetic import r_uint
from pypy.rpython.lltypesystem import lltype, rffi
from pypy import conftest

#
#  This test file is skipped unless run with "py.test --view".
#  If it is run as "py.test --view -s", then it interactively asks
#  for confirmation that the window looks as expected.
#


class TestVideo:

    def setup_method(self, meth):
        if not conftest.option.view:
            py.test.skip("'--view' not specified, "
                         "skipping tests that open a window")
        assert RSDL.Init(RSDL.INIT_VIDEO) >= 0
        self.screen = RSDL.SetVideoMode(640, 480, 32, 0)
        assert self.screen
        self.is_interactive = sys.stdout.isatty()

    def check(self, msg):
        if self.is_interactive:
            print
            answer = raw_input('Interactive test: %s - ok? [Y] ' % msg)
            if answer and not answer.upper().startswith('Y'):
                py.test.fail(msg)
        else:
            print msg

    def test_simple(self):
        pass   # only checks that opening and closing the window works

    def test_fillrect_full(self):
        fmt = self.screen.c_format
        for colorname, r, g, b in [('dark red', 128, 0, 0),
                                   ('yellow', 255, 255, 0),
                                   ('blue', 0, 0, 255)]:
            color = RSDL.MapRGB(fmt, r, g, b)
            RSDL.FillRect(self.screen, lltype.nullptr(RSDL.Rect), color)
            RSDL.Flip(self.screen)
            self.check("Screen filled with %s" % colorname)

    def test_caption(self):
        RSDL.WM_SetCaption("Hello World!", "Hello World!")
        self.check('The window caption is "Hello World!"')

    def test_keypresses(self):
        if not self.is_interactive:
            py.test.skip("interactive test only")
        RSDL.EnableUNICODE(1)
        print
        print "Keys pressed in the Pygame window should be printed below."
        print "    Use Escape to quit."
        event = lltype.malloc(RSDL.Event, flavor='raw')
        try:
            while True:
                    ok = RSDL.WaitEvent(event)
                    assert rffi.cast(lltype.Signed, ok) == 1
                    c_type = rffi.getintfield(event, 'c_type')
                    if c_type == RSDL.KEYDOWN:
                        p = rffi.cast(RSDL.KeyboardEventPtr, event)
                        if rffi.getintfield(p.c_keysym, 'c_sym') == RSDL.K_ESCAPE:
                            print 'Escape key'
                            break
                        char = rffi.getintfield(p.c_keysym, 'c_unicode')
                        if char != 0:
                            print 'Key:', unichr(char).encode('utf-8')
                        else:
                            print 'Some special key'
                    else:
                        print '(event of type %d)' % c_type
        finally:
            lltype.free(event, flavor='raw')

    def test_poll(self):
        if not self.is_interactive:
            py.test.skip("interactive test only")
        import time, sys
        RSDL.EnableUNICODE(1)
        print
        print "Keys pressed in the Pygame window give a dot."
        print "    Wait 3 seconds to quit."
        timeout = time.time() + 3
        event = lltype.malloc(RSDL.Event, flavor='raw')
        try:
            while True:
                # busy polling
                ok = RSDL.PollEvent(event)
                ok = rffi.cast(lltype.Signed, ok)
                assert ok >= 0
                if ok > 0:
                    c_type = rffi.getintfield(event, 'c_type')
                    if c_type == RSDL.KEYDOWN:
                        sys.stderr.write('.')
                        p = rffi.cast(RSDL.KeyboardEventPtr, event)
                        if rffi.getintfield(p.c_keysym, 'c_sym') == RSDL.K_ESCAPE:
                            print 'Escape key'
                            break
                        timeout = time.time() + 3
                else:
                    if time.time() > timeout:
                        break
                time.sleep(0.05)
        finally:
            lltype.free(event, flavor='raw')

    def test_mousemove(self):
        if not self.is_interactive:
            py.test.skip("interactive test only")
        print
        print "Move the Mouse up and down:"
        print "    Use Escape to quit."
        event = lltype.malloc(RSDL.Event, flavor="raw")
        directions = [False]*4
        try:
            while True:
                ok = RSDL.WaitEvent(event)
                assert rffi.cast(lltype.Signed, ok) == 1
                c_type = rffi.getintfield(event, "c_type")
                if c_type == RSDL.MOUSEMOTION:
                    m = rffi.cast(RSDL.MouseMotionEventPtr, event)
                    assert rffi.getintfield(m, "c_x") >= 0
                    assert rffi.getintfield(m, "c_y") >= 0
                    print rffi.getintfield(m, "c_xrel")
                    directions[0] |= rffi.getintfield(m, "c_xrel")>0
                    directions[1] |= rffi.getintfield(m, "c_xrel")<0
                    directions[2] |= rffi.getintfield(m, "c_yrel")>0
                    directions[3] |= rffi.getintfield(m, "c_yrel")<0
                    if False not in directions:
                        break
                elif c_type == RSDL.KEYUP:
                    p = rffi.cast(RSDL.KeyboardEventPtr, event)
                    if rffi.getintfield(p.c_keysym, 'c_sym') == RSDL.K_ESCAPE:
                        print "    test manually aborted"
                        py.test.fail(" mousemovement test aborted")
                        break  
        finally:
            lltype.free(event, flavor='raw')
                

    def test_mousebutton_wheel(self):
        if not self.is_interactive:
            py.test.skip("interactive test only")
        print
        print "Press the given MouseButtons:"
        print "        Use Escape to pass tests."
        
        event_tests = [("left button",   RSDL.BUTTON_LEFT),
                       ("middle button", RSDL.BUTTON_MIDDLE),
                       ("right button",  RSDL.BUTTON_RIGHT),
                       ("scroll up",     RSDL.BUTTON_WHEELUP),
                       ("scroll down",   RSDL.BUTTON_WHEELDOWN)]
        test_success = []
        event = lltype.malloc(RSDL.Event, flavor='raw')
        try:
            for button_test in event_tests:
                print "    press %s:" % button_test[0]
                while True:
                    ok = RSDL.WaitEvent(event)
                    assert rffi.cast(lltype.Signed, ok) == 1
                    c_type = rffi.getintfield(event, 'c_type')
                    if c_type == RSDL.MOUSEBUTTONDOWN:
                        pass
                    elif c_type == RSDL.MOUSEBUTTONUP:
                        b = rffi.cast(RSDL.MouseButtonEventPtr, event)
                        if rffi.getintfield(b, 'c_button') == button_test[1]:
                            test_success.append(True)
                            break
                    elif c_type == RSDL.KEYUP:
                        p = rffi.cast(RSDL.KeyboardEventPtr, event)
                        if rffi.getintfield(p.c_keysym, 'c_sym') == RSDL.K_ESCAPE:
                            test_success.append(False) 
                            print "        manually aborted"
                            break
                        #break
            if False in test_success:
                py.test.fail("")
        finally:
            lltype.free(event, flavor='raw')
            
            
    def test_show_hide_cursor(self):
        RSDL.ShowCursor(RSDL.DISABLE)
        self.check("Is the cursor hidden? ")
        RSDL.ShowCursor(RSDL.ENABLE)
        self.check("Is the cursor shown? ")
        
    def test_bit_pattern(self):
        HEIGHT = WIDTH = 10
        fmt = self.screen.c_format
        white = RSDL.MapRGB(fmt, 255, 255, 255)
        black = RSDL.MapRGB(fmt, 0, 0, 0)
        RSDL.LockSurface(self.screen)
        for i in xrange(WIDTH):
            for j in xrange(HEIGHT):
                k = j*WIDTH + i
                if k % 2:
                    c = white
                else:
                    c = black
                RSDL_helper.set_pixel(self.screen, i, j, c)
        RSDL.UnlockSurface(self.screen)
        RSDL.Flip(self.screen)
        self.check("Upper left corner 10x10 field with vertical black/white stripes")

    def test_blit_rect(self):
        surface = RSDL.CreateRGBSurface(0, 150, 50, 32,
                                        r_uint(0x000000FF),
                                        r_uint(0x0000FF00),
                                        r_uint(0x00FF0000),
                                        r_uint(0xFF000000))
        fmt = surface.c_format
        color = RSDL.MapRGB(fmt, 255, 0, 0)
        RSDL.FillRect(surface, lltype.nullptr(RSDL.Rect), color)
        
        paintrect = RSDL_helper.mallocrect(75, 0, 150, 50)
        dstrect = lltype.malloc(RSDL.Rect, flavor='raw')
        try:
            color = RSDL.MapRGB(fmt, 255, 128, 0)
            RSDL.FillRect(surface, paintrect, color)

            rffi.setintfield(dstrect, 'c_x',  10)
            rffi.setintfield(dstrect, 'c_y',  10)
            rffi.setintfield(dstrect, 'c_w', 150)
            rffi.setintfield(dstrect, 'c_h',  50)
            RSDL.BlitSurface(surface, lltype.nullptr(RSDL.Rect), self.screen, dstrect)
            RSDL.Flip(self.screen)
        finally:
            lltype.free(dstrect, flavor='raw')
            lltype.free(paintrect, flavor='raw')
        RSDL.FreeSurface(surface)
        self.check("Half Red/Orange rectangle(150px * 50px) at the top left, 10 pixels from the border")

    def teardown_method(self, meth):
        RSDL.Quit()

