from PySide6.QtCore import QObject, QRunnable, Slot, Signal

from kayakulator_document import KayakulatorDocument
# ...

class ModelingWorker(QRunnable):
    """Model the kayak in a separate thread"""
    _current_document: KayakulatorDocument = None

    def __init__(self, document: KayakulatorDocument, build_frames: bool = False):
        super().__init__()
        self._document = document
        self._build_frames = build_frames
        self.signals = ModelingWorkerSignals()

    @Slot()
    def run(self):
        """Your long-running job goes in this method."""
        try:
            self._document.model_kayak(status_callback=self.signals.status.emit, build_frames=self._build_frames)
        except Exception as e:
            self.signals.error.emit(str(e))
        finally:
            self.signals.finished.emit()
            self._document._model_builder.setProgressCallback(None)  # Clear the progress callback to avoid holding references to the GUI

class ModelingWorkerSignals(QObject):
    """Defines the signals available from a running worker thread."""
    finished = Signal()
    error = Signal(str)
    status = Signal(str)