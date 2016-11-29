"""
Module objects.
"""

from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError, oefmt
from rpython.rlib.objectmodel import we_are_translated


class Module(W_Root):
    """A module."""

    _immutable_fields_ = ["w_dict?"]

    _frozen = False

    def __init__(self, space, w_name, w_dict=None, add_package=True):
        self.space = space
        if w_dict is None:
            w_dict = space.newdict(module=True)
        self.w_dict = w_dict
        self.w_name = w_name
        if w_name is not None:
            space.setitem(w_dict, space.new_interned_str('__name__'), w_name)
        if add_package:
            # add the __package__ attribute only when created from internal
            # code, but not when created from Python code (as in CPython)
            space.setitem(w_dict, space.new_interned_str('__package__'),
                          space.w_None)
        self.startup_called = False

    def _cleanup_(self):
        """Called by the annotator on prebuilt Module instances.
        We don't have many such modules, but for the ones that
        show up, remove their __file__ rather than translate it
        statically inside the executable."""
        try:
            space = self.space
            space.delitem(self.w_dict, space.wrap('__file__'))
        except OperationError:
            pass

    def install(self):
        """NOT_RPYTHON: installs this module into space.builtin_modules"""
        w_mod = self.space.wrap(self)
        modulename = self.space.str0_w(self.w_name)
        self.space.builtin_modules[modulename] = w_mod

    def setup_after_space_initialization(self):
        """NOT_RPYTHON: to allow built-in modules to do some more setup
        after the space is fully initialized."""

    def init(self, space):
        """This is called each time the module is imported or reloaded
        """
        if not self.startup_called:
            if not we_are_translated():
                # this special case is to handle the case, during annotation,
                # of module A that gets frozen, then module B (e.g. during
                # a getdict()) runs some code that imports A
                if self._frozen:
                    return
            self.startup_called = True
            self.startup(space)

    def startup(self, space):
        """This is called at runtime on import to allow the module to
        do initialization when it is imported for the first time.
        """

    def shutdown(self, space):
        """This is called when the space is shut down, just after
        atexit functions, if the module has been imported.
        """

    def getdict(self, space):
        return self.w_dict

    def descr_module__new__(space, w_subtype, __args__):
        module = space.allocate_instance(Module, w_subtype)
        Module.__init__(module, space, None, add_package=False)
        return space.wrap(module)

    def descr_module__init__(self, w_name, w_doc=None):
        space = self.space
        self.w_name = w_name
        if w_doc is None:
            w_doc = space.w_None
        space.setitem(self.w_dict, space.new_interned_str('__name__'), w_name)
        space.setitem(self.w_dict, space.new_interned_str('__doc__'), w_doc)

    def descr__reduce__(self, space):
        w_name = space.finditem(self.w_dict, space.wrap('__name__'))
        if (w_name is None or
            not space.isinstance_w(w_name, space.w_unicode)):
            # maybe raise exception here (XXX this path is untested)
            return space.w_None
        w_modules = space.sys.get('modules')
        if space.finditem(w_modules, w_name) is None:
            #not imported case
            from pypy.interpreter.mixedmodule import MixedModule
            w_mod    = space.getbuiltinmodule('_pickle_support')
            mod      = space.interp_w(MixedModule, w_mod)
            new_inst = mod.get('module_new')
            return space.newtuple([new_inst,
                                   space.newtuple([w_name,
                                                   self.getdict(space)]),
                                  ])
        #already imported case
        w_import = space.builtin.get('__import__')
        tup_return = [
            w_import,
            space.newtuple([
                w_name,
                space.w_None,
                space.w_None,
                space.newtuple([space.wrap('')])
            ])
        ]

        return space.newtuple(tup_return)

    def descr_module__repr__(self, space):
        w_loader = space.finditem(self.w_dict, space.wrap('__loader__'))
        if w_loader is not None:
            try:
                return space.call_method(w_loader, "module_repr", self)
            except OperationError, operr:
                if not operr.match(space, space.w_Exception):
                    raise
        try:
            w_name = space.getattr(self, space.wrap('__name__'))
            name = space.unicode_w(space.repr(w_name))
        except OperationError:
            name = u"'?'"

        try:
            w___file__ = space.getattr(self, space.wrap('__file__'))
        except OperationError:
            w___file__ = space.w_None
        if not space.isinstance_w(w___file__, space.w_unicode):
            if w_loader is not None:
                w_loader_repr = space.unicode_w(space.repr(w_loader))
                return space.wrap(u"<module %s (%s)>" % (name, w_loader_repr))
            else:
                return space.wrap(u"<module %s>" % (name,))
        else:
            __file__ = space.unicode_w(space.repr(w___file__))
            return space.wrap(u"<module %s from %s>" % (name, __file__))

    def descr_getattribute(self, space, w_attr):
        from pypy.objspace.descroperation import object_getattribute
        try:
            return space.call_function(object_getattribute(space), self, w_attr)
        except OperationError as e:
            if not e.match(space, space.w_AttributeError):
                raise
            w_name = space.finditem(self.w_dict, space.wrap('__name__'))
            if w_name is None:
                raise oefmt(space.w_AttributeError,
                    "module has no attribute %R", w_attr)
            else:
                raise oefmt(space.w_AttributeError,
                    "module %R has no attribute %R", w_name, w_attr)

    def descr_module__dir__(self, space):
        w_dict = space.getattr(self, space.wrap('__dict__'))
        if not space.isinstance_w(w_dict, space.w_dict):
            raise oefmt(space.w_TypeError, "%N.__dict__ is not a dictionary",
                        self)
        return space.call_function(space.w_list, w_dict)
