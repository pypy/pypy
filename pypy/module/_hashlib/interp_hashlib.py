from __future__ import with_statement
from pypy.interpreter.gateway import unwrap_spec, interp2app
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.interpreter.error import OperationError
from pypy.tool.sourcetools import func_renamer
from pypy.interpreter.baseobjspace import Wrappable
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib.objectmodel import keepalive_until_here
from pypy.rlib import ropenssl
from pypy.rlib.rstring import StringBuilder
from pypy.module.thread.os_lock import Lock

algorithms = ('md5', 'sha1', 'sha224', 'sha256', 'sha384', 'sha512')

class W_Hash(Wrappable):
    ctx = lltype.nullptr(ropenssl.EVP_MD_CTX.TO)

    def __init__(self, space, name):
        self.name = name

        # Allocate a lock for each HASH object.
        # An optimization would be to not release the GIL on small requests,
        # and use a custom lock only when needed.
        self.lock = Lock(space)

        digest = ropenssl.EVP_get_digestbyname(name)
        if not digest:
            raise OperationError(space.w_ValueError,
                                 space.wrap("unknown hash function"))
        ctx = lltype.malloc(ropenssl.EVP_MD_CTX.TO, flavor='raw')
        ropenssl.EVP_DigestInit(ctx, digest)
        self.ctx = ctx

    def __del__(self):
        # self.lock.free()
        if self.ctx:
            ropenssl.EVP_MD_CTX_cleanup(self.ctx)
            lltype.free(self.ctx, flavor='raw')

    def descr_repr(self, space):
        addrstring = self.getaddrstring(space)
        return space.wrap("<%s HASH object at 0x%s>" % (
            self.name, addrstring))

    @unwrap_spec(string='bufferstr')
    def update(self, space, string):
        with rffi.scoped_nonmovingbuffer(string) as buf:
            with self.lock:
                # XXX try to not release the GIL for small requests
                ropenssl.EVP_DigestUpdate(self.ctx, buf, len(string))

    def copy(self, space):
        "Return a copy of the hash object."
        w_hash = W_Hash(space, self.name)
        with self.lock:
            ropenssl.EVP_MD_CTX_copy(w_hash.ctx, self.ctx)
        return w_hash

    def digest(self, space):
        "Return the digest value as a string of binary data."
        digest = self._digest(space)
        return space.wrap(digest)

    def hexdigest(self, space):
        "Return the digest value as a string of hexadecimal digits."
        digest = self._digest(space)
        hexdigits = '0123456789abcdef'
        result = StringBuilder(self._digest_size() * 2)
        for c in digest:
            result.append(hexdigits[(ord(c) >> 4) & 0xf])
            result.append(hexdigits[ ord(c)       & 0xf])
        return space.wrap(result.build())

    def get_digest_size(self, space):
        return space.wrap(self._digest_size())

    def get_block_size(self, space):
        return space.wrap(self._block_size())

    def _digest(self, space):
        copy = self.copy(space)
        ctx = copy.ctx
        digest_size = self._digest_size()
        digest = lltype.malloc(rffi.CCHARP.TO, digest_size, flavor='raw')

        try:
            ropenssl.EVP_DigestFinal(ctx, digest, None)
            return rffi.charpsize2str(digest, digest_size)
        finally:
            keepalive_until_here(copy)
            lltype.free(digest, flavor='raw')


    def _digest_size(self):
        # XXX This isn't the nicest way, but the EVP_MD_size OpenSSL
        # XXX function is defined as a C macro on OS X and would be
        # XXX significantly harder to implement in another way.
        # Values are digest sizes in bytes
        return {
            'md5':    16, 'MD5':    16,
            'sha1':   20, 'SHA1':   20,
            'sha224': 28, 'SHA224': 28,
            'sha256': 32, 'SHA256': 32,
            'sha384': 48, 'SHA384': 48,
            'sha512': 64, 'SHA512': 64,
            }.get(self.name, 0)

    def _block_size(self):
        # XXX This isn't the nicest way, but the EVP_MD_CTX_block_size
        # XXX OpenSSL function is defined as a C macro on some systems
        # XXX and would be significantly harder to implement in
        # XXX another way.
        return {
            'md5':     64, 'MD5':     64,
            'sha1':    64, 'SHA1':    64,
            'sha224':  64, 'SHA224':  64,
            'sha256':  64, 'SHA256':  64,
            'sha384': 128, 'SHA384': 128,
            'sha512': 128, 'SHA512': 128,
            }.get(self.name, 0)

W_Hash.typedef = TypeDef(
    'HASH',
    __repr__=interp2app(W_Hash.descr_repr),
    update=interp2app(W_Hash.update),
    copy=interp2app(W_Hash.copy),
    digest=interp2app(W_Hash.digest),
    hexdigest=interp2app(W_Hash.hexdigest),
    #
    digest_size=GetSetProperty(W_Hash.get_digest_size),
    digestsize=GetSetProperty(W_Hash.get_digest_size),
    block_size=GetSetProperty(W_Hash.get_block_size),
    )

@unwrap_spec(name=str, string='bufferstr')
def new(space, name, string=''):
    w_hash = W_Hash(space, name)
    w_hash.update(space, string)
    return space.wrap(w_hash)

# shortcut functions
def make_new_hash(name, funcname):
    @func_renamer(funcname)
    @unwrap_spec(string='bufferstr')
    def new_hash(space, string=''):
        return new(space, name, string)
    return new_hash

for name in algorithms:
    newname = 'new_%s' % (name,)
    globals()[newname] = make_new_hash(name, newname)
