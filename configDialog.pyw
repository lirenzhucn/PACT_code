#!/usr/bin/env python

from Queue import Queue
from PyQt4 import QtCore, QtGui
from os.path import normpath, expanduser
import os

from ui_configDialog import Ui_ConfigDialog
from unpack_data import unpack
from reconstruct_unpacked import reconstruct_2d
from pact_helpers import *

import yaml
import tempfile

class LogListener(QtCore.QThread):
  mysignal = QtCore.pyqtSignal(str)
  def __init__(self, queue):
    QtCore.QThread.__init__(self)
    self.queue = queue
  def run(self):
    while True:
      text = self.queue.get()
      self.mysignal.emit(text)

class OutLogger:
  def __init__(self):
    self.queue = Queue()
    self.listener = LogListener(self.queue)
  def write(self, m):
    self.queue.put(m)
  def flush(self):
    pass

class UnpackThread(QtCore.QThread):
  '''the thread class for unpack function'''
  def __init__(self, opts):
    QtCore.QThread.__init__(self)
    self.opts = opts
  def run(self):
    unpack(self.opts)

class ReconstructThread(QtCore.QThread):
  '''the thread class for reconstruct function'''
  def __init__(self, opts):
    QtCore.QThread.__init__(self)
    self.opts = opts
  def run(self):
    reconstruct_2d(self.opts)

class ConfigDialog(QtGui.QDialog):
  def __init__(self, parent=None):
    '''constructor'''
    super(ConfigDialog, self).__init__(parent)
    self.ui = Ui_ConfigDialog()
    self.ui.setupUi(self)
    self.ui.mEditLog.setWordWrapMode(QtGui.QTextOption.WrapAnywhere)
    # set initial input directory
    #initPath = expanduser(normpath(r'~/Documents'))
    #self.ui.mEditInputDir.setText(initPath)
    # for testing
    initPath =\
        expanduser(normpath(r'~/Documents/Project_data/PACT_data/2014-07-03'))
    self.ui.mEditInputDir.setText(initPath)
    self.ui.mEditInputIndex.setText(r'1')
    # initialize opts dict
    self.opts = {}
    self.opts['extra'] = {}
    self.opts['load'] = {}
    self.opts['unpack'] = {}
    self.opts['display'] = {}
    self.opts['recon'] = {}
    self.setOpts()
    # initialize threads
    self.unpackThread = UnpackThread(self.opts)
    self.reconstructThread = ReconstructThread(self.opts)
    # connecting signals to slots
    self.ui.mBtnCancel.clicked.connect(self.onCancel)
    self.ui.mBtnUnpack.clicked.connect(self.onUnpack)
    self.ui.mBtnReconstruct.clicked.connect(self.onReconstruct)
    self.ui.mBtnChooseInput.clicked.connect(self.onChooseInput)
    self.unpackThread.terminated.connect(self.workThreadTerminated)
    self.unpackThread.finished.connect(self.workThreadFinished)
    self.reconstructThread.terminated.connect(self.workThreadTerminated)
    self.reconstructThread.finished.connect(self.workThreadFinished)

  @QtCore.pyqtSlot()
  def workThreadFinished(self):
    self.logText('Done\n')

  @QtCore.pyqtSlot()
  def workThreadTerminated(self):
    self.logText('Work thread terminated unexpectedly.\n')

  @QtCore.pyqtSlot(str)
  def logText(self, text):
    self.ui.mEditLog.moveCursor(QtGui.QTextCursor.End)
    self.ui.mEditLog.insertPlainText(text)

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
    self.opts['recon']['resolution_factor'] = int(self.ui.mEditRf.text())
    self.opts['recon']['z_resolution'] = int(self.ui.mEditZrf.text())
    self.opts['recon']['fs'] = int(self.ui.mSpnFs.value())
    self.opts['recon']['R'] = self.ui.mSpnR.value()
    self.opts['recon']['Len_R'] = self.ui.mSpnLenR.value()
    self.opts['recon']['z_per_step'] = self.ui.mSpnZPerStep.value()
    self.opts['recon']['out_format'] = str(self.ui.mCmbOutFormat.currentText())

  @QtCore.pyqtSlot()
  def onUnpack(self):
    '''called when OK is pressed'''
    self.setOpts()
    self.unpackThread.opts = self.opts
    self.unpackThread.start()

  @QtCore.pyqtSlot()
  def onReconstruct(self):
    '''called when Reconstruct is pressed'''
    self.setOpts()
    self.reconstructThread.opts = self.opts
    self.reconstructThread.start()

  @QtCore.pyqtSlot()
  def onCancel(self):
    '''called when Cancel is pressed'''
    self.done(0)

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
  # redirecting output to Log TextEdit
  outLogger = OutLogger()
  outLogger.listener.mysignal.connect(configDialog.logText)
  outLogger.listener.start()
  sys.stdout = outLogger
  ret = configDialog.exec_()
  sys.exit(ret)

