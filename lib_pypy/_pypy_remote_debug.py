"""
EXPERIMENTAL and subject to change

Support for injecting Python code into another PyPy process. Can be used for
remote debugging, dumping the heap, interrupting a crashing process, etc.

Usage:

    pypy -m _pypy_remote_debug <pid> <scriptfile>
"""
from __future__ import print_function
import os
import sys
import time

# __________________________________________________________
# Linux support only for now
#
# in case we want to add windows support we could look at pymem: https://pypi.org/project/Pymem/
# for Mac https://developer.apple.com/documentation/kernel/1402070-mach_vm_write

# __________________________________________________________
# first, some elf support
#
# Note that this implementation is inspired by the ELF object file reader
# here:
#
#  http://www.tinyos.net/tinyos-1.x/tools/src/mspgcc-pybsl/elf.py
#
# which includes this copyright:
#
#  (C) 2003 cliechti@gmx.net
#  Python license
#
# Author : Christopher Batten
# Date   : May 20, 2014
#
# BSD License
#
# adapted for pydrofoil and later PyPy by cfbolz

import struct

class ElfBase(object):
    def _unpack(self, data, is_64bit):
        from struct import unpack
        self.is_64bit = is_64bit
        if self.is_64bit:
            format = self.FORMAT64
        else:
            format = self.FORMAT
        return unpack(format, data)

    @classmethod
    def from_file(cls, file_obj, is_64bit, offset=0):
        file_obj.seek(offset)
        ehdr_data = file_obj.read(cls.NBYTES64 if is_64bit else cls.NBYTES)
        return cls(ehdr_data, is_64bit=is_64bit)


class ElfHeader(ElfBase):
    FORMAT64 = "<16sHHIQQQIHHHHHH"
    FORMAT =   "<16sHHIIIIIHHHHHH"
    NBYTES = struct.calcsize(FORMAT)
    NBYTES64 = struct.calcsize(FORMAT64)

    def __init__(self, data, is_64bit=False):
        self.ident, self.type, self.machine, self.version, self.entry, self.phoff, self.shoff, self.flags, self.ehsize, self.phentsize, self.phnum, self.shentsize, self.shnum, self.shstrndx = self._unpack(data, is_64bit)


class ElfProgramHeader(ElfBase):
    FORMAT = "<IIIIIIII"
    FORMAT64 = "<IIQQQQQQ"
    NBYTES = struct.calcsize(FORMAT)
    NBYTES64 = struct.calcsize(FORMAT64)

    PT_LOAD = 1 # loadable segment

    def __init__(self, data, is_64bit=False):
        self.type, self.flags, self.offset, self.vaddr, self.paddr, self.filesz, self.memsz, self.align = self._unpack(data, is_64bit)


class ElfSectionHeader(ElfBase):
    FORMAT = "<IIIIIIIIII"
    FORMAT64 = "<IIQQQQIIQQ"
    NBYTES = struct.calcsize(FORMAT)
    NBYTES64 = struct.calcsize(FORMAT64)

    TYPE_SYMTAB = 2
    TYPE_STRTAB = 3

    name_as_bytes = None
    section_data = None

    def __init__(self, data, is_64bit=False):
        self.name, self.type, self.flags, self.addr, self.offset, self.size, self.link, self.info, self.addralign, self.entsize = self._unpack(data, is_64bit)



class ElfSymTabEntry(ElfBase):
    FORMAT = "<IIIBBH"
    FORMAT64 = "<IBBHQQ"
    NBYTES = struct.calcsize(FORMAT)
    NBYTES64 = struct.calcsize(FORMAT64)

    name_as_bytes = None

    def __init__(self, data="", is_64bit=False):
        self.name, self.info, self.other, self.shndx, self.value, self.size = self._unpack(data, is_64bit)


def read_header(file_obj):
    file_obj.seek(0)
    first_bytes = file_obj.read(5)
    if not first_bytes.startswith(b"\x7fELF"):
        raise ValueError("Not a valid ELF file")
    if first_bytes[4:5] == b'\x02':
        is_64bit = True
    elif first_bytes[4:5] == b'\x01':
        is_64bit = False
    else:
        raise ValueError("unknown kind of elf file")
    return ElfHeader.from_file(file_obj, is_64bit)

def _elf_section_headers(file_obj):
    ehdr = read_header(file_obj)

    symtab_data = None
    strtab_data = None
    shstr_data = None
    sections = []
    for section_idx in range(ehdr.shnum):
        section_header = ElfSectionHeader.from_file(file_obj, ehdr.is_64bit,
                                                    ehdr.shoff + section_idx * ehdr.shentsize)
        file_obj.seek(section_header.offset)
        data = file_obj.read(section_header.size)
        section_header.section_data = data
        sections.append(section_header)
        if section_header.type not in (ElfSectionHeader.TYPE_STRTAB, ElfSectionHeader.TYPE_SYMTAB):
            continue

        if section_header.type == ElfSectionHeader.TYPE_STRTAB:
            if section_idx != ehdr.shstrndx:
                strtab_data = data
            else:
                shstr_data = data
        elif section_header.type == ElfSectionHeader.TYPE_SYMTAB:
            symtab_data = data
    for section_header in sections:
        start = section_header.name
        end = shstr_data.find(b'\0', start)
        assert end >= 0
        section_header.name_as_bytes = shstr_data[start: end]
    return sections, symtab_data, strtab_data


def _iter_symbol_and_dynsym(file_obj):
    sections, symtab_data, strtab_data = _elf_section_headers(file_obj)
    assert strtab_data is not None
    file_obj.seek(0)
    ehdr = read_header(file_obj)
    # yield entries from the symbol table if we have it
    if symtab_data is not None:
        for sym in _elf_iter_symbols(ehdr, symtab_data, strtab_data):
            yield sym
    # yield entries from the dynamic symbol table if we have it
    for section in sections:
        if section.name_as_bytes != b'.dynsym':
            continue
        for sym in _elf_iter_symbols(ehdr, section.section_data, strtab_data):
            yield sym


def elf_find_symbol(file_obj, symbol):
    for sym in _iter_symbol_and_dynsym(file_obj):
        if sym.name_as_bytes == symbol:
            if sym.value:
                return sym.value
            if sym.info:
                return sym.info
    raise ValueError('not found')


def _elf_iter_symbols(ehdr, symtab_data, strtab_data):
    symtabentry_nbytes = ElfSymTabEntry.NBYTES64 if ehdr.is_64bit else ElfSymTabEntry.NBYTES
    num_symbols = len(symtab_data) // symtabentry_nbytes
    for sym_idx in range(num_symbols):
        start = sym_idx * symtabentry_nbytes
        sym_data = symtab_data[start: start + symtabentry_nbytes]
        if sym_idx == 0:
            assert sym_data == b"\x00" * len(sym_data)
            continue

        sym = ElfSymTabEntry(sym_data, ehdr.is_64bit)
        start = sym.name
        assert start >= 0
        end = strtab_data.find(b'\0', start)
        assert end >= 0
        name = strtab_data[start: end]
        sym.name_as_bytes = name
        yield sym


def elf_read_first_load_section(file_obj):
    ehdr = read_header(file_obj)

    for program_index in range(ehdr.phnum):
        phdr = ElfProgramHeader.from_file(file_obj, ehdr.is_64bit,
            ehdr.phoff + program_index * ehdr.phentsize)
        if phdr.type != ElfProgramHeader.PT_LOAD:
            continue
        return phdr

# __________________________________________________________
# reading and writing the memory of another process

import cffi

ffi = cffi.FFI()


ffi.cdef("""
struct iovec {
   void* iov_base;
   size_t iov_len;
};

typedef int pid_t;
long process_vm_readv(pid_t pid,
                      const struct iovec *local_iov,
                      unsigned long liovcnt,
                      const struct iovec *remote_iov,
                      unsigned long riovcnt,
                      unsigned long flags);
long process_vm_writev(pid_t pid,
                      const struct iovec *local_iov,
                      unsigned long liovcnt,
                      const struct iovec *remote_iov,
                      unsigned long riovcnt,
                      unsigned long flags);
""")
lib = ffi.dlopen(None)

def read_memory(pid, address, size):
    iovec = ffi.new('struct iovec[2]')
    target = ffi.new('char[]', size)
    # transfers data to the local process, from the remote process
    iovec[0].iov_base = target
    iovec[0].iov_len = size
    iovec[1].iov_base = ffi.cast('void*', address)
    iovec[1].iov_len = size
    result = lib.process_vm_readv(pid, iovec, 1, iovec + 1, 1, 0)
    if result != size:
        raise OSError(os.strerror(ffi.errno))
    return ffi.buffer(target, size)[:]

def write_memory(pid, address, content):
    iovec = ffi.new('struct iovec[2]')
    # transfers data from the local, to the remote process
    source = ffi.from_buffer(content)
    iovec[0].iov_base = source
    iovec[0].iov_len = len(content)
    iovec[1].iov_base = ffi.cast('void*', address)
    iovec[1].iov_len = len(content)
    result = lib.process_vm_writev(pid, iovec, 1, iovec + 1, 1, 0)
    if result != len(content):
        raise OSError(os.strerror(ffi.errno))

# __________________________________________________________
# parsing proc maps


def _parse_maps(pid='self', filter=None):
    with open('/proc/%s/maps' % pid) as f:
        parsed_maps = []
        libpypy = None
        for entry in f:
            mapping = entry.split()
            mapping_range = mapping[0]
            from_, to_ = mapping_range.split('-', 1)
            from_ = int(from_, 16)
            to_ = int(to_, 16)
            mapping_file = mapping[-1]
            if filter is not None and filter not in mapping_file:
                continue
            parsed_maps.append(dict(file=mapping[-1], from_=from_, to_=to_, full_line=entry))
        return parsed_maps

def _find_file_and_base_addr(pid):
    maps = _parse_maps(pid, 'libpypy')
    if not maps:
        executable = os.path.realpath('/proc/%s/exe' % pid)
        maps = _parse_maps(pid, executable)
        if not maps:
            raise ValueError('could not find executable nor libpypy.so in /proc/%s/maps' % pid)
    return maps[0]['file'], maps[0]['from_']

def _check_elf_debuglink(file):
    with open(file, 'rb') as f:
        sections, _, _ = _elf_section_headers(f)
        debuglinks = [section for section in sections if section.name_as_bytes == b'.gnu_debuglink']
        if debuglinks:
            debuglink = debuglinks[0]
            end = debuglink.section_data.find(b'\x00')
            fn = debuglink.section_data[:end]
            res = os.path.join(os.path.dirname(os.path.realpath(file)), fn)
            try:
                os.stat(res)
            except OSError:
                pass
            else:
                return res
    return file

# __________________________________________________________
# symbolication support, used by _vmprof.vmprof_resolve_address

def _proc_maps_find_map(value):
    maps = _parse_maps()
    base_map = None
    for map_entry in maps:
        if not map_entry['file'].startswith('/'):
            continue
        if base_map is None or base_map['file'] != map_entry['file']:
            base_map = map_entry
        if map_entry['from_'] <= value < map_entry['to_']:
            map_entry['base_map'] = base_map
            return map_entry
    else:
        return None


def _symbolify(value):
    map_entry = _proc_maps_find_map(value)
    if map_entry is None:
        return None
    filename = map_entry['file']
    base_addr = map_entry['base_map']['from_']
    with open(filename, 'rb') as f:
        phdr = elf_read_first_load_section(f)
        assert phdr.vaddr % phdr.align == 0
        symbol_value = value - base_addr + phdr.vaddr
        f.seek(0)
        for sym in _iter_symbol_and_dynsym(f):
            if sym.value <= symbol_value < sym.value + sym.size:
                return sym.name_as_bytes, filename
    return None

def _symbolify_all(values):
    # this is quite efficient, because it sorts the values, then sorts the
    # symbols within a shared library, and proceeds in a sorted order, merging
    # values and symbols
    values = sorted(values)
    res = {}
    map_entry = None
    for value in values:
        if map_entry is None or map_entry['to_'] < value:
            map_entry = _proc_maps_find_map(value)
            if map_entry is None:
                continue
            filename = map_entry['file']
            base_addr = map_entry['base_map']['from_']
            with open(filename, 'rb') as f:
                phdr = elf_read_first_load_section(f)
                assert phdr.vaddr % phdr.align == 0
                f.seek(0)
                syms = list(_iter_symbol_and_dynsym(f))
                syms.sort(key=lambda sym: sym.value)
                symindex = 0
        symbol_value = value - base_addr + phdr.vaddr
        for symindex in range(symindex, len(syms)):
            sym = syms[symindex]
            if sym.value <= symbol_value < sym.value + sym.size:
                res[value] = sym.name_as_bytes, filename
                break
            if sym.value > symbol_value:
                break
        else:
            continue
    return res

# __________________________________________________________
# actually starting the debugger


COOKIE_OFFSET = struct.calcsize('l')
PENDING_CALL_OFFSET = COOKIE_OFFSET + struct.calcsize('cccccccc')
SCRIPT_OFFSET = PENDING_CALL_OFFSET + struct.calcsize('l')
SCRIPT_MAX = 4096


def compute_remote_addr(pid):
    file, base_addr = _find_file_and_base_addr(pid)
    origfile = file
    file = _check_elf_debuglink(file)
    with open(file, 'rb') as f:
        symbol_value = elf_find_symbol(f, b'pypysig_counter')
        f.seek(0)
        phdr = elf_read_first_load_section(f)
    # compute address in target process
    # XXX I don't understand how alignment works, assert that it is aligned
    assert phdr.vaddr % phdr.align == 0
    return base_addr + symbol_value - phdr.vaddr


def start_debugger(pid, script, wait=True):
    if not sys.platform.startswith('linux'):
        raise ValueError('This works on Linux only so far')
    addr = compute_remote_addr(pid)
    cookie = read_memory(pid, addr + COOKIE_OFFSET, 8)
    assert cookie == b'pypysigs'
    if not isinstance(script, bytes):
        raise TypeError('script must be bytes, not %r' % (type(script).__name__, ))
    # write the script, and a null byte
    if not len(script) + 1 < SCRIPT_MAX:
        raise ValueError('script can be at most %s bytes long, not %s' % (SCRIPT_MAX - 1, len(script)))
    if b'\x00' in script:
        raise ValueError('script must not contain null byte')
    write_memory(pid, addr + SCRIPT_OFFSET, script + b'\x00')
    # write a 1 into pypysig_counter.debugger_pending_call
    write_memory(pid, addr + PENDING_CALL_OFFSET, struct.pack('l', 1))
    # write a -1 into pypysig_counter.value
    write_memory(pid, addr, struct.pack('l', -1))
    if wait:
        while 1:
            time.sleep(0.1)
            value, = struct.unpack('l', read_memory(pid, addr + PENDING_CALL_OFFSET, struct.calcsize('l')))
            if value == 0:
                return

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Execute Python code in another PyPy process.")
    parser.add_argument("pid", help="process id of the target process", type=int)
    parser.add_argument("code", help="python code passed as string to execute in the remote process", metavar='code')
    parser.add_argument("--dont-wait", help="dont wait for the other process to run the debug code", action='store_true')
    args = parser.parse_args()

    start_debugger(args.pid, args.code.encode('utf-8'), wait=not args.dont_wait)


if __name__ == '__main__':
    main()
