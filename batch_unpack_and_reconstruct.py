#!/usr/bin/env python
'''Usage:
'''

import npyscreen as nps
from pact_helpers import *
from reconstruct_unpacked import reconstruct_2d
from os.path import expanduser

class ReconOptsApp(nps.NPSApp):
  def __init__(self, opts):
    self.opts = opts
  def main(self):
    recon = self.opts['recon']
    form = nps.Form(name='Reconstruction Options')
    self.dataPath = form.add(nps.TitleFilename, name='Data path:',\
                             use_two_lines=False, begin_entry_at=25,\
                             value=self.opts['extra']['src_dir'])
    self.index = form.add(nps.TitleText, name='Index:',\
                          use_two_lines=False, begin_entry_at=25,\
                          value=str(self.opts['load']['EXP_START']))
    self.vm = form.add(nps.TitleText,\
                       name='Speed of sound (mm/us):',\
                       use_two_lines=False,\
                       begin_entry_at=25,\
                       value=str(recon['V_M']))
    self.initAngle = form.add(nps.TitleText,\
                              name='Init. angle (degrees):',\
                              use_two_lines=False, begin_entry_at=25,\
                              value=str(recon['ini_angle']))
    self.fs = form.add(nps.TitleText, name='Sampling freq. (MHz):',\
                       use_two_lines=False, begin_entry_at=25,\
                       value=str(recon['fs']))
    self.radius = form.add(nps.TitleText, name='Ring radius (mm):',\
                           use_two_lines=False, begin_entry_at=25,
                           value=str(recon['R']))
    self.lenR = form.add(nps.TitleText, name='Focal length (mm):',\
                         use_two_lines=False, begin_entry_at=25,\
                         value=str(recon['Len_R']))
    self.xSize = form.add(nps.TitleText, name='x size (mm):',\
                          use_two_lines=False, begin_entry_at=25,\
                          value=str(recon['x_size']))
    self.ySize = form.add(nps.TitleText, name='y size (mm):',\
                          use_two_lines=False, begin_entry_at=25,\
                          value=str(recon['y_size']))
    self.zSize = form.add(nps.TitleText, name='z size (mm):',\
                          use_two_lines=False, begin_entry_at=25,\
                          value=str(recon['z_size']))
    self.xCenter = form.add(nps.TitleText, name='x center (mm):',\
                            use_two_lines=False, begin_entry_at=25,\
                            value=str(recon['center_x']))
    self.yCenter = form.add(nps.TitleText, name='y center (mm):',\
                            use_two_lines=False, begin_entry_at=25,\
                            value=str(recon['center_y']))
    self.zStep = form.add(nps.TitleText, name='z step (mm):',\
                          use_two_lines=False, begin_entry_at=25,\
                          value=str(recon['z_per_step']))
    self.rf = form.add(nps.TitleText, name='res. factor (px/mm):',\
                       use_two_lines=False, begin_entry_at=25,\
                       value=str(recon['resolution_factor']))
    self.zrf = form.add(nps.TitleText, name='z res. factor (px/mm):',\
                        use_two_lines=False, begin_entry_at=25,\
                        value=str(recon['z_resolution']))
    form.edit()
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
    return self.opts

def getReconOpts(defaultOpts):
  app = ReconOptsApp(defaultOpts)
  app.run()
  opts = app.updateOpts()
  return opts

if __name__ == '__main__':
  opts = loadOptions('default_config_linux.yaml')
  opts = getReconOpts(opts)
  reconstruct_2d(opts)

