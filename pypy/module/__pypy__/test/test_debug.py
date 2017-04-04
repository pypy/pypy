import py

from pypy.interpreter.gateway import interp2app
from rpython.rlib import debug


class AppTestDebug:
    spaceconfig = dict(usemodules=['__pypy__'])

    def setup_class(cls):
        if cls.runappdirect:
            py.test.skip("not meant to be run with -A")
        cls.w_check_log = cls.space.wrap(interp2app(cls.check_log))

    def setup_method(self, meth):
        debug._log = debug.DebugLog()

    def teardown_method(self, meth):
        debug._log = None

    @staticmethod
    def check_log(space, w_expected):
        assert list(debug._log) == space.unwrap(w_expected)

    def test_debug_print(self):
        from __pypy__ import debug_start, debug_stop, debug_print
        debug_start('my-category')
        debug_print('one')
        debug_print('two', 3, [])
        debug_stop('my-category')
        self.check_log([
                ('my-category', [
                        ('debug_print', 'one'),
                        ('debug_print', 'two 3 []'),
                        ])
                ])

    def test_debug_print_once(self):
        from __pypy__ import debug_print_once
        debug_print_once('foobar', 'hello world')
        self.check_log([
                ('foobar', [
                        ('debug_print', 'hello world'),
                        ])
                ])

    def test_debug_flush(self):
        from __pypy__ import debug_flush
        debug_flush()
        # assert did not crash
