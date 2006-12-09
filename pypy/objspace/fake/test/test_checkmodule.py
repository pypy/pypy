import py
from pypy.objspace.fake.checkmodule import checkmodule

def test_dotnet():
    # the only module known to pass checkmodule is _dotnet so far
    checkmodule('_dotnet', 'cli')
