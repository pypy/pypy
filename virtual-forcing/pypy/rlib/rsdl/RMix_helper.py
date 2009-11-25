from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib.rsdl import RMix, RSDL
from pypy.rpython.tool import rffi_platform as platform


def malloc_buffer_chunk(has_own_allocated_buffer, length_bytes, volume):
    buffer_pointer = lltype.malloc(RMix.Buffer, length_bytes, flavor='raw')
    return malloc_chunk(has_own_allocated_buffer, length_bytes, volume)

def malloc_chunk(has_own_allocated_buffer, buffer_pointer, length_bytes, volume):
    """
    Creates a new Mix_Chunk.
    has_own_allocated_buffer:  if 1 struct has its own allocated buffer, 
                                if 0 abuf should not be freed
    buffer_pointer:             pointer to audio data
    length_bytes:               length of audio data in bytes
    volume:                     Per-sample volume, 0-128 (normally 
                                MIX_MAX_VOLUME after loading)"""
    p = lltype.malloc(RMix.Chunk, flavor='raw')
    rffi.setintfield(p, 'c_allocated', has_own_allocated_buffer)
    rffi.setintfield(p, 'c_abuf', buffer_pointer)
    rffi.setintfield(p, 'c_alen', length_bytes)
    rffi.setintfield(p, 'c_volume', volume)
    return p