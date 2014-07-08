#!/usr/bin/env python

from PyQt4 import QtCore, QtGui
from os.path import normpath, expanduser

from ui_configDialog import Ui_ConfigDialog

class ConfigDialog(QtGui.QDialog):
  DONE = 0
  CANCELED = 1
  def __init__(self, parent=None):
    '''constructor'''
    super(ConfigDialog, self).__init__(parent)
    self.ui = Ui_ConfigDialog()
    self.ui.setupUi(self)
    # set initial input directory
    initPath = expanduser(normpath(r'~/Docments'))
    self.ui.mEditInputDir.setText(initPath)
    # initialize opts dict
    self.opts = {}
    self.opts['extra'] = {}
    self.opts['load'] = {}
    self.opts['unpack'] = {}
    self.opts['display'] = {}
    self.opts['recon'] = {}
    self.setOpts()
    # connecting signals to slots
    self.ui.mBtnCancel.clicked.connect(self.onCancel)
    self.ui.mBtnUnpack.clicked.connect(self.onUnpack)
    self.ui.mBtnChooseInput.clicked.connect(self.onChooseInput)
  def setOpts(self):
    '''set self.opts dict according to user input'''
    # object variables
    # extra section
    self.opts['extra']['save_raw'] = True
    self.opts['extra']['src_dir'] = str(self.ui.mEditInputDir.text())
    self.opts['extra']['dest_dir'] =\
        normpath(self.opts['extra']['src_dir'] + '/unpack')
    self.opts['extra']['dtype'] = r'<u4'
    # load section
    self.opts['load']['EXP_START'] = int(self.ui.mEditInputIndex.text())
    self.opts['load']['EXP_END'] = int(self.ui.mEditInputIndex.text())
    self.opts['load']['NUM_EXP'] = -1
    # unpack section
    self.opts['unpack']['Show_Image'] = 0
    self.opts['unpack']['NumBoards'] = self.ui.mLstBoardNames.count()
    self.opts['unpack']['BoardName'] =\
        [str(self.ui.mLstBoardNames.item(idx).text())\
         for idx in range(self.ui.mLstBoardNames.count())]
    self.opts['unpack']['DataBlockSize'] =\
        int(self.ui.mEditDataBlockSize.text())
    self.opts['unpack']['PackSize'] = int(self.ui.mEditPackSize.text())
    self.opts['unpack']['NumDaqChnsBoard'] =\
        int(self.ui.mEditNumDaqChnsBoard.text())
    self.opts['unpack']['TotFirings'] = int(self.ui.mEditTotFirings.text())
    self.opts['unpack']['NumElements'] = int(self.ui.mEditNumElements.text())
    self.opts['unpack']['NumSegments'] = int(self.ui.mEditNumSegments.text())
    self.opts['unpack']['BadChannels'] =\
        [int(self.ui.mLstBadChannels.item(idx).text())\
         for idx in range(self.ui.mLstBadChannels.count())]
    # display section
    self.opts['display']['span'] = int(self.ui.mEditSpan.text())
    self.opts['display']['wi'] = self.ui.mChkWi.isChecked()
    self.opts['display']['pc'] = self.ui.mChkPc.isChecked()
    self.opts['display']['exact'] = self.ui.mChkExact.isChecked()
    self.opts['display']['denoise'] = self.ui.mChkDenoise.isChecked()
    # recon section
    algorithms = ['delay-and-sum', 'envelope']
    self.opts['recon']['algorithm'] =\
        algorithms[self.ui.mCmbAlgorithm.currentIndex()]
    self.opts['recon']['V_M'] = self.ui.mSpnVm.value()
    self.opts['recon']['ini_angle'] = self.ui.mSpnInitAngle.value()
    self.opts['recon']['x_size'] = self.ui.mSpnXSize.value()
    self.opts['recon']['y_size'] = self.ui.mSpnYSize.value()
    self.opts['recon']['z_size'] = self.ui.mSpnZSize.value()
    self.opts['recon']['center_x'] = self.ui.mSpnXCenter.value()
    self.opts['recon']['center_y'] = self.ui.mSpnYCenter.value()
    self.opts['recon']['resolution_factor'] = float(self.ui.mEditRf.text())
    self.opts['recon']['z_resolution'] = float(self.ui.mEditZrf.text())
    self.opts['recon']['fs'] = float(self.ui.mSpnFs.value())
    self.opts['recon']['R'] = self.ui.mSpnR.value()
    self.opts['recon']['Len_R'] = self.ui.mSpnLenR.value()
    self.opts['recon']['z_per_step'] = self.ui.mSpnZPerStep.value()
  @QtCore.pyqtSlot()
  def onUnpack(self):
    '''called when OK is pressed'''
    self.setOpts()
    self.done(self.DONE)
  @QtCore.pyqtSlot()
  def onCancel(self):
    '''called when Cancel is pressed'''
    self.done(self.CANCELED)
  @QtCore.pyqtSlot()
  def onChooseInput(self):
    '''called when Choose button is pressed in the Input group'''
    path = str(self.ui.mEditInputDir.text())
    path = QtGui.QFileDialog.getExistingDirectory\
        (self, "Input directory", path)
    self.ui.mEditInputDir.setText(path)

if __name__ == '__main__':
  import sys
  app = QtGui.QApplication(sys.argv)
  configDialog = ConfigDialog()
  ret = configDialog.exec_()
  #print configDialog.opts
  sys.exit(ret)

