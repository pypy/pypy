from rpython.translator.c.test.test_standalone import StandaloneTests
from rpython.config.translationoption import get_combined_translation_config
from pypy.config.pypyoption import get_pypy_config
from pypy.objspace.fake.checkmodule import checkmodule
from pypy.objspace.fake.objspace import FakeObjSpace
from pypy.module._hpy_universal.state import State

def attach_dict_strategy(space):
    # this is needed for modules which do e.g. "isinstance(w_obj,
    # W_DictMultiObject)", like _hpy_universal. Make sure that the
    # annotator sees a concrete class, like W_DictObject, else lots of
    # operations are blocked.
    from pypy.objspace.std.dictmultiobject import W_DictObject, ObjectDictStrategy
    strategy = ObjectDictStrategy(space)
    storage = strategy.get_empty_storage()
    w_obj = W_DictObject(space, strategy, storage)

def test_checkmodule():
    def extra_func(space):
        state = space.fromcache(State)
        state.setup()
        attach_dict_strategy(space)

    rpython_opts = {'translation.gc': 'boehm'}
    # it isn't possible to ztranslate cpyext easily, so we check _hpy_universal
    # WITHOUT the cpyext parts
    pypy_opts = {'objspace.std.withliststrategies': False,
                 'objspace.hpy_cpyext_API': False}
    checkmodule('_hpy_universal',
                extra_func=extra_func,
                c_compile=True,
                rpython_opts=rpython_opts,
                pypy_opts=pypy_opts,
                show_pdbplus=False,
                )
