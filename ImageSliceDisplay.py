from PyQt4.QtGui import *
from PyQt4.QtCore import Qt

class ImageSliceDisplay(QWidget):
  def __init__(self, parent = None):
    QWidget.__init__(self, parent)
    self.mLbDisplay = QLabel(self)
    self.mScSlice = QScrollBar(Qt.Vertical, self)
    # layout
    layout = QHBoxLayout(self)
    layout.addWidget(self.mLbDisplay)
    layout.addWidget(self.mScSlice)

