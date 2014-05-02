#!/usr/bin/env python

import argh
import yaml
from pact_helpers import *

def reconstruction_inline(chn_data, chn_data_3d, reconOpts):
    """reconstruction function re-implemented according to
    subfunc_reconstruction2_inline.m
    """
    print chn_data_3d.shape
    paData = chn_data_3d[1:1300,:,:] # cropping the first 1300
    return (None, None)

@argh.arg('opts_path', type=str, help='path to YAML option file')
def reconstruct(opts_path):
    """reconstruction from channel data"""

    opts = loadOptions(opts_path)
    print opts['recon']
    # load data from hdf5 files
    
    # check Show_Image and dispatch to the right method
    # currently only 0 is supported
    if opts['unpack']['Show_Image'] == 0:
        return reconstruction_inline(chn_data,
                                     chn_data_3d, opts['recon'])
    else:
        notifyCli('Currently only Show_Image = 0 is supported.')

if __name__ == '__main__':
    argh.dispatch_command(reconstruct)
