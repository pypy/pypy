import py

from pypy.translator.js.test.runtest import compile_function 

import sys

def test_merge_if_blocks_simple():
    def merge_if_blocks_simple(i):
        if i == 5:
            return 1005
        else:
            return 2222
    simple = compile_function(merge_if_blocks_simple, [int])
    for i in range(-20,20):
        assert simple(i) == merge_if_blocks_simple(i)

def test_merge_if_blocks_basic():
    py.test.skip("merge_if_block failing because link exit values are not used")
    def merge_if_blocks_basic(i):
        if i == 5:
            return 1005
        elif i == 8:
            return 1008
        return 2222
    basic  = compile_function(merge_if_blocks_basic , [int], view=True)
    for i in range(-20,20):
        assert basic(i) == merge_if_blocks_basic(i)

def test_merge_if_blocks_chr():
    py.test.skip("merge_if_block failing because link exit values are not used")
    def merge_if_blocks_chr(i):
        c = chr(i)
        if c == '\x05':
            return 1005
        elif c == '!':
            return 1008
        return 2222
    basic  = compile_function(merge_if_blocks_chr , [int])
    for i in range(0, 50):
        assert basic(i) == merge_if_blocks_chr(i)

def test_merge_if_blocks_uni():
    py.test.skip("merge_if_block failing because link exit values are not used")
    def merge_if_blocks_uni(i):
        c = unichr(i)
        if c == u'\x05':
            return 1005
        elif c == u'!':
            return 1008
        return 2222
    basic  = compile_function(merge_if_blocks_uni , [int])
    for i in range(0, 50):
        assert basic(i) == merge_if_blocks_uni(i)


def test_merge_if_blocks_many():
    py.test.skip("merge_if_block failing because link exit values are not used")
    def merge_if_blocks_many(i):
        if i == 0:
            return 1000 
        elif i == 1:
            return 1001
        elif i == 2:
            return 1002
        elif i == 3:
            return 1003
        elif i == 4:
            return 1004
        elif i == 5:
            return 1005
        elif i == 6:
            return 1006
        elif i == 7:
            return 1007
        elif i == 8:
            return 1008
        elif i == 9:
            return 1009
        else:
            return 2222
    many   = compile_function(merge_if_blocks_many  , [int])
    for i in range(-20,20):
        assert many(i)   == merge_if_blocks_many(i)
