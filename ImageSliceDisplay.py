from PyQt4.QtGui import *
from PyQt4.QtCore import Qt, pyqtSlot
import numpy as np

class ImageSliceDisplay(QWidget):
  def __init__(self, parent = None):
    QWidget.__init__(self, parent)
    self.mLbDisplay = QLabel(self)
    self.mScSlice = QScrollBar(Qt.Vertical, self)
    self.mScSlice.setMinimum(0)
    self.mScSlice.setMaximum(0)
    self.mScSlice.setSingleStep(1)
    # layout
    layout = QHBoxLayout(self)
    layout.addWidget(self.mLbDisplay)
    layout.addWidget(self.mScSlice)
    # singal/slot pairs
    self.mScSlice.valueChanged.connect(self.onSliceChanged)

  @pyqtSlot(int)
  def onSliceChanged(self, val):
    self.prepareQImage(val)
    self.update()

  def setInput(self, data):
    self.data = data
    self.dMin = np.amin(data)
    self.dMax = np.amax(data)
    self.mScSlice.setMaximum(data.shape[2] - 1)
    self.mScSlice.setValue(0)
    self.prepareQImage(0)
    self.update()

  def prepareQImage(self, ind):
    rSlice = np.copy(self.data[:,:,ind], order='F')
    uSlice = 255 * (rSlice - self.dMin)/(self.dMax - self.dMin)
    #uSlice = uSlice.astype(np.uint8)
    dSlice = np.zeros([4, rSlice.shape[0], rSlice.shape[1]],
                      dtype=np.uint8, order='F')
    dSlice[0,:,:] = uSlice
    dSlice[1,:,:] = uSlice
    dSlice[2,:,:] = uSlice
    dSlice[3,:,:] = 255
    self.img = QImage(dSlice.tostring(order='F'),
                 rSlice.shape[0], rSlice.shape[1], QImage.Format_RGB32)
    self.mLbDisplay.setPixmap(QPixmap.fromImage(self.img))

