"""Just enough PE parsing to tell an abi3 extension from a CPython-only one.

On Windows both are called <name>.pyd, so the file name says nothing: the
import table is the only marker.  An abi3 extension imports python3.dll,
which PyPy provides as a mapping dll of export forwarders; a full-API
CPython extension imports python3XY.dll, which a PyPy installation does not
have, and must be rejected before anything is mapped into the process.
"""
import os

from rpython.rlib.rstring import assert_str0

O_BINARY = getattr(os, 'O_BINARY', 0)

_ABI3_TOO_OLD = ('this C extension was built for the limited API of Python'
                 ' < 3.12 and inlines reference counting, which PyPy cannot'
                 ' support: only abi3 extensions built for Python 3.12 or'
                 ' newer (cp312-abi3 wheels) can be loaded')


def _u16(data, off):
    return ord(data[off]) | (ord(data[off + 1]) << 8)


def _u32(data, off):
    return (ord(data[off]) | (ord(data[off + 1]) << 8) |
            (ord(data[off + 2]) << 16) | (ord(data[off + 3]) << 24))


def _cstring(data, off):
    end = off
    while end < len(data) and data[end] != '\x00':
        end += 1
    return data[off:end]


def _rva_to_offset(sections, rva):
    for va, vsize, raw_off, raw_size in sections:
        size = vsize
        if raw_size > size:
            size = raw_size
        if va <= rva < va + size:
            delta = rva - va
            if delta < raw_size:
                return raw_off + delta
            return -1
    return -1


def pe_imports(data):
    """The import table of the PE image in 'data', as a list of
    (dll name, [symbol name, ...]).  Empty if 'data' is not a PE image or
    imports nothing; never raises."""
    result = []
    if len(data) < 0x40 or data[0] != 'M' or data[1] != 'Z':
        return result
    pe = _u32(data, 0x3c)
    if pe < 0 or pe + 24 > len(data) or data[pe:pe + 4] != 'PE\x00\x00':
        return result
    coff = pe + 4
    nsections = _u16(data, coff + 2)
    opt_size = _u16(data, coff + 16)
    opt = coff + 20
    if opt + 2 > len(data):
        return result
    magic = _u16(data, opt)
    if magic == 0x20b:          # PE32+
        dirs = opt + 112
        thunk_size = 8
    elif magic == 0x10b:        # PE32
        dirs = opt + 96
        thunk_size = 4
    else:
        return result
    if dirs + 16 > len(data):
        return result
    import_rva = _u32(data, dirs + 8)      # DataDirectory[1], the imports
    if import_rva == 0:
        return result

    sections = []
    sec = opt + opt_size
    for i in range(nsections):
        s = sec + i * 40
        if s + 40 > len(data):
            return result
        sections.append((_u32(data, s + 12), _u32(data, s + 8),
                         _u32(data, s + 20), _u32(data, s + 16)))

    desc = _rva_to_offset(sections, import_rva)
    if desc < 0:
        return result
    while desc + 20 <= len(data):
        orig_thunk = _u32(data, desc)
        name_rva = _u32(data, desc + 12)
        first_thunk = _u32(data, desc + 16)
        if name_rva == 0 and first_thunk == 0:
            break
        desc += 20
        name_off = _rva_to_offset(sections, name_rva)
        if name_off < 0:
            continue
        thunk_rva = orig_thunk
        if thunk_rva == 0:
            thunk_rva = first_thunk
        symbols = []
        off = _rva_to_offset(sections, thunk_rva)
        while off >= 0 and off + thunk_size <= len(data):
            low = _u32(data, off)
            if thunk_size == 8:
                high = _u32(data, off + 4)
            else:
                high = 0
            if low == 0 and high == 0:
                break
            off += thunk_size
            if thunk_size == 8:
                by_ordinal = (high & 0x80000000) != 0
            else:
                by_ordinal = (low & 0x80000000) != 0
            if by_ordinal:
                continue
            sym_off = _rva_to_offset(sections, low)
            if sym_off >= 0 and sym_off + 2 < len(data):
                symbols.append(_cstring(data, sym_off + 2))
        result.append((_cstring(data, name_off), symbols))
    return result


def _is_cpython_dll(lowered):
    """python312.dll, python27.dll, python313t.dll, ... but not python3.dll,
    which is the stable ABI one PyPy provides."""
    if not (lowered.startswith('python') and lowered.endswith('.dll')):
        return False
    end = len(lowered) - len('.dll')
    assert end >= 0
    middle = lowered[len('python'):end]
    if middle.endswith('t'):            # free-threaded build
        assert len(middle) >=1
        middle = middle[:-1]
    if len(middle) < 2:
        return False
    for c in middle:
        if not (48 <= ord(c) <= 57) and c != '.':    # not a digit or a dot
            return False
    return True


def cpython_only_reason(imports):
    """Why this extension cannot be loaded on PyPy, or None if it can."""
    for name, symbols in imports:
        lowered = name.lower()
        if lowered == 'python3.dll':
            for sym in symbols:
                if sym == '_Py_Dealloc':
                    return _ABI3_TOO_OLD
        elif _is_cpython_dll(lowered):
            return ('this C extension imports %s: it was built for the full'
                    ' C API of CPython, which PyPy cannot provide; only abi3'
                    ' extensions built for Python 3.12 or newer (cp312-abi3'
                    ' wheels) can be loaded' % (name,))
    return None


def imports_of(filename):
    """pe_imports() of a file, [] if it cannot be read."""
    try:
        fd = os.open(assert_str0(filename), os.O_RDONLY | O_BINARY, 0400)
        try:
            chunks = []
            while True:
                data = os.read(fd, 65536)
                if not data:
                    break
                chunks.append(data)
        finally:
            os.close(fd)
    except OSError:
        return []
    return pe_imports(''.join(chunks))
