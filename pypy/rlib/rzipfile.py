
from zipfile import ZIP_STORED, ZIP_DEFLATED
from pypy.rlib.streamio import open_file_as_stream
from pypy.rlib.rstruct.runpack import runpack
import os
from pypy.rlib import rzlib
from pypy.rlib.rarithmetic import r_uint, intmask

# XXX hack to get crc32 to work
from pypy.lib.binascii import crc_32_tab

rcrc_32_tab = [r_uint(i) for i in crc_32_tab]

def crc32(s, crc=0):
    result = 0
    crc = ~r_uint(crc) & 0xffffffffL
    for c in s:
        crc = rcrc_32_tab[(crc ^ r_uint(ord(c))) & 0xffL] ^ (crc >> 8)
        #/* Note:  (crc >> 8) MUST zero fill on left

        result = crc ^ 0xffffffffL
    
    return result

# parts copied from zipfile library implementation

class BadZipfile(Exception):
    pass

# Here are some struct module formats for reading headers
structEndArchive = "<4s4H2lH"     # 9 items, end of archive, 22 bytes
stringEndArchive = "PK\005\006"   # magic number for end of archive record
structCentralDir = "<4s4B4HlLL5HLl"# 19 items, central directory, 46 bytes
stringCentralDir = "PK\001\002"   # magic number for central directory
structFileHeader = "<4s2B4HlLL2H"  # 12 items, file header record, 30 bytes
stringFileHeader = "PK\003\004"   # magic number for file header

# indexes of entries in the central directory structure
_CD_SIGNATURE = 0
_CD_CREATE_VERSION = 1
_CD_CREATE_SYSTEM = 2
_CD_EXTRACT_VERSION = 3
_CD_EXTRACT_SYSTEM = 4                  # is this meaningful?
_CD_FLAG_BITS = 5
_CD_COMPRESS_TYPE = 6
_CD_TIME = 7
_CD_DATE = 8
_CD_CRC = 9
_CD_COMPRESSED_SIZE = 10
_CD_UNCOMPRESSED_SIZE = 11
_CD_FILENAME_LENGTH = 12
_CD_EXTRA_FIELD_LENGTH = 13
_CD_COMMENT_LENGTH = 14
_CD_DISK_NUMBER_START = 15
_CD_INTERNAL_FILE_ATTRIBUTES = 16
_CD_EXTERNAL_FILE_ATTRIBUTES = 17
_CD_LOCAL_HEADER_OFFSET = 18

# indexes of entries in the local file header structure
_FH_SIGNATURE = 0
_FH_EXTRACT_VERSION = 1
_FH_EXTRACT_SYSTEM = 2                  # is this meaningful?
_FH_GENERAL_PURPOSE_FLAG_BITS = 3
_FH_COMPRESSION_METHOD = 4
_FH_LAST_MOD_TIME = 5
_FH_LAST_MOD_DATE = 6
_FH_CRC = 7
_FH_COMPRESSED_SIZE = 8
_FH_UNCOMPRESSED_SIZE = 9
_FH_FILENAME_LENGTH = 10
_FH_EXTRA_FIELD_LENGTH = 11

class EndRecStruct(object):
    def __init__(self, stuff, comment, filesize):
        self.stuff = stuff
        self.comment = comment
        self.filesize = filesize

def _EndRecData(fpin):
    """Return data from the "End of Central Directory" record, or None.

    The data is a list of the nine items in the ZIP "End of central dir"
    record followed by a tenth item, the file seek offset of this record."""
    fpin.seek(-22, 2)               # Assume no archive comment.
    filesize = fpin.tell() + 22     # Get file size
    data = fpin.readall()
    start = len(data)-2
    assert start > 0
    if data[0:4] == stringEndArchive and data[start:] == "\000\000":
        endrec = runpack(structEndArchive, data)
        return EndRecStruct(endrec, "", filesize - 22)
    # Search the last END_BLOCK bytes of the file for the record signature.
    # The comment is appended to the ZIP file and has a 16 bit length.
    # So the comment may be up to 64K long.  We limit the search for the
    # signature to a few Kbytes at the end of the file for efficiency.
    # also, the signature must not appear in the comment.
    END_BLOCK = min(filesize, 1024 * 4)
    fpin.seek(filesize - END_BLOCK, 0)
    data = fpin.readall()
    start = data.rfind(stringEndArchive)
    if start >= 0:     # Correct signature string was found
        endrec = runpack(structEndArchive, data[start:start+22])
        comment = data[start+22:]
        if endrec[7] == len(comment):     # Comment length checks out
            # Append the archive comment and start offset
            return EndRecStruct(endrec, comment, filesize - END_BLOCK + start)
    return      # Error, return None

class RZipInfo(object):
    def __init__(self, filename, date_time=(1980,1,1,0,0,0)):
        self.orig_filename = filename
        null_byte = filename.find(chr(0))
        if null_byte >= 0:
            filename = filename[0:null_byte]
# This is used to ensure paths in generated ZIP files always use
# forward slashes as the directory separator, as required by the
# ZIP format specification.
        if os.sep != "/":
            filename = filename.replace(os.sep, "/")
        self.filename = filename        # Normalized file name
        self.date_time = date_time      # year, month, day, hour, min, sec
        # Standard values:
        self.compress_type = ZIP_STORED # Type of compression for the file
        self.comment = ""               # Comment for each file
        self.extra = ""                 # ZIP extra data
        self.create_system = 0          # System which created ZIP archive
        self.create_version = 20        # Version which created ZIP archive
        self.extract_version = 20       # Version needed to extract archive
        self.reserved = 0               # Must be zero
        self.flag_bits = 0              # ZIP flag bits
        self.volume = 0                 # Volume number of file header
        self.internal_attr = 0          # Internal attributes
        self.external_attr = 0          # External file attributes
        # Other attributes are set by class ZipFile:
        # header_offset         Byte offset to the file header
        # file_offset           Byte offset to the start of the file data
        # CRC                   CRC-32 of the uncompressed file
        # compress_size         Size of the compressed file
        # file_size             Size of the uncompressed file

class RZipFile(object):
    def __init__(self, zipname, mode='r', compression=ZIP_STORED):
        if mode != 'r':
            raise TypeError("Read only support by now")
        self.compression = compression
        self.filename = zipname
        self.mode = mode
        self.filelist = []
        self.NameToInfo = {}
        fp = open_file_as_stream(zipname, mode, 1024)
        self._GetContents(fp)
        self.fp = fp

    def _GetContents(self, fp):
        endrec = _EndRecData(fp)
        if not endrec:
            raise BadZipfile, "File is not a zip file"
        size_cd = endrec.stuff[5]             # bytes in central directory
        offset_cd = endrec.stuff[6]   # offset of central directory
        self.comment = endrec.comment
        x = endrec.filesize - size_cd
        concat = x - offset_cd
        self.start_dir = offset_cd + concat
        fp.seek(self.start_dir, 0)
        total = 0
        while total < size_cd:
            centdir = fp.read(46)
            total = total + 46
            if centdir[0:4] != stringCentralDir:
                raise BadZipfile, "Bad magic number for central directory"
            centdir = runpack(structCentralDir, centdir)
            filename = fp.read(centdir[_CD_FILENAME_LENGTH])
            # Create ZipInfo instance to store file information
            x = RZipInfo(filename)
            x.extra = fp.read(centdir[_CD_EXTRA_FIELD_LENGTH])
            x.comment = fp.read(centdir[_CD_COMMENT_LENGTH])
            total = (total + centdir[_CD_FILENAME_LENGTH]
                     + centdir[_CD_EXTRA_FIELD_LENGTH]
                     + centdir[_CD_COMMENT_LENGTH])
            x.header_offset = centdir[_CD_LOCAL_HEADER_OFFSET] + concat
            # file_offset must be computed below...
            (x.create_version, x.create_system, x.extract_version, x.reserved,
                x.flag_bits, x.compress_type, t, d,
                crc, x.compress_size, x.file_size) = centdir[1:12]
            x.CRC = r_uint(crc) & 0xffffffff
            x.dostime = t
            x.dosdate = d
            x.volume, x.internal_attr, x.external_attr = centdir[15:18]
            # Convert date/time code to (year, month, day, hour, min, sec)
            x.date_time = ( (d>>9)+1980, (d>>5)&0xF, d&0x1F,
                                     t>>11, (t>>5)&0x3F, (t&0x1F) * 2 )
            self.filelist.append(x)
            self.NameToInfo[x.filename] = x
        for data in self.filelist:
            fp.seek(data.header_offset, 0)
            fheader = fp.read(30)
            if fheader[0:4] != stringFileHeader:
                raise BadZipfile, "Bad magic number for file header"
            fheader = runpack(structFileHeader, fheader)
            # file_offset is computed here, since the extra field for
            # the central directory and for the local file header
            # refer to different fields, and they can have different
            # lengths
            data.file_offset = (data.header_offset + 30
                                + fheader[_FH_FILENAME_LENGTH]
                                + fheader[_FH_EXTRA_FIELD_LENGTH])
            fname = fp.read(fheader[_FH_FILENAME_LENGTH])
            if fname != data.orig_filename:
                raise RuntimeError, \
                      'File name in directory "%s" and header "%s" differ.' % (
                          data.orig_filename, fname)
        fp.seek(self.start_dir, 0)
        
    def getinfo(self, filename):
        """Return the instance of ZipInfo given 'filename'."""
        return self.NameToInfo[filename]

    def read(self, filename):
        zinfo = self.getinfo(filename)
        filepos = self.fp.tell()
        self.fp.seek(zinfo.file_offset, 0)
        bytes = self.fp.read(intmask(zinfo.compress_size))
        self.fp.seek(filepos, 0)
        if zinfo.compress_type == ZIP_STORED:
            pass
        elif zinfo.compress_type == ZIP_DEFLATED:
            stream = rzlib.inflateInit(wbits=-15)
            try:
                bytes, _, _ = rzlib.decompress(stream, bytes)
                # need to feed in unused pad byte so that zlib won't choke
                ex, _, _ = rzlib.decompress(stream, 'Z')
                if ex:
                    bytes = bytes + ex
            finally:
                rzlib.inflateEnd(stream)
        else:
            raise BadZipfile, \
                  "Unsupported compression method %d for file %s" % \
            (zinfo.compress_type, filename)
        crc = crc32(bytes)
        if crc != zinfo.CRC:
            raise BadZipfile, "Bad CRC-32 for file %s" % filename
        return bytes
    
