How guv works
=============


The "old" way of writing servers
--------------------------------

The classic server design involves blocking sockets, :func:`select.select`, and
spawning operating system threads for each new client connection. The only
advantage of this method is the simplicity of its design. Although sufficient
for serving a very small number of clients, system resources quickly get maxed
out when spawning a large number of threads frequently, and
:func:`select.select` doesn't scale well to a large number of open file
descriptors.

An improvement on this design is using a platform-specific ``poll()`` mechanism
such as ``epoll()``, which handles polling a large number of file descriptors
much more efficiently.

However, the thread issue remains. Typical solutions involve implementing the
"reactor pattern" in an event loop using something like ``epoll()``. The issue
with this approach is that all code runs in a single thread and one must be
careful not to block the thread in any way. Setting the socket file descriptors
to non-blocking mode helps in this aspect, but effectively using this design
pattern is difficult, and requires the cooperation of all parts of the system.


Coroutines, event loops, and monkey-patching
--------------------------------------------

guv is an elegant solution to all of the problems mentioned above. It allows you
to write highly efficient code that *looks* like it's running in its own thread,
and *looks* like it's blocking. It does this by making use of greenlets_ instead
of operating system threads, and globally monkey-patching system modules to
cooperatively yield while waiting for I/O or other events. greenlets are
extremely light-weight, and all run in a single operating system thread;
switching between greenlets incurs very low overhead. Furthermore, only the
greenlets that need switching to will be switched to when I/O or another event
is ready; guv does not unnecessarily waste resources switching to greenlets that
don't need attention.

For example, the ``socket`` module is one of the core modules which is
monkey-patched by guv. When using the patched socket module, calls to
``socket.read()`` on a "blocking" socket will register interest in the file
descriptor, then cooperatively yield to another greenlet instead of blocking the
entire thread.

In addition, all monkey-patched modules are 100% API-compatible with the
original system modules, so this allows existing networking code to run without
modification as long as standard python modules are used. Code using C
extensions will require simple modifications to cooperate with guv, since it is
not possible to monkey-patch C code which may be making blocking function calls.


The hub and :func:`~guv.hubs.switch.trampoline`
---------------------------------------------------

The "hub" (:class:`guv.hubs.abc.AbstractHub`) is the core of guv and serves as
the "scheduler" for greenlets All calls to :func:`spawn` (and related functions)
actually enqueue a request with the hub to spawn the greenlet on the next event
loop iteration. The hub itself is a subclass of :class:`greenlet.greenlet`

The hub also manages the underlying event loop (currently libuv only, but
implementations for any event loop library, or even custom event loops can
easily be written). Calls to monkey-patched functions actually register either a
timer or the underlying file descriptor with libuv and switch ("yield") to the
hub greenlet.

The core function which facilitates the process of registering the file
descriptor of interest and switching to the hub is
:func:`~guv.hubs.switch.trampoline`.  Examining the source code of included
green modules reveals that this function is used extensively whenever interest
in I/O events for a file descriptor needs to be registered. Note that this
function does not need to be called by normal application code when writing code
with the guv library; this is only part of the core inner working of guv.

Another important function provided by guv for working with greenlets is
:func:`~guv.hubs.switch.gyield`. This is a very simple function which simply
yields the current greenlet, and registers a callback to resume on the next
event loop iteration.

If you require providing support for a library which cannot make use of the
patched python standard socket module (such as the case for C extensions), then
it is necessary to provide a support module which calls either
:func:`~guv.hubs.switch.trampoline()` or :func:`~guv.hubs.switch.gyield` when
there is a possibility that the C code will block for I/O.

For examples of support modules for common libraries, see the support modules
provided in the :mod:`guv.support` package.


.. _greenlets: https://greenlet.readthedocs.org/en/latest/
