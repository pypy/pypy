#!/bin/env python
# -*- coding: LATIN-1 -*-

#*************************************************************

def initclassobj(space):
  """NOT_RPYTHON"""

##SECTION##
## filename    'lib/_classobj.py'
## function    '_coerce'
## firstlineno 11
##SECTION##
  def _coerce(space, __args__):
    funcname = "_coerce"
    signature = ['left', 'right'], None, None
    defaults_w = []
    w_left, w_right = __args__.parse(funcname, signature, defaults_w)
    return fastf__coerce(space, w_left, w_right)

  f__coerce = _coerce

  def _coerce(space, w_left, w_right):
    goto = 1 # startblock
    while True:

        if goto == 1:
            try:
                w_0 = space.coerce(w_left, w_right)
                w_1 = w_0
                goto = 5
            except gOperationError, e:
                e.normalize_exception(space)
                if space.is_true(space.issubtype(e.w_type, space.w_Exception)):
                    w_2, w_3 = e.w_type, e.w_value
                    goto = 2
                else:raise # unhandled case, should not happen

        if goto == 2:
            w_4 = space.is_(w_2, space.w_TypeError)
            v0 = space.is_true(w_4)
            if v0 == True:
                w_1 = space.w_None
                goto = 5
            else:
                assert v0 == False
                w_5, w_6 = w_2, w_3
                goto = 3

        if goto == 3:
            w_7 = space.issubtype(w_5, space.w_TypeError)
            v1 = space.is_true(w_7)
            if v1 == True:
                w_1 = space.w_None
                goto = 5
            else:
                assert v1 == False
                w_etype, w_evalue = w_5, w_6
                goto = 4

        if goto == 4:
            raise gOperationError(w_etype, w_evalue)

        if goto == 5:
            return w_1

  fastf__coerce = _coerce

##SECTION##
## filename    'lib/_classobj.py'
## function    'uid'
## firstlineno 22
##SECTION##
# global declarations
# global object gi_0
# global object glong_0x7fffffffL
# global object gi_2

  def uid(space, __args__):
    funcname = "uid"
    signature = ['o'], None, None
    defaults_w = []
    w_o, = __args__.parse(funcname, signature, defaults_w)
    return fastf_uid(space, w_o)

  f_uid = uid

  def uid(space, w_o):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.id(w_o)
            w_1 = space.lt(w_0, gi_0)
            v0 = space.is_true(w_1)
            if v0 == True:
                w_2 = w_0
                goto = 2
            else:
                assert v0 == False
                w_3 = w_0
                goto = 3

        if goto == 2:
            w_4 = space.inplace_add(w_2, glong_0x7fffffffL)
            w_5 = space.inplace_add(w_4, glong_0x7fffffffL)
            w_6 = space.inplace_add(w_5, gi_2)
            w_3 = w_6
            goto = 3

        if goto == 3:
            return w_3

  fastf_uid = uid

##SECTION##
## filename    'lib/_classobj.py'
## function    'type_err'
## firstlineno 39
##SECTION##
# global declaration
# global object gs_argument__s_must_be__s__not__s

  def type_err(space, __args__):
    funcname = "type_err"
    signature = ['arg', 'expected', 'v'], None, None
    defaults_w = []
    w_arg, w_expected, w_v = __args__.parse(funcname, signature, defaults_w)
    return fastf_type_err(space, w_arg, w_expected, w_v)

  f_type_err = type_err

  def type_err(space, w_arg, w_expected, w_v):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.type(w_v)
            w_1 = space.getattr(w_0, gs___name__)
            w_2 = space.newtuple([w_arg, w_expected, w_1])
            w_3 = space.mod(gs_argument__s_must_be__s__not__s, w_2)
            w_4 = space.call_function(space.w_TypeError, w_3)
            w_5 = w_4
            goto = 2

        if goto == 2:
            return w_5

  fastf_type_err = type_err

##SECTION##
## filename    'lib/_classobj.py'
## function    'set_name'
## firstlineno 42
##SECTION##
# global declarations
# global object gs___name___must_be_a_string_object
# global object gdescriptor_classobj__name

  def set_name(space, __args__):
    funcname = "set_name"
    signature = ['cls', 'name'], None, None
    defaults_w = []
    w_cls, w_name = __args__.parse(funcname, signature, defaults_w)
    return fastf_set_name(space, w_cls, w_name)

  f_set_name = set_name

  def set_name(space, w_cls, w_name):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.isinstance(w_name, space.w_str)
            v0 = space.is_true(w_0)
            if v0 == True:
                w_cls_1, w_name_1 = w_cls, w_name
                goto = 3
            else:
                assert v0 == False
                goto = 2

        if goto == 2:
            w_1 = space.call_function(space.w_TypeError, gs___name___must_be_a_string_object)
            w_2 = space.type(w_1)
            w_etype, w_evalue = w_2, w_1
            goto = 4

        if goto == 3:
            w_3 = space.getattr(gdescriptor_classobj__name, gs___set__)
            w_4 = space.call_function(w_3, w_cls_1, w_name_1)
            w_5 = space.w_None
            goto = 5

        if goto == 4:
            raise gOperationError(w_etype, w_evalue)

        if goto == 5:
            return w_5

  fastf_set_name = set_name

##SECTION##
## filename    'lib/_classobj.py'
## function    'set_bases'
## firstlineno 47
##SECTION##
# global declarations
# global object gs___bases___must_be_a_tuple_object
# global object gcls_StopIteration
# global object gs___bases___items_must_be_classes
# global object gdescriptor_classobj__bases
# global object gs___set__

  def set_bases(space, __args__):
    funcname = "set_bases"
    signature = ['cls', 'bases'], None, None
    defaults_w = []
    w_cls, w_bases = __args__.parse(funcname, signature, defaults_w)
    return fastf_set_bases(space, w_cls, w_bases)

  f_set_bases = set_bases

  def set_bases(space, w_cls, w_bases):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.isinstance(w_bases, space.w_tuple)
            v0 = space.is_true(w_0)
            if v0 == True:
                w_cls_1, w_bases_1 = w_cls, w_bases
                goto = 3
            else:
                assert v0 == False
                goto = 2

        if goto == 2:
            w_1 = space.call_function(space.w_TypeError, gs___bases___must_be_a_tuple_object)
            w_2 = space.type(w_1)
            w_etype, w_evalue = w_2, w_1
            goto = 8

        if goto == 3:
            w_3 = space.iter(w_bases_1)
            w_cls_2, w_bases_2, w_4 = w_cls_1, w_bases_1, w_3
            goto = 4

        if goto == 4:
            try:
                w_5 = space.next(w_4)
                w_cls_3, w_bases_3, w_6, w_7 = w_cls_2, w_bases_2, w_4, w_5
                goto = 5
            except gOperationError, e:
                e.normalize_exception(space)
                if space.is_true(space.issubtype(e.w_type, space.w_StopIteration)):
                    w_cls_4, w_bases_4 = w_cls_2, w_bases_2
                    goto = 7
                else:raise # unhandled case, should not happen

        if goto == 5:
            w_8 = space.isinstance(w_7, gcls_classobj)
            v1 = space.is_true(w_8)
            if v1 == True:
                w_cls_2, w_bases_2, w_4 = w_cls_3, w_bases_3, w_6
                goto = 4
                continue
            else:
                assert v1 == False
                goto = 6

        if goto == 6:
            w_9 = space.call_function(space.w_TypeError, gs___bases___items_must_be_classes)
            w_10 = space.type(w_9)
            w_etype, w_evalue = w_10, w_9
            goto = 8

        if goto == 7:
            w_11 = space.getattr(gdescriptor_classobj__bases, gs___set__)
            w_12 = space.call_function(w_11, w_cls_4, w_bases_4)
            w_13 = space.w_None
            goto = 9

        if goto == 8:
            raise gOperationError(w_etype, w_evalue)

        if goto == 9:
            return w_13

  fastf_set_bases = set_bases

##SECTION##
## filename    'lib/_classobj.py'
## function    'set_dict'
## firstlineno 55
##SECTION##
# global declarations
# global object gcls_TypeError
# global object gs___dict___must_be_a_dictionary_ob

  def set_dict(space, __args__):
    funcname = "set_dict"
    signature = ['cls', 'dic'], None, None
    defaults_w = []
    w_cls, w_dic = __args__.parse(funcname, signature, defaults_w)
    return fastf_set_dict(space, w_cls, w_dic)

  f_set_dict = set_dict

  def set_dict(space, w_cls, w_dic):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.isinstance(w_dic, space.w_dict)
            v0 = space.is_true(w_0)
            if v0 == True:
                w_1, w_2 = w_cls, w_dic
                goto = 3
            else:
                assert v0 == False
                goto = 2

        if goto == 2:
            w_3 = space.call_function(space.w_TypeError, gs___dict___must_be_a_dictionary_ob)
            w_4 = space.type(w_3)
            w_etype, w_evalue = w_4, w_3
            goto = 4

        if goto == 3:
            w_5 = space.call_function(gdescriptor_object___setattr__, w_1, gs___dict__, w_2)
            w_6 = space.w_None
            goto = 5

        if goto == 4:
            raise gOperationError(w_etype, w_evalue)

        if goto == 5:
            return w_6

  fastf_set_dict = set_dict

##SECTION##
## filename    'lib/_classobj.py'
## function    'retrieve'
## firstlineno 60
##SECTION##
# global declarations
# global object gdescriptor_object___getattribute__
# global object gcls_KeyError

  def retrieve(space, __args__):
    funcname = "retrieve"
    signature = ['obj', 'attr'], None, None
    defaults_w = []
    w_obj, w_attr = __args__.parse(funcname, signature, defaults_w)
    return fastf_retrieve(space, w_obj, w_attr)

  f_retrieve = retrieve

  def retrieve(space, w_obj, w_attr):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.call_function(gdescriptor_object___getattribute__, w_obj, gs___dict__)
            try:
                w_1 = space.getitem(w_0, w_attr)
                w_2 = w_1
                goto = 7
            except gOperationError, e:
                e.normalize_exception(space)
                if space.is_true(space.issubtype(e.w_type, space.w_KeyError)):
                    w_3 = w_attr
                    goto = 3
                else:raise # unhandled case, should not happen

        if goto == 2:
            w_4 = space.call_function(space.w_AttributeError, )
            w_5 = space.type(w_4)
            w_etype, w_evalue = w_5, w_4
            goto = 6

        if goto == 3:
            w_6 = space.is_(w_3, space.w_None)
            v0 = space.is_true(w_6)
            if v0 == True:
                goto = 2
                continue
            else:
                assert v0 == False
                w_7 = w_3
                goto = 4

        if goto == 4:
            w_8 = space.type(w_7)
            w_9 = space.issubtype(w_8, space.w_AttributeError)
            v1 = space.is_true(w_9)
            if v1 == True:
                w_etype, w_evalue = w_8, w_7
                goto = 6
            else:
                assert v1 == False
                w_10 = w_7
                goto = 5

        if goto == 5:
            w_11 = space.call_function(space.w_AttributeError, w_10)
            w_12 = space.type(w_11)
            w_etype, w_evalue = w_12, w_11
            goto = 6

        if goto == 6:
            raise gOperationError(w_etype, w_evalue)

        if goto == 7:
            return w_2

  fastf_retrieve = retrieve

##SECTION##
## filename    'lib/_classobj.py'
## function    'lookup'
## firstlineno 67
##SECTION##
# global declaration
# global object g2tuple_1

  def lookup(space, __args__):
    funcname = "lookup"
    signature = ['cls', 'attr'], None, None
    defaults_w = []
    w_cls, w_attr = __args__.parse(funcname, signature, defaults_w)
    return fastf_lookup(space, w_cls, w_attr)

  f_lookup = lookup

  def lookup(space, w_cls, w_attr):
    goto = 1 # startblock
    while True:

        if goto == 1:
            try:
                w_0 = fastf_retrieve(space, w_cls, w_attr)
                w_1, w_2 = w_0, w_cls
                goto = 2
            except gOperationError, e:
                e.normalize_exception(space)
                if space.is_true(space.issubtype(e.w_type, space.w_Exception)):
                    w_cls_1, w_attr_1, w_3, w_4 = w_cls, w_attr, e.w_type, e.w_value
                    goto = 3
                else:raise # unhandled case, should not happen

        if goto == 2:
            w_5 = space.newtuple([w_1, w_2])
            w_6 = w_5
            goto = 11

        if goto == 3:
            w_7 = space.is_(w_3, space.w_AttributeError)
            v0 = space.is_true(w_7)
            if v0 == True:
                w_cls_2, w_attr_2 = w_cls_1, w_attr_1
                goto = 5
            else:
                assert v0 == False
                w_cls_3, w_attr_3, w_8, w_9 = w_cls_1, w_attr_1, w_3, w_4
                goto = 4

        if goto == 4:
            w_10 = space.issubtype(w_8, space.w_AttributeError)
            v1 = space.is_true(w_10)
            if v1 == True:
                w_cls_2, w_attr_2 = w_cls_3, w_attr_3
                goto = 5
            else:
                assert v1 == False
                w_etype, w_evalue = w_8, w_9
                goto = 10

        if goto == 5:
            w_11 = space.getattr(gdescriptor_classobj__bases, gs___get__)
            w_12 = space.call_function(w_11, w_cls_2)
            w_13 = space.iter(w_12)
            w_attr_4, w_14 = w_attr_2, w_13
            goto = 6

        if goto == 6:
            try:
                w_15 = space.next(w_14)
                w_attr_5, w_16, w_17 = w_attr_4, w_14, w_15
                goto = 7
            except gOperationError, e:
                e.normalize_exception(space)
                if space.is_true(space.issubtype(e.w_type, space.w_StopIteration)):
                    w_6 = g2tuple_1
                    goto = 11
                else:raise # unhandled case, should not happen

        if goto == 7:
            w_18 = fastf_lookup(space, w_17, w_attr_5)
            w_19 = space.len(w_18)
            w_20 = space.eq(w_19, gi_2)
            v2 = space.is_true(w_20)
            if v2 == True:
                w_attr_6, w_21, w_22 = w_attr_5, w_16, w_18
                goto = 8
            else:
                assert v2 == False
                w_etype, w_evalue = space.w_ValueError, space.w_None
                goto = 10

        if goto == 8:
            w_23 = space.getitem(w_22, gi_0)
            w_24 = space.getitem(w_22, gi_1)
            v3 = space.is_true(w_24)
            if v3 == True:
                w_25, w_26 = w_23, w_24
                goto = 9
            else:
                assert v3 == False
                w_attr_4, w_14 = w_attr_6, w_21
                goto = 6
                continue

        if goto == 9:
            w_27 = space.newtuple([w_25, w_26])
            w_6 = w_27
            goto = 11

        if goto == 10:
            raise gOperationError(w_etype, w_evalue)

        if goto == 11:
            return w_6

  fastf_lookup = lookup

##SECTION##
## filename    'lib/_classobj.py'
## function    'get_class_module'
## firstlineno 79
##SECTION##
# global declarations
# global object gfunc_retrieve
# global object gcls_Exception
# global object gcls_AttributeError

  def get_class_module(space, __args__):
    funcname = "get_class_module"
    signature = ['cls'], None, None
    defaults_w = []
    w_cls, = __args__.parse(funcname, signature, defaults_w)
    return fastf_get_class_module(space, w_cls)

  f_get_class_module = get_class_module

  def get_class_module(space, w_cls):
    goto = 1 # startblock
    while True:

        if goto == 1:
            try:
                w_0 = fastf_retrieve(space, w_cls, gs___module__)
                w_mod = w_0
                goto = 3
            except gOperationError, e:
                e.normalize_exception(space)
                if space.is_true(space.issubtype(e.w_type, space.w_Exception)):
                    w_1, w_2 = e.w_type, e.w_value
                    goto = 2
                else:raise # unhandled case, should not happen

        if goto == 2:
            w_3 = space.is_(w_1, space.w_AttributeError)
            v0 = space.is_true(w_3)
            if v0 == True:
                w_mod = space.w_None
                goto = 3
            else:
                assert v0 == False
                w_4, w_5 = w_1, w_2
                goto = 4

        if goto == 3:
            w_6 = space.isinstance(w_mod, space.w_str)
            v1 = space.is_true(w_6)
            if v1 == True:
                w_7 = w_mod
                goto = 6
            else:
                assert v1 == False
                w_7 = gs__
                goto = 6

        if goto == 4:
            w_8 = space.issubtype(w_4, space.w_AttributeError)
            v2 = space.is_true(w_8)
            if v2 == True:
                w_mod = space.w_None
                goto = 3
                continue
            else:
                assert v2 == False
                w_etype, w_evalue = w_4, w_5
                goto = 5

        if goto == 5:
            raise gOperationError(w_etype, w_evalue)

        if goto == 6:
            return w_7

  fastf_get_class_module = get_class_module

##SECTION##
## filename    'lib/_classobj.py'
## function    'mro_lookup'
## firstlineno 88
##SECTION##
# global declaration
# global object gs___mro__

  def mro_lookup(space, __args__):
    funcname = "mro_lookup"
    signature = ['v', 'name'], None, None
    defaults_w = []
    w_v, w_name = __args__.parse(funcname, signature, defaults_w)
    return fastf_mro_lookup(space, w_v, w_name)

  f_mro_lookup = mro_lookup

  def mro_lookup(space, w_v, w_name):
    goto = 1 # startblock
    while True:

        if goto == 1:
            try:
                w_0 = space.type(w_v)
                w_name_1, w_1 = w_name, w_0
                goto = 2
            except gOperationError, e:
                e.normalize_exception(space)
                if space.is_true(space.issubtype(e.w_type, space.w_Exception)):
                    w_2, w_3 = e.w_type, e.w_value
                    goto = 3
                else:raise # unhandled case, should not happen

        if goto == 2:
            try:
                w_4 = space.getattr(w_1, gs___mro__)
                w_name_2, w_5 = w_name_1, w_4
                goto = 5
            except gOperationError, e:
                e.normalize_exception(space)
                if space.is_true(space.issubtype(e.w_type, space.w_AttributeError)):
                    w_6 = space.w_None
                    goto = 10
                else:raise # unhandled case, should not happen

        if goto == 3:
            w_7 = space.is_(w_2, space.w_AttributeError)
            v0 = space.is_true(w_7)
            if v0 == True:
                w_6 = space.w_None
                goto = 10
            else:
                assert v0 == False
                w_8, w_9 = w_2, w_3
                goto = 4

        if goto == 4:
            w_10 = space.issubtype(w_8, space.w_AttributeError)
            v1 = space.is_true(w_10)
            if v1 == True:
                w_6 = space.w_None
                goto = 10
            else:
                assert v1 == False
                w_etype, w_evalue = w_8, w_9
                goto = 9

        if goto == 5:
            w_11 = space.iter(w_5)
            w_name_3, w_12 = w_name_2, w_11
            goto = 6

        if goto == 6:
            try:
                w_13 = space.next(w_12)
                w_name_4, w_x, w_14 = w_name_3, w_13, w_12
                goto = 7
            except gOperationError, e:
                e.normalize_exception(space)
                if space.is_true(space.issubtype(e.w_type, space.w_StopIteration)):
                    w_6 = space.w_None
                    goto = 10
                else:raise # unhandled case, should not happen

        if goto == 7:
            w_15 = space.getattr(w_x, gs___dict__)
            w_16 = space.contains(w_15, w_name_4)
            v2 = space.is_true(w_16)
            if v2 == True:
                w_name_5, w_17 = w_name_4, w_x
                goto = 8
            else:
                assert v2 == False
                w_name_3, w_12 = w_name_4, w_14
                goto = 6
                continue

        if goto == 8:
            w_18 = space.getattr(w_17, gs___dict__)
            w_19 = space.getitem(w_18, w_name_5)
            w_6 = w_19
            goto = 10

        if goto == 9:
            raise gOperationError(w_etype, w_evalue)

        if goto == 10:
            return w_6

  fastf_mro_lookup = mro_lookup

##SECTION##
## filename    'lib/_classobj.py'
## function    '__new__'
## firstlineno 116
##SECTION##
# global declarations
# global object gfunc_type_err
# global object gs_name
# global object gs_string
# global object g0tuple
# global object gs_bases
# global object gs_tuple
# global object gs_dict
# global object gs___doc__
# global object gs__getframe
# global object gs_f_globals
# global object gs_get
# global object gs_OLD_STYLE_CLASSES_IMPL
# global object g_object
# global object gs_callable
# global object gs_base_must_be_class

  def __new__(space, __args__):
    funcname = "__new__"
    signature = ['subtype', 'name', 'bases', 'dic'], None, None
    defaults_w = []
    w_subtype, w_name, w_bases, w_dic = __args__.parse(funcname, signature, defaults_w)
    return fastf___new__(space, w_subtype, w_name, w_bases, w_dic)

  f___new__ = __new__

  def __new__(space, w_subtype, w_name, w_bases, w_dic):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.isinstance(w_name, space.w_str)
            v0 = space.is_true(w_0)
            if v0 == True:
                w_name_1, w_bases_1, w_dic_1 = w_name, w_bases, w_dic
                goto = 3
            else:
                assert v0 == False
                w_1 = w_name
                goto = 2

        if goto == 2:
            w_2 = fastf_type_err(space, gs_name, gs_string, w_1)
            w_3 = space.type(w_2)
            w_4 = space.issubtype(w_3, space.w_type)
            v1 = space.is_true(w_4)
            if v1 == True:
                w_5 = w_2
                goto = 6
            else:
                assert v1 == False
                w_6 = w_2
                goto = 5

        if goto == 3:
            w_7 = space.is_(w_bases_1, space.w_None)
            v2 = space.is_true(w_7)
            if v2 == True:
                w_name_2, w_bases_2, w_dic_2 = w_name_1, g0tuple, w_dic_1
                goto = 4
            else:
                assert v2 == False
                w_name_2, w_bases_2, w_dic_2 = w_name_1, w_bases_1, w_dic_1
                goto = 4

        if goto == 4:
            w_8 = space.isinstance(w_bases_2, space.w_tuple)
            v3 = space.is_true(w_8)
            if v3 == True:
                w_name_3, w_bases_3, w_dic_3 = w_name_2, w_bases_2, w_dic_2
                goto = 8
            else:
                assert v3 == False
                w_9 = w_bases_2
                goto = 7

        if goto == 5:
            w_10 = space.type(w_6)
            w_etype, w_evalue = w_10, w_6
            goto = 32

        if goto == 6:
            w_11 = space.call_function(w_5, )
            w_12 = space.type(w_11)
            w_etype, w_evalue = w_12, w_11
            goto = 32

        if goto == 7:
            w_13 = fastf_type_err(space, gs_bases, gs_tuple, w_9)
            w_14 = space.type(w_13)
            w_15 = space.issubtype(w_14, space.w_type)
            v4 = space.is_true(w_15)
            if v4 == True:
                w_16 = w_13
                goto = 10
            else:
                assert v4 == False
                w_17 = w_13
                goto = 9

        if goto == 8:
            w_18 = space.isinstance(w_dic_3, space.w_dict)
            v5 = space.is_true(w_18)
            if v5 == True:
                w_name_4, w_bases_4, w_dic_4 = w_name_3, w_bases_3, w_dic_3
                goto = 12
            else:
                assert v5 == False
                w_19 = w_dic_3
                goto = 11

        if goto == 9:
            w_20 = space.type(w_17)
            w_etype, w_evalue = w_20, w_17
            goto = 32

        if goto == 10:
            w_21 = space.call_function(w_16, )
            w_22 = space.type(w_21)
            w_etype, w_evalue = w_22, w_21
            goto = 32

        if goto == 11:
            w_23 = fastf_type_err(space, gs_dict, gs_dict, w_19)
            w_24 = space.type(w_23)
            w_25 = space.issubtype(w_24, space.w_type)
            v6 = space.is_true(w_25)
            if v6 == True:
                w_26 = w_23
                goto = 16
            else:
                assert v6 == False
                w_27 = w_23
                goto = 15

        if goto == 12:
            try:
                w_28 = space.getitem(w_dic_4, gs___doc__)
                w_name_5, w_bases_5, w_dic_5 = w_name_4, w_bases_4, w_dic_4
                goto = 14
            except gOperationError, e:
                e.normalize_exception(space)
                if space.is_true(space.issubtype(e.w_type, space.w_KeyError)):
                    w_name_6, w_bases_6, w_dic_6 = w_name_4, w_bases_4, w_dic_4
                    goto = 13
                else:raise # unhandled case, should not happen

        if goto == 13:
            w_29 = space.setitem(w_dic_6, gs___doc__, space.w_None)
            w_name_5, w_bases_5, w_dic_5 = w_name_6, w_bases_6, w_dic_6
            goto = 14

        if goto == 14:
            try:
                w_30 = space.getitem(w_dic_5, gs___module__)
                w_name_7, w_bases_7, w_dic_7 = w_name_5, w_bases_5, w_dic_5
                goto = 25
            except gOperationError, e:
                e.normalize_exception(space)
                if space.is_true(space.issubtype(e.w_type, space.w_KeyError)):
                    (w_name_8, w_bases_8, w_dic_8, w_i) = (w_name_5, w_bases_5,
                     w_dic_5, gi_0)
                    goto = 17
                else:raise # unhandled case, should not happen

        if goto == 15:
            w_31 = space.type(w_27)
            w_etype, w_evalue = w_31, w_27
            goto = 32

        if goto == 16:
            w_32 = space.call_function(w_26, )
            w_33 = space.type(w_32)
            w_etype, w_evalue = w_33, w_32
            goto = 32

        if goto == 17:
            try:
                w_34 = space.call_function((space.sys.get(space.str_w(gs__getframe))), w_i)
                (w_name_9, w_bases_9, w_dic_9, w_i_1, w_35) = (w_name_8,
                 w_bases_8, w_dic_8, w_i, w_34)
                goto = 18
            except gOperationError, e:
                e.normalize_exception(space)
                if space.is_true(space.issubtype(e.w_type, space.w_Exception)):
                    (w_name_10, w_bases_10, w_dic_10, w_36, w_37) = (w_name_8,
                     w_bases_8, w_dic_8, e.w_type, e.w_value)
                    goto = 21
                else:raise # unhandled case, should not happen

        if goto == 18:
            w_38 = space.getattr(w_35, gs_f_globals)
            w_39 = space.getattr(w_38, gs_get)
            try:
                w_40 = space.call_function(w_39, gs_OLD_STYLE_CLASSES_IMPL, space.w_None)
                (w_name_11, w_bases_11, w_dic_11, w_g, w_i_2, w_41) = (w_name_9,
                 w_bases_9, w_dic_9, w_38, w_i_1, w_40)
                goto = 19
            except gOperationError, e:
                e.normalize_exception(space)
                if space.is_true(space.issubtype(e.w_type, space.w_Exception)):
                    (w_name_10, w_bases_10, w_dic_10, w_36, w_37) = (w_name_9,
                     w_bases_9, w_dic_9, e.w_type, e.w_value)
                    goto = 21
                else:raise # unhandled case, should not happen

        if goto == 19:
            w_42 = space.is_(w_41, g_object)
            v7 = space.is_true(w_42)
            if v7 == True:
                (w_name_12, w_bases_12, w_dic_12, w_43) = (w_name_11, w_bases_11,
                 w_dic_11, w_i_2)
                goto = 20
            else:
                assert v7 == False
                (w_name_13, w_bases_13, w_dic_13, w_44) = (w_name_11, w_bases_11,
                 w_dic_11, w_g)
                goto = 23

        if goto == 20:
            w_45 = space.inplace_add(w_43, gi_1)
            (w_name_8, w_bases_8, w_dic_8, w_i) = (w_name_12, w_bases_12,
             w_dic_12, w_45)
            goto = 17
            continue

        if goto == 21:
            w_46 = space.is_(w_36, space.w_ValueError)
            v8 = space.is_true(w_46)
            if v8 == True:
                w_name_7, w_bases_7, w_dic_7 = w_name_10, w_bases_10, w_dic_10
                goto = 25
            else:
                assert v8 == False
                (w_name_14, w_bases_14, w_dic_14, w_47, w_48) = (w_name_10,
                 w_bases_10, w_dic_10, w_36, w_37)
                goto = 22

        if goto == 22:
            w_49 = space.issubtype(w_47, space.w_ValueError)
            v9 = space.is_true(w_49)
            if v9 == True:
                w_name_7, w_bases_7, w_dic_7 = w_name_14, w_bases_14, w_dic_14
                goto = 25
            else:
                assert v9 == False
                w_etype, w_evalue = w_47, w_48
                goto = 32

        if goto == 23:
            w_50 = space.getattr(w_44, gs_get)
            w_51 = space.call_function(w_50, gs___name__, space.w_None)
            w_52 = space.is_(w_51, space.w_None)
            v10 = space.is_true(w_52)
            if v10 == True:
                w_name_7, w_bases_7, w_dic_7 = w_name_13, w_bases_13, w_dic_13
                goto = 25
            else:
                assert v10 == False
                (w_name_15, w_bases_15, w_dic_15, w_53) = (w_name_13, w_bases_13,
                 w_dic_13, w_51)
                goto = 24

        if goto == 24:
            w_54 = space.setitem(w_dic_15, gs___module__, w_53)
            w_name_7, w_bases_7, w_dic_7 = w_name_15, w_bases_15, w_dic_15
            goto = 25

        if goto == 25:
            w_55 = space.iter(w_bases_7)
            (w_name_16, w_bases_16, w_dic_16, w_56) = (w_name_7, w_bases_7,
             w_dic_7, w_55)
            goto = 26

        if goto == 26:
            try:
                w_57 = space.next(w_56)
                (w_name_17, w_bases_17, w_dic_17, w_b, w_58) = (w_name_16,
                 w_bases_16, w_dic_16, w_57, w_56)
                goto = 27
            except gOperationError, e:
                e.normalize_exception(space)
                if space.is_true(space.issubtype(e.w_type, space.w_StopIteration)):
                    w_name_18, w_bases_18, w_dic_18 = w_name_16, w_bases_16, w_dic_16
                    goto = 31
                else:raise # unhandled case, should not happen

        if goto == 27:
            w_59 = space.isinstance(w_b, gcls_classobj)
            v11 = space.is_true(w_59)
            if v11 == True:
                (w_name_16, w_bases_16, w_dic_16, w_56) = (w_name_17, w_bases_17,
                 w_dic_17, w_58)
                goto = 26
                continue
            else:
                assert v11 == False
                (w_name_19, w_bases_19, w_dic_19, w_b_1) = (w_name_17, w_bases_17,
                 w_dic_17, w_b)
                goto = 28

        if goto == 28:
            w_60 = space.type(w_b_1)
            w_61 = space.call_function((space.builtin.get(space.str_w(gs_callable))), w_60)
            v12 = space.is_true(w_61)
            if v12 == True:
                (w_name_20, w_bases_20, w_dic_20, w_62) = (w_name_19, w_bases_19,
                 w_dic_19, w_b_1)
                goto = 29
            else:
                assert v12 == False
                goto = 30

        if goto == 29:
            w_63 = space.type(w_62)
            w_64 = space.call_function(w_63, w_name_20, w_bases_20, w_dic_20)
            w_65 = w_64
            goto = 33

        if goto == 30:
            w_66 = space.call_function(space.w_TypeError, gs_base_must_be_class)
            w_67 = space.type(w_66)
            w_etype, w_evalue = w_67, w_66
            goto = 32

        if goto == 31:
            w_68 = space.call_function(gbltinmethod___new__, gcls_classobj)
            w_69 = space.call_function(gdescriptor_object___setattr__, w_68, gs___dict__, w_dic_18)
            w_70 = space.getattr(gdescriptor_classobj__name, gs___set__)
            w_71 = space.call_function(w_70, w_68, w_name_18)
            w_72 = space.getattr(gdescriptor_classobj__bases, gs___set__)
            w_73 = space.call_function(w_72, w_68, w_bases_18)
            w_65 = w_68
            goto = 33

        if goto == 32:
            raise gOperationError(w_etype, w_evalue)

        if goto == 33:
            return w_65

  fastf___new__ = __new__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__setattr__'
## firstlineno 166
##SECTION##
# global declarations
# global object gfunc_set_name
# global object gs___bases__
# global object gfunc_set_bases
# global object gfunc_set_dict
# global object gdescriptor_object___setattr__

  def __setattr__(space, __args__):
    funcname = "__setattr__"
    signature = ['self', 'attr', 'value'], None, None
    defaults_w = []
    w_self, w_attr, w_value = __args__.parse(funcname, signature, defaults_w)
    return fastf_classobj___setattr__(space, w_self, w_attr, w_value)

  f_classobj___setattr__ = __setattr__

  def __setattr__(space, w_self, w_attr, w_value):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.eq(w_attr, gs___name__)
            v0 = space.is_true(w_0)
            if v0 == True:
                w_1, w_2 = w_self, w_value
                goto = 2
            else:
                assert v0 == False
                w_self_1, w_attr_1, w_value_1 = w_self, w_attr, w_value
                goto = 3

        if goto == 2:
            w_3 = fastf_set_name(space, w_1, w_2)
            w_4 = space.w_None
            goto = 8

        if goto == 3:
            w_5 = space.eq(w_attr_1, gs___bases__)
            v1 = space.is_true(w_5)
            if v1 == True:
                w_6, w_7 = w_self_1, w_value_1
                goto = 4
            else:
                assert v1 == False
                w_self_2, w_attr_2, w_value_2 = w_self_1, w_attr_1, w_value_1
                goto = 5

        if goto == 4:
            w_8 = fastf_set_bases(space, w_6, w_7)
            w_4 = space.w_None
            goto = 8

        if goto == 5:
            w_9 = space.eq(w_attr_2, gs___dict__)
            v2 = space.is_true(w_9)
            if v2 == True:
                w_10, w_11 = w_self_2, w_value_2
                goto = 6
            else:
                assert v2 == False
                w_12, w_13, w_14 = w_self_2, w_attr_2, w_value_2
                goto = 7

        if goto == 6:
            w_15 = fastf_set_dict(space, w_10, w_11)
            w_4 = space.w_None
            goto = 8

        if goto == 7:
            w_16 = space.call_function(gdescriptor_object___setattr__, w_12, w_13, w_14)
            w_4 = space.w_None
            goto = 8

        if goto == 8:
            return w_4

  fastf_classobj___setattr__ = __setattr__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__delattr__'
## firstlineno 176
##SECTION##
# global declarations
# global object g3tuple_2
# global object gdescriptor_object___delattr__

  def __delattr__(space, __args__):
    funcname = "__delattr__"
    signature = ['self', 'attr'], None, None
    defaults_w = []
    w_self, w_attr = __args__.parse(funcname, signature, defaults_w)
    return fastf_classobj___delattr__(space, w_self, w_attr)

  f_classobj___delattr__ = __delattr__

  def __delattr__(space, w_self, w_attr):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.contains(g3tuple_2, w_attr)
            v0 = space.is_true(w_0)
            if v0 == True:
                w_1, w_2 = w_self, w_attr
                goto = 2
            else:
                assert v0 == False
                w_3, w_4 = w_self, w_attr
                goto = 3

        if goto == 2:
            w_5 = fastf_classobj___setattr__(space, w_1, w_2, space.w_None)
            w_6 = space.w_None
            goto = 4

        if goto == 3:
            w_7 = space.call_function(gdescriptor_object___delattr__, w_3, w_4)
            w_6 = space.w_None
            goto = 4

        if goto == 4:
            return w_6

  fastf_classobj___delattr__ = __delattr__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__getattribute__'
## firstlineno 183
##SECTION##
# global declarations
# global object gs___get__
# global object gi_1
# global object gfunc_lookup
# global object gcls_ValueError
# global object gs_class__s_has_no_attribute__s
# global object gfunc_mro_lookup

  def __getattribute__(space, __args__):
    funcname = "__getattribute__"
    signature = ['self', 'attr'], None, None
    defaults_w = []
    w_self, w_attr = __args__.parse(funcname, signature, defaults_w)
    return fastf_classobj___getattribute__(space, w_self, w_attr)

  f_classobj___getattribute__ = __getattribute__

  def __getattribute__(space, w_self, w_attr):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.eq(w_attr, gs___dict__)
            v0 = space.is_true(w_0)
            if v0 == True:
                w_1 = w_self
                goto = 2
            else:
                assert v0 == False
                w_self_1, w_attr_1 = w_self, w_attr
                goto = 3

        if goto == 2:
            w_2 = space.call_function(gdescriptor_object___getattribute__, w_1, gs___dict__)
            w_3 = w_2
            goto = 16

        if goto == 3:
            w_4 = space.eq(w_attr_1, gs___name__)
            v1 = space.is_true(w_4)
            if v1 == True:
                w_self_2 = w_self_1
                goto = 4
            else:
                assert v1 == False
                w_self_3, w_attr_2 = w_self_1, w_attr_1
                goto = 5

        if goto == 4:
            w_5 = space.getattr(gdescriptor_classobj__name, gs___get__)
            w_6 = space.call_function(w_5, w_self_2)
            w_3 = w_6
            goto = 16

        if goto == 5:
            w_7 = space.eq(w_attr_2, gs___bases__)
            v2 = space.is_true(w_7)
            if v2 == True:
                w_self_4 = w_self_3
                goto = 6
            else:
                assert v2 == False
                w_self_5, w_attr_3 = w_self_3, w_attr_2
                goto = 8

        if goto == 6:
            w_8 = space.getattr(gdescriptor_classobj__bases, gs___get__)
            w_9 = space.call_function(w_8, w_self_4)
            w_3 = w_9
            goto = 16

        if goto == 7:
            w_10 = space.getitem(w_11, gi_0)
            w_12 = space.getitem(w_11, gi_1)
            v3 = space.is_true(w_12)
            if v3 == True:
                w_self_7, w_v = w_self_6, w_10
                goto = 10
            else:
                assert v3 == False
                w_attr_5, w_13 = w_attr_4, w_self_6
                goto = 9

        if goto == 8:
            w_14 = fastf_lookup(space, w_self_5, w_attr_3)
            w_15 = space.len(w_14)
            w_16 = space.eq(w_15, gi_2)
            v4 = space.is_true(w_16)
            if v4 == True:
                w_self_6, w_attr_4, w_11 = w_self_5, w_attr_3, w_14
                goto = 7
                continue
            else:
                assert v4 == False
                w_etype, w_evalue = space.w_ValueError, space.w_None
                goto = 15

        if goto == 9:
            w_17 = space.getattr(w_13, gs___name__)
            w_18 = space.newtuple([w_17, w_attr_5])
            w_19 = space.mod(gs_class__s_has_no_attribute__s, w_18)
            w_20 = space.is_(w_19, space.w_None)
            v5 = space.is_true(w_20)
            if v5 == True:
                goto = 11
            else:
                assert v5 == False
                w_21 = w_19
                goto = 13

        if goto == 10:
            w_22 = fastf_mro_lookup(space, w_v, gs___get__)
            w_23 = space.is_(w_22, space.w_None)
            v6 = space.is_true(w_23)
            if v6 == True:
                w_3 = w_v
                goto = 16
            else:
                assert v6 == False
                w_24, w_25, w_26 = w_22, w_v, w_self_7
                goto = 12

        if goto == 11:
            w_27 = space.call_function(space.w_AttributeError, )
            w_28 = space.type(w_27)
            w_etype, w_evalue = w_28, w_27
            goto = 15

        if goto == 12:
            w_29 = space.call_function(w_24, w_25, space.w_None, w_26)
            w_3 = w_29
            goto = 16

        if goto == 13:
            w_30 = space.type(w_21)
            w_31 = space.issubtype(w_30, space.w_AttributeError)
            v7 = space.is_true(w_31)
            if v7 == True:
                w_etype, w_evalue = w_30, w_21
                goto = 15
            else:
                assert v7 == False
                w_32 = w_21
                goto = 14

        if goto == 14:
            w_33 = space.call_function(space.w_AttributeError, w_32)
            w_34 = space.type(w_33)
            w_etype, w_evalue = w_34, w_33
            goto = 15

        if goto == 15:
            raise gOperationError(w_etype, w_evalue)

        if goto == 16:
            return w_3

  fastf_classobj___getattribute__ = __getattribute__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__repr__'
## firstlineno 200
##SECTION##
# global declarations
# global object gfunc_uid
# global object gs__class__s__s_at_0x_x_

  def __repr__(space, __args__):
    funcname = "__repr__"
    signature = ['self'], None, None
    defaults_w = []
    w_self, = __args__.parse(funcname, signature, defaults_w)
    return fastf_classobj___repr__(space, w_self)

  f_classobj___repr__ = __repr__

  def __repr__(space, w_self):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = fastf_get_class_module(space, w_self)
            w_1 = space.getattr(w_self, gs___name__)
            w_2 = fastf_uid(space, w_self)
            w_3 = space.newtuple([w_0, w_1, w_2])
            w_4 = space.mod(gs__class__s__s_at_0x_x_, w_3)
            w_5 = w_4
            goto = 2

        if goto == 2:
            return w_5

  fastf_classobj___repr__ = __repr__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__str__'
## firstlineno 204
##SECTION##
# global declarations
# global object gfunc_get_class_module
# global object gs__
# global object gs___name__
# global object gs__s__s

  def __str__(space, __args__):
    funcname = "__str__"
    signature = ['self'], None, None
    defaults_w = []
    w_self, = __args__.parse(funcname, signature, defaults_w)
    return fastf_classobj___str__(space, w_self)

  f_classobj___str__ = __str__

  def __str__(space, w_self):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = fastf_get_class_module(space, w_self)
            w_1 = space.eq(w_0, gs__)
            v0 = space.is_true(w_1)
            if v0 == True:
                w_2 = w_self
                goto = 2
            else:
                assert v0 == False
                w_3, w_4 = w_0, w_self
                goto = 3

        if goto == 2:
            w_5 = space.getattr(w_2, gs___name__)
            w_6 = w_5
            goto = 4

        if goto == 3:
            w_7 = space.getattr(w_4, gs___name__)
            w_8 = space.newtuple([w_3, w_7])
            w_9 = space.mod(gs__s__s, w_8)
            w_6 = w_9
            goto = 4

        if goto == 4:
            return w_6

  fastf_classobj___str__ = __str__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__call__'
## firstlineno 211
##SECTION##
# global declarations
# global object gbltinmethod___new__
# global object gdescriptor_instance__class
# global object gfunc_instance_getattr1
# global object gs___init__
# global object gs___init_____should_return_None

  def __call__(space, __args__):
    funcname = "__call__"
    signature = ['self'], 'args', 'kwds'
    defaults_w = []
    w_self, w_args, w_kwds = __args__.parse(funcname, signature, defaults_w)
    return fastf_classobj___call__(space, w_self, w_args, w_kwds)

  f_classobj___call__ = __call__

  def __call__(space, w_self, w_args, w_kwds):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.call_function(gbltinmethod___new__, gcls_instance)
            w_1 = space.getattr(gdescriptor_instance__class, gs___set__)
            w_2 = space.call_function(w_1, w_0, w_self)
            w_3 = space.call_function(gfunc_instance_getattr1, w_0, gs___init__, space.w_False)
            v0 = space.is_true(w_3)
            if v0 == True:
                w_inst, w_4, w_5, w_6 = w_0, w_3, w_args, w_kwds
                goto = 2
            else:
                assert v0 == False
                w_7 = w_0
                goto = 7

        if goto == 2:
            _args = gateway.Arguments.fromshape(space, (0, (), True, True), [w_5, w_6])
            w_8 = space.call_args(w_4, _args)
            w_9 = space.is_(w_8, space.w_None)
            v1 = space.is_true(w_9)
            if v1 == True:
                w_7 = w_inst
                goto = 7
            else:
                assert v1 == False
                goto = 3

        if goto == 3:
            w_10 = space.call_function(space.w_TypeError, gs___init_____should_return_None)
            w_11 = space.type(w_10)
            w_12 = space.issubtype(w_11, space.w_type)
            v2 = space.is_true(w_12)
            if v2 == True:
                w_13 = w_10
                goto = 5
            else:
                assert v2 == False
                w_14 = w_10
                goto = 4

        if goto == 4:
            w_15 = space.type(w_14)
            w_etype, w_evalue = w_15, w_14
            goto = 6

        if goto == 5:
            w_16 = space.call_function(w_13, )
            w_17 = space.type(w_16)
            w_etype, w_evalue = w_17, w_16
            goto = 6

        if goto == 6:
            raise gOperationError(w_etype, w_evalue)

        if goto == 7:
            return w_7

  fastf_classobj___call__ = __call__

##SECTION##
## filename    'lib/_classobj.py'
## function    'instance_getattr1'
## firstlineno 232
##SECTION##
# global declarations
# global object gs___class__
# global object gs__s_instance_has_no_attribute__s

  def instance_getattr1(space, __args__):
    funcname = "instance_getattr1"
    signature = ['inst', 'name', 'exc'], None, None
    defaults_w = [space.w_True]
    w_inst, w_name, w_exc = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance_getattr1(space, w_inst, w_name, w_exc)

  f_instance_getattr1 = instance_getattr1

  def instance_getattr1(space, w_inst, w_name, w_exc):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.eq(w_name, gs___dict__)
            v0 = space.is_true(w_0)
            if v0 == True:
                w_1, w_2 = w_inst, w_name
                goto = 2
            else:
                assert v0 == False
                w_inst_1, w_name_1, w_exc_1 = w_inst, w_name, w_exc
                goto = 3

        if goto == 2:
            w_3 = space.call_function(gdescriptor_object___getattribute__, w_1, w_2)
            w_4 = w_3
            goto = 18

        if goto == 3:
            w_5 = space.eq(w_name_1, gs___class__)
            v1 = space.is_true(w_5)
            if v1 == True:
                w_inst_2 = w_inst_1
                goto = 4
            else:
                assert v1 == False
                w_inst_3, w_name_2, w_exc_2 = w_inst_1, w_name_1, w_exc_1
                goto = 6

        if goto == 4:
            w_6 = space.getattr(gdescriptor_instance__class, gs___get__)
            w_7 = space.call_function(w_6, w_inst_2)
            w_4 = w_7
            goto = 18

        if goto == 5:
            w_8 = space.issubtype(w_9, space.w_AttributeError)
            v2 = space.is_true(w_8)
            if v2 == True:
                w_inst_5, w_name_4, w_exc_4 = w_inst_4, w_name_3, w_exc_3
                goto = 8
            else:
                assert v2 == False
                w_etype, w_evalue = w_9, w_10
                goto = 17

        if goto == 6:
            try:
                w_11 = fastf_retrieve(space, w_inst_3, w_name_2)
                w_4 = w_11
                goto = 18
            except gOperationError, e:
                e.normalize_exception(space)
                if space.is_true(space.issubtype(e.w_type, space.w_Exception)):
                    (w_inst_6, w_name_5, w_exc_5, w_12, w_13) = (w_inst_3, w_name_2,
                     w_exc_2, e.w_type, e.w_value)
                    goto = 7
                else:raise # unhandled case, should not happen

        if goto == 7:
            w_14 = space.is_(w_12, space.w_AttributeError)
            v3 = space.is_true(w_14)
            if v3 == True:
                w_inst_5, w_name_4, w_exc_4 = w_inst_6, w_name_5, w_exc_5
                goto = 8
            else:
                assert v3 == False
                (w_inst_4, w_name_3, w_exc_3, w_9, w_10) = (w_inst_6, w_name_5,
                 w_exc_5, w_12, w_13)
                goto = 5
                continue

        if goto == 8:
            w_15 = space.getattr(gdescriptor_instance__class, gs___get__)
            w_16 = space.call_function(w_15, w_inst_5)
            w_17 = fastf_lookup(space, w_16, w_name_4)
            w_18 = space.len(w_17)
            w_19 = space.eq(w_18, gi_2)
            v4 = space.is_true(w_19)
            if v4 == True:
                (w_inst_7, w_name_6, w_exc_6, w_cls, w_20) = (w_inst_5, w_name_4,
                 w_exc_4, w_16, w_17)
                goto = 9
            else:
                assert v4 == False
                w_etype, w_evalue = space.w_ValueError, space.w_None
                goto = 17

        if goto == 9:
            w_21 = space.getitem(w_20, gi_0)
            w_22 = space.getitem(w_20, gi_1)
            v5 = space.is_true(w_22)
            if v5 == True:
                w_inst_8, w_v, w_cls_1 = w_inst_7, w_21, w_cls
                goto = 15
            else:
                assert v5 == False
                w_name_7, w_cls_2, w_23 = w_name_6, w_cls, w_exc_6
                goto = 10

        if goto == 10:
            v6 = space.is_true(w_23)
            if v6 == True:
                w_name_8, w_24 = w_name_7, w_cls_2
                goto = 11
            else:
                assert v6 == False
                w_4 = space.w_None
                goto = 18

        if goto == 11:
            w_25 = space.getattr(w_24, gs___name__)
            w_26 = space.newtuple([w_25, w_name_8])
            w_27 = space.mod(gs__s_instance_has_no_attribute__s, w_26)
            w_28 = space.is_(w_27, space.w_None)
            v7 = space.is_true(w_28)
            if v7 == True:
                goto = 12
            else:
                assert v7 == False
                w_29 = w_27
                goto = 13

        if goto == 12:
            w_30 = space.call_function(space.w_AttributeError, )
            w_31 = space.type(w_30)
            w_etype, w_evalue = w_31, w_30
            goto = 17

        if goto == 13:
            w_32 = space.type(w_29)
            w_33 = space.issubtype(w_32, space.w_AttributeError)
            v8 = space.is_true(w_33)
            if v8 == True:
                w_etype, w_evalue = w_32, w_29
                goto = 17
            else:
                assert v8 == False
                w_34 = w_29
                goto = 14

        if goto == 14:
            w_35 = space.call_function(space.w_AttributeError, w_34)
            w_36 = space.type(w_35)
            w_etype, w_evalue = w_36, w_35
            goto = 17

        if goto == 15:
            w_37 = fastf_mro_lookup(space, w_v, gs___get__)
            w_38 = space.is_(w_37, space.w_None)
            v9 = space.is_true(w_38)
            if v9 == True:
                w_4 = w_v
                goto = 18
            else:
                assert v9 == False
                w_39, w_40, w_41, w_42 = w_37, w_v, w_inst_8, w_cls_1
                goto = 16

        if goto == 16:
            w_43 = space.call_function(w_39, w_40, w_41, w_42)
            w_4 = w_43
            goto = 18

        if goto == 17:
            raise gOperationError(w_etype, w_evalue)

        if goto == 18:
            return w_4

  fastf_instance_getattr1 = instance_getattr1

##SECTION##
## filename    'lib/_classobj.py'
## function    '__getattribute__'
## firstlineno 256
##SECTION##
# global declaration
# global object gs___getattr__

  def __getattribute__(space, __args__):
    funcname = "__getattribute__"
    signature = ['self', 'name'], None, None
    defaults_w = []
    w_self, w_name = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___getattribute__(space, w_self, w_name)

  f_instance___getattribute__ = __getattribute__

  def __getattribute__(space, w_self, w_name):
    goto = 1 # startblock
    while True:

        if goto == 1:
            try:
                w_0 = space.call_function(gfunc_instance_getattr1, w_self, w_name)
                w_1 = w_0
                goto = 7
            except gOperationError, e:
                e.normalize_exception(space)
                if space.is_true(space.issubtype(e.w_type, space.w_Exception)):
                    (w_self_1, w_name_1, w_2, w_3) = (w_self, w_name, e.w_type,
                     e.w_value)
                    goto = 2
                else:raise # unhandled case, should not happen

        if goto == 2:
            w_4 = space.is_(w_2, space.w_AttributeError)
            v0 = space.is_true(w_4)
            if v0 == True:
                w_name_2, w_5, w_6, w_7 = w_name_1, w_self_1, w_2, w_3
                goto = 4
            else:
                assert v0 == False
                w_self_2, w_name_3, w_8, w_9 = w_self_1, w_name_1, w_2, w_3
                goto = 3

        if goto == 3:
            w_10 = space.issubtype(w_8, space.w_AttributeError)
            v1 = space.is_true(w_10)
            if v1 == True:
                w_name_2, w_5, w_6, w_7 = w_name_3, w_self_2, w_8, w_9
                goto = 4
            else:
                assert v1 == False
                w_etype, w_evalue = w_8, w_9
                goto = 6

        if goto == 4:
            _args = gateway.Arguments.fromshape(space, (2, ('exc',), False, False), [w_5, gs___getattr__, space.w_False])
            w_11 = space.call_args(gfunc_instance_getattr1, _args)
            w_12 = space.is_(w_11, space.w_None)
            v2 = space.is_true(w_12)
            if v2 == True:
                w_etype, w_evalue = w_6, w_7
                goto = 6
            else:
                assert v2 == False
                w_13, w_14 = w_11, w_name_2
                goto = 5

        if goto == 5:
            w_15 = space.call_function(w_13, w_14)
            w_1 = w_15
            goto = 7

        if goto == 6:
            raise gOperationError(w_etype, w_evalue)

        if goto == 7:
            return w_1

  fastf_instance___getattribute__ = __getattribute__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__new__'
## firstlineno 265
##SECTION##
# global declarations
# global object gs_instance___first_arg_must_be_cla
# global object gs_instance___second_arg_must_be_di

  def __new__(space, __args__):
    funcname = "__new__"
    signature = ['typ', 'klass', 'dic'], None, None
    defaults_w = [space.w_None]
    w_typ, w_klass, w_dic = __args__.parse(funcname, signature, defaults_w)
    return fastf___new___1(space, w_typ, w_klass, w_dic)

  f___new___1 = __new__

  def __new__(space, w_typ, w_klass, w_dic):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.isinstance(w_klass, gcls_classobj)
            v0 = space.is_true(w_0)
            if v0 == True:
                w_klass_1, w_dic_1 = w_klass, w_dic
                goto = 3
            else:
                assert v0 == False
                goto = 2

        if goto == 2:
            w_1 = space.call_function(space.w_TypeError, gs_instance___first_arg_must_be_cla)
            w_2 = space.type(w_1)
            w_3 = space.issubtype(w_2, space.w_type)
            v1 = space.is_true(w_3)
            if v1 == True:
                w_4 = w_1
                goto = 6
            else:
                assert v1 == False
                w_5 = w_1
                goto = 5

        if goto == 3:
            w_6 = space.is_(w_dic_1, space.w_None)
            v2 = space.is_true(w_6)
            if v2 == True:
                w_klass_2 = w_klass_1
                goto = 4
            else:
                assert v2 == False
                w_klass_3, w_dic_2 = w_klass_1, w_dic_1
                goto = 7

        if goto == 4:
            w_7 = space.newdict([])
            w_klass_4, w_dic_3 = w_klass_2, w_7
            goto = 9

        if goto == 5:
            w_8 = space.type(w_5)
            w_etype, w_evalue = w_8, w_5
            goto = 12

        if goto == 6:
            w_9 = space.call_function(w_4, )
            w_10 = space.type(w_9)
            w_etype, w_evalue = w_10, w_9
            goto = 12

        if goto == 7:
            w_11 = space.isinstance(w_dic_2, space.w_dict)
            v3 = space.is_true(w_11)
            if v3 == True:
                w_klass_4, w_dic_3 = w_klass_3, w_dic_2
                goto = 9
            else:
                assert v3 == False
                goto = 8

        if goto == 8:
            w_12 = space.call_function(space.w_TypeError, gs_instance___second_arg_must_be_di)
            w_13 = space.type(w_12)
            w_14 = space.issubtype(w_13, space.w_type)
            v4 = space.is_true(w_14)
            if v4 == True:
                w_15 = w_12
                goto = 11
            else:
                assert v4 == False
                w_16 = w_12
                goto = 10

        if goto == 9:
            w_17 = space.call_function(gbltinmethod___new__, gcls_instance)
            w_18 = space.getattr(gdescriptor_instance__class, gs___set__)
            w_19 = space.call_function(w_18, w_17, w_klass_4)
            w_20 = space.call_function(gdescriptor_object___setattr__, w_17, gs___dict__, w_dic_3)
            w_21 = w_17
            goto = 13

        if goto == 10:
            w_22 = space.type(w_16)
            w_etype, w_evalue = w_22, w_16
            goto = 12

        if goto == 11:
            w_23 = space.call_function(w_15, )
            w_24 = space.type(w_23)
            w_etype, w_evalue = w_24, w_23
            goto = 12

        if goto == 12:
            raise gOperationError(w_etype, w_evalue)

        if goto == 13:
            return w_21

  fastf___new___1 = __new__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__setattr__'
## firstlineno 278
##SECTION##
# global declarations
# global object gs___dict___must_be_set_to_a_dictio
# global object gs___class___must_be_set_to_a_class

  def __setattr__(space, __args__):
    funcname = "__setattr__"
    signature = ['self', 'name', 'value'], None, None
    defaults_w = []
    w_self, w_name, w_value = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___setattr__(space, w_self, w_name, w_value)

  f_instance___setattr__ = __setattr__

  def __setattr__(space, w_self, w_name, w_value):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.eq(w_name, gs___dict__)
            v0 = space.is_true(w_0)
            if v0 == True:
                w_self_1, w_value_1 = w_self, w_value
                goto = 2
            else:
                assert v0 == False
                w_self_2, w_name_1, w_value_2 = w_self, w_name, w_value
                goto = 5

        if goto == 2:
            w_1 = space.isinstance(w_value_1, space.w_dict)
            v1 = space.is_true(w_1)
            if v1 == True:
                w_2, w_3 = w_self_1, w_value_1
                goto = 4
            else:
                assert v1 == False
                goto = 3

        if goto == 3:
            w_4 = space.call_function(space.w_TypeError, gs___dict___must_be_set_to_a_dictio)
            w_5 = space.type(w_4)
            w_6 = space.issubtype(w_5, space.w_type)
            v2 = space.is_true(w_6)
            if v2 == True:
                w_7 = w_4
                goto = 10
            else:
                assert v2 == False
                w_8 = w_4
                goto = 9

        if goto == 4:
            w_9 = space.call_function(gdescriptor_object___setattr__, w_2, gs___dict__, w_3)
            w_10 = space.w_None
            goto = 17

        if goto == 5:
            w_11 = space.eq(w_name_1, gs___class__)
            v3 = space.is_true(w_11)
            if v3 == True:
                w_self_3, w_value_3 = w_self_2, w_value_2
                goto = 6
            else:
                assert v3 == False
                w_self_4, w_name_2, w_value_4 = w_self_2, w_name_1, w_value_2
                goto = 13

        if goto == 6:
            w_12 = space.isinstance(w_value_3, gcls_classobj)
            v4 = space.is_true(w_12)
            if v4 == True:
                w_self_5, w_value_5 = w_self_3, w_value_3
                goto = 8
            else:
                assert v4 == False
                goto = 7

        if goto == 7:
            w_13 = space.call_function(space.w_TypeError, gs___class___must_be_set_to_a_class)
            w_14 = space.type(w_13)
            w_15 = space.issubtype(w_14, space.w_type)
            v5 = space.is_true(w_15)
            if v5 == True:
                w_16 = w_13
                goto = 12
            else:
                assert v5 == False
                w_17 = w_13
                goto = 11

        if goto == 8:
            w_18 = space.getattr(gdescriptor_instance__class, gs___set__)
            w_19 = space.call_function(w_18, w_self_5, w_value_5)
            w_10 = space.w_None
            goto = 17

        if goto == 9:
            w_20 = space.type(w_8)
            w_etype, w_evalue = w_20, w_8
            goto = 16

        if goto == 10:
            w_21 = space.call_function(w_7, )
            w_22 = space.type(w_21)
            w_etype, w_evalue = w_22, w_21
            goto = 16

        if goto == 11:
            w_23 = space.type(w_17)
            w_etype, w_evalue = w_23, w_17
            goto = 16

        if goto == 12:
            w_24 = space.call_function(w_16, )
            w_25 = space.type(w_24)
            w_etype, w_evalue = w_25, w_24
            goto = 16

        if goto == 13:
            _args = gateway.Arguments.fromshape(space, (2, ('exc',), False, False), [w_self_4, gs___setattr__, space.w_False])
            w_26 = space.call_args(gfunc_instance_getattr1, _args)
            w_27 = space.is_(w_26, space.w_None)
            v6 = space.is_true(w_27)
            if v6 == True:
                w_name_3, w_28, w_29 = w_name_2, w_value_4, w_self_4
                goto = 15
            else:
                assert v6 == False
                w_30, w_31, w_32 = w_26, w_name_2, w_value_4
                goto = 14

        if goto == 14:
            w_33 = space.call_function(w_30, w_31, w_32)
            w_10 = space.w_None
            goto = 17

        if goto == 15:
            w_34 = space.getattr(w_29, gs___dict__)
            w_35 = space.setitem(w_34, w_name_3, w_28)
            w_10 = space.w_None
            goto = 17

        if goto == 16:
            raise gOperationError(w_etype, w_evalue)

        if goto == 17:
            return w_10

  fastf_instance___setattr__ = __setattr__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__delattr__'
## firstlineno 294
##SECTION##
# global declarations
# global object g2tuple_2
# global object gs__s_instance_has_no_attribute___s

  def __delattr__(space, __args__):
    funcname = "__delattr__"
    signature = ['self', 'name'], None, None
    defaults_w = []
    w_self, w_name = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___delattr__(space, w_self, w_name)

  f_instance___delattr__ = __delattr__

  def __delattr__(space, w_self, w_name):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.contains(g2tuple_2, w_name)
            v0 = space.is_true(w_0)
            if v0 == True:
                w_1, w_2 = w_self, w_name
                goto = 2
            else:
                assert v0 == False
                w_self_1, w_name_1 = w_self, w_name
                goto = 3

        if goto == 2:
            w_3 = fastf_instance___setattr__(space, w_1, w_2, space.w_None)
            w_4 = space.w_None
            goto = 10

        if goto == 3:
            _args = gateway.Arguments.fromshape(space, (2, ('exc',), False, False), [w_self_1, gs___delattr__, space.w_False])
            w_5 = space.call_args(gfunc_instance_getattr1, _args)
            w_6 = space.is_(w_5, space.w_None)
            v1 = space.is_true(w_6)
            if v1 == True:
                w_self_2, w_name_2 = w_self_1, w_name_1
                goto = 5
            else:
                assert v1 == False
                w_7, w_8 = w_5, w_name_1
                goto = 4

        if goto == 4:
            w_9 = space.call_function(w_7, w_8)
            w_4 = space.w_None
            goto = 10

        if goto == 5:
            w_10 = space.getattr(w_self_2, gs___dict__)
            try:
                w_11 = space.delitem(w_10, w_name_2)
                w_4 = space.w_None
                goto = 10
            except gOperationError, e:
                e.normalize_exception(space)
                if space.is_true(space.issubtype(e.w_type, space.w_KeyError)):
                    w_name_3, w_12 = w_name_2, w_self_2
                    goto = 6
                else:raise # unhandled case, should not happen

        if goto == 6:
            w_13 = space.getattr(w_12, gs___class__)
            w_14 = space.getattr(w_13, gs___name__)
            w_15 = space.newtuple([w_14, w_name_3])
            w_16 = space.mod(gs__s_instance_has_no_attribute___s, w_15)
            w_17 = space.call_function(space.w_AttributeError, w_16)
            w_18 = space.type(w_17)
            w_19 = space.issubtype(w_18, space.w_type)
            v2 = space.is_true(w_19)
            if v2 == True:
                w_20 = w_17
                goto = 8
            else:
                assert v2 == False
                w_21 = w_17
                goto = 7

        if goto == 7:
            w_22 = space.type(w_21)
            w_etype, w_evalue = w_22, w_21
            goto = 9

        if goto == 8:
            w_23 = space.call_function(w_20, )
            w_24 = space.type(w_23)
            w_etype, w_evalue = w_24, w_23
            goto = 9

        if goto == 9:
            raise gOperationError(w_etype, w_evalue)

        if goto == 10:
            return w_4

  fastf_instance___delattr__ = __delattr__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__repr__'
## firstlineno 310
##SECTION##
# global declaration
# global object gs___s__s_instance_at_0x_x_

  def __repr__(space, __args__):
    funcname = "__repr__"
    signature = ['self'], None, None
    defaults_w = []
    w_self, = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___repr__(space, w_self)

  f_instance___repr__ = __repr__

  def __repr__(space, w_self):
    goto = 1 # startblock
    while True:

        if goto == 1:
            try:
                w_0 = space.call_function(gfunc_instance_getattr1, w_self, gs___repr__)
                w_1 = w_0
                goto = 4
            except gOperationError, e:
                e.normalize_exception(space)
                if space.is_true(space.issubtype(e.w_type, space.w_Exception)):
                    w_self_1, w_2, w_3 = w_self, e.w_type, e.w_value
                    goto = 2
                else:raise # unhandled case, should not happen

        if goto == 2:
            w_4 = space.is_(w_2, space.w_AttributeError)
            v0 = space.is_true(w_4)
            if v0 == True:
                w_self_2 = w_self_1
                goto = 3
            else:
                assert v0 == False
                w_self_3, w_5, w_6 = w_self_1, w_2, w_3
                goto = 5

        if goto == 3:
            w_7 = space.getattr(w_self_2, gs___class__)
            w_8 = fastf_get_class_module(space, w_7)
            w_9 = space.getattr(w_7, gs___name__)
            w_10 = fastf_uid(space, w_self_2)
            w_11 = space.newtuple([w_8, w_9, w_10])
            w_12 = space.mod(gs___s__s_instance_at_0x_x_, w_11)
            w_13 = w_12
            goto = 7

        if goto == 4:
            w_14 = space.call_function(w_1, )
            w_13 = w_14
            goto = 7

        if goto == 5:
            w_15 = space.issubtype(w_5, space.w_AttributeError)
            v1 = space.is_true(w_15)
            if v1 == True:
                w_self_2 = w_self_3
                goto = 3
                continue
            else:
                assert v1 == False
                w_etype, w_evalue = w_5, w_6
                goto = 6

        if goto == 6:
            raise gOperationError(w_etype, w_evalue)

        if goto == 7:
            return w_13

  fastf_instance___repr__ = __repr__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__str__'
## firstlineno 319
##SECTION##
  def __str__(space, __args__):
    funcname = "__str__"
    signature = ['self'], None, None
    defaults_w = []
    w_self, = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___str__(space, w_self)

  f_instance___str__ = __str__

  def __str__(space, w_self):
    goto = 1 # startblock
    while True:

        if goto == 1:
            try:
                w_0 = space.call_function(gfunc_instance_getattr1, w_self, gs___str__)
                w_1 = w_0
                goto = 4
            except gOperationError, e:
                e.normalize_exception(space)
                if space.is_true(space.issubtype(e.w_type, space.w_Exception)):
                    w_self_1, w_2, w_3 = w_self, e.w_type, e.w_value
                    goto = 2
                else:raise # unhandled case, should not happen

        if goto == 2:
            w_4 = space.is_(w_2, space.w_AttributeError)
            v0 = space.is_true(w_4)
            if v0 == True:
                w_5 = w_self_1
                goto = 3
            else:
                assert v0 == False
                w_self_2, w_6, w_7 = w_self_1, w_2, w_3
                goto = 5

        if goto == 3:
            w_8 = fastf_instance___repr__(space, w_5)
            w_9 = w_8
            goto = 7

        if goto == 4:
            w_10 = space.call_function(w_1, )
            w_9 = w_10
            goto = 7

        if goto == 5:
            w_11 = space.issubtype(w_6, space.w_AttributeError)
            v1 = space.is_true(w_11)
            if v1 == True:
                w_5 = w_self_2
                goto = 3
                continue
            else:
                assert v1 == False
                w_etype, w_evalue = w_6, w_7
                goto = 6

        if goto == 6:
            raise gOperationError(w_etype, w_evalue)

        if goto == 7:
            return w_9

  fastf_instance___str__ = __str__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__hash__'
## firstlineno 326
##SECTION##
# global declarations
# global object gs_unhashable_instance
# global object gs___hash_____should_return_an_int

  def __hash__(space, __args__):
    funcname = "__hash__"
    signature = ['self'], None, None
    defaults_w = []
    w_self, = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___hash__(space, w_self)

  f_instance___hash__ = __hash__

  def __hash__(space, w_self):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.call_function(gfunc_instance_getattr1, w_self, gs___eq__, space.w_False)
            w_1 = space.call_function(gfunc_instance_getattr1, w_self, gs___cmp__, space.w_False)
            w_2 = space.call_function(gfunc_instance_getattr1, w_self, gs___hash__, space.w_False)
            v0 = space.is_true(w_0)
            if v0 == True:
                w_self_1, w__hash = w_self, w_2
                goto = 3
            else:
                assert v0 == False
                w_self_2, w__hash_1, w_3 = w_self, w_2, w_1
                goto = 2

        if goto == 2:
            v1 = space.is_true(w_3)
            if v1 == True:
                w_self_1, w__hash = w_self_2, w__hash_1
                goto = 3
            else:
                assert v1 == False
                w_self_3, w__hash_2 = w_self_2, w__hash_1
                goto = 5

        if goto == 3:
            v2 = space.is_true(w__hash)
            if v2 == True:
                w_self_3, w__hash_2 = w_self_1, w__hash
                goto = 5
            else:
                assert v2 == False
                goto = 4

        if goto == 4:
            w_4 = space.call_function(space.w_TypeError, gs_unhashable_instance)
            w_5 = space.type(w_4)
            w_6 = space.issubtype(w_5, space.w_type)
            v3 = space.is_true(w_6)
            if v3 == True:
                w_7 = w_4
                goto = 8
            else:
                assert v3 == False
                w_8 = w_4
                goto = 7

        if goto == 5:
            v4 = space.is_true(w__hash_2)
            if v4 == True:
                w_9 = w__hash_2
                goto = 6
            else:
                assert v4 == False
                w_10 = w_self_3
                goto = 12

        if goto == 6:
            w_11 = space.call_function(w_9, )
            w_12 = space.isinstance(w_11, space.w_int)
            v5 = space.is_true(w_12)
            if v5 == True:
                w_13 = w_11
                goto = 14
            else:
                assert v5 == False
                goto = 9

        if goto == 7:
            w_14 = space.type(w_8)
            w_etype, w_evalue = w_14, w_8
            goto = 13

        if goto == 8:
            w_15 = space.call_function(w_7, )
            w_16 = space.type(w_15)
            w_etype, w_evalue = w_16, w_15
            goto = 13

        if goto == 9:
            w_17 = space.call_function(space.w_TypeError, gs___hash_____should_return_an_int)
            w_18 = space.type(w_17)
            w_19 = space.issubtype(w_18, space.w_type)
            v6 = space.is_true(w_19)
            if v6 == True:
                w_20 = w_17
                goto = 11
            else:
                assert v6 == False
                w_21 = w_17
                goto = 10

        if goto == 10:
            w_22 = space.type(w_21)
            w_etype, w_evalue = w_22, w_21
            goto = 13

        if goto == 11:
            w_23 = space.call_function(w_20, )
            w_24 = space.type(w_23)
            w_etype, w_evalue = w_24, w_23
            goto = 13

        if goto == 12:
            w_25 = space.id(w_10)
            w_13 = w_25
            goto = 14

        if goto == 13:
            raise gOperationError(w_etype, w_evalue)

        if goto == 14:
            return w_13

  fastf_instance___hash__ = __hash__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__len__'
## firstlineno 340
##SECTION##
# global declarations
# global object gs___len_____should_return____0
# global object gs___len_____should_return_an_int

  def __len__(space, __args__):
    funcname = "__len__"
    signature = ['self'], None, None
    defaults_w = []
    w_self, = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___len__(space, w_self)

  f_instance___len__ = __len__

  def __len__(space, w_self):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.call_function(gfunc_instance_getattr1, w_self, gs___len__)
            w_1 = space.call_function(w_0, )
            w_2 = space.isinstance(w_1, space.w_int)
            v0 = space.is_true(w_2)
            if v0 == True:
                w_ret = w_1
                goto = 2
            else:
                assert v0 == False
                goto = 8

        if goto == 2:
            w_3 = space.lt(w_ret, gi_0)
            v1 = space.is_true(w_3)
            if v1 == True:
                goto = 3
            else:
                assert v1 == False
                w_4 = w_ret
                goto = 10

        if goto == 3:
            w_5 = space.call_function(space.w_ValueError, gs___len_____should_return____0)
            w_6 = space.type(w_5)
            w_7 = space.issubtype(w_6, space.w_type)
            v2 = space.is_true(w_7)
            if v2 == True:
                w_8 = w_5
                goto = 7
            else:
                assert v2 == False
                w_9 = w_5
                goto = 6

        if goto == 4:
            w_10 = space.type(w_11)
            w_etype, w_evalue = w_10, w_11
            goto = 9

        if goto == 5:
            w_13 = space.call_function(w_12, )
            w_14 = space.type(w_13)
            w_etype, w_evalue = w_14, w_13
            goto = 9

        if goto == 6:
            w_15 = space.type(w_9)
            w_etype, w_evalue = w_15, w_9
            goto = 9

        if goto == 7:
            w_16 = space.call_function(w_8, )
            w_17 = space.type(w_16)
            w_etype, w_evalue = w_17, w_16
            goto = 9

        if goto == 8:
            w_18 = space.call_function(space.w_TypeError, gs___len_____should_return_an_int)
            w_19 = space.type(w_18)
            w_20 = space.issubtype(w_19, space.w_type)
            v3 = space.is_true(w_20)
            if v3 == True:
                w_12 = w_18
                goto = 5
                continue
            else:
                assert v3 == False
                w_11 = w_18
                goto = 4
                continue

        if goto == 9:
            raise gOperationError(w_etype, w_evalue)

        if goto == 10:
            return w_4

  fastf_instance___len__ = __len__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__getitem__'
## firstlineno 349
##SECTION##
# global declaration
# global object gs___getslice__

  def __getitem__(space, __args__):
    funcname = "__getitem__"
    signature = ['self', 'key'], None, None
    defaults_w = []
    w_self, w_key = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___getitem__(space, w_self, w_key)

  f_instance___getitem__ = __getitem__

  def __getitem__(space, w_self, w_key):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.isinstance(w_key, space.w_slice)
            v0 = space.is_true(w_0)
            if v0 == True:
                w_self_1, w_key_1 = w_self, w_key
                goto = 2
            else:
                assert v0 == False
                w_key_2, w_1 = w_key, w_self
                goto = 5

        if goto == 2:
            w_2 = space.getattr(w_key_1, gs_step)
            w_3 = space.is_(w_2, space.w_None)
            v1 = space.is_true(w_3)
            if v1 == True:
                w_self_2, w_key_3 = w_self_1, w_key_1
                goto = 3
            else:
                assert v1 == False
                w_key_2, w_1 = w_key_1, w_self_1
                goto = 5

        if goto == 3:
            w_4 = space.call_function(gfunc_instance_getattr1, w_self_2, gs___getslice__, space.w_False)
            v2 = space.is_true(w_4)
            if v2 == True:
                w_key_4, w_5 = w_key_3, w_4
                goto = 4
            else:
                assert v2 == False
                w_key_2, w_1 = w_key_3, w_self_2
                goto = 5

        if goto == 4:
            w_6 = space.getattr(w_key_4, gs_start)
            w_7 = space.getattr(w_key_4, gs_stop)
            w_8 = space.call_function(w_5, w_6, w_7)
            w_9 = w_8
            goto = 6

        if goto == 5:
            w_10 = space.call_function(gfunc_instance_getattr1, w_1, gs___getitem__)
            w_11 = space.call_function(w_10, w_key_2)
            w_9 = w_11
            goto = 6

        if goto == 6:
            return w_9

  fastf_instance___getitem__ = __getitem__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__setitem__'
## firstlineno 356
##SECTION##
# global declarations
# global object gs_step
# global object gs___setslice__
# global object gs_start
# global object gs_stop

  def __setitem__(space, __args__):
    funcname = "__setitem__"
    signature = ['self', 'key', 'value'], None, None
    defaults_w = []
    w_self, w_key, w_value = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___setitem__(space, w_self, w_key, w_value)

  f_instance___setitem__ = __setitem__

  def __setitem__(space, w_self, w_key, w_value):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.isinstance(w_key, space.w_slice)
            v0 = space.is_true(w_0)
            if v0 == True:
                w_self_1, w_key_1, w_value_1 = w_self, w_key, w_value
                goto = 2
            else:
                assert v0 == False
                w_key_2, w_value_2, w_1 = w_key, w_value, w_self
                goto = 5

        if goto == 2:
            w_2 = space.getattr(w_key_1, gs_step)
            w_3 = space.is_(w_2, space.w_None)
            v1 = space.is_true(w_3)
            if v1 == True:
                w_self_2, w_key_3, w_value_3 = w_self_1, w_key_1, w_value_1
                goto = 3
            else:
                assert v1 == False
                w_key_2, w_value_2, w_1 = w_key_1, w_value_1, w_self_1
                goto = 5

        if goto == 3:
            w_4 = space.call_function(gfunc_instance_getattr1, w_self_2, gs___setslice__, space.w_False)
            v2 = space.is_true(w_4)
            if v2 == True:
                (w_self_3, w_key_4, w_value_4, w_5) = (w_self_2, w_key_3,
                 w_value_3, w_4)
                goto = 4
            else:
                assert v2 == False
                w_key_2, w_value_2, w_1 = w_key_3, w_value_3, w_self_2
                goto = 5

        if goto == 4:
            w_6 = space.getattr(w_key_4, gs_start)
            w_7 = space.getattr(w_key_4, gs_stop)
            w_8 = space.call_function(w_5, w_6, w_7, w_value_4)
            w_key_2, w_value_2, w_1 = w_key_4, w_value_4, w_self_3
            goto = 5

        if goto == 5:
            w_9 = space.call_function(gfunc_instance_getattr1, w_1, gs___setitem__)
            w_10 = space.call_function(w_9, w_key_2, w_value_2)
            w_11 = space.w_None
            goto = 6

        if goto == 6:
            return w_11

  fastf_instance___setitem__ = __setitem__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__delitem__'
## firstlineno 363
##SECTION##
# global declaration
# global object gs___delslice__

  def __delitem__(space, __args__):
    funcname = "__delitem__"
    signature = ['self', 'key'], None, None
    defaults_w = []
    w_self, w_key = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___delitem__(space, w_self, w_key)

  f_instance___delitem__ = __delitem__

  def __delitem__(space, w_self, w_key):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.isinstance(w_key, space.w_slice)
            v0 = space.is_true(w_0)
            if v0 == True:
                w_self_1, w_key_1 = w_self, w_key
                goto = 2
            else:
                assert v0 == False
                w_key_2, w_1 = w_key, w_self
                goto = 5

        if goto == 2:
            w_2 = space.getattr(w_key_1, gs_step)
            w_3 = space.is_(w_2, space.w_None)
            v1 = space.is_true(w_3)
            if v1 == True:
                w_self_2, w_key_3 = w_self_1, w_key_1
                goto = 3
            else:
                assert v1 == False
                w_key_2, w_1 = w_key_1, w_self_1
                goto = 5

        if goto == 3:
            w_4 = space.call_function(gfunc_instance_getattr1, w_self_2, gs___delslice__, space.w_False)
            v2 = space.is_true(w_4)
            if v2 == True:
                w_self_3, w_key_4, w_5 = w_self_2, w_key_3, w_4
                goto = 4
            else:
                assert v2 == False
                w_key_2, w_1 = w_key_3, w_self_2
                goto = 5

        if goto == 4:
            w_6 = space.getattr(w_key_4, gs_start)
            w_7 = space.getattr(w_key_4, gs_stop)
            w_8 = space.call_function(w_5, w_6, w_7)
            w_key_2, w_1 = w_key_4, w_self_3
            goto = 5

        if goto == 5:
            w_9 = space.call_function(gfunc_instance_getattr1, w_1, gs___delitem__)
            w_10 = space.call_function(w_9, w_key_2)
            w_11 = space.w_None
            goto = 6

        if goto == 6:
            return w_11

  fastf_instance___delitem__ = __delitem__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__contains__'
## firstlineno 370
##SECTION##
  def __contains__(space, __args__):
    funcname = "__contains__"
    signature = ['self', 'obj'], None, None
    defaults_w = []
    w_self, w_obj = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___contains__(space, w_self, w_obj)

  f_instance___contains__ = __contains__

  def __contains__(space, w_self, w_obj):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.call_function(gfunc_instance_getattr1, w_self, gs___contains__, space.w_False)
            v0 = space.is_true(w_0)
            if v0 == True:
                w_1, w_2 = w_0, w_obj
                goto = 2
            else:
                assert v0 == False
                w_obj_1, w_3 = w_obj, w_self
                goto = 3

        if goto == 2:
            w_4 = space.call_function(w_1, w_2)
            w_5 = space.nonzero(w_4)
            w_6 = w_5
            goto = 6

        if goto == 3:
            w_7 = space.iter(w_3)
            w_obj_2, w_8 = w_obj_1, w_7
            goto = 4

        if goto == 4:
            try:
                w_9 = space.next(w_8)
                w_obj_3, w_10, w_11 = w_obj_2, w_8, w_9
                goto = 5
            except gOperationError, e:
                e.normalize_exception(space)
                if space.is_true(space.issubtype(e.w_type, space.w_StopIteration)):
                    w_6 = space.w_False
                    goto = 6
                else:raise # unhandled case, should not happen

        if goto == 5:
            w_12 = space.eq(w_11, w_obj_3)
            v1 = space.is_true(w_12)
            if v1 == True:
                w_6 = space.w_True
                goto = 6
            else:
                assert v1 == False
                w_obj_2, w_8 = w_obj_3, w_10
                goto = 4
                continue

        if goto == 6:
            return w_6

  fastf_instance___contains__ = __contains__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__abs__'
## firstlineno 385
##SECTION##
  def __abs__(space, __args__):
    funcname = "__abs__"
    signature = ['self'], None, None
    defaults_w = []
    w_self, = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___abs__(space, w_self)

  f_instance___abs__ = __abs__

  def __abs__(space, w_self):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.call_function(gfunc_instance_getattr1, w_self, gs___abs__)
            w_1 = space.call_function(w_0, )
            w_2 = w_1
            goto = 2

        if goto == 2:
            return w_2

  fastf_instance___abs__ = __abs__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__float__'
## firstlineno 385
##SECTION##
  def __float__(space, __args__):
    funcname = "__float__"
    signature = ['self'], None, None
    defaults_w = []
    w_self, = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___float__(space, w_self)

  f_instance___float__ = __float__

  def __float__(space, w_self):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.call_function(gfunc_instance_getattr1, w_self, gs___float__)
            w_1 = space.call_function(w_0, )
            w_2 = w_1
            goto = 2

        if goto == 2:
            return w_2

  fastf_instance___float__ = __float__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__hex__'
## firstlineno 385
##SECTION##
  def __hex__(space, __args__):
    funcname = "__hex__"
    signature = ['self'], None, None
    defaults_w = []
    w_self, = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___hex__(space, w_self)

  f_instance___hex__ = __hex__

  def __hex__(space, w_self):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.call_function(gfunc_instance_getattr1, w_self, gs___hex__)
            w_1 = space.call_function(w_0, )
            w_2 = w_1
            goto = 2

        if goto == 2:
            return w_2

  fastf_instance___hex__ = __hex__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__int__'
## firstlineno 385
##SECTION##
  def __int__(space, __args__):
    funcname = "__int__"
    signature = ['self'], None, None
    defaults_w = []
    w_self, = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___int__(space, w_self)

  f_instance___int__ = __int__

  def __int__(space, w_self):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.call_function(gfunc_instance_getattr1, w_self, gs___int__)
            w_1 = space.call_function(w_0, )
            w_2 = w_1
            goto = 2

        if goto == 2:
            return w_2

  fastf_instance___int__ = __int__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__invert__'
## firstlineno 385
##SECTION##
  def __invert__(space, __args__):
    funcname = "__invert__"
    signature = ['self'], None, None
    defaults_w = []
    w_self, = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___invert__(space, w_self)

  f_instance___invert__ = __invert__

  def __invert__(space, w_self):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.call_function(gfunc_instance_getattr1, w_self, gs___invert__)
            w_1 = space.call_function(w_0, )
            w_2 = w_1
            goto = 2

        if goto == 2:
            return w_2

  fastf_instance___invert__ = __invert__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__long__'
## firstlineno 385
##SECTION##
  def __long__(space, __args__):
    funcname = "__long__"
    signature = ['self'], None, None
    defaults_w = []
    w_self, = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___long__(space, w_self)

  f_instance___long__ = __long__

  def __long__(space, w_self):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.call_function(gfunc_instance_getattr1, w_self, gs___long__)
            w_1 = space.call_function(w_0, )
            w_2 = w_1
            goto = 2

        if goto == 2:
            return w_2

  fastf_instance___long__ = __long__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__neg__'
## firstlineno 385
##SECTION##
  def __neg__(space, __args__):
    funcname = "__neg__"
    signature = ['self'], None, None
    defaults_w = []
    w_self, = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___neg__(space, w_self)

  f_instance___neg__ = __neg__

  def __neg__(space, w_self):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.call_function(gfunc_instance_getattr1, w_self, gs___neg__)
            w_1 = space.call_function(w_0, )
            w_2 = w_1
            goto = 2

        if goto == 2:
            return w_2

  fastf_instance___neg__ = __neg__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__oct__'
## firstlineno 385
##SECTION##
  def __oct__(space, __args__):
    funcname = "__oct__"
    signature = ['self'], None, None
    defaults_w = []
    w_self, = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___oct__(space, w_self)

  f_instance___oct__ = __oct__

  def __oct__(space, w_self):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.call_function(gfunc_instance_getattr1, w_self, gs___oct__)
            w_1 = space.call_function(w_0, )
            w_2 = w_1
            goto = 2

        if goto == 2:
            return w_2

  fastf_instance___oct__ = __oct__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__pos__'
## firstlineno 385
##SECTION##
  def __pos__(space, __args__):
    funcname = "__pos__"
    signature = ['self'], None, None
    defaults_w = []
    w_self, = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___pos__(space, w_self)

  f_instance___pos__ = __pos__

  def __pos__(space, w_self):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.call_function(gfunc_instance_getattr1, w_self, gs___pos__)
            w_1 = space.call_function(w_0, )
            w_2 = w_1
            goto = 2

        if goto == 2:
            return w_2

  fastf_instance___pos__ = __pos__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__coerce__'
## firstlineno 391
##SECTION##
  def __coerce__(space, __args__):
    funcname = "__coerce__"
    signature = ['self', 'other'], None, None
    defaults_w = []
    w_self, w_other = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___coerce__(space, w_self, w_other)

  f_instance___coerce__ = __coerce__

  def __coerce__(space, w_self, w_other):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.call_function(gfunc_instance_getattr1, w_self, gs___coerce__, space.w_False)
            v0 = space.is_true(w_0)
            if v0 == True:
                w_1, w_2 = w_0, w_other
                goto = 2
            else:
                assert v0 == False
                w_3 = space.w_NotImplemented
                goto = 3

        if goto == 2:
            w_4 = space.call_function(w_1, w_2)
            w_3 = w_4
            goto = 3

        if goto == 3:
            return w_3

  fastf_instance___coerce__ = __coerce__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__add__'
## firstlineno 408
##SECTION##
  def __add__(space, __args__):
    funcname = "__add__"
    signature = ['self', 'other'], None, None
    defaults_w = []
    w_self, w_other = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___add__(space, w_self, w_other)

  f_instance___add__ = __add__

  def __add__(space, w_self, w_other):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = fastf__coerce(space, w_self, w_other)
            w_1 = space.is_(w_0, space.w_None)
            v0 = space.is_true(w_1)
            if v0 == True:
                w_other_1, w_2 = w_other, w_self
                goto = 3
            else:
                assert v0 == False
                w_self_1, w_other_2, w_coerced = w_self, w_other, w_0
                goto = 2

        if goto == 2:
            w_3 = space.getitem(w_coerced, gi_0)
            w_4 = space.is_(w_3, w_self_1)
            v1 = space.is_true(w_4)
            if v1 == True:
                w_other_1, w_2 = w_other_2, w_self_1
                goto = 3
            else:
                assert v1 == False
                w_coerced_1 = w_coerced
                goto = 5

        if goto == 3:
            w_5 = space.call_function(gfunc_instance_getattr1, w_2, gs___add__, space.w_False)
            v2 = space.is_true(w_5)
            if v2 == True:
                w_6, w_7 = w_5, w_other_1
                goto = 4
            else:
                assert v2 == False
                w_8 = space.w_NotImplemented
                goto = 6

        if goto == 4:
            w_9 = space.call_function(w_6, w_7)
            w_8 = w_9
            goto = 6

        if goto == 5:
            w_10 = space.getitem(w_coerced_1, gi_0)
            w_11 = space.getitem(w_coerced_1, gi_1)
            w_12 = space.add(w_10, w_11)
            w_8 = w_12
            goto = 6

        if goto == 6:
            return w_8

  fastf_instance___add__ = __add__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__and__'
## firstlineno 408
##SECTION##
  def __and__(space, __args__):
    funcname = "__and__"
    signature = ['self', 'other'], None, None
    defaults_w = []
    w_self, w_other = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___and__(space, w_self, w_other)

  f_instance___and__ = __and__

  def __and__(space, w_self, w_other):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = fastf__coerce(space, w_self, w_other)
            w_1 = space.is_(w_0, space.w_None)
            v0 = space.is_true(w_1)
            if v0 == True:
                w_other_1, w_2 = w_other, w_self
                goto = 3
            else:
                assert v0 == False
                w_self_1, w_other_2, w_coerced = w_self, w_other, w_0
                goto = 2

        if goto == 2:
            w_3 = space.getitem(w_coerced, gi_0)
            w_4 = space.is_(w_3, w_self_1)
            v1 = space.is_true(w_4)
            if v1 == True:
                w_other_1, w_2 = w_other_2, w_self_1
                goto = 3
            else:
                assert v1 == False
                w_coerced_1 = w_coerced
                goto = 5

        if goto == 3:
            w_5 = space.call_function(gfunc_instance_getattr1, w_2, gs___and__, space.w_False)
            v2 = space.is_true(w_5)
            if v2 == True:
                w_6, w_7 = w_5, w_other_1
                goto = 4
            else:
                assert v2 == False
                w_8 = space.w_NotImplemented
                goto = 6

        if goto == 4:
            w_9 = space.call_function(w_6, w_7)
            w_8 = w_9
            goto = 6

        if goto == 5:
            w_10 = space.getitem(w_coerced_1, gi_0)
            w_11 = space.getitem(w_coerced_1, gi_1)
            w_12 = space.and_(w_10, w_11)
            w_8 = w_12
            goto = 6

        if goto == 6:
            return w_8

  fastf_instance___and__ = __and__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__div__'
## firstlineno 408
##SECTION##
  def __div__(space, __args__):
    funcname = "__div__"
    signature = ['self', 'other'], None, None
    defaults_w = []
    w_self, w_other = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___div__(space, w_self, w_other)

  f_instance___div__ = __div__

  def __div__(space, w_self, w_other):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = fastf__coerce(space, w_self, w_other)
            w_1 = space.is_(w_0, space.w_None)
            v0 = space.is_true(w_1)
            if v0 == True:
                w_other_1, w_2 = w_other, w_self
                goto = 3
            else:
                assert v0 == False
                w_self_1, w_other_2, w_coerced = w_self, w_other, w_0
                goto = 2

        if goto == 2:
            w_3 = space.getitem(w_coerced, gi_0)
            w_4 = space.is_(w_3, w_self_1)
            v1 = space.is_true(w_4)
            if v1 == True:
                w_other_1, w_2 = w_other_2, w_self_1
                goto = 3
            else:
                assert v1 == False
                w_coerced_1 = w_coerced
                goto = 5

        if goto == 3:
            w_5 = space.call_function(gfunc_instance_getattr1, w_2, gs___div__, space.w_False)
            v2 = space.is_true(w_5)
            if v2 == True:
                w_6, w_7 = w_5, w_other_1
                goto = 4
            else:
                assert v2 == False
                w_8 = space.w_NotImplemented
                goto = 6

        if goto == 4:
            w_9 = space.call_function(w_6, w_7)
            w_8 = w_9
            goto = 6

        if goto == 5:
            w_10 = space.getitem(w_coerced_1, gi_0)
            w_11 = space.getitem(w_coerced_1, gi_1)
            w_12 = space.div(w_10, w_11)
            w_8 = w_12
            goto = 6

        if goto == 6:
            return w_8

  fastf_instance___div__ = __div__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__divmod__'
## firstlineno 408
##SECTION##
  def __divmod__(space, __args__):
    funcname = "__divmod__"
    signature = ['self', 'other'], None, None
    defaults_w = []
    w_self, w_other = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___divmod__(space, w_self, w_other)

  f_instance___divmod__ = __divmod__

  def __divmod__(space, w_self, w_other):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = fastf__coerce(space, w_self, w_other)
            w_1 = space.is_(w_0, space.w_None)
            v0 = space.is_true(w_1)
            if v0 == True:
                w_other_1, w_2 = w_other, w_self
                goto = 3
            else:
                assert v0 == False
                w_self_1, w_other_2, w_coerced = w_self, w_other, w_0
                goto = 2

        if goto == 2:
            w_3 = space.getitem(w_coerced, gi_0)
            w_4 = space.is_(w_3, w_self_1)
            v1 = space.is_true(w_4)
            if v1 == True:
                w_other_1, w_2 = w_other_2, w_self_1
                goto = 3
            else:
                assert v1 == False
                w_coerced_1 = w_coerced
                goto = 5

        if goto == 3:
            w_5 = space.call_function(gfunc_instance_getattr1, w_2, gs___divmod__, space.w_False)
            v2 = space.is_true(w_5)
            if v2 == True:
                w_6, w_7 = w_5, w_other_1
                goto = 4
            else:
                assert v2 == False
                w_8 = space.w_NotImplemented
                goto = 6

        if goto == 4:
            w_9 = space.call_function(w_6, w_7)
            w_8 = w_9
            goto = 6

        if goto == 5:
            w_10 = space.getitem(w_coerced_1, gi_0)
            w_11 = space.getitem(w_coerced_1, gi_1)
            w_12 = space.divmod(w_10, w_11)
            w_8 = w_12
            goto = 6

        if goto == 6:
            return w_8

  fastf_instance___divmod__ = __divmod__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__floordiv__'
## firstlineno 408
##SECTION##
  def __floordiv__(space, __args__):
    funcname = "__floordiv__"
    signature = ['self', 'other'], None, None
    defaults_w = []
    w_self, w_other = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___floordiv__(space, w_self, w_other)

  f_instance___floordiv__ = __floordiv__

  def __floordiv__(space, w_self, w_other):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = fastf__coerce(space, w_self, w_other)
            w_1 = space.is_(w_0, space.w_None)
            v0 = space.is_true(w_1)
            if v0 == True:
                w_other_1, w_2 = w_other, w_self
                goto = 3
            else:
                assert v0 == False
                w_self_1, w_other_2, w_coerced = w_self, w_other, w_0
                goto = 2

        if goto == 2:
            w_3 = space.getitem(w_coerced, gi_0)
            w_4 = space.is_(w_3, w_self_1)
            v1 = space.is_true(w_4)
            if v1 == True:
                w_other_1, w_2 = w_other_2, w_self_1
                goto = 3
            else:
                assert v1 == False
                w_coerced_1 = w_coerced
                goto = 5

        if goto == 3:
            w_5 = space.call_function(gfunc_instance_getattr1, w_2, gs___floordiv__, space.w_False)
            v2 = space.is_true(w_5)
            if v2 == True:
                w_6, w_7 = w_5, w_other_1
                goto = 4
            else:
                assert v2 == False
                w_8 = space.w_NotImplemented
                goto = 6

        if goto == 4:
            w_9 = space.call_function(w_6, w_7)
            w_8 = w_9
            goto = 6

        if goto == 5:
            w_10 = space.getitem(w_coerced_1, gi_0)
            w_11 = space.getitem(w_coerced_1, gi_1)
            w_12 = space.floordiv(w_10, w_11)
            w_8 = w_12
            goto = 6

        if goto == 6:
            return w_8

  fastf_instance___floordiv__ = __floordiv__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__lshift__'
## firstlineno 408
##SECTION##
  def __lshift__(space, __args__):
    funcname = "__lshift__"
    signature = ['self', 'other'], None, None
    defaults_w = []
    w_self, w_other = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___lshift__(space, w_self, w_other)

  f_instance___lshift__ = __lshift__

  def __lshift__(space, w_self, w_other):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = fastf__coerce(space, w_self, w_other)
            w_1 = space.is_(w_0, space.w_None)
            v0 = space.is_true(w_1)
            if v0 == True:
                w_other_1, w_2 = w_other, w_self
                goto = 3
            else:
                assert v0 == False
                w_self_1, w_other_2, w_coerced = w_self, w_other, w_0
                goto = 2

        if goto == 2:
            w_3 = space.getitem(w_coerced, gi_0)
            w_4 = space.is_(w_3, w_self_1)
            v1 = space.is_true(w_4)
            if v1 == True:
                w_other_1, w_2 = w_other_2, w_self_1
                goto = 3
            else:
                assert v1 == False
                w_coerced_1 = w_coerced
                goto = 5

        if goto == 3:
            w_5 = space.call_function(gfunc_instance_getattr1, w_2, gs___lshift__, space.w_False)
            v2 = space.is_true(w_5)
            if v2 == True:
                w_6, w_7 = w_5, w_other_1
                goto = 4
            else:
                assert v2 == False
                w_8 = space.w_NotImplemented
                goto = 6

        if goto == 4:
            w_9 = space.call_function(w_6, w_7)
            w_8 = w_9
            goto = 6

        if goto == 5:
            w_10 = space.getitem(w_coerced_1, gi_0)
            w_11 = space.getitem(w_coerced_1, gi_1)
            w_12 = space.lshift(w_10, w_11)
            w_8 = w_12
            goto = 6

        if goto == 6:
            return w_8

  fastf_instance___lshift__ = __lshift__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__mod__'
## firstlineno 408
##SECTION##
  def __mod__(space, __args__):
    funcname = "__mod__"
    signature = ['self', 'other'], None, None
    defaults_w = []
    w_self, w_other = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___mod__(space, w_self, w_other)

  f_instance___mod__ = __mod__

  def __mod__(space, w_self, w_other):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = fastf__coerce(space, w_self, w_other)
            w_1 = space.is_(w_0, space.w_None)
            v0 = space.is_true(w_1)
            if v0 == True:
                w_other_1, w_2 = w_other, w_self
                goto = 3
            else:
                assert v0 == False
                w_self_1, w_other_2, w_coerced = w_self, w_other, w_0
                goto = 2

        if goto == 2:
            w_3 = space.getitem(w_coerced, gi_0)
            w_4 = space.is_(w_3, w_self_1)
            v1 = space.is_true(w_4)
            if v1 == True:
                w_other_1, w_2 = w_other_2, w_self_1
                goto = 3
            else:
                assert v1 == False
                w_coerced_1 = w_coerced
                goto = 5

        if goto == 3:
            w_5 = space.call_function(gfunc_instance_getattr1, w_2, gs___mod__, space.w_False)
            v2 = space.is_true(w_5)
            if v2 == True:
                w_6, w_7 = w_5, w_other_1
                goto = 4
            else:
                assert v2 == False
                w_8 = space.w_NotImplemented
                goto = 6

        if goto == 4:
            w_9 = space.call_function(w_6, w_7)
            w_8 = w_9
            goto = 6

        if goto == 5:
            w_10 = space.getitem(w_coerced_1, gi_0)
            w_11 = space.getitem(w_coerced_1, gi_1)
            w_12 = space.mod(w_10, w_11)
            w_8 = w_12
            goto = 6

        if goto == 6:
            return w_8

  fastf_instance___mod__ = __mod__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__mul__'
## firstlineno 408
##SECTION##
  def __mul__(space, __args__):
    funcname = "__mul__"
    signature = ['self', 'other'], None, None
    defaults_w = []
    w_self, w_other = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___mul__(space, w_self, w_other)

  f_instance___mul__ = __mul__

  def __mul__(space, w_self, w_other):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = fastf__coerce(space, w_self, w_other)
            w_1 = space.is_(w_0, space.w_None)
            v0 = space.is_true(w_1)
            if v0 == True:
                w_other_1, w_2 = w_other, w_self
                goto = 3
            else:
                assert v0 == False
                w_self_1, w_other_2, w_coerced = w_self, w_other, w_0
                goto = 2

        if goto == 2:
            w_3 = space.getitem(w_coerced, gi_0)
            w_4 = space.is_(w_3, w_self_1)
            v1 = space.is_true(w_4)
            if v1 == True:
                w_other_1, w_2 = w_other_2, w_self_1
                goto = 3
            else:
                assert v1 == False
                w_coerced_1 = w_coerced
                goto = 5

        if goto == 3:
            w_5 = space.call_function(gfunc_instance_getattr1, w_2, gs___mul__, space.w_False)
            v2 = space.is_true(w_5)
            if v2 == True:
                w_6, w_7 = w_5, w_other_1
                goto = 4
            else:
                assert v2 == False
                w_8 = space.w_NotImplemented
                goto = 6

        if goto == 4:
            w_9 = space.call_function(w_6, w_7)
            w_8 = w_9
            goto = 6

        if goto == 5:
            w_10 = space.getitem(w_coerced_1, gi_0)
            w_11 = space.getitem(w_coerced_1, gi_1)
            w_12 = space.mul(w_10, w_11)
            w_8 = w_12
            goto = 6

        if goto == 6:
            return w_8

  fastf_instance___mul__ = __mul__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__or__'
## firstlineno 408
##SECTION##
  def __or__(space, __args__):
    funcname = "__or__"
    signature = ['self', 'other'], None, None
    defaults_w = []
    w_self, w_other = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___or__(space, w_self, w_other)

  f_instance___or__ = __or__

  def __or__(space, w_self, w_other):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = fastf__coerce(space, w_self, w_other)
            w_1 = space.is_(w_0, space.w_None)
            v0 = space.is_true(w_1)
            if v0 == True:
                w_other_1, w_2 = w_other, w_self
                goto = 3
            else:
                assert v0 == False
                w_self_1, w_other_2, w_coerced = w_self, w_other, w_0
                goto = 2

        if goto == 2:
            w_3 = space.getitem(w_coerced, gi_0)
            w_4 = space.is_(w_3, w_self_1)
            v1 = space.is_true(w_4)
            if v1 == True:
                w_other_1, w_2 = w_other_2, w_self_1
                goto = 3
            else:
                assert v1 == False
                w_coerced_1 = w_coerced
                goto = 5

        if goto == 3:
            w_5 = space.call_function(gfunc_instance_getattr1, w_2, gs___or__, space.w_False)
            v2 = space.is_true(w_5)
            if v2 == True:
                w_6, w_7 = w_5, w_other_1
                goto = 4
            else:
                assert v2 == False
                w_8 = space.w_NotImplemented
                goto = 6

        if goto == 4:
            w_9 = space.call_function(w_6, w_7)
            w_8 = w_9
            goto = 6

        if goto == 5:
            w_10 = space.getitem(w_coerced_1, gi_0)
            w_11 = space.getitem(w_coerced_1, gi_1)
            w_12 = space.or_(w_10, w_11)
            w_8 = w_12
            goto = 6

        if goto == 6:
            return w_8

  fastf_instance___or__ = __or__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__rshift__'
## firstlineno 408
##SECTION##
  def __rshift__(space, __args__):
    funcname = "__rshift__"
    signature = ['self', 'other'], None, None
    defaults_w = []
    w_self, w_other = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___rshift__(space, w_self, w_other)

  f_instance___rshift__ = __rshift__

  def __rshift__(space, w_self, w_other):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = fastf__coerce(space, w_self, w_other)
            w_1 = space.is_(w_0, space.w_None)
            v0 = space.is_true(w_1)
            if v0 == True:
                w_other_1, w_2 = w_other, w_self
                goto = 3
            else:
                assert v0 == False
                w_self_1, w_other_2, w_coerced = w_self, w_other, w_0
                goto = 2

        if goto == 2:
            w_3 = space.getitem(w_coerced, gi_0)
            w_4 = space.is_(w_3, w_self_1)
            v1 = space.is_true(w_4)
            if v1 == True:
                w_other_1, w_2 = w_other_2, w_self_1
                goto = 3
            else:
                assert v1 == False
                w_coerced_1 = w_coerced
                goto = 5

        if goto == 3:
            w_5 = space.call_function(gfunc_instance_getattr1, w_2, gs___rshift__, space.w_False)
            v2 = space.is_true(w_5)
            if v2 == True:
                w_6, w_7 = w_5, w_other_1
                goto = 4
            else:
                assert v2 == False
                w_8 = space.w_NotImplemented
                goto = 6

        if goto == 4:
            w_9 = space.call_function(w_6, w_7)
            w_8 = w_9
            goto = 6

        if goto == 5:
            w_10 = space.getitem(w_coerced_1, gi_0)
            w_11 = space.getitem(w_coerced_1, gi_1)
            w_12 = space.rshift(w_10, w_11)
            w_8 = w_12
            goto = 6

        if goto == 6:
            return w_8

  fastf_instance___rshift__ = __rshift__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__sub__'
## firstlineno 408
##SECTION##
  def __sub__(space, __args__):
    funcname = "__sub__"
    signature = ['self', 'other'], None, None
    defaults_w = []
    w_self, w_other = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___sub__(space, w_self, w_other)

  f_instance___sub__ = __sub__

  def __sub__(space, w_self, w_other):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = fastf__coerce(space, w_self, w_other)
            w_1 = space.is_(w_0, space.w_None)
            v0 = space.is_true(w_1)
            if v0 == True:
                w_other_1, w_2 = w_other, w_self
                goto = 3
            else:
                assert v0 == False
                w_self_1, w_other_2, w_coerced = w_self, w_other, w_0
                goto = 2

        if goto == 2:
            w_3 = space.getitem(w_coerced, gi_0)
            w_4 = space.is_(w_3, w_self_1)
            v1 = space.is_true(w_4)
            if v1 == True:
                w_other_1, w_2 = w_other_2, w_self_1
                goto = 3
            else:
                assert v1 == False
                w_coerced_1 = w_coerced
                goto = 5

        if goto == 3:
            w_5 = space.call_function(gfunc_instance_getattr1, w_2, gs___sub__, space.w_False)
            v2 = space.is_true(w_5)
            if v2 == True:
                w_6, w_7 = w_5, w_other_1
                goto = 4
            else:
                assert v2 == False
                w_8 = space.w_NotImplemented
                goto = 6

        if goto == 4:
            w_9 = space.call_function(w_6, w_7)
            w_8 = w_9
            goto = 6

        if goto == 5:
            w_10 = space.getitem(w_coerced_1, gi_0)
            w_11 = space.getitem(w_coerced_1, gi_1)
            w_12 = space.sub(w_10, w_11)
            w_8 = w_12
            goto = 6

        if goto == 6:
            return w_8

  fastf_instance___sub__ = __sub__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__truediv__'
## firstlineno 408
##SECTION##
  def __truediv__(space, __args__):
    funcname = "__truediv__"
    signature = ['self', 'other'], None, None
    defaults_w = []
    w_self, w_other = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___truediv__(space, w_self, w_other)

  f_instance___truediv__ = __truediv__

  def __truediv__(space, w_self, w_other):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = fastf__coerce(space, w_self, w_other)
            w_1 = space.is_(w_0, space.w_None)
            v0 = space.is_true(w_1)
            if v0 == True:
                w_other_1, w_2 = w_other, w_self
                goto = 3
            else:
                assert v0 == False
                w_self_1, w_other_2, w_coerced = w_self, w_other, w_0
                goto = 2

        if goto == 2:
            w_3 = space.getitem(w_coerced, gi_0)
            w_4 = space.is_(w_3, w_self_1)
            v1 = space.is_true(w_4)
            if v1 == True:
                w_other_1, w_2 = w_other_2, w_self_1
                goto = 3
            else:
                assert v1 == False
                w_coerced_1 = w_coerced
                goto = 5

        if goto == 3:
            w_5 = space.call_function(gfunc_instance_getattr1, w_2, gs___truediv__, space.w_False)
            v2 = space.is_true(w_5)
            if v2 == True:
                w_6, w_7 = w_5, w_other_1
                goto = 4
            else:
                assert v2 == False
                w_8 = space.w_NotImplemented
                goto = 6

        if goto == 4:
            w_9 = space.call_function(w_6, w_7)
            w_8 = w_9
            goto = 6

        if goto == 5:
            w_10 = space.getitem(w_coerced_1, gi_0)
            w_11 = space.getitem(w_coerced_1, gi_1)
            w_12 = space.truediv(w_10, w_11)
            w_8 = w_12
            goto = 6

        if goto == 6:
            return w_8

  fastf_instance___truediv__ = __truediv__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__xor__'
## firstlineno 408
##SECTION##
# global declaration
# global object gfunc__coerce

  def __xor__(space, __args__):
    funcname = "__xor__"
    signature = ['self', 'other'], None, None
    defaults_w = []
    w_self, w_other = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___xor__(space, w_self, w_other)

  f_instance___xor__ = __xor__

  def __xor__(space, w_self, w_other):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = fastf__coerce(space, w_self, w_other)
            w_1 = space.is_(w_0, space.w_None)
            v0 = space.is_true(w_1)
            if v0 == True:
                w_other_1, w_2 = w_other, w_self
                goto = 3
            else:
                assert v0 == False
                w_self_1, w_other_2, w_coerced = w_self, w_other, w_0
                goto = 2

        if goto == 2:
            w_3 = space.getitem(w_coerced, gi_0)
            w_4 = space.is_(w_3, w_self_1)
            v1 = space.is_true(w_4)
            if v1 == True:
                w_other_1, w_2 = w_other_2, w_self_1
                goto = 3
            else:
                assert v1 == False
                w_coerced_1 = w_coerced
                goto = 5

        if goto == 3:
            w_5 = space.call_function(gfunc_instance_getattr1, w_2, gs___xor__, space.w_False)
            v2 = space.is_true(w_5)
            if v2 == True:
                w_6, w_7 = w_5, w_other_1
                goto = 4
            else:
                assert v2 == False
                w_8 = space.w_NotImplemented
                goto = 6

        if goto == 4:
            w_9 = space.call_function(w_6, w_7)
            w_8 = w_9
            goto = 6

        if goto == 5:
            w_10 = space.getitem(w_coerced_1, gi_0)
            w_11 = space.getitem(w_coerced_1, gi_1)
            w_12 = space.xor(w_10, w_11)
            w_8 = w_12
            goto = 6

        if goto == 6:
            return w_8

  fastf_instance___xor__ = __xor__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__radd__'
## firstlineno 418
##SECTION##
  def __radd__(space, __args__):
    funcname = "__radd__"
    signature = ['self', 'other'], None, None
    defaults_w = []
    w_self, w_other = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___radd__(space, w_self, w_other)

  f_instance___radd__ = __radd__

  def __radd__(space, w_self, w_other):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = fastf__coerce(space, w_self, w_other)
            w_1 = space.is_(w_0, space.w_None)
            v0 = space.is_true(w_1)
            if v0 == True:
                w_other_1, w_2 = w_other, w_self
                goto = 3
            else:
                assert v0 == False
                w_self_1, w_other_2, w_coerced = w_self, w_other, w_0
                goto = 2

        if goto == 2:
            w_3 = space.getitem(w_coerced, gi_0)
            w_4 = space.is_(w_3, w_self_1)
            v1 = space.is_true(w_4)
            if v1 == True:
                w_other_1, w_2 = w_other_2, w_self_1
                goto = 3
            else:
                assert v1 == False
                w_coerced_1 = w_coerced
                goto = 5

        if goto == 3:
            w_5 = space.call_function(gfunc_instance_getattr1, w_2, gs___radd__, space.w_False)
            v2 = space.is_true(w_5)
            if v2 == True:
                w_6, w_7 = w_5, w_other_1
                goto = 4
            else:
                assert v2 == False
                w_8 = space.w_NotImplemented
                goto = 6

        if goto == 4:
            w_9 = space.call_function(w_6, w_7)
            w_8 = w_9
            goto = 6

        if goto == 5:
            w_10 = space.getitem(w_coerced_1, gi_1)
            w_11 = space.getitem(w_coerced_1, gi_0)
            w_12 = space.add(w_10, w_11)
            w_8 = w_12
            goto = 6

        if goto == 6:
            return w_8

  fastf_instance___radd__ = __radd__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__rand__'
## firstlineno 418
##SECTION##
  def __rand__(space, __args__):
    funcname = "__rand__"
    signature = ['self', 'other'], None, None
    defaults_w = []
    w_self, w_other = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___rand__(space, w_self, w_other)

  f_instance___rand__ = __rand__

  def __rand__(space, w_self, w_other):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = fastf__coerce(space, w_self, w_other)
            w_1 = space.is_(w_0, space.w_None)
            v0 = space.is_true(w_1)
            if v0 == True:
                w_other_1, w_2 = w_other, w_self
                goto = 3
            else:
                assert v0 == False
                w_self_1, w_other_2, w_coerced = w_self, w_other, w_0
                goto = 2

        if goto == 2:
            w_3 = space.getitem(w_coerced, gi_0)
            w_4 = space.is_(w_3, w_self_1)
            v1 = space.is_true(w_4)
            if v1 == True:
                w_other_1, w_2 = w_other_2, w_self_1
                goto = 3
            else:
                assert v1 == False
                w_coerced_1 = w_coerced
                goto = 5

        if goto == 3:
            w_5 = space.call_function(gfunc_instance_getattr1, w_2, gs___rand__, space.w_False)
            v2 = space.is_true(w_5)
            if v2 == True:
                w_6, w_7 = w_5, w_other_1
                goto = 4
            else:
                assert v2 == False
                w_8 = space.w_NotImplemented
                goto = 6

        if goto == 4:
            w_9 = space.call_function(w_6, w_7)
            w_8 = w_9
            goto = 6

        if goto == 5:
            w_10 = space.getitem(w_coerced_1, gi_1)
            w_11 = space.getitem(w_coerced_1, gi_0)
            w_12 = space.and_(w_10, w_11)
            w_8 = w_12
            goto = 6

        if goto == 6:
            return w_8

  fastf_instance___rand__ = __rand__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__rdiv__'
## firstlineno 418
##SECTION##
  def __rdiv__(space, __args__):
    funcname = "__rdiv__"
    signature = ['self', 'other'], None, None
    defaults_w = []
    w_self, w_other = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___rdiv__(space, w_self, w_other)

  f_instance___rdiv__ = __rdiv__

  def __rdiv__(space, w_self, w_other):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = fastf__coerce(space, w_self, w_other)
            w_1 = space.is_(w_0, space.w_None)
            v0 = space.is_true(w_1)
            if v0 == True:
                w_other_1, w_2 = w_other, w_self
                goto = 3
            else:
                assert v0 == False
                w_self_1, w_other_2, w_coerced = w_self, w_other, w_0
                goto = 2

        if goto == 2:
            w_3 = space.getitem(w_coerced, gi_0)
            w_4 = space.is_(w_3, w_self_1)
            v1 = space.is_true(w_4)
            if v1 == True:
                w_other_1, w_2 = w_other_2, w_self_1
                goto = 3
            else:
                assert v1 == False
                w_coerced_1 = w_coerced
                goto = 5

        if goto == 3:
            w_5 = space.call_function(gfunc_instance_getattr1, w_2, gs___rdiv__, space.w_False)
            v2 = space.is_true(w_5)
            if v2 == True:
                w_6, w_7 = w_5, w_other_1
                goto = 4
            else:
                assert v2 == False
                w_8 = space.w_NotImplemented
                goto = 6

        if goto == 4:
            w_9 = space.call_function(w_6, w_7)
            w_8 = w_9
            goto = 6

        if goto == 5:
            w_10 = space.getitem(w_coerced_1, gi_1)
            w_11 = space.getitem(w_coerced_1, gi_0)
            w_12 = space.div(w_10, w_11)
            w_8 = w_12
            goto = 6

        if goto == 6:
            return w_8

  fastf_instance___rdiv__ = __rdiv__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__rdivmod__'
## firstlineno 418
##SECTION##
  def __rdivmod__(space, __args__):
    funcname = "__rdivmod__"
    signature = ['self', 'other'], None, None
    defaults_w = []
    w_self, w_other = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___rdivmod__(space, w_self, w_other)

  f_instance___rdivmod__ = __rdivmod__

  def __rdivmod__(space, w_self, w_other):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = fastf__coerce(space, w_self, w_other)
            w_1 = space.is_(w_0, space.w_None)
            v0 = space.is_true(w_1)
            if v0 == True:
                w_other_1, w_2 = w_other, w_self
                goto = 3
            else:
                assert v0 == False
                w_self_1, w_other_2, w_coerced = w_self, w_other, w_0
                goto = 2

        if goto == 2:
            w_3 = space.getitem(w_coerced, gi_0)
            w_4 = space.is_(w_3, w_self_1)
            v1 = space.is_true(w_4)
            if v1 == True:
                w_other_1, w_2 = w_other_2, w_self_1
                goto = 3
            else:
                assert v1 == False
                w_coerced_1 = w_coerced
                goto = 5

        if goto == 3:
            w_5 = space.call_function(gfunc_instance_getattr1, w_2, gs___rdivmod__, space.w_False)
            v2 = space.is_true(w_5)
            if v2 == True:
                w_6, w_7 = w_5, w_other_1
                goto = 4
            else:
                assert v2 == False
                w_8 = space.w_NotImplemented
                goto = 6

        if goto == 4:
            w_9 = space.call_function(w_6, w_7)
            w_8 = w_9
            goto = 6

        if goto == 5:
            w_10 = space.getitem(w_coerced_1, gi_1)
            w_11 = space.getitem(w_coerced_1, gi_0)
            w_12 = space.divmod(w_10, w_11)
            w_8 = w_12
            goto = 6

        if goto == 6:
            return w_8

  fastf_instance___rdivmod__ = __rdivmod__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__rfloordiv__'
## firstlineno 418
##SECTION##
  def __rfloordiv__(space, __args__):
    funcname = "__rfloordiv__"
    signature = ['self', 'other'], None, None
    defaults_w = []
    w_self, w_other = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___rfloordiv__(space, w_self, w_other)

  f_instance___rfloordiv__ = __rfloordiv__

  def __rfloordiv__(space, w_self, w_other):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = fastf__coerce(space, w_self, w_other)
            w_1 = space.is_(w_0, space.w_None)
            v0 = space.is_true(w_1)
            if v0 == True:
                w_other_1, w_2 = w_other, w_self
                goto = 3
            else:
                assert v0 == False
                w_self_1, w_other_2, w_coerced = w_self, w_other, w_0
                goto = 2

        if goto == 2:
            w_3 = space.getitem(w_coerced, gi_0)
            w_4 = space.is_(w_3, w_self_1)
            v1 = space.is_true(w_4)
            if v1 == True:
                w_other_1, w_2 = w_other_2, w_self_1
                goto = 3
            else:
                assert v1 == False
                w_coerced_1 = w_coerced
                goto = 5

        if goto == 3:
            w_5 = space.call_function(gfunc_instance_getattr1, w_2, gs___rfloordiv__, space.w_False)
            v2 = space.is_true(w_5)
            if v2 == True:
                w_6, w_7 = w_5, w_other_1
                goto = 4
            else:
                assert v2 == False
                w_8 = space.w_NotImplemented
                goto = 6

        if goto == 4:
            w_9 = space.call_function(w_6, w_7)
            w_8 = w_9
            goto = 6

        if goto == 5:
            w_10 = space.getitem(w_coerced_1, gi_1)
            w_11 = space.getitem(w_coerced_1, gi_0)
            w_12 = space.floordiv(w_10, w_11)
            w_8 = w_12
            goto = 6

        if goto == 6:
            return w_8

  fastf_instance___rfloordiv__ = __rfloordiv__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__rlshift__'
## firstlineno 418
##SECTION##
  def __rlshift__(space, __args__):
    funcname = "__rlshift__"
    signature = ['self', 'other'], None, None
    defaults_w = []
    w_self, w_other = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___rlshift__(space, w_self, w_other)

  f_instance___rlshift__ = __rlshift__

  def __rlshift__(space, w_self, w_other):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = fastf__coerce(space, w_self, w_other)
            w_1 = space.is_(w_0, space.w_None)
            v0 = space.is_true(w_1)
            if v0 == True:
                w_other_1, w_2 = w_other, w_self
                goto = 3
            else:
                assert v0 == False
                w_self_1, w_other_2, w_coerced = w_self, w_other, w_0
                goto = 2

        if goto == 2:
            w_3 = space.getitem(w_coerced, gi_0)
            w_4 = space.is_(w_3, w_self_1)
            v1 = space.is_true(w_4)
            if v1 == True:
                w_other_1, w_2 = w_other_2, w_self_1
                goto = 3
            else:
                assert v1 == False
                w_coerced_1 = w_coerced
                goto = 5

        if goto == 3:
            w_5 = space.call_function(gfunc_instance_getattr1, w_2, gs___rlshift__, space.w_False)
            v2 = space.is_true(w_5)
            if v2 == True:
                w_6, w_7 = w_5, w_other_1
                goto = 4
            else:
                assert v2 == False
                w_8 = space.w_NotImplemented
                goto = 6

        if goto == 4:
            w_9 = space.call_function(w_6, w_7)
            w_8 = w_9
            goto = 6

        if goto == 5:
            w_10 = space.getitem(w_coerced_1, gi_1)
            w_11 = space.getitem(w_coerced_1, gi_0)
            w_12 = space.lshift(w_10, w_11)
            w_8 = w_12
            goto = 6

        if goto == 6:
            return w_8

  fastf_instance___rlshift__ = __rlshift__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__rmod__'
## firstlineno 418
##SECTION##
  def __rmod__(space, __args__):
    funcname = "__rmod__"
    signature = ['self', 'other'], None, None
    defaults_w = []
    w_self, w_other = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___rmod__(space, w_self, w_other)

  f_instance___rmod__ = __rmod__

  def __rmod__(space, w_self, w_other):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = fastf__coerce(space, w_self, w_other)
            w_1 = space.is_(w_0, space.w_None)
            v0 = space.is_true(w_1)
            if v0 == True:
                w_other_1, w_2 = w_other, w_self
                goto = 3
            else:
                assert v0 == False
                w_self_1, w_other_2, w_coerced = w_self, w_other, w_0
                goto = 2

        if goto == 2:
            w_3 = space.getitem(w_coerced, gi_0)
            w_4 = space.is_(w_3, w_self_1)
            v1 = space.is_true(w_4)
            if v1 == True:
                w_other_1, w_2 = w_other_2, w_self_1
                goto = 3
            else:
                assert v1 == False
                w_coerced_1 = w_coerced
                goto = 5

        if goto == 3:
            w_5 = space.call_function(gfunc_instance_getattr1, w_2, gs___rmod__, space.w_False)
            v2 = space.is_true(w_5)
            if v2 == True:
                w_6, w_7 = w_5, w_other_1
                goto = 4
            else:
                assert v2 == False
                w_8 = space.w_NotImplemented
                goto = 6

        if goto == 4:
            w_9 = space.call_function(w_6, w_7)
            w_8 = w_9
            goto = 6

        if goto == 5:
            w_10 = space.getitem(w_coerced_1, gi_1)
            w_11 = space.getitem(w_coerced_1, gi_0)
            w_12 = space.mod(w_10, w_11)
            w_8 = w_12
            goto = 6

        if goto == 6:
            return w_8

  fastf_instance___rmod__ = __rmod__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__rmul__'
## firstlineno 418
##SECTION##
  def __rmul__(space, __args__):
    funcname = "__rmul__"
    signature = ['self', 'other'], None, None
    defaults_w = []
    w_self, w_other = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___rmul__(space, w_self, w_other)

  f_instance___rmul__ = __rmul__

  def __rmul__(space, w_self, w_other):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = fastf__coerce(space, w_self, w_other)
            w_1 = space.is_(w_0, space.w_None)
            v0 = space.is_true(w_1)
            if v0 == True:
                w_other_1, w_2 = w_other, w_self
                goto = 3
            else:
                assert v0 == False
                w_self_1, w_other_2, w_coerced = w_self, w_other, w_0
                goto = 2

        if goto == 2:
            w_3 = space.getitem(w_coerced, gi_0)
            w_4 = space.is_(w_3, w_self_1)
            v1 = space.is_true(w_4)
            if v1 == True:
                w_other_1, w_2 = w_other_2, w_self_1
                goto = 3
            else:
                assert v1 == False
                w_coerced_1 = w_coerced
                goto = 5

        if goto == 3:
            w_5 = space.call_function(gfunc_instance_getattr1, w_2, gs___rmul__, space.w_False)
            v2 = space.is_true(w_5)
            if v2 == True:
                w_6, w_7 = w_5, w_other_1
                goto = 4
            else:
                assert v2 == False
                w_8 = space.w_NotImplemented
                goto = 6

        if goto == 4:
            w_9 = space.call_function(w_6, w_7)
            w_8 = w_9
            goto = 6

        if goto == 5:
            w_10 = space.getitem(w_coerced_1, gi_1)
            w_11 = space.getitem(w_coerced_1, gi_0)
            w_12 = space.mul(w_10, w_11)
            w_8 = w_12
            goto = 6

        if goto == 6:
            return w_8

  fastf_instance___rmul__ = __rmul__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__ror__'
## firstlineno 418
##SECTION##
  def __ror__(space, __args__):
    funcname = "__ror__"
    signature = ['self', 'other'], None, None
    defaults_w = []
    w_self, w_other = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___ror__(space, w_self, w_other)

  f_instance___ror__ = __ror__

  def __ror__(space, w_self, w_other):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = fastf__coerce(space, w_self, w_other)
            w_1 = space.is_(w_0, space.w_None)
            v0 = space.is_true(w_1)
            if v0 == True:
                w_other_1, w_2 = w_other, w_self
                goto = 3
            else:
                assert v0 == False
                w_self_1, w_other_2, w_coerced = w_self, w_other, w_0
                goto = 2

        if goto == 2:
            w_3 = space.getitem(w_coerced, gi_0)
            w_4 = space.is_(w_3, w_self_1)
            v1 = space.is_true(w_4)
            if v1 == True:
                w_other_1, w_2 = w_other_2, w_self_1
                goto = 3
            else:
                assert v1 == False
                w_coerced_1 = w_coerced
                goto = 5

        if goto == 3:
            w_5 = space.call_function(gfunc_instance_getattr1, w_2, gs___ror__, space.w_False)
            v2 = space.is_true(w_5)
            if v2 == True:
                w_6, w_7 = w_5, w_other_1
                goto = 4
            else:
                assert v2 == False
                w_8 = space.w_NotImplemented
                goto = 6

        if goto == 4:
            w_9 = space.call_function(w_6, w_7)
            w_8 = w_9
            goto = 6

        if goto == 5:
            w_10 = space.getitem(w_coerced_1, gi_1)
            w_11 = space.getitem(w_coerced_1, gi_0)
            w_12 = space.or_(w_10, w_11)
            w_8 = w_12
            goto = 6

        if goto == 6:
            return w_8

  fastf_instance___ror__ = __ror__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__rrshift__'
## firstlineno 418
##SECTION##
  def __rrshift__(space, __args__):
    funcname = "__rrshift__"
    signature = ['self', 'other'], None, None
    defaults_w = []
    w_self, w_other = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___rrshift__(space, w_self, w_other)

  f_instance___rrshift__ = __rrshift__

  def __rrshift__(space, w_self, w_other):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = fastf__coerce(space, w_self, w_other)
            w_1 = space.is_(w_0, space.w_None)
            v0 = space.is_true(w_1)
            if v0 == True:
                w_other_1, w_2 = w_other, w_self
                goto = 3
            else:
                assert v0 == False
                w_self_1, w_other_2, w_coerced = w_self, w_other, w_0
                goto = 2

        if goto == 2:
            w_3 = space.getitem(w_coerced, gi_0)
            w_4 = space.is_(w_3, w_self_1)
            v1 = space.is_true(w_4)
            if v1 == True:
                w_other_1, w_2 = w_other_2, w_self_1
                goto = 3
            else:
                assert v1 == False
                w_coerced_1 = w_coerced
                goto = 5

        if goto == 3:
            w_5 = space.call_function(gfunc_instance_getattr1, w_2, gs___rrshift__, space.w_False)
            v2 = space.is_true(w_5)
            if v2 == True:
                w_6, w_7 = w_5, w_other_1
                goto = 4
            else:
                assert v2 == False
                w_8 = space.w_NotImplemented
                goto = 6

        if goto == 4:
            w_9 = space.call_function(w_6, w_7)
            w_8 = w_9
            goto = 6

        if goto == 5:
            w_10 = space.getitem(w_coerced_1, gi_1)
            w_11 = space.getitem(w_coerced_1, gi_0)
            w_12 = space.rshift(w_10, w_11)
            w_8 = w_12
            goto = 6

        if goto == 6:
            return w_8

  fastf_instance___rrshift__ = __rrshift__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__rsub__'
## firstlineno 418
##SECTION##
  def __rsub__(space, __args__):
    funcname = "__rsub__"
    signature = ['self', 'other'], None, None
    defaults_w = []
    w_self, w_other = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___rsub__(space, w_self, w_other)

  f_instance___rsub__ = __rsub__

  def __rsub__(space, w_self, w_other):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = fastf__coerce(space, w_self, w_other)
            w_1 = space.is_(w_0, space.w_None)
            v0 = space.is_true(w_1)
            if v0 == True:
                w_other_1, w_2 = w_other, w_self
                goto = 3
            else:
                assert v0 == False
                w_self_1, w_other_2, w_coerced = w_self, w_other, w_0
                goto = 2

        if goto == 2:
            w_3 = space.getitem(w_coerced, gi_0)
            w_4 = space.is_(w_3, w_self_1)
            v1 = space.is_true(w_4)
            if v1 == True:
                w_other_1, w_2 = w_other_2, w_self_1
                goto = 3
            else:
                assert v1 == False
                w_coerced_1 = w_coerced
                goto = 5

        if goto == 3:
            w_5 = space.call_function(gfunc_instance_getattr1, w_2, gs___rsub__, space.w_False)
            v2 = space.is_true(w_5)
            if v2 == True:
                w_6, w_7 = w_5, w_other_1
                goto = 4
            else:
                assert v2 == False
                w_8 = space.w_NotImplemented
                goto = 6

        if goto == 4:
            w_9 = space.call_function(w_6, w_7)
            w_8 = w_9
            goto = 6

        if goto == 5:
            w_10 = space.getitem(w_coerced_1, gi_1)
            w_11 = space.getitem(w_coerced_1, gi_0)
            w_12 = space.sub(w_10, w_11)
            w_8 = w_12
            goto = 6

        if goto == 6:
            return w_8

  fastf_instance___rsub__ = __rsub__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__rtruediv__'
## firstlineno 418
##SECTION##
  def __rtruediv__(space, __args__):
    funcname = "__rtruediv__"
    signature = ['self', 'other'], None, None
    defaults_w = []
    w_self, w_other = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___rtruediv__(space, w_self, w_other)

  f_instance___rtruediv__ = __rtruediv__

  def __rtruediv__(space, w_self, w_other):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = fastf__coerce(space, w_self, w_other)
            w_1 = space.is_(w_0, space.w_None)
            v0 = space.is_true(w_1)
            if v0 == True:
                w_other_1, w_2 = w_other, w_self
                goto = 3
            else:
                assert v0 == False
                w_self_1, w_other_2, w_coerced = w_self, w_other, w_0
                goto = 2

        if goto == 2:
            w_3 = space.getitem(w_coerced, gi_0)
            w_4 = space.is_(w_3, w_self_1)
            v1 = space.is_true(w_4)
            if v1 == True:
                w_other_1, w_2 = w_other_2, w_self_1
                goto = 3
            else:
                assert v1 == False
                w_coerced_1 = w_coerced
                goto = 5

        if goto == 3:
            w_5 = space.call_function(gfunc_instance_getattr1, w_2, gs___rtruediv__, space.w_False)
            v2 = space.is_true(w_5)
            if v2 == True:
                w_6, w_7 = w_5, w_other_1
                goto = 4
            else:
                assert v2 == False
                w_8 = space.w_NotImplemented
                goto = 6

        if goto == 4:
            w_9 = space.call_function(w_6, w_7)
            w_8 = w_9
            goto = 6

        if goto == 5:
            w_10 = space.getitem(w_coerced_1, gi_1)
            w_11 = space.getitem(w_coerced_1, gi_0)
            w_12 = space.truediv(w_10, w_11)
            w_8 = w_12
            goto = 6

        if goto == 6:
            return w_8

  fastf_instance___rtruediv__ = __rtruediv__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__rxor__'
## firstlineno 418
##SECTION##
  def __rxor__(space, __args__):
    funcname = "__rxor__"
    signature = ['self', 'other'], None, None
    defaults_w = []
    w_self, w_other = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___rxor__(space, w_self, w_other)

  f_instance___rxor__ = __rxor__

  def __rxor__(space, w_self, w_other):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = fastf__coerce(space, w_self, w_other)
            w_1 = space.is_(w_0, space.w_None)
            v0 = space.is_true(w_1)
            if v0 == True:
                w_other_1, w_2 = w_other, w_self
                goto = 3
            else:
                assert v0 == False
                w_self_1, w_other_2, w_coerced = w_self, w_other, w_0
                goto = 2

        if goto == 2:
            w_3 = space.getitem(w_coerced, gi_0)
            w_4 = space.is_(w_3, w_self_1)
            v1 = space.is_true(w_4)
            if v1 == True:
                w_other_1, w_2 = w_other_2, w_self_1
                goto = 3
            else:
                assert v1 == False
                w_coerced_1 = w_coerced
                goto = 5

        if goto == 3:
            w_5 = space.call_function(gfunc_instance_getattr1, w_2, gs___rxor__, space.w_False)
            v2 = space.is_true(w_5)
            if v2 == True:
                w_6, w_7 = w_5, w_other_1
                goto = 4
            else:
                assert v2 == False
                w_8 = space.w_NotImplemented
                goto = 6

        if goto == 4:
            w_9 = space.call_function(w_6, w_7)
            w_8 = w_9
            goto = 6

        if goto == 5:
            w_10 = space.getitem(w_coerced_1, gi_1)
            w_11 = space.getitem(w_coerced_1, gi_0)
            w_12 = space.xor(w_10, w_11)
            w_8 = w_12
            goto = 6

        if goto == 6:
            return w_8

  fastf_instance___rxor__ = __rxor__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__iadd__'
## firstlineno 436
##SECTION##
  def __iadd__(space, __args__):
    funcname = "__iadd__"
    signature = ['self', 'other'], None, None
    defaults_w = []
    w_self, w_other = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___iadd__(space, w_self, w_other)

  f_instance___iadd__ = __iadd__

  def __iadd__(space, w_self, w_other):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.call_function(gfunc_instance_getattr1, w_self, gs___iadd__, space.w_False)
            v0 = space.is_true(w_0)
            if v0 == True:
                w_1, w_2 = w_0, w_other
                goto = 2
            else:
                assert v0 == False
                w_3 = space.w_NotImplemented
                goto = 3

        if goto == 2:
            w_4 = space.call_function(w_1, w_2)
            w_3 = w_4
            goto = 3

        if goto == 3:
            return w_3

  fastf_instance___iadd__ = __iadd__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__iand__'
## firstlineno 436
##SECTION##
  def __iand__(space, __args__):
    funcname = "__iand__"
    signature = ['self', 'other'], None, None
    defaults_w = []
    w_self, w_other = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___iand__(space, w_self, w_other)

  f_instance___iand__ = __iand__

  def __iand__(space, w_self, w_other):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.call_function(gfunc_instance_getattr1, w_self, gs___iand__, space.w_False)
            v0 = space.is_true(w_0)
            if v0 == True:
                w_1, w_2 = w_0, w_other
                goto = 2
            else:
                assert v0 == False
                w_3 = space.w_NotImplemented
                goto = 3

        if goto == 2:
            w_4 = space.call_function(w_1, w_2)
            w_3 = w_4
            goto = 3

        if goto == 3:
            return w_3

  fastf_instance___iand__ = __iand__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__idiv__'
## firstlineno 436
##SECTION##
  def __idiv__(space, __args__):
    funcname = "__idiv__"
    signature = ['self', 'other'], None, None
    defaults_w = []
    w_self, w_other = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___idiv__(space, w_self, w_other)

  f_instance___idiv__ = __idiv__

  def __idiv__(space, w_self, w_other):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.call_function(gfunc_instance_getattr1, w_self, gs___idiv__, space.w_False)
            v0 = space.is_true(w_0)
            if v0 == True:
                w_1, w_2 = w_0, w_other
                goto = 2
            else:
                assert v0 == False
                w_3 = space.w_NotImplemented
                goto = 3

        if goto == 2:
            w_4 = space.call_function(w_1, w_2)
            w_3 = w_4
            goto = 3

        if goto == 3:
            return w_3

  fastf_instance___idiv__ = __idiv__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__ifloordiv__'
## firstlineno 436
##SECTION##
  def __ifloordiv__(space, __args__):
    funcname = "__ifloordiv__"
    signature = ['self', 'other'], None, None
    defaults_w = []
    w_self, w_other = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___ifloordiv__(space, w_self, w_other)

  f_instance___ifloordiv__ = __ifloordiv__

  def __ifloordiv__(space, w_self, w_other):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.call_function(gfunc_instance_getattr1, w_self, gs___ifloordiv__, space.w_False)
            v0 = space.is_true(w_0)
            if v0 == True:
                w_1, w_2 = w_0, w_other
                goto = 2
            else:
                assert v0 == False
                w_3 = space.w_NotImplemented
                goto = 3

        if goto == 2:
            w_4 = space.call_function(w_1, w_2)
            w_3 = w_4
            goto = 3

        if goto == 3:
            return w_3

  fastf_instance___ifloordiv__ = __ifloordiv__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__ilshift__'
## firstlineno 436
##SECTION##
  def __ilshift__(space, __args__):
    funcname = "__ilshift__"
    signature = ['self', 'other'], None, None
    defaults_w = []
    w_self, w_other = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___ilshift__(space, w_self, w_other)

  f_instance___ilshift__ = __ilshift__

  def __ilshift__(space, w_self, w_other):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.call_function(gfunc_instance_getattr1, w_self, gs___ilshift__, space.w_False)
            v0 = space.is_true(w_0)
            if v0 == True:
                w_1, w_2 = w_0, w_other
                goto = 2
            else:
                assert v0 == False
                w_3 = space.w_NotImplemented
                goto = 3

        if goto == 2:
            w_4 = space.call_function(w_1, w_2)
            w_3 = w_4
            goto = 3

        if goto == 3:
            return w_3

  fastf_instance___ilshift__ = __ilshift__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__imod__'
## firstlineno 436
##SECTION##
  def __imod__(space, __args__):
    funcname = "__imod__"
    signature = ['self', 'other'], None, None
    defaults_w = []
    w_self, w_other = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___imod__(space, w_self, w_other)

  f_instance___imod__ = __imod__

  def __imod__(space, w_self, w_other):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.call_function(gfunc_instance_getattr1, w_self, gs___imod__, space.w_False)
            v0 = space.is_true(w_0)
            if v0 == True:
                w_1, w_2 = w_0, w_other
                goto = 2
            else:
                assert v0 == False
                w_3 = space.w_NotImplemented
                goto = 3

        if goto == 2:
            w_4 = space.call_function(w_1, w_2)
            w_3 = w_4
            goto = 3

        if goto == 3:
            return w_3

  fastf_instance___imod__ = __imod__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__imul__'
## firstlineno 436
##SECTION##
  def __imul__(space, __args__):
    funcname = "__imul__"
    signature = ['self', 'other'], None, None
    defaults_w = []
    w_self, w_other = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___imul__(space, w_self, w_other)

  f_instance___imul__ = __imul__

  def __imul__(space, w_self, w_other):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.call_function(gfunc_instance_getattr1, w_self, gs___imul__, space.w_False)
            v0 = space.is_true(w_0)
            if v0 == True:
                w_1, w_2 = w_0, w_other
                goto = 2
            else:
                assert v0 == False
                w_3 = space.w_NotImplemented
                goto = 3

        if goto == 2:
            w_4 = space.call_function(w_1, w_2)
            w_3 = w_4
            goto = 3

        if goto == 3:
            return w_3

  fastf_instance___imul__ = __imul__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__ior__'
## firstlineno 436
##SECTION##
  def __ior__(space, __args__):
    funcname = "__ior__"
    signature = ['self', 'other'], None, None
    defaults_w = []
    w_self, w_other = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___ior__(space, w_self, w_other)

  f_instance___ior__ = __ior__

  def __ior__(space, w_self, w_other):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.call_function(gfunc_instance_getattr1, w_self, gs___ior__, space.w_False)
            v0 = space.is_true(w_0)
            if v0 == True:
                w_1, w_2 = w_0, w_other
                goto = 2
            else:
                assert v0 == False
                w_3 = space.w_NotImplemented
                goto = 3

        if goto == 2:
            w_4 = space.call_function(w_1, w_2)
            w_3 = w_4
            goto = 3

        if goto == 3:
            return w_3

  fastf_instance___ior__ = __ior__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__ipow__'
## firstlineno 436
##SECTION##
  def __ipow__(space, __args__):
    funcname = "__ipow__"
    signature = ['self', 'other'], None, None
    defaults_w = []
    w_self, w_other = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___ipow__(space, w_self, w_other)

  f_instance___ipow__ = __ipow__

  def __ipow__(space, w_self, w_other):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.call_function(gfunc_instance_getattr1, w_self, gs___ipow__, space.w_False)
            v0 = space.is_true(w_0)
            if v0 == True:
                w_1, w_2 = w_0, w_other
                goto = 2
            else:
                assert v0 == False
                w_3 = space.w_NotImplemented
                goto = 3

        if goto == 2:
            w_4 = space.call_function(w_1, w_2)
            w_3 = w_4
            goto = 3

        if goto == 3:
            return w_3

  fastf_instance___ipow__ = __ipow__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__irshift__'
## firstlineno 436
##SECTION##
  def __irshift__(space, __args__):
    funcname = "__irshift__"
    signature = ['self', 'other'], None, None
    defaults_w = []
    w_self, w_other = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___irshift__(space, w_self, w_other)

  f_instance___irshift__ = __irshift__

  def __irshift__(space, w_self, w_other):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.call_function(gfunc_instance_getattr1, w_self, gs___irshift__, space.w_False)
            v0 = space.is_true(w_0)
            if v0 == True:
                w_1, w_2 = w_0, w_other
                goto = 2
            else:
                assert v0 == False
                w_3 = space.w_NotImplemented
                goto = 3

        if goto == 2:
            w_4 = space.call_function(w_1, w_2)
            w_3 = w_4
            goto = 3

        if goto == 3:
            return w_3

  fastf_instance___irshift__ = __irshift__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__isub__'
## firstlineno 436
##SECTION##
  def __isub__(space, __args__):
    funcname = "__isub__"
    signature = ['self', 'other'], None, None
    defaults_w = []
    w_self, w_other = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___isub__(space, w_self, w_other)

  f_instance___isub__ = __isub__

  def __isub__(space, w_self, w_other):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.call_function(gfunc_instance_getattr1, w_self, gs___isub__, space.w_False)
            v0 = space.is_true(w_0)
            if v0 == True:
                w_1, w_2 = w_0, w_other
                goto = 2
            else:
                assert v0 == False
                w_3 = space.w_NotImplemented
                goto = 3

        if goto == 2:
            w_4 = space.call_function(w_1, w_2)
            w_3 = w_4
            goto = 3

        if goto == 3:
            return w_3

  fastf_instance___isub__ = __isub__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__itruediv__'
## firstlineno 436
##SECTION##
  def __itruediv__(space, __args__):
    funcname = "__itruediv__"
    signature = ['self', 'other'], None, None
    defaults_w = []
    w_self, w_other = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___itruediv__(space, w_self, w_other)

  f_instance___itruediv__ = __itruediv__

  def __itruediv__(space, w_self, w_other):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.call_function(gfunc_instance_getattr1, w_self, gs___itruediv__, space.w_False)
            v0 = space.is_true(w_0)
            if v0 == True:
                w_1, w_2 = w_0, w_other
                goto = 2
            else:
                assert v0 == False
                w_3 = space.w_NotImplemented
                goto = 3

        if goto == 2:
            w_4 = space.call_function(w_1, w_2)
            w_3 = w_4
            goto = 3

        if goto == 3:
            return w_3

  fastf_instance___itruediv__ = __itruediv__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__ixor__'
## firstlineno 436
##SECTION##
  def __ixor__(space, __args__):
    funcname = "__ixor__"
    signature = ['self', 'other'], None, None
    defaults_w = []
    w_self, w_other = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___ixor__(space, w_self, w_other)

  f_instance___ixor__ = __ixor__

  def __ixor__(space, w_self, w_other):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.call_function(gfunc_instance_getattr1, w_self, gs___ixor__, space.w_False)
            v0 = space.is_true(w_0)
            if v0 == True:
                w_1, w_2 = w_0, w_other
                goto = 2
            else:
                assert v0 == False
                w_3 = space.w_NotImplemented
                goto = 3

        if goto == 2:
            w_4 = space.call_function(w_1, w_2)
            w_3 = w_4
            goto = 3

        if goto == 3:
            return w_3

  fastf_instance___ixor__ = __ixor__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__pow__'
## firstlineno 445
##SECTION##
  def __pow__(space, __args__):
    funcname = "__pow__"
    signature = ['self', 'other', 'modulo'], None, None
    defaults_w = [space.w_None]
    w_self, w_other, w_modulo = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___pow__(space, w_self, w_other, w_modulo)

  f_instance___pow__ = __pow__

  def __pow__(space, w_self, w_other, w_modulo):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.is_(w_modulo, space.w_None)
            v0 = space.is_true(w_0)
            if v0 == True:
                w_self_1, w_other_1 = w_self, w_other
                goto = 2
            else:
                assert v0 == False
                w_other_2, w_modulo_1, w_1 = w_other, w_modulo, w_self
                goto = 7

        if goto == 2:
            w_2 = fastf__coerce(space, w_self_1, w_other_1)
            w_3 = space.is_(w_2, space.w_None)
            v1 = space.is_true(w_3)
            if v1 == True:
                w_other_3, w_4 = w_other_1, w_self_1
                goto = 4
            else:
                assert v1 == False
                w_self_2, w_other_4, w_coerced = w_self_1, w_other_1, w_2
                goto = 3

        if goto == 3:
            w_5 = space.getitem(w_coerced, gi_0)
            w_6 = space.is_(w_5, w_self_2)
            v2 = space.is_true(w_6)
            if v2 == True:
                w_other_3, w_4 = w_other_4, w_self_2
                goto = 4
            else:
                assert v2 == False
                w_coerced_1 = w_coerced
                goto = 6

        if goto == 4:
            w_7 = space.call_function(gfunc_instance_getattr1, w_4, gs___pow__, space.w_False)
            v3 = space.is_true(w_7)
            if v3 == True:
                w_8, w_9 = w_7, w_other_3
                goto = 5
            else:
                assert v3 == False
                w_10 = space.w_NotImplemented
                goto = 9

        if goto == 5:
            w_11 = space.call_function(w_8, w_9)
            w_10 = w_11
            goto = 9

        if goto == 6:
            w_12 = space.getitem(w_coerced_1, gi_0)
            w_13 = space.getitem(w_coerced_1, gi_1)
            w_14 = space.pow(w_12, w_13, space.w_None)
            w_10 = w_14
            goto = 9

        if goto == 7:
            w_15 = space.call_function(gfunc_instance_getattr1, w_1, gs___pow__, space.w_False)
            v4 = space.is_true(w_15)
            if v4 == True:
                w_16, w_17, w_18 = w_15, w_other_2, w_modulo_1
                goto = 8
            else:
                assert v4 == False
                w_10 = space.w_NotImplemented
                goto = 9

        if goto == 8:
            w_19 = space.call_function(w_16, w_17, w_18)
            w_10 = w_19
            goto = 9

        if goto == 9:
            return w_10

  fastf_instance___pow__ = __pow__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__rpow__'
## firstlineno 463
##SECTION##
  def __rpow__(space, __args__):
    funcname = "__rpow__"
    signature = ['self', 'other', 'modulo'], None, None
    defaults_w = [space.w_None]
    w_self, w_other, w_modulo = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___rpow__(space, w_self, w_other, w_modulo)

  f_instance___rpow__ = __rpow__

  def __rpow__(space, w_self, w_other, w_modulo):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.is_(w_modulo, space.w_None)
            v0 = space.is_true(w_0)
            if v0 == True:
                w_self_1, w_other_1 = w_self, w_other
                goto = 2
            else:
                assert v0 == False
                w_other_2, w_modulo_1, w_1 = w_other, w_modulo, w_self
                goto = 7

        if goto == 2:
            w_2 = fastf__coerce(space, w_self_1, w_other_1)
            w_3 = space.is_(w_2, space.w_None)
            v1 = space.is_true(w_3)
            if v1 == True:
                w_other_3, w_4 = w_other_1, w_self_1
                goto = 4
            else:
                assert v1 == False
                w_self_2, w_other_4, w_coerced = w_self_1, w_other_1, w_2
                goto = 3

        if goto == 3:
            w_5 = space.getitem(w_coerced, gi_0)
            w_6 = space.is_(w_5, w_self_2)
            v2 = space.is_true(w_6)
            if v2 == True:
                w_other_3, w_4 = w_other_4, w_self_2
                goto = 4
            else:
                assert v2 == False
                w_coerced_1 = w_coerced
                goto = 6

        if goto == 4:
            w_7 = space.call_function(gfunc_instance_getattr1, w_4, gs___rpow__, space.w_False)
            v3 = space.is_true(w_7)
            if v3 == True:
                w_8, w_9 = w_7, w_other_3
                goto = 5
            else:
                assert v3 == False
                w_10 = space.w_NotImplemented
                goto = 9

        if goto == 5:
            w_11 = space.call_function(w_8, w_9)
            w_10 = w_11
            goto = 9

        if goto == 6:
            w_12 = space.getitem(w_coerced_1, gi_1)
            w_13 = space.getitem(w_coerced_1, gi_0)
            w_14 = space.pow(w_12, w_13, space.w_None)
            w_10 = w_14
            goto = 9

        if goto == 7:
            w_15 = space.call_function(gfunc_instance_getattr1, w_1, gs___rpow__, space.w_False)
            v4 = space.is_true(w_15)
            if v4 == True:
                w_16, w_17, w_18 = w_15, w_other_2, w_modulo_1
                goto = 8
            else:
                assert v4 == False
                w_10 = space.w_NotImplemented
                goto = 9

        if goto == 8:
            w_19 = space.call_function(w_16, w_17, w_18)
            w_10 = w_19
            goto = 9

        if goto == 9:
            return w_10

  fastf_instance___rpow__ = __rpow__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__nonzero__'
## firstlineno 481
##SECTION##
# global declarations
# global object gs___nonzero_____should_return____0
# global object gs___nonzero_____should_return_an_i

  def __nonzero__(space, __args__):
    funcname = "__nonzero__"
    signature = ['self'], None, None
    defaults_w = []
    w_self, = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___nonzero__(space, w_self)

  f_instance___nonzero__ = __nonzero__

  def __nonzero__(space, w_self):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.call_function(gfunc_instance_getattr1, w_self, gs___nonzero__, space.w_False)
            v0 = space.is_true(w_0)
            if v0 == True:
                w_1 = w_0
                goto = 3
            else:
                assert v0 == False
                w_2 = w_self
                goto = 2

        if goto == 2:
            w_3 = space.call_function(gfunc_instance_getattr1, w_2, gs___nonzero__, space.w_False)
            v1 = space.is_true(w_3)
            if v1 == True:
                w_1 = w_3
                goto = 3
            else:
                assert v1 == False
                w_4 = space.w_True
                goto = 13

        if goto == 3:
            w_5 = space.call_function(w_1, )
            w_6 = space.isinstance(w_5, space.w_int)
            v2 = space.is_true(w_6)
            if v2 == True:
                w_ret = w_5
                goto = 4
            else:
                assert v2 == False
                goto = 11

        if goto == 4:
            w_7 = space.lt(w_ret, gi_0)
            v3 = space.is_true(w_7)
            if v3 == True:
                goto = 5
            else:
                assert v3 == False
                w_8 = w_ret
                goto = 10

        if goto == 5:
            w_9 = space.call_function(space.w_ValueError, gs___nonzero_____should_return____0)
            w_10 = space.type(w_9)
            w_11 = space.issubtype(w_10, space.w_type)
            v4 = space.is_true(w_11)
            if v4 == True:
                w_12 = w_9
                goto = 9
            else:
                assert v4 == False
                w_13 = w_9
                goto = 8

        if goto == 6:
            w_14 = space.type(w_15)
            w_etype, w_evalue = w_14, w_15
            goto = 12

        if goto == 7:
            w_17 = space.call_function(w_16, )
            w_18 = space.type(w_17)
            w_etype, w_evalue = w_18, w_17
            goto = 12

        if goto == 8:
            w_19 = space.type(w_13)
            w_etype, w_evalue = w_19, w_13
            goto = 12

        if goto == 9:
            w_20 = space.call_function(w_12, )
            w_21 = space.type(w_20)
            w_etype, w_evalue = w_21, w_20
            goto = 12

        if goto == 10:
            w_22 = space.gt(w_8, gi_0)
            w_4 = w_22
            goto = 13

        if goto == 11:
            w_23 = space.call_function(space.w_TypeError, gs___nonzero_____should_return_an_i)
            w_24 = space.type(w_23)
            w_25 = space.issubtype(w_24, space.w_type)
            v5 = space.is_true(w_25)
            if v5 == True:
                w_16 = w_23
                goto = 7
                continue
            else:
                assert v5 == False
                w_15 = w_23
                goto = 6
                continue

        if goto == 12:
            raise gOperationError(w_etype, w_evalue)

        if goto == 13:
            return w_4

  fastf_instance___nonzero__ = __nonzero__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__call__'
## firstlineno 496
##SECTION##
# global declaration
# global object gs__s_instance_has_no___call___meth

  def __call__(space, __args__):
    funcname = "__call__"
    signature = ['self'], 'args', 'kwds'
    defaults_w = []
    w_self, w_args, w_kwds = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___call__(space, w_self, w_args, w_kwds)

  f_instance___call__ = __call__

  def __call__(space, w_self, w_args, w_kwds):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.call_function(gfunc_instance_getattr1, w_self, gs___call__, space.w_False)
            v0 = space.is_true(w_0)
            if v0 == True:
                w_1, w_2, w_3 = w_0, w_args, w_kwds
                goto = 6
            else:
                assert v0 == False
                w_4 = w_self
                goto = 2

        if goto == 2:
            w_5 = space.getattr(w_4, gs___class__)
            w_6 = space.getattr(w_5, gs___name__)
            w_7 = space.mod(gs__s_instance_has_no___call___meth, w_6)
            w_8 = space.is_(w_7, space.w_None)
            v1 = space.is_true(w_8)
            if v1 == True:
                goto = 3
            else:
                assert v1 == False
                w_9 = w_7
                goto = 4

        if goto == 3:
            w_10 = space.call_function(space.w_AttributeError, )
            w_11 = space.type(w_10)
            w_etype, w_evalue = w_11, w_10
            goto = 7

        if goto == 4:
            w_12 = space.type(w_9)
            w_13 = space.issubtype(w_12, space.w_AttributeError)
            v2 = space.is_true(w_13)
            if v2 == True:
                w_etype, w_evalue = w_12, w_9
                goto = 7
            else:
                assert v2 == False
                w_14 = w_9
                goto = 5

        if goto == 5:
            w_15 = space.call_function(space.w_AttributeError, w_14)
            w_16 = space.type(w_15)
            w_etype, w_evalue = w_16, w_15
            goto = 7

        if goto == 6:
            _args = gateway.Arguments.fromshape(space, (0, (), True, True), [w_2, w_3])
            w_17 = space.call_args(w_1, _args)
            w_18 = w_17
            goto = 8

        if goto == 7:
            raise gOperationError(w_etype, w_evalue)

        if goto == 8:
            return w_18

  fastf_instance___call__ = __call__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__eq__'
## firstlineno 507
##SECTION##
  def __eq__(space, __args__):
    funcname = "__eq__"
    signature = ['self', 'other'], None, None
    defaults_w = []
    w_self, w_other = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___eq__(space, w_self, w_other)

  f_instance___eq__ = __eq__

  def __eq__(space, w_self, w_other):
    goto = 1 # startblock
    while True:

        if goto == 1:
            try:
                w_0 = space.call_function(gfunc_instance_getattr1, w_self, gs___eq__)
                w_1, w_2 = w_0, w_other
                goto = 2
            except gOperationError, e:
                e.normalize_exception(space)
                if space.is_true(space.issubtype(e.w_type, space.w_Exception)):
                    w_3, w_4 = e.w_type, e.w_value
                    goto = 3
                else:raise # unhandled case, should not happen

        if goto == 2:
            try:
                w_5 = space.call_function(w_1, w_2)
                w_6 = w_5
                goto = 6
            except gOperationError, e:
                e.normalize_exception(space)
                if space.is_true(space.issubtype(e.w_type, space.w_Exception)):
                    w_3, w_4 = e.w_type, e.w_value
                    goto = 3
                else:raise # unhandled case, should not happen

        if goto == 3:
            w_7 = space.is_(w_3, space.w_AttributeError)
            v0 = space.is_true(w_7)
            if v0 == True:
                w_6 = space.w_NotImplemented
                goto = 6
            else:
                assert v0 == False
                w_8, w_9 = w_3, w_4
                goto = 4

        if goto == 4:
            w_10 = space.issubtype(w_8, space.w_AttributeError)
            v1 = space.is_true(w_10)
            if v1 == True:
                w_6 = space.w_NotImplemented
                goto = 6
            else:
                assert v1 == False
                w_etype, w_evalue = w_8, w_9
                goto = 5

        if goto == 5:
            raise gOperationError(w_etype, w_evalue)

        if goto == 6:
            return w_6

  fastf_instance___eq__ = __eq__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__ge__'
## firstlineno 507
##SECTION##
  def __ge__(space, __args__):
    funcname = "__ge__"
    signature = ['self', 'other'], None, None
    defaults_w = []
    w_self, w_other = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___ge__(space, w_self, w_other)

  f_instance___ge__ = __ge__

  def __ge__(space, w_self, w_other):
    goto = 1 # startblock
    while True:

        if goto == 1:
            try:
                w_0 = space.call_function(gfunc_instance_getattr1, w_self, gs___ge__)
                w_1, w_2 = w_0, w_other
                goto = 2
            except gOperationError, e:
                e.normalize_exception(space)
                if space.is_true(space.issubtype(e.w_type, space.w_Exception)):
                    w_3, w_4 = e.w_type, e.w_value
                    goto = 3
                else:raise # unhandled case, should not happen

        if goto == 2:
            try:
                w_5 = space.call_function(w_1, w_2)
                w_6 = w_5
                goto = 6
            except gOperationError, e:
                e.normalize_exception(space)
                if space.is_true(space.issubtype(e.w_type, space.w_Exception)):
                    w_3, w_4 = e.w_type, e.w_value
                    goto = 3
                else:raise # unhandled case, should not happen

        if goto == 3:
            w_7 = space.is_(w_3, space.w_AttributeError)
            v0 = space.is_true(w_7)
            if v0 == True:
                w_6 = space.w_NotImplemented
                goto = 6
            else:
                assert v0 == False
                w_8, w_9 = w_3, w_4
                goto = 4

        if goto == 4:
            w_10 = space.issubtype(w_8, space.w_AttributeError)
            v1 = space.is_true(w_10)
            if v1 == True:
                w_6 = space.w_NotImplemented
                goto = 6
            else:
                assert v1 == False
                w_etype, w_evalue = w_8, w_9
                goto = 5

        if goto == 5:
            raise gOperationError(w_etype, w_evalue)

        if goto == 6:
            return w_6

  fastf_instance___ge__ = __ge__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__gt__'
## firstlineno 507
##SECTION##
  def __gt__(space, __args__):
    funcname = "__gt__"
    signature = ['self', 'other'], None, None
    defaults_w = []
    w_self, w_other = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___gt__(space, w_self, w_other)

  f_instance___gt__ = __gt__

  def __gt__(space, w_self, w_other):
    goto = 1 # startblock
    while True:

        if goto == 1:
            try:
                w_0 = space.call_function(gfunc_instance_getattr1, w_self, gs___gt__)
                w_1, w_2 = w_0, w_other
                goto = 2
            except gOperationError, e:
                e.normalize_exception(space)
                if space.is_true(space.issubtype(e.w_type, space.w_Exception)):
                    w_3, w_4 = e.w_type, e.w_value
                    goto = 3
                else:raise # unhandled case, should not happen

        if goto == 2:
            try:
                w_5 = space.call_function(w_1, w_2)
                w_6 = w_5
                goto = 6
            except gOperationError, e:
                e.normalize_exception(space)
                if space.is_true(space.issubtype(e.w_type, space.w_Exception)):
                    w_3, w_4 = e.w_type, e.w_value
                    goto = 3
                else:raise # unhandled case, should not happen

        if goto == 3:
            w_7 = space.is_(w_3, space.w_AttributeError)
            v0 = space.is_true(w_7)
            if v0 == True:
                w_6 = space.w_NotImplemented
                goto = 6
            else:
                assert v0 == False
                w_8, w_9 = w_3, w_4
                goto = 4

        if goto == 4:
            w_10 = space.issubtype(w_8, space.w_AttributeError)
            v1 = space.is_true(w_10)
            if v1 == True:
                w_6 = space.w_NotImplemented
                goto = 6
            else:
                assert v1 == False
                w_etype, w_evalue = w_8, w_9
                goto = 5

        if goto == 5:
            raise gOperationError(w_etype, w_evalue)

        if goto == 6:
            return w_6

  fastf_instance___gt__ = __gt__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__le__'
## firstlineno 507
##SECTION##
  def __le__(space, __args__):
    funcname = "__le__"
    signature = ['self', 'other'], None, None
    defaults_w = []
    w_self, w_other = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___le__(space, w_self, w_other)

  f_instance___le__ = __le__

  def __le__(space, w_self, w_other):
    goto = 1 # startblock
    while True:

        if goto == 1:
            try:
                w_0 = space.call_function(gfunc_instance_getattr1, w_self, gs___le__)
                w_1, w_2 = w_0, w_other
                goto = 2
            except gOperationError, e:
                e.normalize_exception(space)
                if space.is_true(space.issubtype(e.w_type, space.w_Exception)):
                    w_3, w_4 = e.w_type, e.w_value
                    goto = 3
                else:raise # unhandled case, should not happen

        if goto == 2:
            try:
                w_5 = space.call_function(w_1, w_2)
                w_6 = w_5
                goto = 6
            except gOperationError, e:
                e.normalize_exception(space)
                if space.is_true(space.issubtype(e.w_type, space.w_Exception)):
                    w_3, w_4 = e.w_type, e.w_value
                    goto = 3
                else:raise # unhandled case, should not happen

        if goto == 3:
            w_7 = space.is_(w_3, space.w_AttributeError)
            v0 = space.is_true(w_7)
            if v0 == True:
                w_6 = space.w_NotImplemented
                goto = 6
            else:
                assert v0 == False
                w_8, w_9 = w_3, w_4
                goto = 4

        if goto == 4:
            w_10 = space.issubtype(w_8, space.w_AttributeError)
            v1 = space.is_true(w_10)
            if v1 == True:
                w_6 = space.w_NotImplemented
                goto = 6
            else:
                assert v1 == False
                w_etype, w_evalue = w_8, w_9
                goto = 5

        if goto == 5:
            raise gOperationError(w_etype, w_evalue)

        if goto == 6:
            return w_6

  fastf_instance___le__ = __le__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__lt__'
## firstlineno 507
##SECTION##
  def __lt__(space, __args__):
    funcname = "__lt__"
    signature = ['self', 'other'], None, None
    defaults_w = []
    w_self, w_other = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___lt__(space, w_self, w_other)

  f_instance___lt__ = __lt__

  def __lt__(space, w_self, w_other):
    goto = 1 # startblock
    while True:

        if goto == 1:
            try:
                w_0 = space.call_function(gfunc_instance_getattr1, w_self, gs___lt__)
                w_1, w_2 = w_0, w_other
                goto = 2
            except gOperationError, e:
                e.normalize_exception(space)
                if space.is_true(space.issubtype(e.w_type, space.w_Exception)):
                    w_3, w_4 = e.w_type, e.w_value
                    goto = 3
                else:raise # unhandled case, should not happen

        if goto == 2:
            try:
                w_5 = space.call_function(w_1, w_2)
                w_6 = w_5
                goto = 6
            except gOperationError, e:
                e.normalize_exception(space)
                if space.is_true(space.issubtype(e.w_type, space.w_Exception)):
                    w_3, w_4 = e.w_type, e.w_value
                    goto = 3
                else:raise # unhandled case, should not happen

        if goto == 3:
            w_7 = space.is_(w_3, space.w_AttributeError)
            v0 = space.is_true(w_7)
            if v0 == True:
                w_6 = space.w_NotImplemented
                goto = 6
            else:
                assert v0 == False
                w_8, w_9 = w_3, w_4
                goto = 4

        if goto == 4:
            w_10 = space.issubtype(w_8, space.w_AttributeError)
            v1 = space.is_true(w_10)
            if v1 == True:
                w_6 = space.w_NotImplemented
                goto = 6
            else:
                assert v1 == False
                w_etype, w_evalue = w_8, w_9
                goto = 5

        if goto == 5:
            raise gOperationError(w_etype, w_evalue)

        if goto == 6:
            return w_6

  fastf_instance___lt__ = __lt__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__ne__'
## firstlineno 507
##SECTION##
  def __ne__(space, __args__):
    funcname = "__ne__"
    signature = ['self', 'other'], None, None
    defaults_w = []
    w_self, w_other = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___ne__(space, w_self, w_other)

  f_instance___ne__ = __ne__

  def __ne__(space, w_self, w_other):
    goto = 1 # startblock
    while True:

        if goto == 1:
            try:
                w_0 = space.call_function(gfunc_instance_getattr1, w_self, gs___ne__)
                w_1, w_2 = w_0, w_other
                goto = 2
            except gOperationError, e:
                e.normalize_exception(space)
                if space.is_true(space.issubtype(e.w_type, space.w_Exception)):
                    w_3, w_4 = e.w_type, e.w_value
                    goto = 3
                else:raise # unhandled case, should not happen

        if goto == 2:
            try:
                w_5 = space.call_function(w_1, w_2)
                w_6 = w_5
                goto = 6
            except gOperationError, e:
                e.normalize_exception(space)
                if space.is_true(space.issubtype(e.w_type, space.w_Exception)):
                    w_3, w_4 = e.w_type, e.w_value
                    goto = 3
                else:raise # unhandled case, should not happen

        if goto == 3:
            w_7 = space.is_(w_3, space.w_AttributeError)
            v0 = space.is_true(w_7)
            if v0 == True:
                w_6 = space.w_NotImplemented
                goto = 6
            else:
                assert v0 == False
                w_8, w_9 = w_3, w_4
                goto = 4

        if goto == 4:
            w_10 = space.issubtype(w_8, space.w_AttributeError)
            v1 = space.is_true(w_10)
            if v1 == True:
                w_6 = space.w_NotImplemented
                goto = 6
            else:
                assert v1 == False
                w_etype, w_evalue = w_8, w_9
                goto = 5

        if goto == 5:
            raise gOperationError(w_etype, w_evalue)

        if goto == 6:
            return w_6

  fastf_instance___ne__ = __ne__

##SECTION##
## filename    'lib/_classobj.py'
## function    '__iter__'
## firstlineno 516
##SECTION##
# global declarations
# global object gs___iter___returned_non_iterator_o
# global object gs_iteration_over_non_sequence

  def __iter__(space, __args__):
    funcname = "__iter__"
    signature = ['self'], None, None
    defaults_w = []
    w_self, = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___iter__(space, w_self)

  f_instance___iter__ = __iter__

  def __iter__(space, w_self):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.call_function(gfunc_instance_getattr1, w_self, gs___iter__, space.w_False)
            v0 = space.is_true(w_0)
            if v0 == True:
                w_1 = w_0
                goto = 2
            else:
                assert v0 == False
                w_self_1 = w_self
                goto = 7

        if goto == 2:
            w_2 = space.call_function(w_1, )
            w_3 = fastf_mro_lookup(space, w_2, gs_next)
            v1 = space.is_true(w_3)
            if v1 == True:
                w_4 = w_2
                goto = 11
            else:
                assert v1 == False
                w_5 = w_2
                goto = 3

        if goto == 3:
            w_6 = space.type(w_5)
            w_7 = space.getattr(w_6, gs___name__)
            w_8 = space.mod(gs___iter___returned_non_iterator_o, w_7)
            w_9 = space.is_(w_8, space.w_None)
            v2 = space.is_true(w_9)
            if v2 == True:
                goto = 4
            else:
                assert v2 == False
                w_10 = w_8
                goto = 5

        if goto == 4:
            w_11 = space.call_function(space.w_TypeError, )
            w_12 = space.type(w_11)
            w_etype, w_evalue = w_12, w_11
            goto = 10

        if goto == 5:
            w_13 = space.type(w_10)
            w_14 = space.issubtype(w_13, space.w_TypeError)
            v3 = space.is_true(w_14)
            if v3 == True:
                w_etype, w_evalue = w_13, w_10
                goto = 10
            else:
                assert v3 == False
                w_15 = w_10
                goto = 6

        if goto == 6:
            w_16 = space.call_function(space.w_TypeError, w_15)
            w_17 = space.type(w_16)
            w_etype, w_evalue = w_17, w_16
            goto = 10

        if goto == 7:
            w_18 = space.call_function(gfunc_instance_getattr1, w_self_1, gs___getitem__, space.w_False)
            v4 = space.is_true(w_18)
            if v4 == True:
                w_19 = w_self_1
                goto = 9
            else:
                assert v4 == False
                goto = 8

        if goto == 8:
            w_20 = space.call_function(space.w_TypeError, gs_iteration_over_non_sequence)
            w_21 = space.type(w_20)
            w_etype, w_evalue = w_21, w_20
            goto = 10

        if goto == 9:
            w_22 = space.call_function(space.builtin.get('_seqiter'), w_19)
            w_4 = w_22
            goto = 11

        if goto == 10:
            raise gOperationError(w_etype, w_evalue)

        if goto == 11:
            return w_4

  fastf_instance___iter__ = __iter__

##SECTION##
## filename    'lib/_classobj.py'
## function    'next'
## firstlineno 531
##SECTION##
# global declaration
# global object gs_instance_has_no_next___method

  def next(space, __args__):
    funcname = "next"
    signature = ['self'], None, None
    defaults_w = []
    w_self, = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance_next(space, w_self)

  f_instance_next = next

  def next(space, w_self):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.call_function(gfunc_instance_getattr1, w_self, gs_next, space.w_False)
            v0 = space.is_true(w_0)
            if v0 == True:
                w_1 = w_0
                goto = 3
            else:
                assert v0 == False
                goto = 2

        if goto == 2:
            w_2 = space.call_function(space.w_TypeError, gs_instance_has_no_next___method)
            w_3 = space.type(w_2)
            w_etype, w_evalue = w_3, w_2
            goto = 4

        if goto == 3:
            w_4 = space.call_function(w_1, )
            w_5 = w_4
            goto = 5

        if goto == 4:
            raise gOperationError(w_etype, w_evalue)

        if goto == 5:
            return w_5

  fastf_instance_next = next

##SECTION##
## filename    'lib/_classobj.py'
## function    '__cmp__'
## firstlineno 537
##SECTION##
# global declarations
# global object gi_minus_1
# global object gs___cmp___must_return_int

  def __cmp__(space, __args__):
    funcname = "__cmp__"
    signature = ['self', 'other'], None, None
    defaults_w = []
    w_self, w_other = __args__.parse(funcname, signature, defaults_w)
    return fastf_instance___cmp__(space, w_self, w_other)

  f_instance___cmp__ = __cmp__

  def __cmp__(space, w_self, w_other):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = fastf__coerce(space, w_self, w_other)
            w_1 = space.is_(w_0, space.w_None)
            v0 = space.is_true(w_1)
            if v0 == True:
                w_w, w_v = w_other, w_self
                goto = 5
            else:
                assert v0 == False
                w_coerced = w_0
                goto = 2

        if goto == 2:
            w_2 = space.getitem(w_coerced, gi_0)
            w_3 = space.getitem(w_coerced, gi_1)
            w_4 = space.isinstance(w_2, gcls_instance)
            v1 = space.is_true(w_4)
            if v1 == True:
                w_w, w_v = w_3, w_2
                goto = 5
            else:
                assert v1 == False
                w_w_1, w_v_1 = w_3, w_2
                goto = 3

        if goto == 3:
            w_5 = space.isinstance(w_w_1, gcls_instance)
            v2 = space.is_true(w_5)
            if v2 == True:
                w_w, w_v = w_w_1, w_v_1
                goto = 5
            else:
                assert v2 == False
                w_6, w_7 = w_v_1, w_w_1
                goto = 4

        if goto == 4:
            w_8 = space.cmp(w_6, w_7)
            w_9 = w_8
            goto = 18

        if goto == 5:
            w_10 = space.isinstance(w_v, gcls_instance)
            v3 = space.is_true(w_10)
            if v3 == True:
                w_w_2, w_v_2 = w_w, w_v
                goto = 6
            else:
                assert v3 == False
                w_w_3, w_v_3 = w_w, w_v
                goto = 11

        if goto == 6:
            w_11 = space.call_function(gfunc_instance_getattr1, w_v_2, gs___cmp__, space.w_False)
            v4 = space.is_true(w_11)
            if v4 == True:
                w_12, w_13 = w_11, w_w_2
                goto = 7
            else:
                assert v4 == False
                w_w_3, w_v_3 = w_w_2, w_v_2
                goto = 11

        if goto == 7:
            w_14 = space.call_function(w_12, w_13)
            w_15 = space.isinstance(w_14, space.w_int)
            v5 = space.is_true(w_15)
            if v5 == True:
                w_res = w_14
                goto = 8
            else:
                assert v5 == False
                goto = 10

        if goto == 8:
            w_16 = space.gt(w_res, gi_0)
            v6 = space.is_true(w_16)
            if v6 == True:
                w_9 = gi_1
                goto = 18
            else:
                assert v6 == False
                w_17 = w_res
                goto = 9

        if goto == 9:
            w_18 = space.lt(w_17, gi_0)
            v7 = space.is_true(w_18)
            if v7 == True:
                w_9 = gi_minus_1
                goto = 18
            else:
                assert v7 == False
                w_9 = gi_0
                goto = 18

        if goto == 10:
            w_19 = space.call_function(space.w_TypeError, gs___cmp___must_return_int)
            w_20 = space.type(w_19)
            w_etype, w_evalue = w_20, w_19
            goto = 17

        if goto == 11:
            w_21 = space.isinstance(w_w_3, gcls_instance)
            v8 = space.is_true(w_21)
            if v8 == True:
                w_v_4, w_22 = w_v_3, w_w_3
                goto = 12
            else:
                assert v8 == False
                w_9 = space.w_NotImplemented
                goto = 18

        if goto == 12:
            w_23 = space.call_function(gfunc_instance_getattr1, w_22, gs___cmp__, space.w_False)
            v9 = space.is_true(w_23)
            if v9 == True:
                w_24, w_25 = w_23, w_v_4
                goto = 13
            else:
                assert v9 == False
                w_9 = space.w_NotImplemented
                goto = 18

        if goto == 13:
            w_26 = space.call_function(w_24, w_25)
            w_27 = space.isinstance(w_26, space.w_int)
            v10 = space.is_true(w_27)
            if v10 == True:
                w_res_1 = w_26
                goto = 14
            else:
                assert v10 == False
                goto = 16

        if goto == 14:
            w_28 = space.gt(w_res_1, gi_0)
            v11 = space.is_true(w_28)
            if v11 == True:
                w_9 = gi_1
                goto = 18
            else:
                assert v11 == False
                w_29 = w_res_1
                goto = 15

        if goto == 15:
            w_30 = space.lt(w_29, gi_0)
            v12 = space.is_true(w_30)
            if v12 == True:
                w_9 = gi_minus_1
                goto = 18
            else:
                assert v12 == False
                w_9 = gi_0
                goto = 18

        if goto == 16:
            w_31 = space.call_function(space.w_TypeError, gs___cmp___must_return_int)
            w_32 = space.type(w_31)
            w_etype, w_evalue = w_32, w_31
            goto = 17

        if goto == 17:
            raise gOperationError(w_etype, w_evalue)

        if goto == 18:
            return w_9

  fastf_instance___cmp__ = __cmp__

##SECTION##
## filename    'lib/_classobj.py'
## function    'purify'
## firstlineno 575
##SECTION##
# global declarations
# global object g3tuple
# global object gcls_classobj
# global object gs___module__
# global object gs__classobj
# global object gs___new__
# global object gsm___new__
# global object gfunc___new__
# global object gs___slots__
# global object g3tuple_1
# global object gs__name
# global object gs__bases
# global object gs___dict__
# global object gs_classobj
# global object gcls_instance
# global object gsm___new___1
# global object gfunc___new___1
# global object g2tuple
# global object gs__class
# global object gs_instance
# global object gfunc_purify

  def purify(space, __args__):
    funcname = "purify"
    signature = [], None, None
    defaults_w = []
    __args__.parse(funcname, signature, defaults_w)
    return fastf_purify(space)

  f_purify = purify

  def purify(space):
    goto = 1 # startblock
    while True:

        if goto == 1:
            w_0 = space.delattr(gcls_classobj, gs__name)
            w_1 = space.delattr(gcls_classobj, gs__bases)
            w_2 = space.delattr(gcls_classobj, gs___slots__)
            w_3 = space.delattr(gcls_instance, gs__class)
            w_4 = space.delattr(gcls_instance, gs___slots__)
            w_5 = space.w_None
            goto = 2

        if goto == 2:
            return w_5

  fastf_purify = purify

# global declarations
# global object gs___abs__
# global object gfunc_instance___abs__
# global object gs___add__
# global object gfunc_instance___add__
# global object gs___and__
# global object gfunc_instance___and__
# global object gs___call__
# global object gfunc_instance___call__
# global object gs___cmp__
# global object gfunc_instance___cmp__
# global object gs___coerce__
# global object gfunc_instance___coerce__
# global object gs___contains__
# global object gfunc_instance___contains__
# global object gs___delattr__
# global object gfunc_instance___delattr__
# global object gs___delitem__
# global object gfunc_instance___delitem__
# global object gs___div__
# global object gfunc_instance___div__
# global object gs___divmod__
# global object gfunc_instance___divmod__
# global object gs___eq__
# global object gfunc_instance___eq__
# global object gs___float__
# global object gfunc_instance___float__
# global object gs___floordiv__
# global object gfunc_instance___floordiv__
# global object gs___ge__
# global object gfunc_instance___ge__
# global object gs___getattribute__
# global object gfunc_instance___getattribute__
# global object gs___getitem__
# global object gfunc_instance___getitem__
# global object gs___gt__
# global object gfunc_instance___gt__
# global object gs___hash__
# global object gfunc_instance___hash__
# global object gs___hex__
# global object gfunc_instance___hex__
# global object gs___iadd__
# global object gfunc_instance___iadd__
# global object gs___iand__
# global object gfunc_instance___iand__
# global object gs___idiv__
# global object gfunc_instance___idiv__
# global object gs___ifloordiv__
# global object gfunc_instance___ifloordiv__
# global object gs___ilshift__
# global object gfunc_instance___ilshift__
# global object gs___imod__
# global object gfunc_instance___imod__
# global object gs___imul__
# global object gfunc_instance___imul__
# global object gs___int__
# global object gfunc_instance___int__
# global object gs___invert__
# global object gfunc_instance___invert__
# global object gs___ior__
# global object gfunc_instance___ior__
# global object gs___ipow__
# global object gfunc_instance___ipow__
# global object gs___irshift__
# global object gfunc_instance___irshift__
# global object gs___isub__
# global object gfunc_instance___isub__
# global object gs___iter__
# global object gfunc_instance___iter__
# global object gs___itruediv__
# global object gfunc_instance___itruediv__
# global object gs___ixor__
# global object gfunc_instance___ixor__
# global object gs___le__
# global object gfunc_instance___le__
# global object gs___len__
# global object gfunc_instance___len__
# global object gs___long__
# global object gfunc_instance___long__
# global object gs___lshift__
# global object gfunc_instance___lshift__
# global object gs___lt__
# global object gfunc_instance___lt__
# global object gs___mod__
# global object gfunc_instance___mod__
# global object gs___mul__
# global object gfunc_instance___mul__
# global object gs___ne__
# global object gfunc_instance___ne__
# global object gs___neg__
# global object gfunc_instance___neg__
# global object gs___nonzero__
# global object gfunc_instance___nonzero__
# global object gs___oct__
# global object gfunc_instance___oct__
# global object gs___or__
# global object gfunc_instance___or__
# global object gs___pos__
# global object gfunc_instance___pos__
# global object gs___pow__
# global object gfunc_instance___pow__
# global object gs___radd__
# global object gfunc_instance___radd__
# global object gs___rand__
# global object gfunc_instance___rand__
# global object gs___rdiv__
# global object gfunc_instance___rdiv__
# global object gs___rdivmod__
# global object gfunc_instance___rdivmod__
# global object gs___repr__
# global object gfunc_instance___repr__
# global object gs___rfloordiv__
# global object gfunc_instance___rfloordiv__
# global object gs___rlshift__
# global object gfunc_instance___rlshift__
# global object gs___rmod__
# global object gfunc_instance___rmod__
# global object gs___rmul__
# global object gfunc_instance___rmul__
# global object gs___ror__
# global object gfunc_instance___ror__
# global object gs___rpow__
# global object gfunc_instance___rpow__
# global object gs___rrshift__
# global object gfunc_instance___rrshift__
# global object gs___rshift__
# global object gfunc_instance___rshift__
# global object gs___rsub__
# global object gfunc_instance___rsub__
# global object gs___rtruediv__
# global object gfunc_instance___rtruediv__
# global object gs___rxor__
# global object gfunc_instance___rxor__
# global object gs___setattr__
# global object gfunc_instance___setattr__
# global object gs___setitem__
# global object gfunc_instance___setitem__
# global object gs___str__
# global object gfunc_instance___str__
# global object gs___sub__
# global object gfunc_instance___sub__
# global object gs___truediv__
# global object gfunc_instance___truediv__
# global object gs___xor__
# global object gfunc_instance___xor__
# global object gs_next
# global object gfunc_instance_next
# global object gfunc_classobj___call__
# global object gfunc_classobj___delattr__
# global object gfunc_classobj___getattribute__
# global object gfunc_classobj___repr__
# global object gfunc_classobj___setattr__
# global object gfunc_classobj___str__

##SECTION##
  _dic = space.newdict([])
  gs___module__ = space.wrap('__module__')
  gs__classobj = space.wrap('_classobj')
  space.setitem(_dic, gs___module__, gs__classobj)
  gs___new__ = space.wrap('__new__')
  from pypy.interpreter import gateway
  gfunc___new__ = space.wrap(gateway.interp2app(f___new__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  gsm___new__ = space.wrap(gfunc___new__)
  space.setitem(_dic, gs___new__, gsm___new__)
  gs___slots__ = space.wrap('__slots__')
  gs__name = space.wrap('_name')
  gs__bases = space.wrap('_bases')
  gs___dict__ = space.wrap('__dict__')
  g3tuple_1 = space.newtuple([gs__name, gs__bases, gs___dict__])
  space.setitem(_dic, gs___slots__, g3tuple_1)
  gs_classobj = space.wrap('classobj')
  _bases = space.newtuple([space.w_object])
  _args = space.newtuple([gs_classobj, _bases, _dic])
  gcls_classobj = space.call(space.w_type, _args)
  _dic = space.newdict([])
  space.setitem(_dic, gs___module__, gs__classobj)
  gfunc___new___1 = space.wrap(gateway.interp2app(f___new___1, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  gsm___new___1 = space.wrap(gfunc___new___1)
  space.setitem(_dic, gs___new__, gsm___new___1)
  gs__class = space.wrap('_class')
  g2tuple = space.newtuple([gs__class, gs___dict__])
  space.setitem(_dic, gs___slots__, g2tuple)
  gs_instance = space.wrap('instance')
  _bases = space.newtuple([space.w_object])
  _args = space.newtuple([gs_instance, _bases, _dic])
  gcls_instance = space.call(space.w_type, _args)
  gfunc_purify = space.wrap(gateway.interp2app(f_purify, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  g3tuple = space.newtuple([gcls_classobj, gcls_instance, gfunc_purify])
  gs___abs__ = space.wrap('__abs__')
  gfunc_instance___abs__ = space.wrap(gateway.interp2app(f_instance___abs__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___abs__, gfunc_instance___abs__)
  gs___add__ = space.wrap('__add__')
  gfunc_instance___add__ = space.wrap(gateway.interp2app(f_instance___add__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___add__, gfunc_instance___add__)
  gs___and__ = space.wrap('__and__')
  gfunc_instance___and__ = space.wrap(gateway.interp2app(f_instance___and__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___and__, gfunc_instance___and__)
  gs___call__ = space.wrap('__call__')
  gfunc_instance___call__ = space.wrap(gateway.interp2app(f_instance___call__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___call__, gfunc_instance___call__)
  gs___cmp__ = space.wrap('__cmp__')
  gfunc_instance___cmp__ = space.wrap(gateway.interp2app(f_instance___cmp__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___cmp__, gfunc_instance___cmp__)
  gs___coerce__ = space.wrap('__coerce__')
  gfunc_instance___coerce__ = space.wrap(gateway.interp2app(f_instance___coerce__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___coerce__, gfunc_instance___coerce__)
  gs___contains__ = space.wrap('__contains__')
  gfunc_instance___contains__ = space.wrap(gateway.interp2app(f_instance___contains__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___contains__, gfunc_instance___contains__)
  gs___delattr__ = space.wrap('__delattr__')
  gfunc_instance___delattr__ = space.wrap(gateway.interp2app(f_instance___delattr__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___delattr__, gfunc_instance___delattr__)
  gs___delitem__ = space.wrap('__delitem__')
  gfunc_instance___delitem__ = space.wrap(gateway.interp2app(f_instance___delitem__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___delitem__, gfunc_instance___delitem__)
  gs___div__ = space.wrap('__div__')
  gfunc_instance___div__ = space.wrap(gateway.interp2app(f_instance___div__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___div__, gfunc_instance___div__)
  gs___divmod__ = space.wrap('__divmod__')
  gfunc_instance___divmod__ = space.wrap(gateway.interp2app(f_instance___divmod__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___divmod__, gfunc_instance___divmod__)
  gs___eq__ = space.wrap('__eq__')
  gfunc_instance___eq__ = space.wrap(gateway.interp2app(f_instance___eq__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___eq__, gfunc_instance___eq__)
  gs___float__ = space.wrap('__float__')
  gfunc_instance___float__ = space.wrap(gateway.interp2app(f_instance___float__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___float__, gfunc_instance___float__)
  gs___floordiv__ = space.wrap('__floordiv__')
  gfunc_instance___floordiv__ = space.wrap(gateway.interp2app(f_instance___floordiv__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___floordiv__, gfunc_instance___floordiv__)
  gs___ge__ = space.wrap('__ge__')
  gfunc_instance___ge__ = space.wrap(gateway.interp2app(f_instance___ge__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___ge__, gfunc_instance___ge__)
  gs___getattribute__ = space.wrap('__getattribute__')
  gfunc_instance___getattribute__ = space.wrap(gateway.interp2app(f_instance___getattribute__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___getattribute__, gfunc_instance___getattribute__)
  gs___getitem__ = space.wrap('__getitem__')
  gfunc_instance___getitem__ = space.wrap(gateway.interp2app(f_instance___getitem__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___getitem__, gfunc_instance___getitem__)
  gs___gt__ = space.wrap('__gt__')
  gfunc_instance___gt__ = space.wrap(gateway.interp2app(f_instance___gt__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___gt__, gfunc_instance___gt__)
  gs___hash__ = space.wrap('__hash__')
  gfunc_instance___hash__ = space.wrap(gateway.interp2app(f_instance___hash__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___hash__, gfunc_instance___hash__)
  gs___hex__ = space.wrap('__hex__')
  gfunc_instance___hex__ = space.wrap(gateway.interp2app(f_instance___hex__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___hex__, gfunc_instance___hex__)
  gs___iadd__ = space.wrap('__iadd__')
  gfunc_instance___iadd__ = space.wrap(gateway.interp2app(f_instance___iadd__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___iadd__, gfunc_instance___iadd__)
  gs___iand__ = space.wrap('__iand__')
  gfunc_instance___iand__ = space.wrap(gateway.interp2app(f_instance___iand__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___iand__, gfunc_instance___iand__)
  gs___idiv__ = space.wrap('__idiv__')
  gfunc_instance___idiv__ = space.wrap(gateway.interp2app(f_instance___idiv__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___idiv__, gfunc_instance___idiv__)
  gs___ifloordiv__ = space.wrap('__ifloordiv__')
  gfunc_instance___ifloordiv__ = space.wrap(gateway.interp2app(f_instance___ifloordiv__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___ifloordiv__, gfunc_instance___ifloordiv__)
  gs___ilshift__ = space.wrap('__ilshift__')
  gfunc_instance___ilshift__ = space.wrap(gateway.interp2app(f_instance___ilshift__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___ilshift__, gfunc_instance___ilshift__)
  gs___imod__ = space.wrap('__imod__')
  gfunc_instance___imod__ = space.wrap(gateway.interp2app(f_instance___imod__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___imod__, gfunc_instance___imod__)
  gs___imul__ = space.wrap('__imul__')
  gfunc_instance___imul__ = space.wrap(gateway.interp2app(f_instance___imul__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___imul__, gfunc_instance___imul__)
  gs___int__ = space.wrap('__int__')
  gfunc_instance___int__ = space.wrap(gateway.interp2app(f_instance___int__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___int__, gfunc_instance___int__)
  gs___invert__ = space.wrap('__invert__')
  gfunc_instance___invert__ = space.wrap(gateway.interp2app(f_instance___invert__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___invert__, gfunc_instance___invert__)
  gs___ior__ = space.wrap('__ior__')
  gfunc_instance___ior__ = space.wrap(gateway.interp2app(f_instance___ior__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___ior__, gfunc_instance___ior__)
  gs___ipow__ = space.wrap('__ipow__')
  gfunc_instance___ipow__ = space.wrap(gateway.interp2app(f_instance___ipow__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___ipow__, gfunc_instance___ipow__)
  gs___irshift__ = space.wrap('__irshift__')
  gfunc_instance___irshift__ = space.wrap(gateway.interp2app(f_instance___irshift__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___irshift__, gfunc_instance___irshift__)
  gs___isub__ = space.wrap('__isub__')
  gfunc_instance___isub__ = space.wrap(gateway.interp2app(f_instance___isub__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___isub__, gfunc_instance___isub__)
  gs___iter__ = space.wrap('__iter__')
  gfunc_instance___iter__ = space.wrap(gateway.interp2app(f_instance___iter__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___iter__, gfunc_instance___iter__)
  gs___itruediv__ = space.wrap('__itruediv__')
  gfunc_instance___itruediv__ = space.wrap(gateway.interp2app(f_instance___itruediv__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___itruediv__, gfunc_instance___itruediv__)
  gs___ixor__ = space.wrap('__ixor__')
  gfunc_instance___ixor__ = space.wrap(gateway.interp2app(f_instance___ixor__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___ixor__, gfunc_instance___ixor__)
  gs___le__ = space.wrap('__le__')
  gfunc_instance___le__ = space.wrap(gateway.interp2app(f_instance___le__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___le__, gfunc_instance___le__)
  gs___len__ = space.wrap('__len__')
  gfunc_instance___len__ = space.wrap(gateway.interp2app(f_instance___len__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___len__, gfunc_instance___len__)
  gs___long__ = space.wrap('__long__')
  gfunc_instance___long__ = space.wrap(gateway.interp2app(f_instance___long__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___long__, gfunc_instance___long__)
  gs___lshift__ = space.wrap('__lshift__')
  gfunc_instance___lshift__ = space.wrap(gateway.interp2app(f_instance___lshift__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___lshift__, gfunc_instance___lshift__)
  gs___lt__ = space.wrap('__lt__')
  gfunc_instance___lt__ = space.wrap(gateway.interp2app(f_instance___lt__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___lt__, gfunc_instance___lt__)
  gs___mod__ = space.wrap('__mod__')
  gfunc_instance___mod__ = space.wrap(gateway.interp2app(f_instance___mod__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___mod__, gfunc_instance___mod__)
  gs___mul__ = space.wrap('__mul__')
  gfunc_instance___mul__ = space.wrap(gateway.interp2app(f_instance___mul__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___mul__, gfunc_instance___mul__)
  gs___ne__ = space.wrap('__ne__')
  gfunc_instance___ne__ = space.wrap(gateway.interp2app(f_instance___ne__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___ne__, gfunc_instance___ne__)
  gs___neg__ = space.wrap('__neg__')
  gfunc_instance___neg__ = space.wrap(gateway.interp2app(f_instance___neg__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___neg__, gfunc_instance___neg__)
  gs___nonzero__ = space.wrap('__nonzero__')
  gfunc_instance___nonzero__ = space.wrap(gateway.interp2app(f_instance___nonzero__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___nonzero__, gfunc_instance___nonzero__)
  gs___oct__ = space.wrap('__oct__')
  gfunc_instance___oct__ = space.wrap(gateway.interp2app(f_instance___oct__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___oct__, gfunc_instance___oct__)
  gs___or__ = space.wrap('__or__')
  gfunc_instance___or__ = space.wrap(gateway.interp2app(f_instance___or__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___or__, gfunc_instance___or__)
  gs___pos__ = space.wrap('__pos__')
  gfunc_instance___pos__ = space.wrap(gateway.interp2app(f_instance___pos__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___pos__, gfunc_instance___pos__)
  gs___pow__ = space.wrap('__pow__')
  gfunc_instance___pow__ = space.wrap(gateway.interp2app(f_instance___pow__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___pow__, gfunc_instance___pow__)
  gs___radd__ = space.wrap('__radd__')
  gfunc_instance___radd__ = space.wrap(gateway.interp2app(f_instance___radd__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___radd__, gfunc_instance___radd__)
  gs___rand__ = space.wrap('__rand__')
  gfunc_instance___rand__ = space.wrap(gateway.interp2app(f_instance___rand__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___rand__, gfunc_instance___rand__)
  gs___rdiv__ = space.wrap('__rdiv__')
  gfunc_instance___rdiv__ = space.wrap(gateway.interp2app(f_instance___rdiv__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___rdiv__, gfunc_instance___rdiv__)
  gs___rdivmod__ = space.wrap('__rdivmod__')
  gfunc_instance___rdivmod__ = space.wrap(gateway.interp2app(f_instance___rdivmod__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___rdivmod__, gfunc_instance___rdivmod__)
  gs___repr__ = space.wrap('__repr__')
  gfunc_instance___repr__ = space.wrap(gateway.interp2app(f_instance___repr__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___repr__, gfunc_instance___repr__)
  gs___rfloordiv__ = space.wrap('__rfloordiv__')
  gfunc_instance___rfloordiv__ = space.wrap(gateway.interp2app(f_instance___rfloordiv__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___rfloordiv__, gfunc_instance___rfloordiv__)
  gs___rlshift__ = space.wrap('__rlshift__')
  gfunc_instance___rlshift__ = space.wrap(gateway.interp2app(f_instance___rlshift__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___rlshift__, gfunc_instance___rlshift__)
  gs___rmod__ = space.wrap('__rmod__')
  gfunc_instance___rmod__ = space.wrap(gateway.interp2app(f_instance___rmod__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___rmod__, gfunc_instance___rmod__)
  gs___rmul__ = space.wrap('__rmul__')
  gfunc_instance___rmul__ = space.wrap(gateway.interp2app(f_instance___rmul__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___rmul__, gfunc_instance___rmul__)
  gs___ror__ = space.wrap('__ror__')
  gfunc_instance___ror__ = space.wrap(gateway.interp2app(f_instance___ror__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___ror__, gfunc_instance___ror__)
  gs___rpow__ = space.wrap('__rpow__')
  gfunc_instance___rpow__ = space.wrap(gateway.interp2app(f_instance___rpow__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___rpow__, gfunc_instance___rpow__)
  gs___rrshift__ = space.wrap('__rrshift__')
  gfunc_instance___rrshift__ = space.wrap(gateway.interp2app(f_instance___rrshift__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___rrshift__, gfunc_instance___rrshift__)
  gs___rshift__ = space.wrap('__rshift__')
  gfunc_instance___rshift__ = space.wrap(gateway.interp2app(f_instance___rshift__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___rshift__, gfunc_instance___rshift__)
  gs___rsub__ = space.wrap('__rsub__')
  gfunc_instance___rsub__ = space.wrap(gateway.interp2app(f_instance___rsub__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___rsub__, gfunc_instance___rsub__)
  gs___rtruediv__ = space.wrap('__rtruediv__')
  gfunc_instance___rtruediv__ = space.wrap(gateway.interp2app(f_instance___rtruediv__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___rtruediv__, gfunc_instance___rtruediv__)
  gs___rxor__ = space.wrap('__rxor__')
  gfunc_instance___rxor__ = space.wrap(gateway.interp2app(f_instance___rxor__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___rxor__, gfunc_instance___rxor__)
  gs___setattr__ = space.wrap('__setattr__')
  gfunc_instance___setattr__ = space.wrap(gateway.interp2app(f_instance___setattr__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___setattr__, gfunc_instance___setattr__)
  gs___setitem__ = space.wrap('__setitem__')
  gfunc_instance___setitem__ = space.wrap(gateway.interp2app(f_instance___setitem__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___setitem__, gfunc_instance___setitem__)
  gs___str__ = space.wrap('__str__')
  gfunc_instance___str__ = space.wrap(gateway.interp2app(f_instance___str__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___str__, gfunc_instance___str__)
  gs___sub__ = space.wrap('__sub__')
  gfunc_instance___sub__ = space.wrap(gateway.interp2app(f_instance___sub__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___sub__, gfunc_instance___sub__)
  gs___truediv__ = space.wrap('__truediv__')
  gfunc_instance___truediv__ = space.wrap(gateway.interp2app(f_instance___truediv__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___truediv__, gfunc_instance___truediv__)
  gs___xor__ = space.wrap('__xor__')
  gfunc_instance___xor__ = space.wrap(gateway.interp2app(f_instance___xor__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs___xor__, gfunc_instance___xor__)
  gs_next = space.wrap('next')
  gfunc_instance_next = space.wrap(gateway.interp2app(f_instance_next, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_instance, gs_next, gfunc_instance_next)
  gfunc_classobj___call__ = space.wrap(gateway.interp2app(f_classobj___call__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_classobj, gs___call__, gfunc_classobj___call__)
  gfunc_classobj___delattr__ = space.wrap(gateway.interp2app(f_classobj___delattr__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_classobj, gs___delattr__, gfunc_classobj___delattr__)
  gfunc_classobj___getattribute__ = space.wrap(gateway.interp2app(f_classobj___getattribute__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_classobj, gs___getattribute__, gfunc_classobj___getattribute__)
  gfunc_classobj___repr__ = space.wrap(gateway.interp2app(f_classobj___repr__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_classobj, gs___repr__, gfunc_classobj___repr__)
  gfunc_classobj___setattr__ = space.wrap(gateway.interp2app(f_classobj___setattr__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_classobj, gs___setattr__, gfunc_classobj___setattr__)
  gfunc_classobj___str__ = space.wrap(gateway.interp2app(f_classobj___str__, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  space.setattr(gcls_classobj, gs___str__, gfunc_classobj___str__)
  gfunc_get_class_module = space.wrap(gateway.interp2app(f_get_class_module, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  gs__ = space.wrap('?')
  gs___name__ = space.wrap('__name__')
  gs__s__s = space.wrap('%s.%s')
  gfunc_retrieve = space.wrap(gateway.interp2app(f_retrieve, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  from pypy.interpreter.error import OperationError as gOperationError
  gdescriptor_object___getattribute__ = space.getattr(space.w_object, gs___getattribute__)
  gfunc_set_name = space.wrap(gateway.interp2app(f_set_name, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  gs___bases__ = space.wrap('__bases__')
  gfunc_set_bases = space.wrap(gateway.interp2app(f_set_bases, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  gfunc_set_dict = space.wrap(gateway.interp2app(f_set_dict, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  gdescriptor_object___setattr__ = space.getattr(space.w_object, gs___setattr__)
  gs___dict___must_be_a_dictionary_ob = space.wrap(
"""__dict__ must be a dictionary object""")
  gs___bases___must_be_a_tuple_object = space.wrap(
"""__bases__ must be a tuple object""")
  gs___bases___items_must_be_classes = space.wrap(
"""__bases__ items must be classes""")
  gdescriptor_classobj__bases = space.getattr(gcls_classobj, gs__bases)
  gs___set__ = space.wrap('__set__')
  gs___name___must_be_a_string_object = space.wrap(
"""__name__ must be a string object""")
  gdescriptor_classobj__name = space.getattr(gcls_classobj, gs__name)
  gfunc_uid = space.wrap(gateway.interp2app(f_uid, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  gs__class__s__s_at_0x_x_ = space.wrap('<class %s.%s at 0x%x>')
  gi_0 = space.wrap(0)
  glong_0x7fffffffL = space.wrap(0x7fffffffL) # XXX implement long!
  gi_2 = space.wrap(2)
  gs___get__ = space.wrap('__get__')
  gi_1 = space.wrap(1)
  gfunc_lookup = space.wrap(gateway.interp2app(f_lookup, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  gs_class__s_has_no_attribute__s = space.wrap('class %s has no attribute %s')
  gfunc_mro_lookup = space.wrap(gateway.interp2app(f_mro_lookup, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  gs___mro__ = space.wrap('__mro__')
  g2tuple_1 = space.newtuple([space.w_None, space.w_None])
  g3tuple_2 = space.newtuple([gs___name__, gs___bases__, gs___dict__])
  gdescriptor_object___delattr__ = space.getattr(space.w_object, gs___delattr__)
  gbltinmethod___new__ = space.getattr(space.w_object, gs___new__)
  gdescriptor_instance__class = space.getattr(gcls_instance, gs__class)
  gfunc_instance_getattr1 = space.wrap(gateway.interp2app(f_instance_getattr1, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  gs___init__ = space.wrap('__init__')
  gs___init_____should_return_None = space.wrap('__init__() should return None')
  gs___class__ = space.wrap('__class__')
  gs__s_instance_has_no_attribute__s = space.wrap(
"""%s instance has no attribute %s""")
  gs_instance_has_no_next___method = space.wrap('instance has no next() method')
  gfunc__coerce = space.wrap(gateway.interp2app(f__coerce, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  gs_step = space.wrap('step')
  gs___setslice__ = space.wrap('__setslice__')
  gs_start = space.wrap('start')
  gs_stop = space.wrap('stop')
  gs___dict___must_be_set_to_a_dictio = space.wrap(
"""__dict__ must be set to a dictionary""")
  gs___class___must_be_set_to_a_class = space.wrap(
"""__class__ must be set to a class""")
  gs___s__s_instance_at_0x_x_ = space.wrap('<%s.%s instance at 0x%x>')
  gs___nonzero_____should_return____0 = space.wrap(
"""__nonzero__() should return >= 0""")
  gs___nonzero_____should_return_an_i = space.wrap(
"""__nonzero__() should return an int""")
  gs___len_____should_return____0 = space.wrap('__len__() should return >= 0')
  gs___len_____should_return_an_int = space.wrap(
"""__len__() should return an int""")
  gs___iter___returned_non_iterator_o = space.wrap(
"""__iter__ returned non-iterator of type %s""")
  gs_iteration_over_non_sequence = space.wrap('iteration over non-sequence')
  gs_unhashable_instance = space.wrap('unhashable instance')
  gs___hash_____should_return_an_int = space.wrap(
"""__hash__() should return an int""")
  gs___getslice__ = space.wrap('__getslice__')
  gs___getattr__ = space.wrap('__getattr__')
  gs___delslice__ = space.wrap('__delslice__')
  g2tuple_2 = space.newtuple([gs___dict__, gs___class__])
  gs__s_instance_has_no_attribute___s = space.wrap(
"""%s instance has no attribute '%s'""")
  gi_minus_1 = space.wrap(-1)
  gs___cmp___must_return_int = space.wrap('__cmp__ must return int')
  gs__s_instance_has_no___call___meth = space.wrap(
"""%s instance has no __call__ method""")
  gs_instance___first_arg_must_be_cla = space.wrap(
"""instance() first arg must be class""")
  gs_instance___second_arg_must_be_di = space.wrap(
"""instance() second arg must be dictionary or None""")
  gfunc_type_err = space.wrap(gateway.interp2app(f_type_err, unwrap_spec=[gateway.ObjSpace, gateway.Arguments]))
  gs_name = space.wrap('name')
  gs_string = space.wrap('string')
  g0tuple = space.newtuple([])
  gs_bases = space.wrap('bases')
  gs_tuple = space.wrap('tuple')
  gs_dict = space.wrap('dict')
  gs___doc__ = space.wrap('__doc__')
  gs__getframe = space.wrap('_getframe')
  gs_f_globals = space.wrap('f_globals')
  gs_get = space.wrap('get')
  gs_OLD_STYLE_CLASSES_IMPL = space.wrap('OLD_STYLE_CLASSES_IMPL')
  _tup = space.newtuple([])
  g_object = space.call(space.w_object, _tup)
  gs_callable = space.wrap('callable')
  gs_base_must_be_class = space.wrap('base must be class')
  gs_argument__s_must_be__s__not__s = space.wrap(
"""argument %s must be %s, not %s""")
  return g3tuple

