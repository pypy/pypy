package pypy;

import java.lang.ref.WeakReference;

public final class PyPyWeakRef {
    WeakReference wref;
    
    public static PyPyWeakRef create(Object obj) {
        PyPyWeakRef res = new PyPyWeakRef();
        res.ll_set(obj);
        return res;
    }

    public void ll_set(Object obj)
    {            
        this.wref = new WeakReference(obj);
    }

    public Object ll_deref()
    {
        return this.wref.get();
    }
}
