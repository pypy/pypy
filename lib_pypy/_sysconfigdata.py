import _imp

so_ext = _imp.extension_suffixes()[0]

build_time_vars = {
    "EXT_SUFFIX": so_ext,
    "SHLIB_SUFFIX": so_ext,
    "SOABI": '-'.join(so_ext.split('.')[1].split('-')[:2]),
    "SO": so_ext  # deprecated in Python 3, for backward compatibility
}
