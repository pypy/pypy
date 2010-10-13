from pypy.interpreter.gateway import unwrap_spec, interp2app
from pypy.interpreter.typedef import TypeDef
from pypy.tool.sourcetools import func_renamer
from pypy.interpreter.baseobjspace import Wrappable, W_Root, ObjSpace
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib import ropenssl

algorithms = ('md5', 'sha1', 'sha224', 'sha256', 'sha384', 'sha512')

class W_Hash(Wrappable):
    def __init__(self, name):
        self.name = name
        self.ctx = lltype.malloc(ropenssl.EVP_MD_CTX.TO, flavor='raw')

    @unwrap_spec('self', ObjSpace, str, str)
    def descr_init(self, space, name, buffer):
        digest = ropenssl.EVT_get_digestbyname(name)
        if not digest:
            raise OperationError(space.w_ValueError,
                                 space.wrap("unknown hash function"))
        ropenssl.EVP_DigestInit(self.ctx, digest)

        if buffer:
            self._hash(buffer)

    @unwrap_spec('self', ObjSpace)
    def descr_repr(self, space):
        return space.wrap("<%s HASH object @ 0x%x>" % (self.name, id(self)))

    @unwrap_spec('self', ObjSpace, str)
    def update(self, space, buffer):
        self._hash(buffer)

    def _hash(self, buffer):
        buf = rffi.str2charp(buffer)
        try:
            ropenssl.EVP_DigestUpdate(self.ctx, buf, len(buffer))
        finally:
            rffi.free_charp(buf)

W_Hash.typedef = TypeDef(
    'HASH',
    __init__=interp2app(W_Hash.descr_init),
    __repr__=interp2app(W_Hash.descr_repr),
    update=interp2app(W_Hash.update),
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
