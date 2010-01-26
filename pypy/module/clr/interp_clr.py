import os.path
from pypy.module.clr import assemblyname
from pypy.interpreter.baseobjspace import ObjSpace, W_Root, Wrappable
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.gateway import interp2app, ApplevelClass
from pypy.interpreter.typedef import TypeDef
from pypy.rpython.ootypesystem import ootype
from pypy.translator.cli.dotnet import CLR, box, unbox, NativeException, native_exc,\
     new_array, init_array, typeof

System = CLR.System
Assembly = CLR.System.Reflection.Assembly
TargetInvocationException = NativeException(CLR.System.Reflection.TargetInvocationException)
AmbiguousMatchException = NativeException(CLR.System.Reflection.AmbiguousMatchException)

def get_method(space, b_type, name, b_paramtypes):
    try:
        method = b_type.GetMethod(name, b_paramtypes)
    except AmbiguousMatchException:
        msg = 'Multiple overloads for %s could match'
        raise operationerrfmt(space.w_TypeError, msg, name)
    if method is None:
        msg = 'No overloads for %s could match'
        raise operationerrfmt(space.w_TypeError, msg, name)
    return method

def get_constructor(space, b_type, b_paramtypes):
    try:
        ctor = b_type.GetConstructor(b_paramtypes)
    except AmbiguousMatchException:
        msg = 'Multiple constructors could match'
        raise OperationError(space.w_TypeError, space.wrap(msg))
    if ctor is None:
        msg = 'No overloads for constructor could match'
        raise OperationError(space.w_TypeError, space.wrap(msg))
    return ctor

def rewrap_args(space, w_args, startfrom):
    args = space.unpackiterable(w_args)
    paramlen = len(args)-startfrom
    b_args = new_array(System.Object, paramlen)
    b_paramtypes = new_array(System.Type, paramlen)
    for i in range(startfrom, len(args)):
        j = i-startfrom
        b_obj = py2cli(space, args[i])
        b_args[j] = b_obj
        if b_obj is None:
            b_paramtypes[j] = typeof(System.Object) # we really can't be more precise
        else:
            b_paramtypes[j] = b_obj.GetType() # XXX: potentially inefficient
    return b_args, b_paramtypes


def call_method(space, b_obj, b_type, name, w_args, startfrom):
    b_args, b_paramtypes = rewrap_args(space, w_args, startfrom)
    b_meth = get_method(space, b_type, name, b_paramtypes)
    try:
        # for an explanation of the box() call, see the log message for revision 35167
        b_res = box(b_meth.Invoke(b_obj, b_args))
    except TargetInvocationException, e:
        b_inner = native_exc(e).get_InnerException()
        message = str(b_inner.get_Message())
        # TODO: use the appropriate exception, not StandardError
        raise OperationError(space.w_StandardError, space.wrap(message))
    if b_meth.get_ReturnType().get_Name() == 'Void':
        return space.w_None
    else:
        return cli2py(space, b_res)

def call_staticmethod(space, typename, methname, w_args):
    """
    Call a .NET static method.

    Parameters:

      - typename: the fully qualified .NET name of the class
        containing the method (e.g. ``System.Math``)

      - methname: the name of the static method to call (e.g. ``Abs``)

      - args: a list containing the arguments to be passed to the
        method.
    """
    b_type = System.Type.GetType(typename) # XXX: cache this!
    return call_method(space, None, b_type, methname, w_args, 0)
call_staticmethod.unwrap_spec = [ObjSpace, str, str, W_Root]

def py2cli(space, w_obj):
    try:
        cliobj = space.getattr(w_obj, space.wrap('__cliobj__'))
    except OperationError, e:
        if e.match(space, space.w_AttributeError):
            # it hasn't got a __cloobj__
            return w_obj.tocli()
        else:
            raise
    else:
        if isinstance(cliobj, W_CliObject):
            return cliobj.b_obj # unwrap it!
        else:
            # this shouldn't happen! Fallback to the default impl
            return w_obj.tocli()

def cli2py(space, b_obj):
    # TODO: support other types and find the most efficient way to
    # select the correct case
    if b_obj is None:
        return space.w_None

    w_obj = unbox(b_obj, W_Root)
    if w_obj is not None:
        return w_obj # it's already a wrapped object!
    
    b_type = b_obj.GetType()
    if b_type == typeof(System.Int32):
        intval = unbox(b_obj, ootype.Signed)
        return space.wrap(intval)
    elif b_type == typeof(System.Double):
        floatval = unbox(b_obj, ootype.Float)
        return space.wrap(floatval)
    elif b_type == typeof(System.Boolean):
        boolval = unbox(b_obj, ootype.Bool)
        return space.wrap(boolval)
    elif b_type == typeof(System.String):
        strval = unbox(b_obj, ootype.String)
        return space.wrap(strval)
    else:
        namespace, classname = split_fullname(b_type.ToString())
        assemblyname = b_type.get_Assembly().get_FullName()
        w_cls = load_cli_class(space, assemblyname, namespace, classname)
        cliobj = W_CliObject(space, b_obj)
        return wrapper_from_cliobj(space, w_cls, cliobj)

def split_fullname(name):
    lastdot = name.rfind('.')
    if lastdot < 0:
        return '', name
    return name[:lastdot], name[lastdot+1:]

def wrap_list_of_tuples(space, lst):
    list_w = []
    for (a,b,c,d) in lst:
        items_w = [space.wrap(a), space.wrap(b), space.wrap(c), space.wrap(d)]
        list_w.append(space.newtuple(items_w))
    return space.newlist(list_w)

def wrap_list_of_pairs(space, lst):
    list_w = []
    for (a,b) in lst:
        items_w = [space.wrap(a), space.wrap(b)]
        list_w.append(space.newtuple(items_w))
    return space.newlist(list_w)

def wrap_list_of_strings(space, lst):
    list_w = [space.wrap(s) for s in lst]
    return space.newlist(list_w)

def get_methods(space, b_type):
    methods = []
    staticmethods = []
    b_methodinfos = b_type.GetMethods()
    for i in range(len(b_methodinfos)):
        b_meth = b_methodinfos[i]
        if b_meth.get_IsPublic():
            if b_meth.get_IsStatic():
                staticmethods.append(str(b_meth.get_Name()))
            else:
                methods.append(str(b_meth.get_Name()))
    w_staticmethods = wrap_list_of_strings(space, staticmethods)
    w_methods = wrap_list_of_strings(space, methods)
    return w_staticmethods, w_methods

def get_properties(space, b_type):
    properties = []
    indexers = {}
    b_propertyinfos = b_type.GetProperties()
    for i in range(len(b_propertyinfos)):
        b_prop = b_propertyinfos[i]
        get_name = None
        set_name = None
        is_static = False
        if b_prop.get_CanRead():
            get_meth = b_prop.GetGetMethod()
            get_name = get_meth.get_Name()
            is_static = get_meth.get_IsStatic()
        if b_prop.get_CanWrite():
            set_meth = b_prop.GetSetMethod()
            if set_meth:
                set_name = set_meth.get_Name()
                is_static = set_meth.get_IsStatic()
        b_indexparams = b_prop.GetIndexParameters()
        if len(b_indexparams) == 0:
            properties.append((b_prop.get_Name(), get_name, set_name, is_static))
        else:
            indexers[b_prop.get_Name(), get_name, set_name, is_static] = None
    w_properties = wrap_list_of_tuples(space, properties)
    w_indexers = wrap_list_of_tuples(space, indexers.keys())
    return w_properties, w_indexers

class _CliClassCache:
    def __init__(self):
        self.cache = {}

    def put(self, fullname, cls):
        assert fullname not in self.cache
        self.cache[fullname] = cls

    def get(self, fullname):
        return self.cache.get(fullname, None)
CliClassCache = _CliClassCache()

class _AssembliesInfo:
    w_namespaces = None
    w_classes = None
    w_generics = None
    w_info = None # a tuple containing (w_namespaces, w_classes, w_generics)
AssembliesInfo = _AssembliesInfo()

def save_info_for_assembly(space, b_assembly):
    info = AssembliesInfo
    b_types = b_assembly.GetTypes()
    w_assemblyName = space.wrap(b_assembly.get_FullName())
    for i in range(len(b_types)):
        b_type = b_types[i]
        namespace = b_type.get_Namespace()
        fullname = b_type.get_FullName()
        if '+' in fullname:
            # it's an internal type, skip it
            continue
        if namespace is not None:
            # builds all possible sub-namespaces
            # (e.g. 'System', 'System.Windows', 'System.Windows.Forms')
            chunks = namespace.split(".")
            temp_name = chunks[0]
            space.setitem(info.w_namespaces, space.wrap(temp_name), space.w_None)
            for chunk in chunks[1:]:
                temp_name += "."+chunk
                space.setitem(info.w_namespaces, space.wrap(temp_name), space.w_None)
        if b_type.get_IsGenericType():
            index = fullname.rfind("`")
            assert index >= 0
            pyName = fullname[0:index]
            space.setitem(info.w_classes, space.wrap(pyName), w_assemblyName)
            space.setitem(info.w_generics, space.wrap(pyName), space.wrap(fullname))
        else:
            space.setitem(info.w_classes, space.wrap(fullname), w_assemblyName)

    
def save_info_for_std_assemblies(space):
    # in theory we should use Assembly.Load, but it doesn't work with
    # pythonnet because it thinks it should use the Load(byte[]) overload
    b_mscorlib = Assembly.LoadWithPartialName(assemblyname.mscorlib)
    b_System = Assembly.LoadWithPartialName(assemblyname.System)
    save_info_for_assembly(space, b_mscorlib)
    save_info_for_assembly(space, b_System)

def get_assemblies_info(space):
    info = AssembliesInfo
    if info.w_info is None:
        info.w_namespaces = space.newdict()
        info.w_classes = space.newdict()
        info.w_generics = space.newdict()
        info.w_info = space.newtuple([info.w_namespaces, info.w_classes, info.w_generics])
        save_info_for_std_assemblies(space)
    return info.w_info
get_assemblies_info.unwrap_spec = [ObjSpace]

#_______________________________________________________________________________
# AddReference* methods

# AddReference', 'AddReferenceByName', 'AddReferenceByPartialName', 'AddReferenceToFile', 'AddReferenceToFileAndPath'

def AddReferenceByPartialName(space, name):
    b_assembly = Assembly.LoadWithPartialName(name)
    if b_assembly is not None:
        save_info_for_assembly(space, b_assembly)
AddReferenceByPartialName.unwrap_spec = [ObjSpace, str]


def load_cli_class(space, assemblyname, namespace, classname):
    """
    Load the given .NET class into the PyPy interpreter and return a
    Python class referencing to it.

    Parameters:

       - namespace: the full name of the namespace containing the
         class (e.g., ``System.Collections``).

       - classname: the name of the class in the specified namespace
         (e.g. ``ArrayList``).    """
    fullname = '%s.%s' % (namespace, classname)
    w_cls = CliClassCache.get(fullname)
    if w_cls is None:
        w_cls = build_cli_class(space, namespace, classname, fullname, assemblyname)
        CliClassCache.put(fullname, w_cls)
    return w_cls
load_cli_class.unwrap_spec = [ObjSpace, str, str, str]

def build_cli_class(space, namespace, classname, fullname, assemblyname):
    assembly_qualified_name = '%s, %s' % (fullname, assemblyname)
    b_type = System.Type.GetType(assembly_qualified_name)
    if b_type is None:
        raise operationerrfmt(space.w_ImportError,
                              "Cannot load .NET type: %s", fullname)

    # this is where we locate the interfaces inherited by the class
    # set the flag hasIEnumerable if IEnumerable interface has been by the class
    hasIEnumerable = b_type.GetInterface("System.Collections.IEnumerable") is not None

    # this is where we test if the class is Generic
    # set the flag isClassGeneric 
    isClassGeneric = False
    if b_type.get_IsGenericType():
        isClassGeneric = True

    w_staticmethods, w_methods = get_methods(space, b_type)
    w_properties, w_indexers = get_properties(space, b_type)
    return build_wrapper(space,
                         space.wrap(namespace),
                         space.wrap(classname),
                         space.wrap(assemblyname),
                         w_staticmethods,
                         w_methods,
                         w_properties,
                         w_indexers,
                         space.wrap(hasIEnumerable),
                         space.wrap(isClassGeneric))


class W_CliObject(Wrappable):
    def __init__(self, space, b_obj):
        self.space = space
        self.b_obj = b_obj

    def call_method(self, name, w_args, startfrom=0):
        return call_method(self.space, self.b_obj, self.b_obj.GetType(), name, w_args, startfrom)
    call_method.unwrap_spec = ['self', str, W_Root, int]

def cli_object_new(space, w_subtype, typename, w_args):
    b_type = System.Type.GetType(typename)
    b_args, b_paramtypes = rewrap_args(space, w_args, 0)
    b_ctor = get_constructor(space, b_type, b_paramtypes)
    try:
        b_obj = b_ctor.Invoke(b_args)
    except TargetInvocationException, e:
        b_inner = native_exc(e).get_InnerException()
        message = str(b_inner.get_Message())
        # TODO: use the appropriate exception, not StandardError
        raise OperationError(space.w_StandardError, space.wrap(message))
    return space.wrap(W_CliObject(space, b_obj))
cli_object_new.unwrap_spec = [ObjSpace, W_Root, str, W_Root]

W_CliObject.typedef = TypeDef(
    '_CliObject_internal',
    __new__ = interp2app(cli_object_new),
    call_method = interp2app(W_CliObject.call_method),
    )

path, _ = os.path.split(__file__)
app_clr = os.path.join(path, 'app_clr.py')
app = ApplevelClass(file(app_clr).read())
del path, app_clr
build_wrapper = app.interphook("build_wrapper")
wrapper_from_cliobj = app.interphook("wrapper_from_cliobj")
