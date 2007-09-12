package pypy;

import java.io.*;
import java.util.HashMap;
import java.util.ArrayList;
import java.util.Map;

abstract class FileWrapper
{
    public abstract void write(String buffer);
    public abstract String read(int count);
    public abstract void close();
    public abstract RandomAccessFile getFile();
}

class PrintStreamWrapper extends FileWrapper
{
    private PrintStream stream;

    public PrintStreamWrapper(PrintStream stream)
    {
        this.stream = stream;
    }

    public void write(String buffer)
    {
        this.stream.print(buffer);
    }

    public String read(int count)
    {
        ll_os.throwOSError(PyPy.EBADF, "Write-only fd");
        return null; // never reached
    }

    public void close()
    {
        ll_os.throwOSError(PyPy.EBADF, "Cannot close stdout or stderr");
    }

    public RandomAccessFile getFile()
    {
        return null;
    }
}

class InputStreamWrapper extends FileWrapper
{
    private InputStream stream;

    public InputStreamWrapper(InputStream stream)
    {
        this.stream = stream;
    }

    public void write(String buffer)
    {
        ll_os.throwOSError(PyPy.EBADF, "Read-only fd");
    }

    public String read(int count)
    {
        try {
            byte[] buf = new byte[count];
            int n = stream.read(buf, 0, count);
            return new String(buf);
        }
        catch(IOException e) {
            ll_os.throwOSError(PyPy.EIO, e.getMessage());
            return null; // never reached
        }
    }

    public void close()
    {
        ll_os.throwOSError(PyPy.EBADF, "Cannot close stdin");
    }

    public RandomAccessFile getFile()
    {
        return null;
    }
}

class RandomAccessFileWrapper extends FileWrapper
{
    private RandomAccessFile file;
    private boolean canRead;
    private boolean canWrite;

    public RandomAccessFileWrapper(RandomAccessFile file, boolean canRead, boolean canWrite)
    {
        this.file = file;
        this.canRead = canRead;
        this.canWrite = canWrite;
    }

    public void write(String buffer)
    {
        if (!this.canWrite)
            ll_os.throwOSError(PyPy.EBADF, "Cannot write to this fd");

        try {
            this.file.writeChars(buffer);
        }
        catch(IOException e) {
            ll_os.throwOSError(PyPy.EIO, e.getMessage());
        }
    }

    public String read(int count)
    {
        if (!this.canRead)
            ll_os.throwOSError(PyPy.EBADF, "Cannot read from this fd");

        try {
            byte[] buffer = new byte[count];
            int n = this.file.read(buffer);
            if (n == -1)
                return ""; // XXX: is it right?
            else
                return new String(buffer, 0, n);
        }
        catch(IOException e) {
            ll_os.throwOSError(PyPy.EIO, e.getMessage());
            return null; // never reached
        }
    }

    public void close()
    {
        try {
            this.file.close();
        }
        catch(IOException e) {
            ll_os.throwOSError(PyPy.EIO, e.getMessage());
        }
    }

    public RandomAccessFile getFile()
    {
        return this.file;
    }
}


public class ll_os {

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

    private static int fdcount;
    private static Map<Integer, FileWrapper> FileDescriptors = new HashMap<Integer, FileWrapper>();
    private static Map<Integer, String> ErrorMessages = new HashMap<Integer, String>();

    static {
        FileDescriptors.put(new Integer(0), new InputStreamWrapper(System.in));
        FileDescriptors.put(new Integer(1), new PrintStreamWrapper(System.out));
        FileDescriptors.put(new Integer(2), new PrintStreamWrapper(System.err));
        fdcount = 2;
    }

    public static void throwOSError(int errno, String errText) {
        ErrorMessages.put(new Integer(errno), errText);
        PyPy.interlink.throwOSError(errno);
    }

    private static FileWrapper getfd(int fd)
    {
        FileWrapper f = FileDescriptors.get(new Integer(fd));
        if (f == null)
            throwOSError(PyPy.EBADF, "Invalid file descriptor: " + fd);
        return f;
    }

    private static RandomAccessFile open_file(String name, String javaMode, int flags)
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

    public static int ll_os_open(String name, int flags, int mode)
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
        RandomAccessFileWrapper wrapper = new RandomAccessFileWrapper(file, canRead, canWrite);

        fdcount++;
        FileDescriptors.put(new Integer(fdcount), wrapper);
        return fdcount;
    }

    public static void ll_os_close(int fd)
    {
        FileWrapper wrapper = getfd(fd);
        wrapper.close();
        FileDescriptors.remove(new Integer(fd));
    }

    public static String ll_os_read(int fd, int count)
    {
        return getfd(fd).read(count);
    }

    public static String ll_os_read(int fd, long count)
    {
        return ll_os_read(fd, (int)count);
    }

    public static long ll_os_lseek(int fd, long offset, int whence)
    {
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

    public static StatResult ll_os_lstat(String path)
    {
        return ll_os_stat(path); // XXX
    }

    public static String ll_os_strerror(int errno)
    {
        String msg = ErrorMessages.remove(new Integer(errno));
        if (msg == null)
            return "errno: " + errno;
        else
            return msg;
    }

    public static int ll_os_write(int fd, String text) {
        FileWrapper f = FileDescriptors.get(new Integer(fd));
        if (f == null)
            throwOSError(PyPy.EBADF, "Invalid fd: " + fd);
        f.write(text);
        return text.length();
    }

    public static boolean ll_os_isatty(int x)
    {
        // XXX: this is not the right behaviour, but it's needed
        // to have the interactive interpreter working
        if (x == 0 || x == 1 || x == 2)
            return true;
        else
            return false;
    }
    
    public static ArrayList ll_os_envitems()
    {
        return new ArrayList(); // XXX
    }

    public static String ll_os_getcwd()
    {
        return System.getProperty("user.dir");
    }

    public static StatResult ll_os_stat(String path)
    {
        if (path.equals(""))
            ll_os.throwOSError(PyPy.ENOENT, "No such file or directory: ''");

        File f = new File(path);
        
        if (f.exists()) {
            StatResult res = new StatResult();
            if (f.isDirectory())
                res.setMode(S_IFDIR);
            else {
                res.setMode(S_IFREG);
                res.setSize(f.length());
                res.setMtime((int)f.lastModified());
            }
            return res;
        }

        ll_os.throwOSError(PyPy.ENOENT, "No such file or directory: '"+path+"'");
        return null; // never reached
    }
}
