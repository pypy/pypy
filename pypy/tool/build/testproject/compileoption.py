import py
from pypy.config.config import OptionDescription, BoolOption, IntOption
from pypy.config.config import ChoiceOption, Config

import sys
compile_optiondescription = OptionDescription('compile', '', [
    IntOption('moo', 'moo level', default=1),
])

