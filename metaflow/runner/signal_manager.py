import asyncio
import signal
from typing import NewType, Mapping, Set, Callable, Optional

SignalHandler = NewType("SignalHandler", Callable[[int, []], None])


class SignalManager:
    event_loop: Optional[asyncio.AbstractEventLoop]
    signal_map: Mapping[int, Set[SignalHandler]] = {}
    replaced_signals: Mapping[int, SignalHandler] = {}

    def __init__(self, event_loop: Optional[asyncio.AbstractEventLoop] = None):
        try:
            self.event_loop = event_loop or asyncio.get_running_loop()
        except RuntimeError:
            self.event_loop = None

    def __exit__(self, exc_type, exc_value, traceback):
        for sig in self.signal_map:
            self._remove_signal_handler(sig)

        for sig in self.replaced_signals:
            signal.signal(sig, self.replaced_signals[sig])

    def _handle_signal(self, signum, frame):
        for handler in self.signal_map[signum]:
            handler(signum, frame)

    def _add_signal_handler(self, sig):
        if self.event_loop is None:
            replaced = signal.signal(sig, self._handle_signal)
            self.replaced_signals[sig] = replaced
        else:
            self.event_loop.add_signal_handler(
                sig, lambda: self._handle_signal(sig, None)
            )

    def _remove_signal_handler(self, sig: int):
        if self.event_loop is None:
            signal.signal(sig, self.replaced_signals[sig])
            del self.replaced_signals[sig]
        else:
            self.event_loop.remove_signal_handler(sig)

    def add_signal_handler(self, sig: int, handler: SignalHandler):
        """
        Add a signal handler for the given signal.

        Parameters
        ----------
        sig : int
            The signal to handle.
        handler : SignalHandler
            The handler to call when the signal is received.
        """
        if sig not in self.signal_map:
            self.signal_map[sig] = set()
            self._add_signal_handler(sig)

        self.signal_map[sig].add(handler)

    def remove_signal_handler(self, sig: signal.Signals, handler: SignalHandler):
        """
        Remove a signal handler for the given signal.

        Parameters
        ----------
        sig : int
            The signal to handle.
        handler : SignalHandler
            The handler to remove.
        """
        if sig not in self.signal_map:
            return

        try:
            self.signal_map[sig].remove(handler)
        except KeyError:
            pass
