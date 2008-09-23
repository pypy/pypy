import py, sys
from pypy import conftest

from pypy.lang.gameboy import constants

# check if the lib-sdl import fails here
try:
    from pypy.lang.gameboy.gameboy_implementation import *
except ImportError:
    py.test.skip("lib sdl is not installed")

#
#  This test file is skipped unless run with "py.test --view".
#  If it is run as "py.test --view -s", then it interactively asks
#  for confirmation that the window looks as expected.
#

if sys.platform == 'darwin':
    from AppKit import NSApplication
    NSApplication.sharedApplication()


class TestGameBoyImplementation(object):

    def setup_method(self, meth):
        if not conftest.option.view:
            py.test.skip("'--view' not specified, "
                         "skipping tests that open a window")
        self.gameboy = GameBoyImplementation()
        self.is_interactive = sys.stdout.isatty()

    def check(self, msg):
        if self.is_interactive:
            print
            answer = raw_input('Interactive test: %s - ok? [Y] ' % msg)
            if answer and not answer.upper().startswith('Y'):
                py.test.fail(msg)
        else:
            print msg

    def test_buttons(self):
        for i in [("A",      constants.BUTTON_A),
                  ("B",      constants.BUTTON_B),
                  ("START",  constants.BUTTON_START),
                  ("SELECT", constants.BUTTON_SELECT),
                  ("A and B",      constants.BUTTON_A | constants.BUTTON_B),]:
            print "press ", i[0]
            isRunning = True
            while isRunning:
                while self.gameboy.poll_event():
                    if self.gameboy.check_for_escape():
                        isRunning = False
                        break 
                    self.gameboy.joypad_driver.update(self.gameboy.event)
                    if self.gameboy.joypad_driver.get_button_code() == i[1]:
                        isRunning = False
                        
    def test_directions(self):
        for i in [("up",    constants.BUTTON_UP),
                  ("left",  constants.BUTTON_LEFT),
                  ("down",  constants.BUTTON_DOWN),
                  ("right", constants.BUTTON_RIGHT),
                  ("down + right",  constants.BUTTON_DOWN | constants.BUTTON_RIGHT)]:
            print "press ", i[0]
            isRunning = True
            while isRunning:
                while self.gameboy.poll_event():
                    if self.gameboy.check_for_escape():
                        isRunning = False
                        break 
                    self.gameboy.joypad_driver.update(self.gameboy.event)
                    if self.gameboy.joypad_driver.get_direction_code() == i[1]:
                        isRunning = False
        

   

    def teardown_method(self, meth):
        RSDL.Quit()

