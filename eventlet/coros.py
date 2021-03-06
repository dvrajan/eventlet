from __future__ import print_function

import collections
import traceback
import warnings

import eventlet
from eventlet import event as _event
from eventlet import hubs
from eventlet import greenthread
from eventlet import semaphore as semaphoremod


class NOT_USED:
    def __repr__(self):
        return 'NOT_USED'

NOT_USED = NOT_USED()


def Event(*a, **kw):
    warnings.warn("The Event class has been moved to the event module! "
                  "Please construct event.Event objects instead.",
                  DeprecationWarning, stacklevel=2)
    return _event.Event(*a, **kw)


def event(*a, **kw):
    warnings.warn(
        "The event class has been capitalized and moved!  Please "
        "construct event.Event objects instead.",
        DeprecationWarning, stacklevel=2)
    return _event.Event(*a, **kw)


def Semaphore(count):
    warnings.warn(
        "The Semaphore class has moved!  Please "
        "use semaphore.Semaphore instead.",
        DeprecationWarning, stacklevel=2)
    return semaphoremod.Semaphore(count)


def BoundedSemaphore(count):
    warnings.warn(
        "The BoundedSemaphore class has moved!  Please "
        "use semaphore.BoundedSemaphore instead.",
        DeprecationWarning, stacklevel=2)
    return semaphoremod.BoundedSemaphore(count)


def semaphore(count=0, limit=None):
    warnings.warn(
        "coros.semaphore is deprecated.  Please use either "
        "semaphore.Semaphore or semaphore.BoundedSemaphore instead.",
        DeprecationWarning, stacklevel=2)
    if limit is None:
        return Semaphore(count)
    else:
        return BoundedSemaphore(count)


class metaphore(object):
    """This is sort of an inverse semaphore: a counter that starts at 0 and
    waits only if nonzero. It's used to implement a "wait for all" scenario.

    >>> from eventlet import api, coros
    >>> count = coros.metaphore()
    >>> count.wait()
    >>> def decrementer(count, id):
    ...     print("{0} decrementing".format(id))
    ...     count.dec()
    ...
    >>> _ = eventlet.spawn(decrementer, count, 'A')
    >>> _ = eventlet.spawn(decrementer, count, 'B')
    >>> count.inc(2)
    >>> count.wait()
    A decrementing
    B decrementing
    """

    def __init__(self):
        self.counter = 0
        self.event = _event.Event()
        # send() right away, else we'd wait on the default 0 count!
        self.event.send()

    def inc(self, by=1):
        """Increment our counter. If this transitions the counter from zero to
        nonzero, make any subsequent :meth:`wait` call wait.
        """
        assert by > 0
        self.counter += by
        if self.counter == by:
            # If we just incremented self.counter by 'by', and the new count
            # equals 'by', then the old value of self.counter was 0.
            # Transitioning from 0 to a nonzero value means wait() must
            # actually wait.
            self.event.reset()

    def dec(self, by=1):
        """Decrement our counter. If this transitions the counter from nonzero
        to zero, a current or subsequent wait() call need no longer wait.
        """
        assert by > 0
        self.counter -= by
        if self.counter <= 0:
            # Don't leave self.counter < 0, that will screw things up in
            # future calls.
            self.counter = 0
            # Transitioning from nonzero to 0 means wait() need no longer wait.
            self.event.send()

    def wait(self):
        """Suspend the caller only if our count is nonzero. In that case,
        resume the caller once the count decrements to zero again.
        """
        self.event.wait()


def execute(func, *args, **kw):
    """ Executes an operation asynchronously in a new coroutine, returning
    an event to retrieve the return value.

    This has the same api as the :meth:`eventlet.coros.CoroutinePool.execute`
    method; the only difference is that this one creates a new coroutine
    instead of drawing from a pool.

    >>> from eventlet import coros
    >>> evt = coros.execute(lambda a: ('foo', a), 1)
    >>> evt.wait()
    ('foo', 1)
    """
    warnings.warn(
        "Coros.execute is deprecated.  Please use eventlet.spawn "
        "instead.", DeprecationWarning, stacklevel=2)
    return greenthread.spawn(func, *args, **kw)


def CoroutinePool(*args, **kwargs):
    warnings.warn(
        "CoroutinePool is deprecated.  Please use "
        "eventlet.GreenPool instead.", DeprecationWarning, stacklevel=2)
    from eventlet.pool import Pool
    return Pool(*args, **kwargs)


class Queue(object):

    def __init__(self):
        warnings.warn(
            "coros.Queue is deprecated.  Please use "
            "eventlet.queue.Queue instead.",
            DeprecationWarning, stacklevel=2)
        self.items = collections.deque()
        self._waiters = set()

    def __nonzero__(self):
        return len(self.items) > 0

    __bool__ = __nonzero__

    def __len__(self):
        return len(self.items)

    def __repr__(self):
        params = (self.__class__.__name__, hex(id(self)),
                  len(self.items), len(self._waiters))
        return '<%s at %s items[%d] _waiters[%s]>' % params

    def send(self, result=None, exc=None):
        if exc is not None and not isinstance(exc, tuple):
            exc = (exc, )
        self.items.append((result, exc))
        if self._waiters:
            hubs.get_hub().schedule_call_global(0, self._do_send)

    def send_exception(self, *args):
        # the arguments are the same as for greenlet.throw
        return self.send(exc=args)

    def _do_send(self):
        if self._waiters and self.items:
            waiter = self._waiters.pop()
            result, exc = self.items.popleft()
            waiter.switch((result, exc))

    def wait(self):
        if self.items:
            result, exc = self.items.popleft()
            if exc is None:
                return result
            else:
                eventlet.getcurrent().throw(*exc)
        else:
            self._waiters.add(eventlet.getcurrent())
            try:
                result, exc = hubs.get_hub().switch()
                if exc is None:
                    return result
                else:
                    eventlet.getcurrent().throw(*exc)
            finally:
                self._waiters.discard(eventlet.getcurrent())

    def ready(self):
        return len(self.items) > 0

    def full(self):
        # for consistency with Channel
        return False

    def waiting(self):
        return len(self._waiters)

    def __iter__(self):
        return self

    def next(self):
        return self.wait()


class Channel(object):

    def __init__(self, max_size=0):
        warnings.warn(
            "coros.Channel is deprecated.  Please use "
            "eventlet.queue.Queue(0) instead.",
            DeprecationWarning, stacklevel=2)
        self.max_size = max_size
        self.items = collections.deque()
        self._waiters = set()
        self._senders = set()

    def __nonzero__(self):
        return len(self.items) > 0

    __bool__ = __nonzero__

    def __len__(self):
        return len(self.items)

    def __repr__(self):
        params = (self.__class__.__name__, hex(id(self)),
                  self.max_size, len(self.items),
                  len(self._waiters), len(self._senders))
        return '<%s at %s max=%s items[%d] _w[%s] _s[%s]>' % params

    def send(self, result=None, exc=None):
        if exc is not None and not isinstance(exc, tuple):
            exc = (exc, )
        if eventlet.getcurrent() is hubs.get_hub().greenlet:
            self.items.append((result, exc))
            if self._waiters:
                hubs.get_hub().schedule_call_global(0, self._do_switch)
        else:
            self.items.append((result, exc))
            # note that send() does not work well with timeouts. if your timeout fires
            # after this point, the item will remain in the queue
            if self._waiters:
                hubs.get_hub().schedule_call_global(0, self._do_switch)
            if len(self.items) > self.max_size:
                self._senders.add(eventlet.getcurrent())
                try:
                    hubs.get_hub().switch()
                finally:
                    self._senders.discard(eventlet.getcurrent())

    def send_exception(self, *args):
        # the arguments are the same as for greenlet.throw
        return self.send(exc=args)

    def _do_switch(self):
        while True:
            if self._waiters and self.items:
                waiter = self._waiters.pop()
                result, exc = self.items.popleft()
                try:
                    waiter.switch((result, exc))
                except:
                    traceback.print_exc()
            elif self._senders and len(self.items) <= self.max_size:
                sender = self._senders.pop()
                try:
                    sender.switch()
                except:
                    traceback.print_exc()
            else:
                break

    def wait(self):
        if self.items:
            result, exc = self.items.popleft()
            if len(self.items) <= self.max_size:
                hubs.get_hub().schedule_call_global(0, self._do_switch)
            if exc is None:
                return result
            else:
                eventlet.getcurrent().throw(*exc)
        else:
            if self._senders:
                hubs.get_hub().schedule_call_global(0, self._do_switch)
            self._waiters.add(eventlet.getcurrent())
            try:
                result, exc = hubs.get_hub().switch()
                if exc is None:
                    return result
                else:
                    eventlet.getcurrent().throw(*exc)
            finally:
                self._waiters.discard(eventlet.getcurrent())

    def ready(self):
        return len(self.items) > 0

    def full(self):
        return len(self.items) >= self.max_size

    def waiting(self):
        return max(0, len(self._waiters) - len(self.items))


def queue(max_size=None):
    if max_size is None:
        return Queue()
    else:
        return Channel(max_size)
