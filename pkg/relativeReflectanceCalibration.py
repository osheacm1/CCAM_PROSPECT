import numpy as np
import os
import argparse
from pkg.Utilities import get_integration_time, write_final
from pkg.radianceCalibration import calibrate_to_radiance
from pkg.InputType import InputType

psvfile = ''
radfile = ''
wavelength = []


def do_division(values):
    '''
    Divide each value in the file by the calibration values
    :param values:
    :return:
    '''
    global radfile
    values_orig = [float(x.split(' ')[1].strip()) for x in open(radfile).readlines()]

    # divide original values by the appropriate calibration values
    # to get relative reflectance.  If divide by 0, just = 0
    with np.errstate(divide='ignore', invalid='ignore'):
        c = np.true_divide(values_orig, values)
        c[c == np.inf] = 0
        c = np.nan_to_num(c)

    return c


def do_multiplication(values):
    '''
    Multiply each value in the file by the lab bidirectional spectrum value
    :param values:
    :return:
    '''
    my_path = os.path.abspath(os.path.dirname(__file__))
    sol76dir = os.path.join(my_path, "../sol76")
    conv = os.path.join(sol76dir, 'Target11_60_95.txt.conv');
    values_conv = [float(x.split()[1].strip()) for x in open(conv).readlines()]

    # multiply original values by the appropriate calibration values
    # to get relative reflectance.
    c = np.multiply(values_conv, values)

    return c


def get_rad_file(psv_file, out_dir):
    global radfile, psvfile
    # get all of the values from the rad file and divide by the value_7
    radfile = psv_file.replace('psv', 'rad')
    psvfile = psv_file.replace('rad', 'psv')
    exists = os.path.isfile(radfile)
    if not exists:
        # create rad file and change path to where it'll be in output dir
        # move to the output dir
        (path, filename) = os.path.split(radfile)
        out_filename = out_dir + filename
        radfile = out_filename
        return calibrate_to_radiance(psv_file, out_dir)
    else:
        return True


def choose_values(custom_target_file):
    if not custom_target_file:
        my_path = os.path.abspath(os.path.dirname(__file__))
        sol76dir = os.path.join(my_path, "../sol76")
        ms7 = os.path.join(sol76dir, 'cl0_404238481cor_f0050104ccam02076p1.tab')
        ms34 = os.path.join(sol76dir, 'cl0_404238492cor_f0050104ccam02076p1.tab')
        ms404 = os.path.join(sol76dir, 'cl9_404238503cor_f0050104ccam02076p1.tab')
        ms5004 = os.path.join(sol76dir, 'cl9_404238538cor_f0050104ccam02076p1.tab')
        # ms7 = os.path.join(sol76dir, 'CL0_404238481PSV_F0050104CCAM02076P1.TXT.RAD.cor.7ms.txt.cos')
        # ms34 = os.path.join(sol76dir, 'CL0_404238492PSV_F0050104CCAM02076P1.TXT.RAD.cor.34ms.txt.cos')
        # ms404 = os.path.join(sol76dir, 'CL9_404238503PSV_F0050104CCAM02076P1.TXT.RAD.cor.404ms.txt.cos')
        # ms5004 = os.path.join(sol76dir, 'CL9_404238538PSV_F0050104CCAM02076P1.TXT.RAD.cor.5004ms.txt.cos')
    else:
        ms7 = custom_target_file
        ms34 = custom_target_file
        ms404 = custom_target_file
        ms5004 = custom_target_file

    # now get the cosine-corrected values from the correct file
    # check t_int for file
    global psvfile
    t_int = get_integration_time(psvfile)
    t_int = round(t_int * 1000);
    if t_int == 7:
        fn = ms7
    elif t_int == 34:
        fn = ms34
    elif t_int == 404:
        fn = ms404
    elif t_int == 5004:
        fn = ms5004
    else:
        fn = None
        print('error - integration time in input file is not 7, 34, 404, or 5004.')
        # throw an error

    if fn is not None:
        values = [float(x.split(' ')[1].strip()) for x in open(fn).readlines()]
        # get the wavelengths
        global wavelength
        wavelength = [float(x.split(' ')[0].strip()) for x in open(fn).readlines()]

    return values


def calibrate_file(filename, custom_dir, out_dir):
    global wavelength

    print("filename in calibrate_file: " + filename)
    valid = get_rad_file(filename, out_dir)
    if valid:
        values = choose_values(custom_dir)
        new_values = do_division(values)
        final_values = do_multiplication(new_values)
        out_filename = radfile.replace('RAD', 'REF')
        out_filename = out_filename.replace('rad', 'ref')
        if out_dir is not None:
            (path, filename) = os.path.split(out_filename)
            out_filename = out_dir + filename
        print("out_dir" + out_dir)
        write_final(out_filename, wavelength, final_values)


def calibrate_directory(directory, custom_dir, out_dir):
    for file_name in os.listdir(directory):
        if ('psv' in file_name.lower() or 'rad' in file_name.lower()) and '.tab' in file_name.lower():
            full_path = os.path.join(directory, file_name)
            calibrate_file(full_path, custom_dir, out_dir)
        elif os.path.isdir(os.path.join(directory, file_name)):
            calibrate_directory(os.path.join(directory, file_name), custom_dir, out_dir)


def calibrate_list(list_file, custom_dir, out_dir):
    files = open(list_file).read().splitlines()
    for file_name in files:
        calibrate_file(file_name, custom_dir, out_dir)


def calibrate_relative_reflectance(file_type, file_name, custom_dir, out_dir):
    if file_type == InputType.FILE:
        calibrate_file(file_name, custom_dir, out_dir)
    elif file_type == InputType.FILE_LIST:
        calibrate_list(file_name, custom_dir, out_dir)
    else:
        calibrate_directory(file_name, custom_dir, out_dir)


if __name__ == "__main__":
    # create a command line parser
    parser = argparse.ArgumentParser(description='Relative Reflectance Calibration')
    parser.add_argument('-f', action="store", dest='ccamFile', help="CCAM psv or rad *.tab file")
    parser.add_argument('-d', action="store", dest='directory', help="Directory containing .tab files to calibrate")
    parser.add_argument('-l', action="store", dest='list', help="File with a list of .tab files to calibrate")
    parser.add_argument('-c', action="store", dest='customDir', help="directory containing custom calibration files")
    parser.add_argument('-o', action="store", dest='out_dir', help="directory to store the output files")

    args = parser.parse_args()
    if args.ccamFile is not None:
        file_type = InputType.FILE
        file = args.ccamFile
    elif args.directory is not None:
        file_type = InputType.DIRECTORY
        file = args.directory
    else:
        file_type = InputType.FILE_LIST
        file = args.list

    calibrate_relative_reflectance(file_type, file, args.customDir, args.out_dir)
