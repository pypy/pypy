import pytest
import audioop


@pytest.mark.parametrize('call', [
    lambda d: audioop.tostereo(d, 2, 1, 1),
    lambda d: audioop.add(d, d, 2),
    lambda d: audioop.ratecv(d, 2, 1, 8000, 8000, None),
    lambda d: audioop.lin2adpcm(d, 2, None),
    lambda d: audioop.adpcm2lin(d, 2, None),
])
def test_bytearray_resize_after_call(call):
    # issue 5589: the ffi.from_buffer() export must be released when the
    # call returns, otherwise resizing the bytearray raises BufferError
    data = bytearray(b'\x01\x02\x03\x04\x05\x06\x07\x08')
    call(data)
    del data[4:]
    assert data == b'\x01\x02\x03\x04'
