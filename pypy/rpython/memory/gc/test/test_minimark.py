from pypy.rpython.lltypesystem import llmemory
from pypy.rpython.memory.gc.minimark import MiniMarkGC
from pypy.rlib.rarithmetic import LONG_BIT

# Note that most tests are in test_direct.py.


def test_stringbuilder_default_initsize_is_small():
    # Check that pypy.rlib.rstring.INIT_SIZE is short enough to let
    # the allocated object be considered as a "small" object.
    # Otherwise it would not be allocated in the nursery at all,
    # which is kind of bad (and also prevents shrink_array() from
    # being useful).
    from pypy.rlib.rstring import INIT_SIZE
    from pypy.rpython.lltypesystem.rstr import STR, UNICODE
    #
    size_gc_header = llmemory.raw_malloc_usage(
        llmemory.sizeof(llmemory.Address))
    #
    size1 = llmemory.raw_malloc_usage(llmemory.sizeof(STR, INIT_SIZE))
    size1 = size_gc_header + size1
    assert size1 <= MiniMarkGC.TRANSLATION_PARAMS["small_request_threshold"]
    #
    size2 = llmemory.raw_malloc_usage(llmemory.sizeof(UNICODE, INIT_SIZE))
    size2 = size_gc_header + size2
    assert size2 <= MiniMarkGC.TRANSLATION_PARAMS["small_request_threshold"]

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
