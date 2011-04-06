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

# this test case should contain as-verbatim-as-possible versions of
# (applicable) feature requests

class WishesTestCase(ReaderTestCase):

    def test_quoted_insert_repeat(self):
        self.run_test([(('digit-arg', '3'),      ['']),
                       ( 'quoted-insert',        ['']),
                       (('self-insert', '\033'), ['^[^[^[']),
                       ( 'accept',               None)])

def test():
    run_testcase(WishesTestCase)

if __name__ == '__main__':
    test()
