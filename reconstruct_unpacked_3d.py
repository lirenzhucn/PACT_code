#!/usr/bin/env python

import os
import argh
import numpy as np
from time import time
from pact_helpers import *
from preprocess import subfunc_wiener, subfunc_exact

#import pycuda.autoinit
import pycuda.driver as cuda
from pycuda.compiler import SourceModule
from scipy.signal import hilbert
from StringIO import StringIO

KERNEL_CU_FILE = 'reconstruct_3d_kernel.cu'
PULSE_STR = """
129 133 137 141 145 149 153 157 161 165 169 173 177 181 185 189 385 389 393 397 401 405 409 413 417 421 425 429 433 437 441 445 257 261 265 269 273 277 281 285 289 293 297 301 305 309 313 317 1 5 9 13 17 21 25 29 33 37 41 45 49 53 57 61
130 134 138 142 146 150 154 158 162 166 170 174 178 182 186 190 386 390 394 398 402 406 410 414 418 422 426 430 434 438 442 446 258 262 266 270 274 278 282 286 290 294 298 302 306 310 314 318 2 6 10 14 18 22 26 30 34 38 42 46 50 54 58 62
131 135 139 143 147 151 155 159 163 167 171 175 179 183 187 191 387 391 395 399 403 407 411 415 419 423 427 431 435 439 443 447 259 263 267 271 275 279 283 287 291 295 299 303 307 311 315 319 3 7 11 15 19 23 27 31 35 39 43 47 51 55 59 63
132 136 140 144 148 152 156 160 164 168 172 176 180 184 188 192 388 392 396 400 404 408 412 416 420 424 428 432 436 440 444 448 260 264 268 272 276 280 284 288 292 296 300 304 308 312 316 320 4 8 12 16 20 24 28 32 36 40 44 48 52 56 60 64
196 200 204 208 212 216 220 224 228 232 236 240 244 248 252 256 452 456 460 464 468 472 476 480 484 488 492 496 500 504 508 512 324 328 332 336 340 344 348 352 356 360 364 368 372 376 380 384 68 72 76 80 84 88 92 96 100 104 108 112 116 120 124 128
195 199 203 207 211 215 219 223 227 231 235 239 243 247 251 255 451 455 459 463 467 471 475 479 483 487 491 495 499 503 507 511 323 327 331 335 339 343 347 351 355 359 363 367 371 375 379 383 67 71 75 79 83 87 91 95 99 103 107 111 115 119 123 127
194 198 202 206 210 214 218 222 226 230 234 238 242 246 250 254 450 454 458 462 466 470 474 478 482 486 490 494 498 502 506 510 322 326 330 334 338 342 346 350 354 358 362 366 370 374 378 382 66 70 74 78 82 86 90 94 98 102 106 110 114 118 122 126
193 197 201 205 209 213 217 221 225 229 233 237 241 245 249 253 449 453 457 461 465 469 473 477 481 485 489 493 497 501 505 509 321 325 329 333 337 341 345 349 353 357 361 365 369 373 377 381 65 69 73 77 81 85 89 93 97 101 105 109 113 117 121 125
"""


def rearrange_pa_data(paData):
    """rearrange paData array according to 8 firing order
    """
    nSamples, nSteps, zSteps = paData.shape
    assert nSteps == 512
    # load pulse list from the pre-defined string
    sio = StringIO(PULSE_STR)
    pulseList = np.loadtxt(sio, dtype=np.int)
    # pulse list was created based on MATLAB's 1-starting index
    # minus 1 to correct for the 0-starting index in Python
    pulseList = pulseList - 1
    numGroup = pulseList.shape[0]
    paDataE = np.zeros((nSamples, nSteps / numGroup, zSteps * numGroup),
                       dtype=np.float32, order='F')
    for zi in range(zSteps):
        for fi in range(numGroup):
            paDataE[:, :, zi * numGroup + fi] = paData[:, pulseList[fi, :], zi]
    return paDataE, pulseList, numGroup


def reconstruction_3d_stational(paData, reconOpts,
                                progress=update_progress_with_time):
    """3D reconstruction algorithm for stational scanning
    see Jun's focal-line reconstruction paper and codes for details
    """
    # reading parameters from option dict
    lenR = reconOpts['Len_R']
    R = reconOpts['R']
    vm = reconOpts['V_M']
    iniAngle = reconOpts['ini_angle']
    zPerStep = reconOpts['z_per_step']
    xSize = reconOpts['x_size']
    ySize = reconOpts['y_size']
    zSize = reconOpts['z_size']
    xCenter = reconOpts['center_x']
    yCenter = reconOpts['center_y']
    rf = reconOpts['resolution_factor']
    zrf = reconOpts['z_resolution']
    fs = reconOpts['fs']
    nSamples, nSteps, zSteps = paData.shape
    zCenter = zPerStep * zSteps / 2
    # use the first z step data to calibrate DAQ delay
    delayIdx = find_delay_idx(paData[:, :, 0], fs)
    delayIdx = delayIdx.astype(np.float32)
    anglePerStep = 2 * np.pi / nSteps
    nPixelx = int(round(xSize * rf))
    nPixely = int(round(ySize * rf))
    nPixelz = int(round(zSize * zrf))
    # note range is 0-start indices
    xRange = (np.arange(1, nPixelx + 1, 1, dtype=np.float32)
              - nPixelx / 2) * xSize / nPixelx + xCenter
    yRange = (np.arange(nPixely, 0, -1, dtype=np.float32)
              - nPixely / 2) * ySize / nPixely + yCenter
    zRange = (np.arange(1, nPixelz + 1, 1, dtype=np.float32)
              - nPixelz / 2) * zSize / nPixelz + zCenter
    # receiver position
    angleStep1 = iniAngle / 180.0 * np.pi
    detectorAngle = np.arange(0, nSteps, 1, dtype=np.float32)\
        * anglePerStep + angleStep1
    xReceive = np.cos(detectorAngle) * R
    yReceive = np.sin(detectorAngle) * R
    zReceive = np.arange(0, zSteps, dtype=np.float32) * zPerStep
    # create buffer on GPU for reconstructed image
    reImg = np.zeros((nPixely, nPixelx, nPixelz), order='C', dtype=np.float32)
    d_reImg = cuda.mem_alloc(nPixely * nPixelx * nPixelz * 4)
    cuda.memcpy_htod(d_reImg, reImg)
    # back projection loop
    notifyCli('Reconstruction starting. Keep patient.')
    d_xRange = cuda.mem_alloc(xRange.nbytes)
    cuda.memcpy_htod(d_xRange, xRange)
    d_yRange = cuda.mem_alloc(yRange.nbytes)
    cuda.memcpy_htod(d_yRange, yRange)
    d_zRange = cuda.mem_alloc(zRange.nbytes)
    cuda.memcpy_htod(d_zRange, zRange)
    # get module right before execution of function
    MOD = SourceModule(open(KERNEL_CU_FILE, 'r').read())
    bpk = MOD.get_function('backprojection_kernel')
    d_paDataLine = cuda.mem_alloc(nSamples * 4)
    # convert to single
    paData = paData.astype(np.float32)
    st_all = time()
    for zi in range(zSteps):
        for ni in range(nSteps):
            # print ni
            cuda.memcpy_htod(d_paDataLine, paData[:, ni, zi])
            bpk(d_reImg, d_paDataLine, d_xRange, d_yRange, d_zRange,
                xReceive[ni], yReceive[ni], zReceive[zi],
                np.float32(lenR), np.float32(vm), delayIdx[ni],
                np.float32(fs), np.uint32(nSamples),
                grid=(nPixelx, nPixely), block=(nPixelz, 1, 1))
        et = time()
        # use the execution time of the last loop to guess the remaining time
        time_remaining = ((zSteps - zi + 1) * (et - st_all) / (zi + 1)) / 60.0
        #update_progress_with_time(zi+1, zSteps, time_remaining)
        progress(zi + 1, zSteps, time_remaining)
    cuda.memcpy_dtoh(reImg, d_reImg)
    et_all = time()
    notifyCli(
        'Total time elapsed: {:.2f} mins'.format((et_all - st_all) / 60.0))
    return reImg


def reconstruction_3d(paData, reconOpts, progress=update_progress_with_time):
    """3D reconstruction algorithm
    see Jun's focal-line reconstruction paper and codes for details
    """
    # reading parameters from option dict
    lenR = reconOpts['Len_R']
    R = reconOpts['R']
    vm = reconOpts['V_M']
    iniAngle = reconOpts['ini_angle']
    zPerStep = reconOpts['z_per_step']
    xSize = reconOpts['x_size']
    ySize = reconOpts['y_size']
    zSize = reconOpts['z_size']
    xCenter = reconOpts['center_x']
    yCenter = reconOpts['center_y']
    rf = reconOpts['resolution_factor']
    zrf = reconOpts['z_resolution']
    fs = reconOpts['fs']
    algorithm = reconOpts['algorithm']
    # use the first z step data to calibrate DAQ delay
    delayIdx = find_delay_idx(paData[:, :, 0], fs)
    delayIdx = delayIdx.astype(np.float32)
    # rearrange paData array according to firing order
    notifyCli('Re-arranging raw RF data according to firing squence')
    # DEBUGGING
    paData = paData.astype(np.float32)
    paData, pulseList, numGroup = rearrange_pa_data(paData)
    nSamples, nSteps, zSteps = paData.shape
    # notice the z step size is divided by firing group count
    zPerStep = zPerStep / numGroup
    zCenter = zPerStep * zSteps / 2
    if algorithm == 'envelope':
        notifyCli('Extracting envelope of A-line signals')
        paData = np.abs(hilbert(paData, axis=0))
        paData = paData.astype(np.float32)
    elif algorithm == 'exact':
        notifyCli('Filtered backprojection')
        # TODO: impelement the 'exact' algorithm
    # notice nSteps is now 64!!
    anglePerStep = 2 * np.pi / nSteps / numGroup
    nPixelx = int(xSize * rf)
    nPixely = int(ySize * rf)
    nPixelz = int(zSize * zrf)
    # note range is 0-start indices
    xRange = (np.arange(1, nPixelx + 1, 1, dtype=np.float32)
              - nPixelx / 2) * xSize / nPixelx + xCenter
    yRange = (np.arange(nPixely, 0, -1, dtype=np.float32)
              - nPixely / 2) * ySize / nPixely + yCenter
    zRange = (np.arange(1, nPixelz + 1, 1, dtype=np.float32)
              - nPixelz / 2) * zSize / nPixelz + zCenter
    # receiver position
    angleStep1 = iniAngle / 180.0 * np.pi
    detectorAngle = np.arange(0, nSteps * numGroup, 1, dtype=np.float32)\
        * anglePerStep + angleStep1
    xReceive = np.cos(detectorAngle) * R
    yReceive = np.sin(detectorAngle) * R
    zReceive = np.arange(0, zSteps, dtype=np.float32) * zPerStep
    # create buffer on GPU for reconstructed image
    reImg = np.zeros((nPixely, nPixelx, nPixelz), order='C', dtype=np.float32)
    d_reImg = cuda.mem_alloc(nPixely * nPixelx * nPixelz * 4)
    cuda.memcpy_htod(d_reImg, reImg)
    # back projection loop
    notifyCli('Reconstruction starting. Keep patient.')
    d_xRange = cuda.mem_alloc(xRange.nbytes)
    cuda.memcpy_htod(d_xRange, xRange)
    d_yRange = cuda.mem_alloc(yRange.nbytes)
    cuda.memcpy_htod(d_yRange, yRange)
    d_zRange = cuda.mem_alloc(zRange.nbytes)
    cuda.memcpy_htod(d_zRange, zRange)
    # get module right before execution of function
    MOD = SourceModule(open(KERNEL_CU_FILE, 'r').read())
    bpk = MOD.get_function('backprojection_kernel')
    d_paDataLine = cuda.mem_alloc(nSamples * 4)
    st_all = time()
    for zi in range(zSteps):
        st = time()
        # find out the index of fire at each virtual plane
        fi = zi % numGroup
        for ni in range(nSteps):
            # transducer index
            ti = pulseList[fi, ni]
            cuda.memcpy_htod(d_paDataLine, paData[:, ni, zi])
            bpk(d_reImg, d_paDataLine, d_xRange, d_yRange, d_zRange,
                xReceive[ti], yReceive[ti], zReceive[zi],
                np.float32(lenR), np.float32(vm), delayIdx[ti],
                np.float32(fs), np.uint32(nSamples),
                grid=(nPixelx, nPixely), block=(nPixelz, 1, 1))
        et = time()
        # use the execution time of the last loop to guess the remaining time
        time_remaining = ((zSteps - zi) * (et - st)) / 60.0
        #update_progress_with_time(zi+1, zSteps, time_remaining)
        progress(zi + 1, zSteps, time_remaining)
    cuda.memcpy_dtoh(reImg, d_reImg)
    et_all = time()
    notifyCli(
        'Total time elapsed: {:.2f} mins'.format((et_all - st_all) / 60.0))
    return reImg


def reconstruct_3d_stational(opts, progress=update_progress_with_time):
    '''interface function for other python scripts such as Qt applications'''
    ind = opts['load']['EXP_START']
    chn_data, chn_data_3d = load_hdf5_data(opts['extra']['dest_dir'], ind)
    if opts['display']['wi']:
        notifyCli('Performing Weiner deconvolution...')
        chn_data_3d = subfunc_wiener(chn_data_3d)
    if opts['display']['exact']:
        notifyCli('Performing filtering...')
        chn_data_3d = subfunc_exact(chn_data_3d)
    # initialize pycuda properly
    cuda.init()
    dev = cuda.Device(0)
    ctx = dev.make_context()
    reImg = reconstruction_3d_stational(chn_data_3d, opts['recon'], progress)
    ctx.pop()
    del ctx
    save_reconstructed_image(reImg, opts['extra']['dest_dir'],
                             ind, opts['recon']['out_format'], '_3d')
    return reImg


def reconstruct_3d(opts, progress=update_progress_with_time):
    '''interface function for other python scripts such as Qt applications'''
    ind = opts['load']['EXP_START']
    chn_data, chn_data_3d = load_hdf5_data(opts['extra']['dest_dir'], ind)
    if opts['display']['wi']:
        notifyCli('Performing Weiner deconvolution...')
        chn_data_3d = subfunc_wiener(chn_data_3d)
    if opts['display']['exact']:
        notifyCli('Performing filtering...')
        chn_data_3d = subfunc_exact(chn_data_3d)
    # initialize pycuda properly
    cuda.init()
    dev = cuda.Device(0)
    ctx = dev.make_context()
    reImg = reconstruction_3d(chn_data_3d, opts['recon'], progress)
    ctx.pop()
    del ctx
    save_reconstructed_image(reImg, opts['extra']['dest_dir'],
                             ind, opts['recon']['out_format'], '_3d')
    return reImg


@argh.arg('opts_path', type=str, help='path to YAML option file')
def reconstruct(opts_path):
    """reconstruct from channel data
    """
    opts = loadOptions(opts_path)
    # normalize paths according to the platform
    opts['extra']['src_dir'] =\
        os.path.expanduser(os.path.normpath(opts['extra']['src_dir']))
    opts['extra']['dest_dir'] =\
        os.path.expanduser(os.path.normpath(opts['extra']['dest_dir']))
    # load data from hdf5 files
    ind = opts['load']['EXP_START']
    if opts['load']['EXP_END'] != -1 and\
       opts['load']['EXP_END'] != ind:
        notifyCli('WARNING: multiple experiments selected. '
                  'Only the first dataset will be processed')
    chn_data, chn_data_3d = load_hdf5_data(
        opts['extra']['dest_dir'], ind)
    if opts['unpack']['Show_Image'] != 0:
        notifyCli('Currently only Show_Image = 0 is supported.')
    # initialize pyCuda environment
    cuda.init()
    dev = cuda.Device(0)
    ctx = dev.make_context()
    reImg = reconstruction_3d(chn_data_3d, opts['recon'])
    ctx.pop()
    del ctx
    save_reconstructed_image(reImg, opts['extra']['dest_dir'],
                             ind, 'tiff', '_3d')

if __name__ == '__main__':
    argh.dispatch_command(reconstruct)
