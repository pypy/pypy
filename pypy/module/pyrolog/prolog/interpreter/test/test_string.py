#coding=utf-8

import py
from prolog.interpreter.test.tool import assert_true, assert_false

def test_strings():
    assert_true('X = "abc", X = [97, 98, 99].')
    assert_true('X = "", X = [].')
    assert_true('X = [97], X = "a".')
    assert_true('X = [97], X = Y, Y = "a".')
    assert_false('X = "a", X = \'a\'.')
    assert_true('X = "²³¼½¬", X = [178, 179, 188, 189, 172].')
    assert_true('X = [], X = "".')
