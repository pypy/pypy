from pypy.annotation.pairtype import pairtype
from pypy.annotation import model as annmodel
from pypy.objspace.flow.model import Constant
from pypy.rpython.rdict import AbstractDictRepr, rtype_newdict
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.rarithmetic import r_uint
from pypy.rpython.objectmodel import hlinvoke
from pypy.rpython import robject
from pypy.rpython import objectmodel
from pypy.rpython import rmodel


class DictRepr(AbstractDictRepr):
    def __init__(self, rtyper, key_repr, value_repr, dictkey, dictvalue,
                 custom_eq_hash=None):
        self.rtyper = rtyper
        self.custom_eq_hash = custom_eq_hash is not None

        already_computed = True
        if not isinstance(key_repr, rmodel.Repr):  # not computed yet, done by setup()
            assert callable(key_repr)
            self._key_repr_computer = key_repr
            already_computed = False
        else:
            self.external_key_repr, self.key_repr = self.pickkeyrepr(key_repr)
        if not isinstance(value_repr, rmodel.Repr):  # not computed yet, done by setup()
            assert callable(value_repr)
            self._value_repr_computer = value_repr
            already_computed = False
        else:
            self.external_value_repr, self.value_repr = self.pickrepr(value_repr)

        if already_computed:
            self.DICT = ootype.Dict(key_repr.lowleveltype, value_repr.lowleveltype)
        else:
            self.DICT = ootype.ForwardReference()
        self.lowleveltype = self.DICT

        self.dictkey = dictkey
        self.dictvalue = dictvalue
        self.dict_cache = {}
        self._custom_eq_hash_repr = custom_eq_hash
        # setup() needs to be called to finish this initialization

    def _setup_repr(self):
        if 'key_repr' not in self.__dict__:
            key_repr = self._key_repr_computer()
            self.external_key_repr, self.key_repr = self.pickkeyrepr(key_repr)
        if 'value_repr' not in self.__dict__:
            self.external_value_repr, self.value_repr = self.pickrepr(self._value_repr_computer())
            
        if isinstance(self.DICT, ootype.ForwardReference):
            self.lowleveltype.become(ootype.Dict(self.key_repr.lowleveltype,
                                                 self.value_repr.lowleveltype))

    def send_message(self, hop, message, can_raise=False, v_args=None):
        if v_args is None:
            v_args = hop.inputargs(self, *hop.args_r[1:])
        c_name = hop.inputconst(ootype.Void, message)
        if can_raise:
            hop.exception_is_here()
        return hop.genop("oosend", [c_name] + v_args,
                resulttype=hop.r_result.lowleveltype)


class __extend__(pairtype(DictRepr, rmodel.Repr)): 

    def rtype_getitem((r_dict, r_key), hop):
        v_dict, v_key = hop.inputargs(r_dict, r_dict.key_repr)
        if not r_dict.custom_eq_hash: # TODO: why only in this case?
            hop.has_implicit_exception(KeyError)   # record that we know about it
        hop.exception_is_here()
        v_res = r_dict.send_message(hop, 'll_getitem', can_raise=True)
        return r_dict.recast_value(hop.llops, v_res)

##    def rtype_delitem((r_dict, r_key), hop):
##        v_dict, v_key = hop.inputargs(r_dict, r_dict.key_repr)
##        if not r_dict.custom_eq_hash:
##            hop.has_implicit_exception(KeyError)   # record that we know about it        
##        hop.exception_is_here()
##        return hop.gendirectcall(ll_dict_delitem, v_dict, v_key)

    def rtype_setitem((r_dict, r_key), hop):
        v_dict, v_key, v_value = hop.inputargs(r_dict, r_dict.key_repr, r_dict.value_repr)
##        if r_dict.custom_eq_hash:
##            hop.exception_is_here()
##        else:
##            hop.exception_cannot_occur()
        hop.exception_is_here()
        return r_dict.send_message(hop, 'll_setitem', can_raise=True)


def ll_newdict(DICT):
    return ootype.new(DICT)
