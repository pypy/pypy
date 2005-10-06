# patches for the Boehm GC for PyPy under Windows

"""
How to build a pypy compatible version of the Boehm collector
for Windows and Visual Studio .net 2003.

First of all, download the official Boehm collector suite
from http://www.hpl.hp.com/personal/Hans_Boehm/gc/gc_source/gc.tar.gz
At the time of writing (2005-10-06) this contains version gc6.5 .

Unpack this folder somewhere, for instance to "d:\tmp".
Change to this folder using

d:
cd \tmp\gc6.5

Then copy the file NT_THREADS_MAKEFILE to Makefile:

copy NT_THREADS_MAKEFILE Makefile

This file is the general-purpose gc dllmakefile. For some internal
reasons, this file's defaults are bad for PyPy. Use this script to
do a patch: (assuming that you have d:\pypy\dist\pypy\translator\goal)

python d:\pypy\dist\pypy\translator\goal\gc_patch_windows.py

Now, your makefile is patched a little bit. In particular,

ALL_INTERIOR_POINTERS   is now undefined, which PyPy wants to have
NO_GETENV               is specified, since we don't want dependencies

and the name of the .lib and .dll files is changed to gc_pypy.???

Now you need to build your gc, either as a debug or as a release
build. First of all, make sure that you have your environment prepared.

With my setup, I have to do

"e:\Programme\Microsoft Visual Studio .NET 2003\Vc7\bin\vcvars32.bat"

After that, you can either build a release or a debug gc. 

After a successful build, you need to enable gc_pypy.dll for your compiler.
There are many ways to install this. The followong recommendation just
works without changing your environment variables. I think this is the
easiest way possible, but this is a matter of taste. What I did is:

nmake CFG="gc - Win32 Release"

After the build, you will find a gc_pypy.dll file in the Release folder.
Copy this file to c:\windows\system32 or any other folder that is always
in your PATH variable.

Also, copy Release\gc_pypy.lib to (in my case)
"e:\Programme\Microsoft Visual Studio .NET 2003\Vc7\lib"

That's all, folks!

In case of a debug build, replace "Release" by "Debug", and also copy
gc_pypy.pdb to your lib folder. This allows you to use source-level
debugging.

Please use the above recipe and report any bugs to me.

cheers - chris
"""

REPLACE = {
    '"ALL_INTERIOR_POINTERS"': '"NO_GETENV"',
    }

for ending in "lib exp map pdb bsc dll pch".split():
    REPLACE["gc.%s" % ending] = "gc_pypy.%s" % ending

def change_settings(src):
    for old, new in REPLACE.items():
        newsrc = src.replace(old, new)
        if newsrc == src:
            raise ValueError, "this makefile does not contain %s" % old
        src = newsrc
    return src

def find_file():
    import os
    for name in os.listdir("."):
        if name.lower() == 'makefile':
            return name
    else:
        raise ValueError, 'Makefile not found'

try:
    name = find_file()
    source = change_settings(file(name).read())
    file(name, "w").write(source)
    print "Updated your Makefile to fit PyPy's needs. Your lib will be named gc_pypy.dll"
    print "and gc_pypy.lib. Please put them into appropriate places, see __doc__."
except:
    print __doc__
    raise
