import yaml

def notifyCli(msg):
    print msg

def loadOptions(opts_path):
    # read and process YAML file
    f = open(opts_path)
    opts = yaml.safe_load(f)
    f.close()
    return opts
