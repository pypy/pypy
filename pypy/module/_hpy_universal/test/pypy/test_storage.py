from pypy.module._hpy_universal.interp_type import storage_alloc, storage_get_raw_data

def test_storage():
    storage = storage_alloc(size=3)
    assert len(storage.data) == 3
    assert list(storage.data) == ['\00', '\00', '\00']
    storage.data[0] = 'A'
    storage.data[1] = 'B'
    storage.data[2] = 'C'
    raw_data = storage_get_raw_data(storage)
    assert raw_data[0] == 'A'
    assert raw_data[1] == 'B'
    assert raw_data[2] == 'C'
