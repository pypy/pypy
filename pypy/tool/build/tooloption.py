import py
from pypy.config.config import StrOption, IntOption
from pypy.config.config import OptionDescription, Config

import sys
tool_optiondescription = OptionDescription('tool', '', [
    IntOption('svnrev', 'Subversion revision', default='HEAD'),
    StrOption('svnpath', 'Subversion path (relative to the project root)',
              default='dist'),
    StrOption('revrange', 'Revision range (max difference in revision between '
                          'requested build and result)', default=0),
])

tool_config = Config(tool_optiondescription)
