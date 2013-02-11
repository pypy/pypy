#   Copyright 2000-2004 Michael Hudson-Doyle <micahel@gmail.com>
#
#                        All Rights Reserved
#
#
# Permission to use, copy, modify, and distribute this software and
# its documentation for any purpose is hereby granted without fee,
# provided that the above copyright notice appear in all copies and
# that both that copyright notice and this permission notice appear in
# supporting documentation.
#
# THE AUTHOR MICHAEL HUDSON DISCLAIMS ALL WARRANTIES WITH REGARD TO
# THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
# AND FITNESS, IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL,
# INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER
# RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF
# CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN
# CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

from pyrepl.console import Event
from pyrepl.tests.infrastructure import ReaderTestCase, EA, run_testcase

class SimpleTestCase(ReaderTestCase):

    def test_basic(self):
        self.run_test([(('self-insert', 'a'), ['a']),
                       ( 'accept',            ['a'])])

    def test_repeat(self):
        self.run_test([(('digit-arg', '3'),   ['']),
                       (('self-insert', 'a'), ['aaa']),
                       ( 'accept',            ['aaa'])])

    def test_kill_line(self):
        self.run_test([(('self-insert', 'abc'), ['abc']),
                       ( 'left',                None),
                       ( 'kill-line',           ['ab']),
                       ( 'accept',              ['ab'])])

    def test_unix_line_discard(self):
        self.run_test([(('self-insert', 'abc'), ['abc']),
                       ( 'left',                None),
                       ( 'unix-word-rubout',    ['c']),
                       ( 'accept',              ['c'])])

    def test_kill_word(self):
        self.run_test([(('self-insert', 'ab cd'), ['ab cd']),
                       ( 'beginning-of-line',     ['ab cd']),
                       ( 'kill-word',             [' cd']),
                       ( 'accept',                [' cd'])])

    def test_backward_kill_word(self):
        self.run_test([(('self-insert', 'ab cd'), ['ab cd']),
                       ( 'backward-kill-word',    ['ab ']),
                       ( 'accept',                ['ab '])])

    def test_yank(self):
        self.run_test([(('self-insert', 'ab cd'), ['ab cd']),
                       ( 'backward-kill-word',    ['ab ']),
                       ( 'beginning-of-line',     ['ab ']),
                       ( 'yank',                  ['cdab ']),
                       ( 'accept',                ['cdab '])])
        
    def test_yank_pop(self):
        self.run_test([(('self-insert', 'ab cd'), ['ab cd']),
                       ( 'backward-kill-word',    ['ab ']),
                       ( 'left',                  ['ab ']),
                       ( 'backward-kill-word',    [' ']),
                       ( 'yank',                  ['ab ']),
                       ( 'yank-pop',              ['cd ']),
                       ( 'accept',                ['cd '])])

    def test_interrupt(self):
        try:
            self.run_test([( 'interrupt',  [''])])
        except KeyboardInterrupt:
            pass
        else:
            self.fail('KeyboardInterrupt got lost')

    # test_suspend -- hah

    def test_up(self):
        self.run_test([(('self-insert', 'ab\ncd'), ['ab', 'cd']),
                       ( 'up',                     ['ab', 'cd']),
                       (('self-insert', 'e'),      ['abe', 'cd']),
                       ( 'accept',                 ['abe', 'cd'])])

    def test_down(self):
        self.run_test([(('self-insert', 'ab\ncd'), ['ab', 'cd']),
                       ( 'up',                     ['ab', 'cd']),
                       (('self-insert', 'e'),      ['abe', 'cd']),
                       ( 'down',                   ['abe', 'cd']),
                       (('self-insert', 'f'),      ['abe', 'cdf']),
                       ( 'accept',                 ['abe', 'cdf'])])

    def test_left(self):
        self.run_test([(('self-insert', 'ab'), ['ab']),
                       ( 'left',               ['ab']),
                       (('self-insert', 'c'),  ['acb']),
                       ( 'accept',             ['acb'])])

    def test_right(self):
        self.run_test([(('self-insert', 'ab'), ['ab']),
                       ( 'left',               ['ab']),
                       (('self-insert', 'c'),  ['acb']),
                       ( 'right',              ['acb']),
                       (('self-insert', 'd'),  ['acbd']),
                       ( 'accept',             ['acbd'])])
        
def test():
    run_testcase(SimpleTestCase)

if __name__ == '__main__':
    test()
