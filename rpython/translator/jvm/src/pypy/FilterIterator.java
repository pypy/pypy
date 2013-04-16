package pypy;

import java.util.Iterator;

public class FilterIterator<F, T> implements Iterator<T> {
    
    public final Iterator<F> iter;
    public final Filter<F,T> filter;      
    
    public FilterIterator(final Iterator<F> iter, final Filter<F, T> filter) {
        this.iter = iter;
        this.filter = filter;
    }

    public boolean hasNext() {
        return this.iter.hasNext();        
    }

    public T next() {
        return filter.to(this.iter.next());
    }

    public void remove() {
        this.iter.remove();
    }

}
