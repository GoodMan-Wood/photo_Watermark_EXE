from PySide6.QtCore import QObject, Signal, QRunnable, Slot
import traceback
import sys


class WorkerSignals(QObject):
    """Signals available from a running worker thread."""
    result = Signal(object)
    error = Signal(tuple)
    finished = Signal()


class Worker(QRunnable):
    """QRunnable wrapper to run a function in a threadpool and emit signals."""
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @Slot()
    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
        except Exception:
            exctype, value = sys.exc_info()[:2]
            tb = traceback.format_exc()
            self.signals.error.emit((exctype, value, tb))
        else:
            self.signals.result.emit(result)
        finally:
            self.signals.finished.emit()
