from pypy.annotation.model import SomeCTypesObject
from pypy.annotation import model as annmodel
from pypy.rpython.error import TyperError
from pypy.rpython.rctypes.implementation import CTypesEntry
from pypy.rpython.lltypesystem import lltype

import ctypes


CFuncPtrType = type(ctypes.CFUNCTYPE(None))


class CallEntry(CTypesEntry):
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

##    def object_seen(self, bookkeeper):
##        "Called when the annotator sees this ctypes function object."
##        # if the function is a Python callback, emulate a call to it
##        # so that the callback is properly annotated
##        if hasattr(self.instance, 'callback'):
##            callback = self.instance.callback
##            argtypes = self.instance.argtypes
##            restype  = self.instance.restype
##            s_callback = bookkeeper.immutablevalue(callback)
##            # the input arg annotations, which are automatically unwrapped
##            args_s = [bookkeeper.valueoftype(ctype).return_annotation()
##                      for ctype in argtypes]
##            uniquekey = (callback, argtypes, restype)
##            s_res = bookkeeper.emulate_pbc_call(uniquekey, s_callback, args_s)
##            # check the result type
##            if restype is None:
##                s_expected = annmodel.s_None
##            else:
##                s_expected = bookkeeper.valueoftype(restype)
##            # can also return the unwrapped version of the ctype,
##            # e.g. an int instead of a c_int
##            s_orelse = s_expected.return_annotation()
##            assert s_expected.contains(s_res) or s_orelse.contains(s_res), (
##                "%r should return a %s but returned %s" % (callback,
##                                                           restype,
##                                                           s_res))

    def specialize_call(self, hop):
        from pypy.rpython.rctypes.rmodel import CTypesValueRepr
        cfuncptr = self.instance
        fnname = cfuncptr.__name__

        def repr_for_ctype(ctype):
            s = SomeCTypesObject(ctype, SomeCTypesObject.MEMORYALIAS)
            r = hop.rtyper.getrepr(s)
            r.setup()
            return r

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
                        r_arg = repr_for_ctype(ctypes.c_long)
                    elif (isinstance(s_arg, annmodel.SomeString)
                          or s_arg == annmodel.s_None):
                        r_arg = repr_for_ctype(ctypes.c_char_p)
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
            r_res.setup()
            RESTYPE = r_res.ll_type
        else:
            RESTYPE = lltype.Void

        kwds = {}
        if hasattr(cfuncptr, 'llinterp_friendly_version'):
            kwds['_callable'] = cfuncptr.llinterp_friendly_version
        suppress_pyerr_occurred = False
        if (cfuncptr._flags_ & ctypes._FUNCFLAG_PYTHONAPI) == 0:
            suppress_pyerr_occurred = True
        if hasattr(cfuncptr, '_rctypes_pyerrchecker_'):
            suppress_pyerr_occurred = True
        if suppress_pyerr_occurred:
            kwds['includes'] = getattr(cfuncptr, 'includes', ())
            kwds['libraries'] = getattr(cfuncptr, 'libraries', ())
        #else:
        #   no 'includes': hack to trigger in GenC a PyErr_Occurred() check

        hop.exception_cannot_occur()
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

        if getattr(cfuncptr, '_rctypes_pyerrchecker_', None):
            # special extension to support the CPyObjSpace
            # XXX hackish: someone else -- like the annotator policy --
            # must ensure that this extra function has been annotated
            from pypy.translator.translator import graphof
            func = cfuncptr._rctypes_pyerrchecker_
            graph = graphof(hop.rtyper.annotator.translator, func)
            hop.llops.record_extra_call(graph)
            # build the 'direct_call' operation
            f = hop.rtyper.getcallable(graph)
            c = hop.inputconst(lltype.typeOf(f), f)
            hop.genop('direct_call', [c])

        if RESTYPE is lltype.Void:
            return None
        else:
            return r_res.return_value(hop.llops, v_result)
