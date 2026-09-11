import pytest

import os

lzma = pytest.importorskip('lzma')


def test_compressor():
    compressor = lzma.LZMACompressor(
        check=lzma.CHECK_CRC64,
        filters=[
            {"id": lzma.FILTER_X86},
            {"id": lzma.FILTER_LZMA2, "preset": lzma.PRESET_DEFAULT},
        ],
    )

    compressor.compress(b"hello world")


def _partially_fed_decompressor():
    blob = lzma.compress(bytes(range(256)) * 400)
    d = lzma.LZMADecompressor()
    for offset in range(0, 200, 7):
        d.decompress(blob[offset:offset + 7], max_length=1)
    return d


def test_decompressor_input_buffer_free_branch():
    from _lzma import ffi
    d = _partially_fed_decompressor()
    assert d._input_buffer != ffi.NULL
    d.lzs.avail_in = d._input_buffer_size + 1
    d.post_decompress_avail_data()
    assert d._input_buffer != ffi.NULL
    assert d._input_buffer_size == d.lzs.avail_in
    d.clear_input_buffer()
    assert d._input_buffer == ffi.NULL
    d.clear_input_buffer()


def test_decompressor_clear_input_buffer_threads():
    import threading
    from _lzma import ffi
    for _ in range(50):
        d = _partially_fed_decompressor()
        assert d._input_buffer != ffi.NULL
        threads = [threading.Thread(target=d.clear_input_buffer)
                   for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert d._input_buffer == ffi.NULL

