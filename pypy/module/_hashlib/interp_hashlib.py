from pypy.interpreter.gateway import unwrap_spec, interp2app
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.tool.sourcetools import func_renamer
from pypy.interpreter.baseobjspace import Wrappable, W_Root, ObjSpace
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib import ropenssl
from pypy.rlib.rstring import StringBuilder

algorithms = ('md5', 'sha1', 'sha224', 'sha256', 'sha384', 'sha512')

class W_Hash(Wrappable):
    def __init__(self, name):
        self.name = name
        self.ctx = lltype.malloc(ropenssl.EVP_MD_CTX.TO, flavor='raw')

        digest = ropenssl.EVP_get_digestbyname(name)
        if not digest:
            raise OperationError(space.w_ValueError,
                                 space.wrap("unknown hash function"))
        ropenssl.EVP_DigestInit(self.ctx, digest)

    @unwrap_spec('self', ObjSpace)
    def descr_repr(self, space):
        return space.wrap("<%s HASH object @ 0x%x>" % (self.name, id(self)))

    @unwrap_spec('self', ObjSpace, str)
    def update(self, space, buffer):
        buf = rffi.str2charp(buffer)
        try:
            ropenssl.EVP_DigestUpdate(self.ctx, buf, len(buffer))
        finally:
            rffi.free_charp(buf)

    @unwrap_spec('self', ObjSpace)
    def copy(self, space):
        "Return a copy of the hash object."
        w_hash = W_Hash(self.name)
        ropenssl.EVP_MD_CTX_copy(w_hash.ctx, self.ctx)
        return w_hash

    @unwrap_spec('self', ObjSpace)
    def digest(self, space):
        "Return the digest value as a string of binary data."
        digest = self._digest(space)
        return space.wrap(digest)

    @unwrap_spec('self', ObjSpace)
    def hexdigest(self, space):
        "Return the digest value as a string of hexadecimal digits."
        digest = self._digest(space)
        hexdigits = '0123456789abcdef'
        result = StringBuilder(self._digest_size() * 2)
        for c in digest:
            result.append(hexdigits[(ord(c) >> 4) & 0xf])
            result.append(hexdigits[ ord(c)       & 0xf])
        return space.wrap(result.build())

    def get_digest_size(space, self):
        return space.wrap(self._digest_size())

    def get_block_size(space, self):
        return space.wrap(self._block_size())

    def _digest(self, space):
        ctx = self.copy(space).ctx
        digest_size = self._digest_size()
        digest = lltype.malloc(rffi.CCHARP.TO, digest_size, flavor='raw')

        try:
            ropenssl.EVP_DigestFinal(ctx, digest, None)
            return rffi.charp2strn(digest, digest_size)
        finally:
            lltype.free(digest, flavor='raw')


    def _digest_size(self):
        # XXX This isn't the nicest way, but the EVP_MD_size OpenSSL
        # XXX function is defined as a C macro on OS X and would be
        # XXX significantly harder to implement in another way.
        # Values are digest sizes in bytes
        return {
            'md5': 16,
            'sha1': 20,
            'sha224': 28,
            'sha256': 32,
            'sha384': 48,
            'sha512': 64,
            }.get(self.name, 0)

    def _block_size(self):
        # XXX This isn't the nicest way, but the EVP_MD_CTX_block_size
        # XXX OpenSSL function is defined as a C macro on some systems
        # XXX and would be significantly harder to implement in
        # XXX another way.
        return {
            'md5':     64,
            'sha1':    64,
            'sha224':  64,
            'sha256':  64,
            'sha384': 128,
            'sha512': 128,
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

@unwrap_spec(ObjSpace, str, str)
def new(space, method, string=''):
    w_hash = W_Hash(method)
    w_hash.update(space, string)
    return space.wrap(w_hash)

# shortcut functions
for name in algorithms:
    newname = 'new_%s' % (name,)
    @func_renamer(newname)
    def new_hash(w_string=''):
        return _new(name, w_string)
    globals()[newname] = new_hash
