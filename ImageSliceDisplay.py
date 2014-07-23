from PyQt4.QtGui import *
from PyQt4.QtCore import Qt, pyqtSlot, SIGNAL
import numpy as np

class DoubleClickableLabel(QLabel):
  """A QLabel that sends out doubleClicked signal"""
  __pyqtSignals__ = ('doubleClicked()')
  def mouseDoubleClickEvent(self, event):
    self.emit(SIGNAL('doubleClicked()'))

class MinMaxDialog(QDialog):
  def __init__(self, dMin, dMax, parent = None):
    QDialog.__init__(self, parent)
    self.dMin = dMin
    self.dMax = dMax
    self.initUi()
  def initUi(self):
    minLabel = QLabel(self.tr('Min'))
    maxLabel = QLabel(self.tr('Max'))
    self.minEdit = QLineEdit(str(self.dMin))
    self.maxEdit = QLineEdit(str(self.dMax))
    self.minEdit.setValidator(QDoubleValidator())
    self.maxEdit.setValidator(QDoubleValidator())
    self.mBtnOK = QPushButton(self.tr('OK'))
    self.mBtnCancel = QPushButton(self.tr('Cancel'))
    self.mBtnOK.clicked.connect(self.accept)
    self.mBtnCancel.clicked.connect(self.reject)
    # layout
    gLayout = QGridLayout()
    gLayout.addWidget(minLabel, 1, 1)
    gLayout.addWidget(maxLabel, 2, 1)
    gLayout.addWidget(self.minEdit, 1, 2)
    gLayout.addWidget(self.maxEdit, 2, 2)
    hLayout = QHBoxLayout()
    hLayout.addWidget(self.mBtnOK)
    hLayout.addWidget(self.mBtnCancel)
    vLayout = QVBoxLayout()
    vLayout.addLayout(gLayout)
    vLayout.addLayout(hLayout)
    self.setLayout(vLayout)
  @pyqtSlot()
  def accept(self):
    self.dMin = float(self.minEdit.text())
    self.dMax = float(self.maxEdit.text())
    QDialog.accept(self)
  def getResults(self):
    return (self.dMin, self.dMax)

class ImageSliceDisplay(QWidget):
  def __init__(self, parent = None):
    QWidget.__init__(self, parent)
    self.dMin = 0.0
    self.dMax = 0.0
    #self.mLbDisplay = QLabel(self)
    self.mLbDisplay = DoubleClickableLabel(self)
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
    #self.mLbDisplay.doubleClicked.connect(self.onDisplayDoubleClicked)
    self.connect(self.mLbDisplay, SIGNAL('doubleClicked()'),
                 self.onDisplayDoubleClicked)

  @pyqtSlot(int)
  def onSliceChanged(self, val):
    self.prepareQImage(val)
    self.update()

  @pyqtSlot()
  def onDisplayDoubleClicked(self):
    mmDialog = MinMaxDialog(self.dMin, self.dMax, self)
    ret = mmDialog.exec_()
    if ret == 1:
      (self.dMin, self.dMax) = mmDialog.getResults()
      self.prepareQImage(self.mScSlice.value())
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
    uSlice = (rSlice - self.dMin)/(self.dMax - self.dMin)
    uSlice[uSlice < 0.0] = 0.0
    uSlice[uSlice > 1.0] = 1.0
    #uSlice = uSlice.astype(np.uint8)
    dSlice = np.zeros([4, rSlice.shape[0], rSlice.shape[1]],
                      dtype=np.uint8, order='F')
    dSlice[0,:,:] = uSlice * 255
    dSlice[1,:,:] = uSlice * 255
    dSlice[2,:,:] = uSlice * 255
    dSlice[3,:,:] = 255
    self.img = QImage(dSlice.tostring(order='F'),
                 rSlice.shape[0], rSlice.shape[1], QImage.Format_RGB32)
    self.mLbDisplay.setPixmap(QPixmap.fromImage(self.img))

