import argparse
import os
import math as math
import numpy as np
import pkg.constants as cnst
from Utilities import get_integration_time, write_final, get_header_values

# variables parsed from spectra file
vnir = []
vis = []
uv = []
headers = {}


def read_spectra(filename):
    """read_spectra
    open the response file and read the appropriate lines into
    each array of vnir, vis, and uv, as well as info from the header

        field    line

        vnir:     79:2127
        vis:      2227:4275
        uv:       4375:6423
    """

    global vnir, vis, uv

    with open(filename, 'r') as f:
        vnir = np.array([float(line.rstrip('\n')) for line in f.readlines()[79:2127]])
    with open(filename, 'r') as f:
        vis = np.array([float(line.rstrip('\n')) for line in f.readlines()[2227:4275]])
    with open(filename, 'r') as f:
        uv = np.array([float(line.rstrip('\n')) for line in f.readlines()[4375:6423]])


def remove_offsets():
    """remove_offsets
    Find the offsets for each channel and subtract from each signal in DN
    This version uses the following lines to compute offsets
        VNIR: 1905-1920  ->   1816:1832
        VIS:  2237-2241  ->   0:5
        UV:   4385-4395  ->   0:11

    :return: the new values, with offset subtracted
    """
    global vnir, vis, uv

    # get appropriate sets of values
    vnir_off = vnir[1816:1832]
    vis_off = vis[0:5]
    uv_off = uv[0:11]

    # get mean of each set of values
    vnir_mean = np.mean(vnir_off)
    vis_mean = np.mean(vis_off)
    uv_mean = np.mean(uv_off)

    # subtract offset from each channel
    vnir = np.array([v - vnir_mean for v in vnir])
    vis = np.array([v - vis_mean for v in vis])
    uv = np.array([v - uv_mean for v in uv])


def get_solid_angle():
    """get_solid_angle
    Calculate the solid angle subtended by the telescope aperature
    SA = pi * sin(arctan((a/2)/d))^2

    :return: the solid angle, in radians
    """
    global headers
    distance = float(headers['distToTarget'])
    return math.pi * math.pow(math.sin(math.atan(cnst.aperature / 2 / distance)), 2)


def get_area_on_target():
    """get_area_on_target
    Calculate the associated area on the target based on the
    distance to target and angular field of view
    TODO We divide the distance by 10 because why?
        A = pi * (FOV * d/2)^2

    :return: the area on the target
    """
    global headers
    distance = float(headers['distToTarget'])
    return math.pi * math.pow(cnst.fov * distance / 2 / 10, 2)


def get_radiance(photons, wavelengths, t_int, fov_tgt, sa_steradian):
    """get_radiance
    Calculate the radiance value of each of the spectra values in photons
    RAD = p/t/A/SA/w
    where p  = value of spectra in photons
          t  = integration time
          A  = area on the target
          SA = the solid angle subtended by the telescope aperature
          w  = the spectral bin width

    :param photons: the values for the observation, in photons
    :param wavelengths: the wavelengths corresponding to each value in photos
    :return: the calibrated radiance values
    """
    rad = np.array([p / t_int / fov_tgt / sa_steradian for p in photons])

    # divide each photon by the bin width (w = next wavelength - this wavelength)
    w = np.zeros(len(wavelengths))
    for iw in range(0, len(wavelengths) - 1):
        inext = iw + 1
        w[iw] = wavelengths[inext] - wavelengths[iw]
    w[-1] = w[-2]  # TODO what to use as last bin width?
    return np.divide(rad, w)


def get_wl_and_gain(gain_file):
    """get_wl_and_response
    read the gain file to get the wavelength and response function
    (photons/DN) for each response to use to convert to units of photons

    :return: wl, the wavelength for each response
    :return: gain, the gain for each response to get photons/DN
    """
    with open(gain_file, 'r') as f:
        wl = np.array([float(row.split()[0]) for row in f])
    with open(gain_file, 'r') as f:
        gain = np.array([float(row.split()[1]) for row in f])

    return wl, gain


def convert_to_output_units(radiance, wavelengths):
    rad_hc = np.multiply(radiance, cnst.hc)
    converted_rad = np.divide(rad_hc, np.multiply(wavelengths, 1E-9))
    return np.multiply(converted_rad, 1E7)


def calibrate_to_radiance(ccamFile):
    if "psv" in ccamFile.lower() and ccamFile.lower().endswith(".tab"):
        global headers
        headers = get_header_values(ccamFile)
        read_spectra(ccamFile)
        remove_offsets()
        t_int = get_integration_time(ccamFile)

        sa_steradian = get_solid_angle()
        fov_tgt = get_area_on_target()

        # combine arrays into one ordered by wavelength
        allSpectra_DN = np.concatenate([uv, vis, vnir])

        # get the wavelengths and gains from gain_mars.edit
        (wavelength, gain) = get_wl_and_gain('gain_mars.edit')
        allSpectra_photons = np.multiply(allSpectra_DN, gain)
        radiance = get_radiance(allSpectra_photons, wavelength, t_int, fov_tgt, sa_steradian)

        # convert to units of W/m^2/sr/um from phot/sec/cm^2/sr/nm
        radiance_final = convert_to_output_units(radiance, wavelength)

        outfilename = ccamFile.replace('psv', 'rad')
        outfilename = outfilename.replace('PSV', 'RAD')
        write_final(outfilename, wavelength, radiance_final)
    else:
        print(ccamFile + ": not a raw PSV file")


def calibrate_directory(directory):
    for file in os.listdir(directory):
        fullpath = directory + file
        calibrate_to_radiance(fullpath)


def calibrate_list(listfile):
    files = open(listfile).read().splitlines()
    for file in files:
        calibrate_to_radiance(file)


if __name__ == "__main__":
    # create an argument parser
    parser = argparse.ArgumentParser(description='Calibrate CCAM to Radiance')
    parser.add_argument('-f', action="store", dest='ccamFile', help="CCAM psv *.tab file")
    parser.add_argument('-d', action="store", dest='directory', help="Directory containing .tab files")
    parser.add_argument('-l', action="store", dest='list', help="File with a list of .tab files")

    args = parser.parse_args()
    if args.ccamFile is not None:
        calibrate_to_radiance(args.ccamFile)
    if args.directory is not None:
        calibrate_directory(args.directory)
    if args.list is not None:
        calibrate_list(args.list)


