from rpython.rlib import rposix
from rpython.rlib.objectmodel import specialize
from rpython.rtyper.lltypesystem import rffi


@specialize.argtype(0)
def opendir(path):
    path = rposix._as_bytes0(path)
    return opendir_bytes(path)

def opendir_bytes(path):
    dirp = rposix.c_opendir(path)
    if not dirp:
        raise OSError(rposix.get_saved_errno(), "opendir failed")
    return dirp

def closedir(dirp):
    rposix.c_closedir(dirp)

def nextentry(dirp):
    """Read the next entry and returns an opaque object.
    Use the methods has_xxx() and get_xxx() to read from that
    opaque object.  The opaque object is valid until the next
    time nextentry() or closedir() is called.  This may raise
    StopIteration, or OSError.  Note that this doesn't filter
    out the "." and ".." entries.
    """
    direntp = rposix.c_readdir(dirp)
    if direntp:
        return direntp
    error = rposix.get_saved_errno()
    if error:
        raise OSError(error, "readdir failed")
    raise StopIteration

def has_name_bytes(direntp):
    return True

def get_name_bytes(direntp):
    namep = rffi.cast(rffi.CCHARP, direntp.c_d_name)
    return rffi.charp2str(namep)

DT_UNKNOWN = rposix.dirent_config.get('DT_UNKNOWN', None)
DT_REG = rposix.dirent_config.get('DT_REG', None)
DT_DIR = rposix.dirent_config.get('DT_DIR', None)
DT_LNK = rposix.dirent_config.get('DT_LNK', None)

def has_type(direntp):
    return (DT_UNKNOWN is not None and
            rffi.getintfield(direntp, 'c_d_type') != DT_UNKNOWN)

def type_is_regular(direntp):
    return rffi.getintfield(direntp, 'c_d_type') == DT_REG

def type_is_dir(direntp):
    return rffi.getintfield(direntp, 'c_d_type') == DT_DIR

def type_is_link(direntp):
    return rffi.getintfield(direntp, 'c_d_type') == DT_LNK
