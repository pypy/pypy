from ._sha3_cffi import ffi as _ffi, lib as _lib
import codecs

SHA3_MAX_DIGESTSIZE = 64 # 64 Bytes (512 Bits) for 224 to 512
SHA3_LANESIZE = (20 * 8) # ExtractLane needs max uint64_t[20] extra.

class Immutable(type):
    def __init__(cls, name, bases, dct):
        type.__setattr__(cls,"attr",set(dct.keys()))
        type.__init__(cls, name, bases, dct)

    def __setattr__(cls, name, value):
        # Mock Py_TPFLAGS_IMMUTABLETYPE
        qualname = '.'.join([cls.__module__, cls.__name__])
        raise TypeError(f"cannot set '{name}' attribute of immutable type '{qualname}'")


class _sha3(metaclass=Immutable):
    _keccak_init = None  # Overridden in subclasses

    def __new__(cls, string=None, usedforsecurity=True):
        self = super().__new__(cls)
        self._hash_state = _ffi.new("Keccak_HashInstance*")

        assert self._keccak_init is not None
        self._keccak_init()

        if string:
            self.update(string)
        return self

    def update(self, string):
        if isinstance(string, memoryview):
            buf = string.tobytes()
        else:
            buf = _ffi.from_buffer(string)
        res = _lib.Keccak_HashUpdate(self._hash_state, buf, len(buf) * 8)

    def digest(self):
        digest = _ffi.new("char[]",
                          SHA3_MAX_DIGESTSIZE + SHA3_LANESIZE)
        state_copy = _ffi.new("Keccak_HashInstance*")
        _ffi.memmove(state_copy, self._hash_state,
                     _ffi.sizeof("Keccak_HashInstance"))
        if _lib.Keccak_HashFinal(state_copy, digest) != _lib.SUCCESS:
            raise RuntimeError("internal error in SHA3 Final()")
        return _ffi.unpack(digest, self._hash_state.fixedOutputLength // 8)

    def hexdigest(self):
        return codecs.encode(self.digest(), 'hex').decode()

    def copy(self):
        copy = super().__new__(type(self))
        copy._hash_state = _ffi.new("Keccak_HashInstance*")
        _ffi.memmove(copy._hash_state, self._hash_state,
                     _ffi.sizeof("Keccak_HashInstance"))
        return copy

    @property
    def digest_size(self):
        return self._hash_state.fixedOutputLength // 8

    @property
    def block_size(self):
        return self._hash_state.sponge.rate // 8

    @property
    def _capacity_bits(self):
        return 1600 - self._hash_state.sponge.rate

    @property
    def _rate_bits(self):
        return self._hash_state.sponge.rate

    @property
    def _suffix(self):
        return bytes([self._hash_state.delimitedSuffix])


class _shake(_sha3):
    def digest(self, length):
        if length >= (1 << 29):
            raise ValueError("length is too large")
        if length < 0:
            raise ValueError("value must be positive")
        # ExtractLane needs at least SHA3_MAX_DIGESTSIZE + SHA3_LANESIZE and
        # SHA_LANESIZE extra space.
        digest = _ffi.new("char[]", length + SHA3_LANESIZE)
        # Get the raw (binary) digest value
        state_copy = _ffi.new("Keccak_HashInstance*")
        _ffi.memmove(state_copy, self._hash_state,
                     _ffi.sizeof("Keccak_HashInstance"))
        if _lib.Keccak_HashFinal(state_copy, digest) != _lib.SUCCESS:
            raise RuntimeError("internal error in SHA3 Final()")
        if _lib.Keccak_HashSqueeze(state_copy, digest, length * 8) != _lib.SUCCESS:
            raise RuntimeError("internal error in SHA3 Squeeze()")
        return _ffi.unpack(digest, length)

    def hexdigest(self, length):
        return codecs.encode(self.digest(length), 'hex').decode()


class sha3_224(_sha3):
    name = "sha3_224"
    def _keccak_init(self):
        return _lib.Keccak_HashInitialize_SHA3_224(self._hash_state)

class sha3_256(_sha3):
    name = "sha3_256"
    def _keccak_init(self):
        return _lib.Keccak_HashInitialize_SHA3_256(self._hash_state)

class sha3_384(_sha3):
    name = "sha3_384"
    def _keccak_init(self):
        return _lib.Keccak_HashInitialize_SHA3_384(self._hash_state)

class sha3_512(_sha3):
    name = "sha3_512"
    def _keccak_init(self):
        return _lib.Keccak_HashInitialize_SHA3_512(self._hash_state)

class shake_128(_shake):
    name = "shake_128"
    def _keccak_init(self):
        return _lib.Keccak_HashInitialize_SHAKE128(self._hash_state)

class shake_256(_shake):
    name = "shake_256"
    def _keccak_init(self):
        return _lib.Keccak_HashInitialize_SHAKE256(self._hash_state)

