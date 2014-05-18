import yaml
import sys

def notifyCli(msg):
  print msg

def update_progress(current, total):
  """update progress bar"""
  TOTAL_INDICATOR_NUM = 50
  CHAR_INDICATOR = '#'
  progress = int(float(current)/total * 100)
  numIndicator = int(float(current)/total * TOTAL_INDICATOR_NUM)
  sys.stdout.write('\r{:>3}% [{:<50}]'.format(progress,\
                                              CHAR_INDICATOR*numIndicator))
  sys.stdout.flush()
  if current == total:
    print '\tDone'

def loadOptions(opts_path):
  # read and process YAML file
  f = open(opts_path)
  opts = yaml.safe_load(f)
  f.close()
  return opts
