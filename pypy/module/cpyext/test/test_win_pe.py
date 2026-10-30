import struct

from pypy.module.cpyext.win_pe import (
    pe_imports, cpython_only_reason, imports_of, _is_cpython_dll)

SECT_RVA = 0x1000
SECT_OFF = 0x400


def make_pe(dlls, magic=0x20b):
    """A minimal PE image whose import directory holds 'dlls', a list of
    (name, [symbol, ...])."""
    thunk_size = 8 if magic == 0x20b else 4
    pack_thunk = '<Q' if thunk_size == 8 else '<I'
    pieces = []
    cursor = [20 * (len(dlls) + 1)]      # after the import descriptors

    def place(data):
        off = cursor[0]
        pieces.append((off, data))
        cursor[0] += len(data) + len(data) % 2
        return SECT_RVA + off

    descs = ''
    for name, symbols in dlls:
        name_rva = place(name + '\x00')
        sym_rvas = [place(struct.pack('<H', 0) + sym + '\x00')
                    for sym in symbols]
        thunks = ''.join([struct.pack(pack_thunk, rva) for rva in sym_rvas])
        thunk_rva = place(thunks + '\x00' * thunk_size)
        descs += struct.pack('<IIIII', thunk_rva, 0, 0, name_rva, thunk_rva)
    descs += '\x00' * 20

    section = bytearray(cursor[0])
    section[0:len(descs)] = descs
    for off, data in pieces:
        section[off:off + len(data)] = data

    optional = bytearray(112 if magic == 0x20b else 96)
    optional[0:2] = struct.pack('<H', magic)
    directories = bytearray(16 * 8)
    directories[8:16] = struct.pack('<II', SECT_RVA, 20 * (len(dlls) + 1))
    coff = struct.pack('<HHIIIHH', 0x8664, 1, 0, 0, 0,
                       len(optional) + len(directories), 0x2022)
    sect_header = (('.rdata' + '\x00' * 2) +
                   struct.pack('<IIII', len(section), SECT_RVA,
                               len(section), SECT_OFF) +
                   struct.pack('<IIHHI', 0, 0, 0, 0, 0x40000040))
    assert len(sect_header) == 40

    head = ('MZ' + '\x00' * 0x3a + struct.pack('<I', 0x40) +
            'PE\x00\x00' + coff + str(optional) + str(directories) +
            sect_header)
    assert len(head) <= SECT_OFF
    return head + '\x00' * (SECT_OFF - len(head)) + str(section)


def test_parse_imports():
    data = make_pe([('python3.dll', ['PyList_New', 'PyExc_ValueError']),
                    ('KERNEL32.dll', ['Sleep'])])
    assert pe_imports(data) == [
        ('python3.dll', ['PyList_New', 'PyExc_ValueError']),
        ('KERNEL32.dll', ['Sleep'])]


def test_parse_imports_pe32():
    data = make_pe([('python3.dll', ['PyList_New'])], magic=0x10b)
    assert pe_imports(data) == [('python3.dll', ['PyList_New'])]


def test_not_a_pe_file():
    for data in ['', 'MZ', 'not a PE at all', 'MZ' + 'x' * 500,
                 make_pe([])[:0x30]]:
        assert pe_imports(data) == []
        assert cpython_only_reason(pe_imports(data)) is None


def test_abi3_extension_is_accepted():
    data = make_pe([('python3.dll', ['PyList_New', '_Py_IncRef',
                                     '_Py_DecRef']),
                    ('KERNEL32.dll', ['Sleep'])])
    assert cpython_only_reason(pe_imports(data)) is None


def test_full_api_extension_is_rejected():
    data = make_pe([('python312.dll', ['PyList_New'])])
    reason = cpython_only_reason(pe_imports(data))
    assert 'python312.dll' in reason
    assert 'full' in reason


def test_old_abi3_extension_is_rejected():
    # a cp37..cp311 abi3 wheel inlines the refcount and calls _Py_Dealloc
    data = make_pe([('python3.dll', ['PyList_New', '_Py_Dealloc'])])
    reason = cpython_only_reason(pe_imports(data))
    assert 'limited API' in reason
    assert '3.12' in reason


def test_is_cpython_dll():
    for name in ['python312.dll', 'python27.dll', 'python313t.dll',
                 'python3.12.dll', 'PYTHON312.DLL'.lower()]:
        assert _is_cpython_dll(name)
    for name in ['python3.dll', 'kernel32.dll', 'libpypy3.12-c.dll',
                 'python.dll', 'pythonxy.dll', 'mypython312.dll']:
        assert not _is_cpython_dll(name)


def test_imports_of_missing_file(tmpdir):
    assert imports_of(str(tmpdir.join('nope.pyd'))) == []
    pyd = tmpdir.join('mod.pyd')
    pyd.write(make_pe([('python312.dll', ['PyList_New'])]), mode='wb')
    assert cpython_only_reason(imports_of(str(pyd))) is not None
