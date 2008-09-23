package pypy;

public class VoidArray {
    public final int length;

    public VoidArray(int length) {
        this.length = length;
    }

    /** invoked by generated code because it is easier than the constructor */
    public static VoidArray make(int length) {
        return new VoidArray(length);
    }

    public int ll_length() {
        return length;
    }

    public void ll_getitem_fast(int index) {
    }

    public void ll_setitem_fast(int index) {
    }
}
