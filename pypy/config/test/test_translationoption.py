import py
from pypy.config.translationoption import get_combined_translation_config
from pypy.config.translationoption import set_opt_level
from pypy.config.config import ConflictConfigError


def test_no_gcrootfinder_with_boehm():
    config = get_combined_translation_config()
    config.translation.gcrootfinder = "shadowstack"
    py.test.raises(ConflictConfigError, set_opt_level, config, '0')
