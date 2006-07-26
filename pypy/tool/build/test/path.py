import py

testpath = py.magic.autopath().dirpath()
packagepath = testpath.dirpath()
rootpath = packagepath.dirpath().dirpath().dirpath()
py.std.sys.path.append(str(rootpath))
