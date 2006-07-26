import py

packagedir = py.magic.autopath().dirpath().dirpath()
rootpath = packagedir.dirpath().dirpath().dirpath()
py.std.sys.path.append(str(rootpath))
