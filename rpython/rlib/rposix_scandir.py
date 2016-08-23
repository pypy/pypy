from rpython.rlib import rposix
from rpython.rlib.objectmodel import specialize
from rpython.rtyper.lltypesystem import lltype, rffi


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

NULL_DIRP = lltype.nullptr(rposix.DIRP.TO)

def nextentry(dirp):
    """Read the next entry and returns an opaque object.
    Use the methods has_xxx() and get_xxx() to read from that
    opaque object.  The opaque object is valid until the next
    time nextentry() or closedir() is called.  This may raise
    OSError, or return a NULL pointer when exhausted.  Note
    that this doesn't filter out the "." and ".." entries.
    """
    direntp = rposix.c_readdir(dirp)
    if direntp:
        error = rposix.get_saved_errno()
        if error:
            raise OSError(error, "readdir failed")
    return direntp

def has_name_bytes(direntp):
    return True

def get_name_bytes(direntp):
    namep = rffi.cast(rffi.CCHARP, direntp.c_d_name)
    return rffi.charp2str(namep)

DT_UNKNOWN = rposix.dirent_config.get('DT_UNKNOWN', 0)
DT_REG = rposix.dirent_config.get('DT_REG', 255)
DT_DIR = rposix.dirent_config.get('DT_DIR', 255)
DT_LNK = rposix.dirent_config.get('DT_LNK', 255)

def get_known_type(direntp):
    if rposix.HAVE_D_TYPE:
        return rffi.getintfield(direntp, 'c_d_type')
    return DT_UNKNOWN
