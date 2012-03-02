package pypy;

import java.io.*;
import java.util.HashMap;
import java.util.ArrayList;
import java.util.Map;
import java.util.Set;
import java.util.Iterator;
import java.util.Arrays;

import com.sun.jna.Library;
import com.sun.jna.Native;
import com.sun.jna.Platform;

abstract class FileWrapper
{
    private final String name;

    public FileWrapper(String name)
    {
        this.name = name;
    }

    public abstract void write(String buffer);
    public abstract String read(int count);
    public abstract void close();
    public abstract RandomAccessFile getFile();

    public String getName()
    {
        return this.name;
    }
}

class PrintStreamWrapper extends FileWrapper
{
    private final PrintStream stream;
    private final ll_os os;

    public PrintStreamWrapper(String name, PrintStream stream, ll_os os)
    {
        super(name);
        this.stream = stream;
        this.os = os;
    }

    public void write(String buffer)
    {
        this.stream.print(buffer);
    }

    public String read(int count)
    {
        os.throwOSError(PyPy.EBADF, "Write-only fd");
        return null; // never reached
    }

    public void close()
    {
        os.throwOSError(PyPy.EBADF, "Cannot close stdout or stderr");
    }

    public RandomAccessFile getFile()
    {
        return null;
    }
}

class InputStreamWrapper extends FileWrapper
{
    private final InputStream stream;
    private final ll_os os;

    public InputStreamWrapper(String name, InputStream stream, ll_os os)
    {
        super(name);
        this.stream = stream;
        this.os = os;
    }

    public void write(String buffer)
    {
        os.throwOSError(PyPy.EBADF, "Read-only fd");
    }

    public String read(int count)
    {
        try {
            byte[] buf = new byte[count];
            int n = stream.read(buf, 0, count);
            if (n == -1)
                return ""; // XXX: is it right?
            return ll_os.bytes2string(buf, n);
        }
        catch(IOException e) {
            os.throwOSError(PyPy.EIO, e.getMessage());
            return null; // never reached
        }
    }

    public void close()
    {
        os.throwOSError(PyPy.EBADF, "Cannot close stdin");
    }

    public RandomAccessFile getFile()
    {
        return null;
    }
}

class RandomAccessFileWrapper extends FileWrapper
{
    private final RandomAccessFile file;
    private final boolean canRead;
    private final boolean canWrite;
    private final ll_os os;

    public RandomAccessFileWrapper(String name,
                                   RandomAccessFile file, 
                                   boolean canRead, 
                                   boolean canWrite,
                                   ll_os os)
    {
        super(name);
        this.file = file;
        this.canRead = canRead;
        this.canWrite = canWrite;
        this.os = os;
    }

    public void write(String buffer)
    {
        if (!this.canWrite)
            os.throwOSError(PyPy.EBADF, "Cannot write to this fd");

        try {
            this.file.writeBytes(buffer);
        }
        catch(IOException e) {
            os.throwOSError(PyPy.EIO, e.getMessage());
        }
    }

    public String read(int count)
    {
        if (!this.canRead)
            os.throwOSError(PyPy.EBADF, "Cannot read from this fd");

        try {
            byte[] buffer = new byte[count];
            int n = this.file.read(buffer);
            if (n == -1)
                return ""; // XXX: is it right?
            else
                return ll_os.bytes2string(buffer, n);
        }
        catch(IOException e) {
            os.throwOSError(PyPy.EIO, e.getMessage());
            return null; // never reached
        }
    }

    public void close()
    {
        try {
            this.file.close();
        }
        catch(IOException e) {
            os.throwOSError(PyPy.EIO, e.getMessage());
        }
    }

    public RandomAccessFile getFile()
    {
        return this.file;
    }
}


public class ll_os implements Constants {

    /** 
     * JNA Interface: allows access to functions we don't normally
     * have in the Java standard lib
     */
    static public interface Libc extends Library {
        public int getpid();
        public int symlink(String path1, String path2);
        public int access(String path, int mode);
    }

    static public interface Msvcrt extends Library {
         public int _access(String path, int mode);
    }

    static final Libc libc;
    static final Msvcrt msvcrt;
    static {
        Libc res = null;
        Msvcrt vcrt = null;
        try {
            if ((Platform.isWindows())) {
                vcrt = (Msvcrt) Native.loadLibrary("msvcrt", Msvcrt.class);
            }
            else {
                res = (Libc) Native.loadLibrary("c", Libc.class);
            }
        } catch (Throwable t) {
            res = null;
            vcrt = null;
        }
        libc = res;
        msvcrt = vcrt;
    }

    // NB: these values are those used by Windows and they differs
    // from the Unix ones; the os module is patched with these
    // values before flowgraphing to make sure we get the very
    // same values on each platform we do the compilation.
    private static final int O_RDONLY = 0x0000;
    private static final int O_WRONLY = 0x0001;
    private static final int O_RDWR   = 0x0002;
    private static final int O_APPEND = 0x0008;
    private static final int O_CREAT  = 0x0100;
    private static final int O_TRUNC  = 0x0200;
    private static final int O_TEXT   = 0x4000;
    private static final int O_BINARY = 0x8000;
    
    private static final int S_IFMT = 61440;
    private static final int S_IFDIR = 16384;
    private static final int S_IFREG = 32768;

    private static final int SEEK_SET = 0;
    private static final int SEEK_CUR = 1;
    private static final int SEEK_END = 2;

    private int fdcount;
    private final Map<Integer, FileWrapper> FileDescriptors = 
      new HashMap<Integer, FileWrapper>();
    private final Map<Integer, String> ErrorMessages = 
      new HashMap<Integer, String>();
    private final Interlink interlink;

    public ll_os(Interlink interlink) {
        this.interlink = interlink;
        FileDescriptors.put(0, new InputStreamWrapper("<stdin>", System.in, this));
        FileDescriptors.put(1, new PrintStreamWrapper("<stdout>", System.out, this));
        FileDescriptors.put(2, new PrintStreamWrapper("<stderr>", System.err, this));
        fdcount = 2;
    }

    public static final String bytes2string(byte[] buf, int n)
    {
        // careful: use this char set (ISO-8859-1) because it basically
        // passes all bytes through unhindered.
        try {
            return new String(buf, 0, n, "ISO-8859-1");
        } catch (UnsupportedEncodingException e) {
            // this should not happen, all Java impl are required
            // to support ISO-8859-1.
            throw new RuntimeException(e);
        }
    }

    public static final boolean STRACE = false;
    public static void strace(String arg) {
        System.err.println(arg);
    }

    public void throwOSError(int errno, String errText) {
        ErrorMessages.put(errno, errText);
        interlink.throwOSError(errno);
    }

    private FileWrapper getfd(int fd)
    {
        FileWrapper f = FileDescriptors.get(fd);
        if (f == null)
            throwOSError(PyPy.EBADF, "Invalid file descriptor: " + fd);
        return f;
    }

    private RandomAccessFile open_file(String name, String javaMode, int flags)
    {
        RandomAccessFile file;

        try {
            file = new RandomAccessFile(name, javaMode);
        }
        catch(IOException e) {
            throwOSError(PyPy.ENOENT, e.getMessage());
            return null;
        }

        try {
            if ((flags & O_TRUNC) !=0 )
                file.setLength(0);

            if ((flags & O_APPEND) !=0 )
                file.seek(file.length()-1);
        }
        catch(IOException e) {
            throwOSError(PyPy.EPERM, e.getMessage());
            return null;
        }

        return file;
    }
    
    public boolean ll_os_access(String path, int mode) {
        final int F_OK = 0;
        final int X_OK = 1;
        final int W_OK = 2;
        final int R_OK = 4; // XXX can we load these from RPython somehow?
        
        File file = new File(path);

        if (!file.exists())
            return false;
        
        // These methods only exist in Java 1.6:    
        //if ((mode & R_OK) != 0 && !file.canRead())
        //    return false;
        //
        //if ((mode & W_OK) != 0 && !file.canWrite())
        //    return false;
        //
        //if ((mode & X_OK) != 0 && !file.canExecute())
        //    return false;
        
        if (msvcrt != null) {
            return msvcrt._access(path, mode) == 0;
        }
        
        return libc.access(path, mode) == 0; // note that 0==success
    }

    public int ll_os_open(String name, int flags, int mode)
    {
        boolean canRead = false;
        boolean canWrite = false;

        if ((flags & O_RDWR) != 0) {
            canRead = true;
            canWrite = true;
        }
        else if ((flags & O_WRONLY) != 0)
            canWrite = true;
        else
            canRead = true;

        String javaMode = canWrite ? "rw" : "r";

        // XXX: we ignore O_CREAT
        RandomAccessFile file = open_file(name, javaMode, flags);
        RandomAccessFileWrapper wrapper = 
            new RandomAccessFileWrapper(name, file, canRead, canWrite, this);

        fdcount++;
        FileDescriptors.put(fdcount, wrapper);

        if (STRACE) strace("ll_os_open: "+name+"->"+fdcount);
        return fdcount;
    }

    public void ll_os_close(int fd)
    {
        if (STRACE) strace("ll_os_close: "+fd);
        FileWrapper wrapper = getfd(fd);
        wrapper.close();
        FileDescriptors.remove(fd);
    }

    public int ll_os_dup(int fd)
    {
        FileWrapper wrapper = getfd(fd);
        for (int i = 0; i < Integer.MAX_VALUE; i++) {
            if (FileDescriptors.get(i) == null) {
                FileDescriptors.put(i, wrapper);
                if (STRACE) strace("ll_os_dup: "+fd+" -> "+i);
                return i;
            }
        }
        throwOSError(EMFILE, "No remaining file descriptors.");
        return -1;
    }
    
    public String ll_os_read(int fd, int count)
    {
        if (STRACE) strace("ll_os_read: "+fd);
        return getfd(fd).read(count);
    }

    public String ll_os_read(int fd, long count)
    {
        if (STRACE) strace("ll_os_read: "+fd);
        return ll_os_read(fd, (int)count);
    }

    public long ll_os_lseek(int fd, long offset, int whence)
    {
        if (STRACE) strace("ll_os_lseek: "+fd);
        FileWrapper wrapper = getfd(fd);
        RandomAccessFile file = wrapper.getFile();
        if (file == null)
            throwOSError(PyPy.ESPIPE, "Illegal seek");

        long pos = 0;
        try {
            switch(whence) 
                {
                case SEEK_SET:
                    pos = offset;
                    break;
                case SEEK_CUR:
                    pos = file.getFilePointer() + offset;
                    break;
                case SEEK_END:
                    pos = file.length() + offset;
                    break;
                }
            file.seek(pos);
        }
        catch(IOException e) {
            throwOSError(PyPy.ESPIPE, e.getMessage());
        }
        
        return pos;
    }

    public StatResult ll_os_lstat(String path)
    {
        return ll_os_stat(path); // XXX
    }

    public StatResult ll_os_fstat(int fd)
    {
        String name = getfd(fd).getName();
        return ll_os_stat(name);
    }

    public String ll_os_strerror(int errno)
    {
        String msg = ErrorMessages.remove(errno);
        if (msg == null)
            return "errno: " + errno;
        else
            return msg;
    }

    public int ll_os_write(int fd, String text) {
        if (STRACE) strace("ll_os_write: "+fd+" "+text);        
        FileWrapper f = FileDescriptors.get(fd);
        if (f == null)
            throwOSError(PyPy.EBADF, "Invalid fd: " + fd);
        f.write(text);
        return text.length();
    }

    public void ll_os_mkdir(String path, int mode) {
        File f = new File(path);
        if (f.exists())
            throwOSError(PyPy.EEXIST, "File exists: '"+path+"'");
        if (!f.mkdir())
            throwOSError(PyPy.EPERM, "Operation not permitted: '"+path+"'");
    }

    public void delete(String path, boolean should_be_dir) {
        File f = new File(path);
        if (!f.exists())
            throwOSError(PyPy.ENOENT, "No such file or directory: '"+path+"'");
        if (f.isDirectory() != should_be_dir)
            throwOSError(PyPy.EPERM, "Operation not permitted: '"+path+"'");
        if (!f.delete())
            throwOSError(PyPy.EPERM, "Operation not permitted: '"+path+"'");
    }

    public void ll_os_rmdir(String path) {
        if (STRACE) strace("ll_os_rmdir: "+path);
        delete(path, true);
    }

    public void ll_os_unlink(String path) {
        if (STRACE) strace("ll_os_unlink: "+path);
        delete(path, false);
    }

    public boolean ll_os_isatty(int x)
    {
        // XXX: this is not the right behaviour, but it's needed
        // to have the interactive interpreter working
        if (x == 0 || x == 1 || x == 2)
            return true;
        else
            return false;
    }

    public String ll_os_getenv(String key)
    {
        return System.getenv(key);
    }
    
    public void ll_os_putenv(String key, String value)
    {
        //System.setenv(key, value);
        // it appears that there is no such method??!!
    }    
    
    public ArrayList ll_os_envkeys()
    {
        Map variables = System.getenv();
        Set variableNames = variables.keySet();
        return new ArrayList(variableNames);
    }
    
    public ArrayList ll_os_envitems()
    {
        Map variables = System.getenv();
        Set variableNames = variables.keySet();
        Iterator nameIterator = variableNames.iterator();
        ArrayList result = new ArrayList();

        for (int index = 0; index < variableNames.size(); index++)
        {
             String name = (String) nameIterator.next();
             String value = (String) variables.get(name);
             result.add(interlink.recordStringString(name, value));
        }
        
        return result;
    }
    
    public ArrayList<String> ll_os_listdir(String path)
    {
        if (path == "")
            throwOSError(PyPy.ENOENT, "No such file or directory: ''");
            
        File f = new File(path);
        if (!f.exists() || !f.isDirectory())
            throwOSError(PyPy.ENOENT, "No such file or directory: '"+path+"'");

        return new ArrayList(Arrays.asList(f.list()));
    }

    public String ll_os_getcwd()
    {
        return System.getProperty("user.dir");
    }

    public StatResult ll_os_stat(String path)
    {
        if (path.equals(""))
            throwOSError(PyPy.ENOENT, "No such file or directory: ''");

        File f = new File(path);
        
        if (f.exists()) {
            StatResult res = new StatResult();
            if (f.isDirectory())
                res.setMode(S_IFDIR);
            else {
                res.setMode(S_IFREG);
                res.setSize(f.length());
                res.setMtime((double)f.lastModified());
            }
            return res;
        }

        throwOSError(PyPy.ENOENT, "No such file or directory: '"+path+"'");
        return null; // never reached
    }

    public void checkLibc() {
        if (libc == null)
            throwOSError(EPERM, "jna.jar and an Unix are required");
    }

    public int ll_os_getpid() 
    {
        checkLibc();
        return libc.getpid();
    }

    public void ll_os_symlink(String path1, String path2) 
    {
        checkLibc();
        int res = libc.symlink(path1, path2);
        if (res != 0)
            throwOSError(res, "");
    }

    public String posix__getfullpathname(String name)
    {
        return new File(name).getAbsolutePath();
    }
}
