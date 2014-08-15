#!/usr/bin/env python
'''Usage:
'''

import npyscreen as nps
from pact_helpers import *
from reconstruct_unpacked import reconstruct_2d, reconstruct_2d_average
from reconstruct_unpacked_3d import reconstruct_3d
from unpack_data import unpack
from os.path import expanduser
from enum import IntEnum

ReconActions = IntEnum('ReconActions',\
                       'SLICE_2D AVERAGE_2D STATIONAL_2D SCAN_3D STATIONAL_3D UNPACK')
ACTION_STR = ('2D slice', '2D average', '2D stational',\
              '3D scanning', '3D stational', 'Unpack')
def actionToString(action):
  return ACTION_STR[action - 1]

TITLE_WIDTH = 25
class ReconOptsApp(nps.NPSApp):
  def __init__(self, opts):
    self.opts = opts
    self.action = ReconActions.SLICE_2D
  def main(self):
    recon = self.opts['recon']
    form = nps.Form(name='Reconstruction Options')
    self.dataPath = form.add(nps.TitleFilename, name='Data path:',\
                             use_two_lines=False,\
                             begin_entry_at=TITLE_WIDTH,\
                             value=self.opts['extra']['src_dir'])
    self.index = form.add(nps.TitleText, name='Index:',\
                          use_two_lines=False,\
                          begin_entry_at=TITLE_WIDTH,\
                          value=str(self.opts['load']['EXP_START']))
    self.actionChoice = form.add(nps.TitleSelectOne, name='Action:',\
                                 use_two_lines=False,\
                                 begin_entry_at=TITLE_WIDTH,\
                                 max_height=len(ACTION_STR)+1,\
                                 value=0, values=ACTION_STR,\
                                 scroll_exit=True)
    self.vm = form.add(nps.TitleText,\
                       name='Speed of sound (mm/us):',\
                       use_two_lines=False,\
                       begin_entry_at=TITLE_WIDTH,\
                       value=str(recon['V_M']))
    self.xSize = form.add(nps.TitleText, name='x size (mm):',\
                          use_two_lines=False,\
                          begin_entry_at=TITLE_WIDTH,\
                          value=str(recon['x_size']))
    self.ySize = form.add(nps.TitleText, name='y size (mm):',\
                          use_two_lines=False,\
                          begin_entry_at=TITLE_WIDTH,\
                          value=str(recon['y_size']))
    self.zSize = form.add(nps.TitleText, name='z size (mm):',\
                          use_two_lines=False,\
                          begin_entry_at=TITLE_WIDTH,\
                          value=str(recon['z_size']))
    self.xCenter = form.add(nps.TitleText, name='x center (mm):',\
                            use_two_lines=False,\
                            begin_entry_at=TITLE_WIDTH,\
                            value=str(recon['center_x']))
    self.yCenter = form.add(nps.TitleText, name='y center (mm):',\
                            use_two_lines=False,\
                            begin_entry_at=TITLE_WIDTH,\
                            value=str(recon['center_y']))
    self.initAngle = form.add(nps.TitleText,\
                              name='Init. angle (degrees):',\
                              use_two_lines=False,\
                              begin_entry_at=TITLE_WIDTH,\
                              value=str(recon['ini_angle']))
    self.fs = form.add(nps.TitleText, name='Sampling freq. (MHz):',\
                       use_two_lines=False,\
                       begin_entry_at=TITLE_WIDTH,\
                       value=str(recon['fs']))
    self.radius = form.add(nps.TitleText, name='Ring radius (mm):',\
                           use_two_lines=False,\
                           begin_entry_at=TITLE_WIDTH,
                           value=str(recon['R']))
    self.lenR = form.add(nps.TitleText, name='Focal length (mm):',\
                         use_two_lines=False,\
                         begin_entry_at=TITLE_WIDTH,\
                         value=str(recon['Len_R']))
    self.zStep = form.add(nps.TitleText, name='z step (mm):',\
                          use_two_lines=False,\
                          begin_entry_at=TITLE_WIDTH,\
                          value=str(recon['z_per_step']))
    self.rf = form.add(nps.TitleText, name='res. factor (px/mm):',\
                       use_two_lines=False,\
                       begin_entry_at=TITLE_WIDTH,\
                       value=str(recon['resolution_factor']))
    self.zrf = form.add(nps.TitleText, name='z res. factor (px/mm):',\
                        use_two_lines=False,\
                        begin_entry_at=TITLE_WIDTH,\
                        value=str(recon['z_resolution']))
    self.preprocess = form.add(nps.TitleMultiSelect,\
                               name='Preprocess',\
                               use_two_lines=False,\
                               begin_entry_at=TITLE_WIDTH,\
                               max_height=3,\
                               values=('Wiener', 'Exact'),\
                               scroll_exit=True)
    form.edit()
  def updateAction(self):
    self.action = ReconActions(self.actionChoice.value[0] + 1)
    return self.action
  def updateOpts(self):
    self.opts['extra']['src_dir'] = expanduser(self.dataPath.value)
    self.opts['extra']['dest_dir'] =\
            self.opts['extra']['src_dir'] + '/unpack'
    self.opts['load']['EXP_START'] = int(self.index.value)
    self.opts['load']['EXP_END'] = self.opts['load']['EXP_START']
    self.opts['load']['NUM_EXP'] = -1
    self.opts['recon']['V_M'] = float(self.vm.value)
    self.opts['recon']['ini_angle'] = float(self.initAngle.value)
    self.opts['recon']['fs'] = float(self.fs.value)
    self.opts['recon']['R'] = float(self.radius.value)
    self.opts['recon']['Len_R'] = float(self.lenR.value)
    self.opts['recon']['x_size'] = float(self.xSize.value)
    self.opts['recon']['y_size'] = float(self.ySize.value)
    self.opts['recon']['z_size'] = float(self.zSize.value)
    self.opts['recon']['center_x'] = float(self.xCenter.value)
    self.opts['recon']['center_y'] = float(self.yCenter.value)
    self.opts['recon']['z_per_step'] = float(self.zStep.value)
    self.opts['recon']['resolution_factor'] = float(self.rf.value)
    self.opts['recon']['z_resolution'] = float(self.zrf.value)
    if 0 in self.preprocess.value:
      self.opts['display']['wi'] = True
    if 1 in self.preprocess.value:
      self.opts['display']['exact'] = True
    return self.opts

def getReconOpts(defaultOpts):
  app = ReconOptsApp(defaultOpts)
  app.run()
  opts = app.updateOpts()
  action = app.updateAction()
  return opts, action

if __name__ == '__main__':
  opts = loadOptions('default_config_linux.yaml')
  opts, action = getReconOpts(opts)
  if action == ReconActions.SLICE_2D:
    reImg = reconstruct_2d(opts)
  elif action == ReconActions.AVERAGE_2D:
    reImg = reconstruct_2d_average(opts)
  #elif action == ReconActions.STATIONAL_2D:
  elif action == ReconActions.SCAN_3D:
    reImg = reconstruct_3d(opts)
  #elif action == ReconActions.STATIONAL_3D:
  elif action == ReconActions.UNPACK:
    # unpack
    unpack(opts)
  else:
    print 'Action ' + ACTION_STR[action - 1] + ' not supported yet.'

