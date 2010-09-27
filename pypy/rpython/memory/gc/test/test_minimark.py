from pypy.rpython.lltypesystem import llmemory
from pypy.rpython.memory.gc.minimark import MiniMarkGC
from pypy.rlib.rarithmetic import LONG_BIT

# Note that most tests are in test_direct.py.


def test_card_marking_words_for_length():
    gc = MiniMarkGC(None, card_page_indices=128)
    assert gc.card_page_shift == 7
    P = 128 * LONG_BIT
    assert gc.card_marking_words_for_length(1) == 1
    assert gc.card_marking_words_for_length(P) == 1
    assert gc.card_marking_words_for_length(P+1) == 2
    assert gc.card_marking_words_for_length(P+P) == 2
    assert gc.card_marking_words_for_length(P+P+1) == 3
    assert gc.card_marking_words_for_length(P+P+P+P+P+P+P+P) == 8
    assert gc.card_marking_words_for_length(P+P+P+P+P+P+P+P+1) == 9

def test_card_marking_bytes_for_length():
    gc = MiniMarkGC(None, card_page_indices=128)
    assert gc.card_page_shift == 7
    P = 128 * 8
    assert gc.card_marking_bytes_for_length(1) == 1
    assert gc.card_marking_bytes_for_length(P) == 1
    assert gc.card_marking_bytes_for_length(P+1) == 2
    assert gc.card_marking_bytes_for_length(P+P) == 2
    assert gc.card_marking_bytes_for_length(P+P+1) == 3
    assert gc.card_marking_bytes_for_length(P+P+P+P+P+P+P+P) == 8
    assert gc.card_marking_bytes_for_length(P+P+P+P+P+P+P+P+1) == 9
