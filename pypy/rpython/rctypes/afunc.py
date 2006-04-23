from pypy.annotation.model import SomeCTypesObject
from pypy.annotation import model as annmodel
from pypy.rpython.error import TyperError
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.lltypesystem import lltype

import ctypes


CFuncPtrType = type(ctypes.CFUNCTYPE(None))


class CallEntry(ExtRegistryEntry):
    """Annotation and rtyping of calls to external functions
    declared with ctypes.
    """
    _metatype_ = CFuncPtrType

    def compute_result_annotation(self, *args_s):
        """
        Answer the annotation of the external function's result
        """
        result_ctype = self.instance.restype
        if result_ctype is None:
            return None
        if result_ctype is ctypes.py_object:
            raise Exception("ctypes functions cannot have restype=py_object; "
                            "set their restype to a subclass of py_object "
                            "and call apyobject.register_py_object_subclass")
            #... because then in ctypes you don't get automatic unwrapping.
            #    That would not be annotatable, for the same reason that
            #    reading the .value attribute of py_object is not annotatable
        s_result = SomeCTypesObject(result_ctype, SomeCTypesObject.OWNSMEMORY)
        return s_result.return_annotation()

    def specialize_call(self, hop):
        from pypy.rpython.rctypes.rmodel import CTypesValueRepr
        cfuncptr = self.instance
        fnname = cfuncptr.__name__

        def repr_for_ctype(ctype):
            s = SomeCTypesObject(ctype, SomeCTypesObject.MEMORYALIAS)
            return hop.rtyper.getrepr(s)

        args_r = []
        if getattr(cfuncptr, 'argtypes', None) is not None:
            for ctype in cfuncptr.argtypes:
                args_r.append(repr_for_ctype(ctype))
        else:
            # unspecified argtypes: use ctypes rules for arguments
            for s_arg, r_arg in zip(hop.args_s, hop.args_r):
                if not isinstance(s_arg, SomeCTypesObject):
                    # accept integers, strings, or None
                    if isinstance(s_arg, annmodel.SomeInteger):
                        r_arg = repr_for_ctype(c_long)
                    elif (isinstance(s_arg, annmodel.SomeString)
                          or s_arg == annmodel.s_None):
                        r_arg = repr_for_ctype(c_char_p)
                    else:
                        raise TyperError("call with no argtypes: don't know "
                                         "how to convert argument %r"%(s_arg,))
                args_r.append(r_arg)

        vlist = hop.inputargs(*args_r)
        unwrapped_args_v = []
        ARGTYPES = []
        for r_arg, v in zip(args_r, vlist):
            if isinstance(r_arg, CTypesValueRepr):
                # ValueRepr case
                unwrapped_args_v.append(r_arg.getvalue(hop.llops, v))
                ARGTYPES.append(r_arg.ll_type)
            else:
                # RefRepr case -- i.e. the function argument that we pass by
                # value is e.g. a complete struct; we pass a pointer to it
                # in the low-level graphs and it's up to the back-end to
                # generate the correct dereferencing
                unwrapped_args_v.append(r_arg.get_c_data(hop.llops, v))
                ARGTYPES.append(r_arg.c_data_type)
        if cfuncptr.restype is not None:
            s_res = SomeCTypesObject(cfuncptr.restype,
                                     SomeCTypesObject.OWNSMEMORY)
            r_res = hop.rtyper.getrepr(s_res)
            RESTYPE = r_res.ll_type
        else:
            RESTYPE = lltype.Void

        kwds = {}
        if hasattr(cfuncptr, 'llinterp_friendly_version'):
            kwds['_callable'] = cfuncptr.llinterp_friendly_version
        if (cfuncptr._flags_ & ctypes._FUNCFLAG_PYTHONAPI) == 0:
            kwds['includes'] = getattr(cfuncptr, 'includes', ())
        #else:
        #   no 'includes': hack to trigger in GenC a PyErr_Occurred() check

        v_result = hop.llops.gencapicall(fnname, unwrapped_args_v,
                                         resulttype = RESTYPE,
                                         **kwds)
        # XXX hack! hack! temporary! I promize!
        FUNCTYPE = lltype.FuncType(ARGTYPES, RESTYPE)
        last_op = hop.llops[-1]
        assert last_op.opname == 'direct_call'
        last_op.args[0].concretetype = lltype.Ptr(FUNCTYPE)
        last_op.args[0].value._set_TYPE(last_op.args[0].concretetype)
        last_op.args[0].value._set_T(FUNCTYPE)
        last_op.args[0].value._obj._TYPE = FUNCTYPE

        if RESTYPE is lltype.Void:
            return None
        else:
            return r_res.return_value(hop.llops, v_result)
