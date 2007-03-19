import py
from pypy.config.config import OptionDescription, BoolOption, IntOption
from pypy.config.config import ChoiceOption, Config

import sys
system_optiondescription = OptionDescription('system', '', [
    IntOption('maxint', 'maximum int value', default=sys.maxint),
    ChoiceOption('byteorder', 'endianness, byte order (little/big)',
                 ['little', 'big'], default=sys.byteorder),
    ChoiceOption('os', 'operating system', ['win32', 'linux2'],
                 default=sys.platform),
])

