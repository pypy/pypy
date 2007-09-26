import struct

native_is_bigendian = struct.pack("=i", 1) == struct.pack(">i", 1)
