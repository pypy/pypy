
def __getattribute__(w_obj,w_name):
  type = space.gettype(w_obj)
  name = space.unwrap(w_name)
  w_descr = type.lookup(name)
  if w_descr is not None:
     if space.is_data_descr(w_descr):
         return space.get(w_descr,w_obj,space.wrap(type))
  w_dict = space.getdict(w_obj)
  if w_dict is not None:
     try:
       return space.getitem(w_dict,w_name)
     except OperationError, e:
       if not e.match(space,space.w_KeyError):
         raise
  if w_descr is not None:
     return space.get(w_descr,w_obj,space.wrap(type))
  raise OperationError(space.w_AttributeError,w_name)

def space.getattr(w_obj,w_name):
   type = space.gettype(w_obj)
   w_descr = type.lookup('__getattribute__')
   w_impl = space.get(w_descr,w_obj, space.wrap(type))
   try:
     return space.call_function(w_impl, w_name)
   except: # AttributeError
     w_descr = type.lookup('__getattr__')
     if w_descr is None:
       raise
     w_impl = space.get(w_descr,w_obj, space.wrap(type))
     return space.call_function(w_descr,w_obj, space.wrap(type))

def space.get(w_obj,w_name):
   type = space.gettype(w_obj)
   w_descr = type.lookup('__get__')
   if w_descr is not None:
     w_impl = space.get(w_descr,w_obj, space.wrap(type))
     return space.call_function(w_impl, w_name)
   else:
     return w_obj
