from rpython.rlib import jit
from rpython.rlib.objectmodel import specialize, we_are_translated
from rpython.rlib.unroll import unrolling_iterable

class SignatureFactory(object):
    def __init__(self):
        self.cache = {}
        self.extra_attrs = []
        self.extra_attr_names = []
        self.init_extra_attrs = lambda self: None

    def getsignature(self, name, numargs, cache=True):
        if cache:
            return self._getsignature_elidable(name, numargs)
        return self._getsignature(name, numargs, False)

    @jit.elidable
    def _getsignature_elidable(self, name, numargs):
        return self._getsignature(name, numargs, True)

    def _getsignature(self, name, numargs, cache):
        if (name, numargs) in self.cache:
            return self.cache[name, numargs]
        res = Signature(name, numargs, cached=cache, factory=self)
        if cache:
            self.cache[name, numargs] = res
        return res

    def ensure_cached(self, signature):
        sig = self.cache.get((signature.name, signature.numargs), None)
        if sig:
            return sig
        self.cache[signature.name, signature.numargs] = signature
        signature.cached = True
        return signature

    def register_extr_attr(self, name, engine=False, default=None):
        aname = "extra_attr_" + name
        ename = "extra_attr_engine_" + name
        self.extra_attr_names.append(aname)
        self.extra_attrs.append((aname, default))
        if engine:
            assert default is None
            self.extra_attr_names.append(ename)
            self.extra_attrs.append((ename, None))
        for signature in self.cache.itervalues():
            setattr(signature, aname, default)
            if engine:
                setattr(signature, ename, None)
        extra_attrs_unrolling = unrolling_iterable(self.extra_attrs)
        def init_extra_attrs(signature):
            for attr, val in extra_attrs_unrolling:
                setattr(signature, attr, val)
        self.init_extra_attrs = init_extra_attrs

    def __freeze__(self):
        return True


class Signature(object):
    """An object representing the signature of a Prolog term."""

    _cache = SignatureFactory()

    _immutable_fields_ = ["name", "numargs", "atom_signature", "factory"]

    def __init__(self, name, numargs, cached=False, factory=None):
        assert name is not None
        assert isinstance(name, str)
        self.name = name
        self.numargs = numargs
        self.cached = cached
        if factory is None:
            factory = self._cache
        self.factory = factory
        if numargs:
            atom_signature = factory.getsignature(name, 0, cached)
        else:
            atom_signature = self
        self.atom_signature = atom_signature
        factory.init_extra_attrs(self)

    def eq(self, other):
        # slightly evil
        if jit.isconstant(self):
            jit.promote(other)
        elif jit.isconstant(other):
            jit.promote(self)
        return self is other or (
                self.numargs == other.numargs and
                self.name == other.name)

    @specialize.arg(1)
    def get_extra(self, name):
        aname = "extra_attr_" + name
        if not we_are_translated():
            assert aname in self.factory.extra_attr_names
        self = self.ensure_cached()
        return getattr(self, aname)

    @specialize.arg(1)
    def set_extra(self, name, val):
        aname = "extra_attr_" + name
        if not we_are_translated():
            assert aname in self.factory.extra_attr_names
        self = self.ensure_cached()
        setattr(self, aname, val)


    @specialize.arg(1)
    def get_extra_engine_local(self, name, engine):
        ename = "extra_attr_engine_" + name
        if not we_are_translated():
            assert ename in self.factory.extra_attr_names
        if getattr(self, ename) is not engine:
            setattr(self, ename, engine)
            aname = "extra_attr_" + name
            setattr(self, aname, None)    
        return self.get_extra(name)

    @specialize.arg(1)
    def set_extra_engine_local(self, name, val, engine):
        ename = "extra_attr_engine_" + name
        setattr(self, ename, engine)
        self.set_extra(name, val)

    def ensure_cached(self):
        if self.cached:
            return self
        return self.factory.ensure_cached(self)

    def string(self):
        return "%s/%s" % (self.name, self.numargs)

    def __repr__(self):
        return "<Signature %s>" % (self.string(), )

    @staticmethod
    @jit.elidable
    def getsignature(name, numargs):
        return Signature._cache.getsignature(name, numargs)

    @staticmethod
    def register_extr_attr(name, engine=False, default=None):
        Signature._cache.register_extr_attr(name, engine, default)
