from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import ObjSpace, W_Root, NoneNotWrapped, interp2app
from pypy.interpreter.baseobjspace import Wrappable
from pypy.lib.md5 import MD5Type

class W_MD5Type(Wrappable):
     """A wrappable box around an interp level md5 object."""   
     def __init__(self, md5o=None):
          if md5o is None:
               self.md5 = MD5Type()
          else:
               self.md5 = md5o
     
     def update(self, space, arg):
          self.md5.update(arg)
     update.unwrap_spec = ['self', ObjSpace, str]
     
     def digest(self, space):
          d = self.md5.digest()
          return space.wrap(d)
     digest.unwrap_spec = ['self', ObjSpace]
     
     def hexdigest(self, space):
          hd = self.md5.hexdigest()
          return space.wrap(hd)
     hexdigest.unwrap_spec = ['self', ObjSpace]
     
     def copy(self, space):
          cmd5 = self.md5.copy()
          return W_MD5Type(cmd5)
     copy.unwrap_spec = ['self', ObjSpace]

W_MD5Type.typedef = TypeDef("W_MD5Type",
     update = interp2app(W_MD5Type.update, unwrap_spec=W_MD5Type.update.unwrap_spec),
     digest = interp2app(W_MD5Type.digest, unwrap_spec=W_MD5Type.digest.unwrap_spec),
     hexdigest = interp2app(W_MD5Type.hexdigest, unwrap_spec=W_MD5Type.hexdigest.unwrap_spec),
     copy = interp2app(W_MD5Type.copy, unwrap_spec=W_MD5Type.copy.unwrap_spec),
                            )

def new_md5(space, arg=''):
     """
     Return a new md5 crypto object.
     If arg is present, the method call update(arg) is made.
     """
    
     w_crypto = W_MD5Type()
     if len(arg) != 0:
          w_crypto.update(space, arg)
     return w_crypto
new_md5.unwrap_spec = [ObjSpace, str]