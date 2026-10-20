from PySide6.QtCore import QObject, Signal


# ==========================================================
# WATCHER -> INTERFACE
# ==========================================================
# The watcher (and its AI worker) call emitir() from their
# own threads; Qt delivers the signal on the interface
# thread because the receivers live there.
# ==========================================================

class Ponte(QObject):

    evento = Signal(object)

    def emitir(self, evento):
        self.evento.emit(evento)
