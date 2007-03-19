import py
from pypy.config.config import OptionDescription, BoolOption, IntOption
from pypy.config.config import ChoiceOption, Config

import sys
compile_optiondescription = OptionDescription('compile', '', [
    BoolOption('moo', 'moo while compiling', default=False),
])

