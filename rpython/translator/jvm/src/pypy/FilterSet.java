package pypy;

import java.lang.reflect.Array;
import java.util.Collection;
import java.util.Iterator;
import java.util.Set;

public class FilterSet<F,T> implements Set<T> {
    
    public final Set<F> base;    
    public final Filter<F,T> filter;

    public FilterSet(final Set<F> base, final Filter<F, T> filter) {
        this.base = base;
        this.filter = filter;
    }

    public boolean add(T o) {
        return this.base.add(filter.from(o));
    }

    public boolean addAll(Collection<? extends T> c) {
        boolean res = false;
        for (T t : c) {
            res = add(t) || res;
        }
        return res;
    }

    public void clear() {
        this.base.clear();
    }

    public boolean contains(Object o) {
        return this.base.contains(o);
    }

    public boolean containsAll(Collection<?> c) {
        return this.base.containsAll(c);
    }

    public boolean isEmpty() {
        return this.base.isEmpty();
    }

    public Iterator<T> iterator() {
        return new FilterIterator<F,T>(this.base.iterator(), filter);
    }

    public boolean remove(Object o) {
        return this.base.remove(o);
    }

    public boolean removeAll(Collection<?> c) {
        return this.base.removeAll(c);
    }

    public boolean retainAll(Collection<?> c) {
        return this.base.retainAll(c);
    }

    public int size() {
        return this.base.size();
    }

    @SuppressWarnings("unchecked")
    public Object[] toArray() {        
        Object[] froms = this.base.toArray();
        Object[] tos = new Object[froms.length];
        for (int i = 0; i < froms.length; i++)
            tos[i] = filter.to((F)tos[i]);
        return tos;
    }

    public <X> X[] toArray(X[] a) {
        Object[] arr = toArray();
        if (a.length == arr.length) {
            System.arraycopy(arr, 0, a, 0, a.length);
            return a;
        }
        // can't be bothered to navigate reflection apis right now
        throw new RuntimeException("TODO"); 
    }

}
