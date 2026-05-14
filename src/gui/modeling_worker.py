from PySide6.QtCore import QObject, QRunnable, Slot, Signal

from kayakulator_document import KayakulatorDocument
# ...

class ModelingWorker(QRunnable):
    """Model the kayakk in a separate thread"""
    _current_document: KayakulatorDocument = None

    def __init__(self, document: KayakulatorDocument):
        super().__init__()
        self._document = document
        self.signals = ModelingWorkerSignals()

    @Slot()
    def run(self):
        """Your long-running job goes in this method."""
        try:
            self._document.model_kayak(status_callback=self.signals.status.emit)
        except Exception as e:
            self.signals.error.emit(str(e))
        finally:
            self.signals.finished.emit()

class ModelingWorkerSignals(QObject):
    """Defines the signals available from a running worker thread."""
    # No signals for now, but could add progress updates or something later
    finished = Signal()
    error = Signal(str)
    status = Signal(str)