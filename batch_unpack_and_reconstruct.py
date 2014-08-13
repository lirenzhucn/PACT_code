'''
'''

import npyscreen as nps

class ReconOptsApp(nps.NPSApp):
  def main(self):
    form = nps.Form(name='Reconstruction Options')
    self.dataPath = form.add(nps.TitleFilename, name='Data path:')
    self.speedOfSound = form.add(nps.TitleText,\
                                 name='Speed of sound (mm/us):')
    self.initAngle = form.add(nps.TitleText,\
                              name='Init. angle (degrees):')
    self.fs = form.add(nps.TitleText, name='Sampling freq. (MHz):')
    self.radius = form.add(nps.TitleText, name='Ring radius (mm):')
    self.lenR = form.add(nps.TitleText, name='Focal length (mm):')
    self.xSize = form.add(nps.TitleText, name='x size (mm):')
    form.edit()

def getReconOpts():
  app = ReconOptsApp()
  app.run()

if __name__ == '__main__':
  getReconOpts()

