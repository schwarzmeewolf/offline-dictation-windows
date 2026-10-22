"""
Where print(), tracebacks and native crash reports go when there is no console.

Kept apart from main.py so it can be tested without loading the model, Qt or
the native runtimes whose import order main.py has to protect. Nothing here
imports more than the standard library.
"""
import faulthandler
import os
import re
import sys
import threading

# Each log starts over once it passes this size, keeping the previous file
# beside it as <name>.1. Two weeks of daily use write a few dozen kilobytes, so
# this holds months of history while still bounding an app that runs for weeks.
LOG_LIMIT_BYTES = 512 * 1024

# Windows reports these to faulthandler although nothing is wrong: RPC and COM
# raise them inside the audio driver stack when a sound stream opens, and catch
# them again themselves. A real crash is an access violation, a stack overflow
# and the like, which faulthandler names in words instead of printing a code.
HARMLESS_FAULT = re.compile(r'Windows fatal exception: code 0x8001[0-9a-f]{4}\b')

# faulthandler writes through the file's descriptor for as long as it is
# enabled, so the file object has to outlive attach().
_fault_file = None


class CappedLog:
    """
    A text log that starts over when it grows past a limit.

    Stands in for sys.stdout and sys.stderr under pythonw.exe. Rolling happens on
    write rather than only at start-up, because this app is left running for
    days and the logs would otherwise grow for as long as it stays up.
    """

    def __init__(self, path, limit=LOG_LIMIT_BYTES):
        self.path = path
        self.limit = limit
        self.encoding = 'utf-8'
        self._lock = threading.Lock()
        if os.path.isfile(path) and os.path.getsize(path) > limit:
            os.replace(path, path + '.1')
        self._file = open(path, 'a', encoding='utf-8', buffering=1)

    def write(self, text):
        with self._lock:
            written = self._file.write(text)
            if os.fstat(self._file.fileno()).st_size > self.limit:
                self._roll()
            return written

    def _roll(self):
        self._file.close()
        try:
            os.replace(self.path, self.path + '.1')
        except OSError:
            pass  # the old file is held open elsewhere; keep writing to it
        self._file = open(self.path, 'a', encoding='utf-8', buffering=1)

    def flush(self):
        with self._lock:
            self._file.flush()

    def close(self):
        with self._lock:
            self._file.close()

    def fileno(self):
        return self._file.fileno()

    def isatty(self):
        return False


def harvest_faults(fault_path, err_log):
    """
    Move the real crash reports of the previous run into the error log.

    faulthandler has to write to a file of its own: it prints a full dump of
    every thread for each Windows exception, the harmless ones included, and in
    ww_err.log those buried the one report that mattered. This keeps the reports
    that name a real fault and drops the COM noise.

    :param fault_path: the file faulthandler wrote to during the previous run
    :param err_log: where real reports go
    :return: how many real reports were moved
    """
    try:
        with open(fault_path, encoding='utf-8', errors='replace') as file:
            text = file.read()
    except OSError:
        return 0

    blocks = re.split(r'(?m)^(?=Windows fatal exception:|Fatal Python error:)', text)
    real = [block for block in blocks if block.strip() and not HARMLESS_FAULT.match(block)]
    if real:
        err_log.write('--- faulthandler report from the previous run ---\n')
        for block in real:
            err_log.write(block if block.endswith('\n') else block + '\n')
    return len(real)


def attach(root):
    """
    Give print() and tracebacks somewhere to go.

    Under pythonw.exe there is no console: sys.stdout and sys.stderr are None,
    and Python drops every message and every traceback silently. Point them at
    log files in the project root instead, so a failure leaves a trace.

    :param root: the project folder, where the log files live
    """
    global _fault_file
    fault_path = os.path.join(root, 'ww_fault.log')
    try:
        if sys.stdout is None:
            sys.stdout = CappedLog(os.path.join(root, 'ww_out.log'))
        if sys.stderr is None:
            sys.stderr = CappedLog(os.path.join(root, 'ww_err.log'))
            harvest_faults(fault_path, sys.stderr)
    except OSError:
        # An unwritable folder must not keep the app from starting; without the
        # log files print() simply stays the no-op it was before.
        pass

    # A native crash - an access violation inside a C extension - kills the
    # process without raising anything Python can catch, so the error log stays
    # empty and the app simply vanishes. faulthandler dumps the stack of every
    # thread as the process dies, which is the only way to learn where it was.
    # With a console it prints there; without one, to a file that starts empty
    # each run and is sorted by harvest_faults() at the next start.
    try:
        if isinstance(sys.stderr, CappedLog):
            _fault_file = open(fault_path, 'w', encoding='utf-8')
            faulthandler.enable(file=_fault_file)
        elif sys.stderr is not None:
            faulthandler.enable(file=sys.stderr)
    except (OSError, ValueError, RuntimeError):
        pass
