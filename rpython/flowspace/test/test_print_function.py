"""We test the print function logic in flowspace/specialcase.py"""
import os

import pytest

from rpython.flowspace.specialcase import (
    stdoutbuffer,
    rpython_print_end,
    rpython_print_item,
    rpython_print_newline,
)


class TestPrintFunctionLogic(object):

    def _write_spy(self, monkeypatch):
        spied = []
        monkeypatch.setattr(stdoutbuffer, "linebuf", [])
        monkeypatch.setattr(os, "write", lambda *args: spied.append(args))
        return spied

    def test_rpython_print_end(self, monkeypatch):
        spied = self._write_spy(monkeypatch)

        rpython_print_item("spam")
        rpython_print_item("eggs\n")
        rpython_print_item("spam")
        rpython_print_end("@")

        assert stdoutbuffer.linebuf == list("spam eggs\n spam@")
        assert len(spied) == 0  # writes are buffered

    def test_rpython_print_newline(self, monkeypatch):
        spied = self._write_spy(monkeypatch)

        # empty print() call
        rpython_print_newline()
        assert len(spied) == 1
        assert spied[-1] == (1, "\n")
        assert stdoutbuffer.linebuf == []

        # print call with a few items in it
        rpython_print_item("spam")
        rpython_print_item("eggs\n")
        rpython_print_item("spam")
        rpython_print_newline()

        assert len(spied) == 2
        assert spied[-1] == (1, "spam eggs\n spam\n")
        assert stdoutbuffer.linebuf == []

    @pytest.mark.parametrize(
        ("first", "end", "second", "expected"),
        (
            (("one", "two"), "", ("three", "four"), "one twothree four"),
            (("one", "two"), " ", ("three", "four"), "one two three four"),
            (("one", "two"), "", (), "one two"),
            (("one", "two"), " ", (), "one two "),
            ((), "", ("three", "four"), "three four"),
            ((), " ", ("three", "four"), " three four"),
        ),
    )
    def test_rpython_print_newline_end_mixed(self, monkeypatch, first, end, second, expected):
        spied = self._write_spy(monkeypatch)

        # Tests the equivalent of
        # print(*first, end=end)
        # print(*second)

        for item in first:
            rpython_print_item(item)
        rpython_print_end(end)
        for item in second:
            rpython_print_item(item)
        rpython_print_newline()
        assert len(spied) == 1
        expected = expected + "\n"
        assert spied[-1] == (1, expected)

    def test_rpython_print_newline_end_complex(self, monkeypatch):
        spied = self._write_spy(monkeypatch)

        rpython_print_item("one")
        rpython_print_item("two")
        rpython_print_end(" point\nfive")
        rpython_print_item("three")
        rpython_print_item("four")
        rpython_print_newline()

        assert len(spied) == 2
        assert spied[0] == (1, "one two point\n")
        assert spied[1] == (1, "fivethree four\n")
