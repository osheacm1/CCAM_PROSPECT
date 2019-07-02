import sys
import math as math
import numpy as np
import os
from Utilities import get_integration_time, write_final
from convertCCAM2Radiance import calibrate_to_radiance


def calibrate_relative_reflectance(radFile, values):
    '''

    :param radFile:
    :param values:
    :return:
    '''
    values_orig = [float(x.split(' ')[1].strip()) for x in open(radFile).readlines()]

    # divide original values by the appropriate calibration values
    # to get relative reflectance.  If divide by 0, just = 0
    with np.errstate(divide='ignore', invalid='ignore'):
        c = np.true_divide(values_orig, values)
        c[c == np.inf] = 0
        c = np.nan_to_num(c)

    return c


def get_rad_file(psv_file):
    # get all of the values from the rad file and divide by the value_7
    radFile = filename.replace('psv', 'rad')
    exists = os.path.isfile(radFile)
    if not exists:
        # create rad file
        calibrate_to_radiance(filename)
    return radFile


def choose_values(psv_file):
    # check t_int for file
    t_int = get_integration_time(filename)
    t_int = t_int * 1000;
    values = []
    if round(t_int) == 7:
       values = value_7
    elif round(t_int) == 34:
        values = value_34
    elif round(t_int) == 404:
        values = value_404
    elif round(t_int) == 5004:
        values = value_5004
    else:
        print('error - integration time is not 7, 34, 404, or 5004')
        # throw an error
    return values


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print('Please provide the full path to the CCAM PSV file to be calibrated to relative reflectance')
        exit(0)

    baseDir = '/Users/osheacm1/Documents/SAA/PDART/oldCode/target11sol76/'
    filename = sys.argv[1]

    default = True

    if default:
        '''
        If the user wants to use the default, we use sol76 data.
        Calculate the cosine correction for each of the four calibration files from sol76
        '''

        # for every line in cl0_404238481rad_f0050104ccam02076p3.tab
        # divide by cos(24.84 deg)
        wavelength = [float(x.split(' ')[0].strip())
                      for x in open(baseDir + 'cl0_404238481rad_f0050104ccam02076p3.tab').readlines()]
        value_7 = [float(x.split(' ')[1].strip())/math.cos(math.radians(24.84))
                   for x in open(baseDir + 'cl0_404238481rad_f0050104ccam02076p3.tab').readlines()]

        # for every line in cl0_404238492rad_f0050104ccam02076p3.tab
        # divide by cos(24.79 deg)
        value_34 = [float(x.split(' ')[1].strip())/math.cos(math.radians(24.79))
                   for x in open(baseDir + 'cl0_404238492rad_f0050104ccam02076p3.tab').readlines()]

        # for every line in cl9_404238503rad_f0050104ccam02076p3.tab
        # divide by cos(24.75 deg)
        value_404 = [float(x.split(' ')[1].strip())/math.cos(math.radians(24.75))
                   for x in open(baseDir + 'cl9_404238503rad_f0050104ccam02076p3.tab').readlines()]

        # for every line in cl9_404238538rad_f0050104ccam02076p3.tab
        # divide by cos(24.61 deg)
        value_5004 = [float(x.split(' ')[1].strip())/math.cos(math.radians(24.61))
                   for x in open(baseDir + 'cl9_404238538rad_f0050104ccam02076p3.tab').readlines()]
    else:
        # get wavelengths and values for each of the integration times
        x = 3 #TODO

    values = choose_values(filename)
    radFile = get_rad_file(filename)
    newValues = calibrate_relative_reflectance(radFile, values)
    outfilename = radFile.replace('rad', 'ref')
    write_final(outfilename, wavelength, newValues)
