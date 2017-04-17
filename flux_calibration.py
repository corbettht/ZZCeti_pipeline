"""

Written by JT Fuchs in July 2015
Based off pySALT redution routine specsens.py by S. Crawford
And reading the darned IRAF documentation

spec_sens.py calculates the calibration curve given an
observation and a standard star.

To run file:
python spec_sens.py liststandard listflux liststar
######
Each list should have the names of the stars, with blue and red exposures next to each other.
The ordering of the standard star flux files should match the order of the standard star list.
Example:

liststandard:
wtfb.LTT3218_930_blue.ms.fits
wtfb.LTT3218_930_red.ms.fits
wnb.GD50_930_blue.ms.fits
wnb.GD50_930_red.ms.fits

listflux:
mltt3218.dat
mgd50.dat

liststar
wnb.WD0122p0030_930_blue.ms.fits
wnb.WD0122p0030_930_red.ms.fits
wnb.WD0235p069_930_blue.ms.fits
wnb.WD0235p069_930_red.ms.fits

#####

Counting variables are fruits and vegetables.

:INPUTS: 
        stdlist: string, file with list of 1D standard star spectra

        fluxlist: string, file containing standard star fluxes. These are typically m*.dat.

        speclist: string, file with list of  1D spectrum of observed stars you want to flux calibrate

:OUTPUTS: 
        flux calibrated files (_flux is added to the filename). User will be prompted if file will overwrite existing file.

        sensitivity_params.txt:  File is updated everytime spec_sens.py is run. Contains information used in the flux calibration. Columns are: input observed spectrum, date/time program was run, observed standard spectrum used for calibration, flux calibration file (m*dat), pixel regions excluded in fit, order of polynomial to flux standard, width in Angstroms used for rebinning, output spectrum filename

        sens_fits_DATE.txt: File for diagnostics. Columns are: wavelength, observed flux, polynomial fit, and residuals for each standard listed above. There are extra zeros at the bottom of some columns. 

To do:


"""

import os
import sys
import time
import numpy as np
import pyfits as fits
import spectools as st
import datetime
from glob import glob
import matplotlib.pyplot as plt
from scipy.interpolate import UnivariateSpline
import argparse

#=============================================
#To help with command line interpretation
def str2bool(v):
    if v.lower() in ('yes','true','t','y','1'):
        return True
    if v.lower() in ('no','false','f','n','0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


#=============================================
#These functions are to help with excluding regions from the sensitivity function
def find_nearest(array,value):
    idx = (np.abs(array-value)).argmin()
    return array[idx]

def onclick(event):
    global ix,iy
    ix, iy = event.xdata,event.ydata
    global coords
    ax.axvline(x=ix,color='k',linewidth='3')
    fig.canvas.draw()
    coords.append((ix,iy))

#=============================================

def extinction_correction(lams, flux, airmass):
    # Function inputs are wavelengths and flux values for the spectrum as well 
    # as the airmass the spectrum was measured at
    
    # wavelength-dependent extinction coefficients from CTIO
    # Strizinger et. al. 2005
    ctio_lams = [3050.0, 3084.6500000000001, 3119.3099999999999, 3153.96, 3188.6100000000001, 3223.27, 3257.9200000000001, 3292.5700000000002, 3327.23, 3361.8800000000001, 3396.54, 3431.1900000000001, 3465.8400000000001, 3500.5, 3535.1500000000001, 3569.8000000000002, 3604.46, 3639.1100000000001, 3673.7600000000002, 3708.4200000000001, 3743.0700000000002, 3777.7199999999998, 3812.3800000000001, 3847.0300000000002, 3881.6900000000001, 3916.3400000000001, 3950.9899999999998, 3985.6500000000001, 4020.3000000000002, 4054.9499999999998, 4089.6100000000001, 4124.2600000000002, 4158.9099999999999, 4193.5699999999997, 4228.2200000000003, 4262.8699999999999, 4297.5299999999997, 4332.1800000000003, 4366.8299999999999, 4401.4899999999998, 4436.1400000000003, 4470.79, 4505.4499999999998, 4540.1000000000004, 4574.7600000000002, 4609.4099999999999, 4644.0600000000004, 4678.7200000000003, 4713.3699999999999, 4748.0200000000004, 4782.6800000000003, 4817.3299999999999, 4851.9799999999996, 4886.6400000000003, 4921.29, 4955.9399999999996, 4990.6000000000004, 5025.25, 5059.9099999999999, 5094.5600000000004, 5129.21, 5163.8699999999999, 5198.5200000000004, 5233.1700000000001, 5267.8299999999999, 5302.4799999999996, 5337.1300000000001, 5371.79, 5406.4399999999996, 5441.0900000000001, 5475.75, 5510.3999999999996, 5545.0500000000002, 5579.71, 5614.3599999999997, 5649.0200000000004, 5683.6700000000001, 5718.3199999999997, 5752.9799999999996, 5787.6300000000001, 5822.2799999999997, 5856.9399999999996, 5891.5900000000001, 5926.2399999999998, 5960.8999999999996, 5995.5500000000002, 6030.1999999999998, 6064.8599999999997, 6099.5100000000002, 6134.1700000000001, 6168.8199999999997, 6203.4700000000003, 6238.1300000000001, 6272.7799999999997, 6307.4300000000003, 6342.0900000000001, 6376.7399999999998, 6411.3900000000003, 6446.0500000000002, 6480.6999999999998, 6482.8500000000004, 6535.3800000000001, 6587.9099999999999, 6640.4399999999996, 6692.96, 6745.4899999999998, 6798.0200000000004, 6850.5500000000002, 6903.0699999999997, 6955.6000000000004, 7008.1300000000001, 7060.6499999999996, 7113.1800000000003, 7165.71, 7218.2399999999998, 7270.7600000000002, 7323.29, 7375.8199999999997, 7428.3500000000004, 7480.8699999999999, 7533.3999999999996, 7585.9300000000003, 7638.4499999999998, 7690.9799999999996, 7743.5100000000002, 7796.04, 7848.5600000000004, 7901.0900000000001, 7953.6199999999999, 8006.1499999999996, 8058.6700000000001, 8111.1999999999998, 8163.7299999999996, 8216.25, 8268.7800000000007, 8321.3099999999995, 8373.8400000000001, 8426.3600000000006, 8478.8899999999994, 8531.4200000000001, 8583.9500000000007, 8636.4699999999993, 8689.0, 8741.5300000000007, 8794.0499999999993, 8846.5799999999999, 8899.1100000000006, 8951.6399999999994, 9004.1599999999999, 9056.6900000000005, 9109.2199999999993, 9161.75, 9214.2700000000004, 9266.7999999999993, 9319.3299999999999, 9371.8500000000004, 9424.3799999999992, 9476.9099999999999, 9529.4400000000005, 9581.9599999999991, 9634.4899999999998, 9687.0200000000004, 9739.5499999999993, 9792.0699999999997, 9844.6000000000004, 9897.1299999999992, 9949.6499999999996, 10002.200000000001, 10054.700000000001, 10107.200000000001, 10159.799999999999, 10212.299999999999, 10264.799999999999, 10317.299999999999, 10369.9, 10422.4, 10474.9, 10527.5, 10580.0, 10632.5, 10685.0, 10737.6, 10790.1, 10842.6, 10895.1, 10947.700000000001, 11000.200000000001]
    ctio_ext = [1.395, 1.2830000000000001, 1.181, 1.0880000000000001, 1.004, 0.92900000000000005, 0.86099999999999999, 0.80099999999999993, 0.748, 0.69999999999999996, 0.65900000000000003, 0.623, 0.59099999999999997, 0.56399999999999995, 0.54000000000000004, 0.52000000000000002, 0.502, 0.48700000000000004, 0.47299999999999998, 0.46000000000000002, 0.44799999999999995, 0.436, 0.42499999999999999, 0.41399999999999998, 0.40200000000000002, 0.39100000000000001, 0.38100000000000001, 0.37, 0.35999999999999999, 0.34899999999999998, 0.33899999999999997, 0.33000000000000002, 0.32100000000000001, 0.313, 0.30399999999999999, 0.29600000000000004, 0.28899999999999998, 0.28100000000000003, 0.27399999999999997, 0.26700000000000002, 0.26000000000000001, 0.254, 0.247, 0.24100000000000002, 0.23600000000000002, 0.23000000000000001, 0.22500000000000001, 0.22, 0.215, 0.20999999999999999, 0.20600000000000002, 0.20199999999999999, 0.19800000000000001, 0.19399999999999998, 0.19, 0.187, 0.184, 0.18100000000000002, 0.17800000000000002, 0.17600000000000002, 0.17300000000000001, 0.17100000000000001, 0.16899999999999998, 0.16699999999999998, 0.16600000000000001, 0.16399999999999998, 0.16300000000000001, 0.16200000000000001, 0.16, 0.159, 0.158, 0.158, 0.157, 0.156, 0.155, 0.155, 0.154, 0.153, 0.153, 0.152, 0.151, 0.151, 0.14999999999999999, 0.14899999999999999, 0.14899999999999999, 0.14800000000000002, 0.14699999999999999, 0.14599999999999999, 0.14400000000000002, 0.14300000000000002, 0.14199999999999999, 0.14000000000000001, 0.13800000000000001, 0.13600000000000001, 0.13400000000000001, 0.13200000000000001, 0.129, 0.126, 0.12300000000000001, 0.12, 0.12, 0.115, 0.111, 0.107, 0.10300000000000001, 0.099000000000000005, 0.096000000000000002, 0.091999999999999998, 0.088000000000000009, 0.085000000000000006, 0.08199999999999999, 0.078, 0.074999999999999997, 0.072000000000000008, 0.069000000000000006, 0.066000000000000003, 0.064000000000000001, 0.060999999999999999, 0.057999999999999996, 0.055999999999999994, 0.052999999999999999, 0.050999999999999997, 0.049000000000000002, 0.047, 0.044999999999999998, 0.042999999999999997, 0.040999999999999995, 0.039, 0.037000000000000005, 0.035000000000000003, 0.034000000000000002, 0.032000000000000001, 0.029999999999999999, 0.028999999999999998, 0.027999999999999997, 0.026000000000000002, 0.025000000000000001, 0.024, 0.023, 0.022000000000000002, 0.02, 0.019, 0.019, 0.018000000000000002, 0.017000000000000001, 0.016, 0.014999999999999999, 0.014999999999999999, 0.013999999999999999, 0.013000000000000001, 0.013000000000000001, 0.012, 0.011000000000000001, 0.011000000000000001, 0.011000000000000001, 0.01, 0.01, 0.0090000000000000011, 0.0090000000000000011, 0.0090000000000000011, 0.0080000000000000002, 0.0080000000000000002, 0.0080000000000000002, 0.0069999999999999993, 0.0069999999999999993, 0.0069999999999999993, 0.0069999999999999993, 0.0069999999999999993, 0.0060000000000000001, 0.0060000000000000001, 0.0060000000000000001, 0.0060000000000000001, 0.0060000000000000001, 0.0060000000000000001, 0.0050000000000000001, 0.0050000000000000001, 0.0050000000000000001, 0.0050000000000000001, 0.0050000000000000001, 0.0050000000000000001, 0.0040000000000000001, 0.0040000000000000001, 0.0040000000000000001, 0.0040000000000000001, 0.0030000000000000001, 0.0030000000000000001, 0.0030000000000000001]

    smooth_param = 0.001
    spline_fit = UnivariateSpline(ctio_lams, ctio_ext, s=smooth_param, k=3)

    a_lambda = spline_fit(lams)

    corrected_flux = flux*(10.0**(.4*a_lambda*(1.0+airmass)))    
    
    xx = np.linspace(np.min(ctio_lams), np.max(ctio_lams), 1000)
    yy = spline_fit(xx)
    '''
    plt.figure()
    plt.scatter(ctio_lams, ctio_ext, label=smooth_param)
    plt.axvline(np.min(lams), color='g')
    plt.axvline(np.max(lams), color='g')
    plt.plot(xx, yy)
    plt.xlabel('Wavelength')
    plt.ylabel('Extinction Coefficient')
    plt.title('Gemini Extinction Coefficient Fit')
    '''
    '''
    plt.figure()
    plt.plot(lams,flux)
    plt.plot(lams,corrected_flux)
    plt.show()
    '''
    return corrected_flux



#=============================================


def flux_calibrate_now(stdlist,fluxlist,speclist,extinct_correct=False,masterresp=False):
    if masterresp: #Use the master response function
        #Read in master response function and use that.
        cwd = os.getcwd()
        os.chdir('/afs/cas.unc.edu/depts/physics_astronomy/clemens/students/group/standards/response_curves/')
        standards = sorted(glob('*resp*.npy'))

        master_response_blue_in = np.load(standards[0])
        master_response_blue_in_pol = np.poly1d(master_response_blue_in)
        master_response_blue_out = np.load(standards[1])
        master_response_blue_out_pol = np.poly1d(master_response_blue_out)
        master_response_red_in = np.load(standards[2])
        master_response_red_in_pol = np.poly1d(master_response_red_in)
        master_response_red_out = np.load(standards[3])
        master_response_red_out_pol = np.poly1d(master_response_red_out)

        os.chdir(cwd)

        airstd = np.ones([4])
        #airstd[0] = 1.1

        #For saving files correctly
        stdflux = np.array(['mmaster.dat'])
        #standards = np.array([masterlist])
        allexcluded = [[None] for i in range(len(standards))]
        orderused = np.zeros([len(standards)])
        size = 0.

        #Find shift for each night
        #For blue setup: use mean of 4530-4590
        #for red setup: use mean of 6090-6190
        try:
            flux_tonight_list = np.genfromtxt('response_curves.txt',dtype=str)
            print 'Found response_curves.txt file.'
            print flux_tonight_list
            print type(flux_tonight_list)
            flux_tonight_list = np.array([flux_tonight_list])
            print flux_tonight_list
            print type(flux_tonight_list)
            for x in flux_tonight_list:
                print x
                if 'blue' in x.lower():
                    wave_tonight, sens_tonight = np.genfromtxt(x,unpack=True)
                    blue_low_index = np.min(np.where(wave_tonight > 4530.))
                    blue_high_index = np.min(np.where(wave_tonight > 4590.))
                    blue_mean_tonight = np.mean(sens_tonight[blue_low_index:blue_high_index])
                elif 'red' in x.lower():
                    wave_tonight, sens_tonight = np.genfromtxt(x,unpack=True)
                    red_low_index = np.min(np.where(wave_tonight > 6090.))
                    red_high_index = np.min(np.where(wave_tonight > 6190.))
                    red_mean_tonight = np.mean(sens_tonight[red_low_index:red_high_index])
        except:
            print 'No response_curves.txt file found.'
            blue_mean_tonight = None
            red_mean_tonight = None

    else: #Use the standard star fluxes in the typical manner
        #Read in each standard star spectrum 
        standards = np.genfromtxt(stdlist,dtype=str)
        if standards.size ==1:
            standards = np.array([standards])
        stdflux = np.genfromtxt(fluxlist,dtype=str)
        if stdflux.size == 1:
            stdflux = np.array([stdflux]) #save stdflux explicitly as an array so you can index if only 1 element
        #Check that the files are set up correctly to avoid mixing standards.
        #This checks that the files in liststandard have similar characters to those in listflux and the correct order. But might break if flux file doesn't match. E.G. mcd32d9927.dat is often called CD-32_9927 in our system. 
        '''
        onion = 0
        for stanspec in standards:
            quickcheck = stdflux[onion//2].lower()[1:-4] in stanspec.lower()
            if not quickcheck:
                print 'Check your standard star and flux files. They are mixed up.'
                sys.exit()
            onion += 1
        '''
        orderused = np.zeros([len(standards)])
        senspolys = []
        airstd = np.zeros([len(standards)])
        allexcluded = [[None] for i in range(len(standards))]
        
        #Calculating the sensitivity function of each standard star
        cucumber = 0
        for stdspecfile in standards:
            print stdspecfile
            #Read in the observed spectrum of the standard star
            obs_spectra,airmass,exptime,dispersion = st.readspectrum(stdspecfile) #obs_spectra is an object containing opfarr,farr,sky,sigma,warr
            airstd[cucumber] = airmass
            #plt.clf()
            #plt.plot(obs_spectra.warr,obs_spectra.opfarr)
            #plt.show()
        
            #Do the extinction correction
            if extinct_correct:
                print 'Extinction correcting spectra.'
                plt.clf()
                plt.plot(obs_spectra.warr,obs_spectra.opfarr)
                obs_spectra.opfarr = extinction_correction(obs_spectra.warr,obs_spectra.opfarr,airmass)
                plt.plot(obs_spectra.warr,obs_spectra.opfarr)
                #plt.show()

            #Change to the standard star directory
            cwd = os.getcwd()
            os.chdir('/afs/cas.unc.edu/depts/physics_astronomy/clemens/students/group/standards')

            #read in the standard file
            placeholder = cucumber // 2
            stdfile = stdflux[placeholder]
            std_spectra = st.readstandard(stdfile)
            os.chdir(cwd)
            #plt.clf()
            #plt.plot(std_spectra.warr,std_spectra.magarr,'.')
            #plt.show()
            #Only keep the part of the standard file that overlaps with observation.
            lowwv = np.where(std_spectra.warr >= np.min(obs_spectra.warr))
            lowwv = np.asarray(lowwv)
            highwv = np.where(std_spectra.warr <= np.max(obs_spectra.warr))
            highwv = np.asarray(highwv)
            index = np.intersect1d(lowwv,highwv)
        
            std_spectra.warr = std_spectra.warr[index]
            std_spectra.magarr = std_spectra.magarr[index]
            std_spectra.wbin = std_spectra.wbin[index]
        
            #Convert from AB mag to fnu, then to fwave (ergs/s/cm2/A)
            stdzp = 3.68e-20 #The absolute flux per unit frequency at an AB mag of zero
            std_spectra.magarr = st.magtoflux(std_spectra.magarr,stdzp)
            std_spectra.magarr = st.fnutofwave(std_spectra.warr, std_spectra.magarr)

            #plt.clf()
            #plt.plot(std_spectra.warr,std_spectra.magarr,'.')
            #plt.show()
            #np.savetxt('hz4_stan.txt',np.transpose([std_spectra.warr,std_spectra.magarr]))
            #exit()
        
            #We want to rebin the observed spectrum to match with the bins in the standard file. This makes summing up counts significantly easier.
            #Set the new binning here.
            print 'Starting to rebin: ',stdspecfile 
            low = np.rint(np.min(obs_spectra.warr)) #Rounds to nearest integer
            high = np.rint(np.max(obs_spectra.warr))
            size = 0.05 #size in Angstroms you want each bin
        
            num = (high - low) / size + 1. #number of bins. Must add one to get correct number.
            wavenew = np.linspace(low,high,num=num) #wavelength of each new bin

            #Now do the rebinning using Ian Crossfield's rebinning package
            binflux = st.resamplespec(wavenew,obs_spectra.warr,obs_spectra.opfarr,200.) #200 is the oversampling factor
            print 'Done rebinning. Now summing the spectrum into new bins to match', stdfile
            #plt.clf()
            #plt.plot(obs_spectra.warr,obs_spectra.opfarr)
            #plt.plot(wavenew,binflux)
            #plt.show()
        
            #Now sum the rebinned spectra into the same bins as the standard star file
            counts = st.sum_std(std_spectra.warr,std_spectra.wbin,wavenew,binflux)
            #plt.clf()
            #plt.plot(std_spectra.warr,std_spectra.magarr)
            #plt.plot(obs_spectra.warr,obs_spectra.opfarr,'b')
            #plt.plot(std_spectra.warr,counts,'g+')
            #plt.show()
            
            #Calculate the sensitivity function
            sens_function = st.sensfunc(counts,std_spectra.magarr,exptime,std_spectra.wbin,airmass)
            #plt.clf()
            #plt.plot(std_spectra.warr,sens_function)
            #plt.show()
            #sys.exit()
            #Fit a low order polynomial to this function so that it is smooth.
            #The sensitivity function is in units of 2.5 * log10[counts/sec/Ang / ergs/cm2/sec/Ang]
            #Choose regions to not include in fit, first by checking if a mask file exists, and if not the prompt for user interaction.
            if 'blue' in stdspecfile.lower():
                std_mask = stdfile[0:-4] + '_blue_maskasdf.dat'
            if 'red' in stdspecfile.lower():
                std_mask = stdfile[0:-4] + '_red_maskasdf.dat'
            std_mask2 = glob(std_mask)
            if len(std_mask2) == 1.:
                print 'Found mask file.\n'
                mask = np.ones(len(std_spectra.warr))
                excluded_wave = np.genfromtxt(std_mask) #Read in wavelengths to exclude
                #print excluded_wave
                #print type(excluded_wave)
                #Find index of each wavelength
                excluded = []
                for x in excluded_wave:
                    #print x
                    #print np.where(std_spectra.warr == find_nearest(std_spectra.warr,x))
                    pix_val = np.where(std_spectra.warr == find_nearest(std_spectra.warr,x))
                    excluded.append(pix_val[0][0])
                #print excluded
                lettuce = 0
                while lettuce < len(excluded):
                    mask[excluded[lettuce]:excluded[lettuce+1]+1] = 0
                    lettuce += 2
                excluded =  np.array(excluded).tolist()
                allexcluded[cucumber] = excluded
                indices = np.where(mask !=0.)
                lambdasfit = std_spectra.warr[indices]
                fluxesfit = sens_function[indices]
            else:
                print 'No mask found. User interaction required.\n'
                
                global ax, fig, coords
                coords = []
                plt.clf()
                fig = plt.figure(1)
                ax = fig.add_subplot(111)
                ax.plot(std_spectra.warr,sens_function)
                cid = fig.canvas.mpl_connect('button_press_event',onclick)
                print 'Please click on both sides of regions you want to exclude. Then close the plot.'
                plt.title('Click both sides of regions you want to exclude. Then close the plot.')
                plt.show(1)
        
        
                #Mask our the regions you don't want to fit
                #We need make sure left to right clicking and right to left clicking both work.
                mask = np.ones(len(std_spectra.warr))
                excluded = np.zeros(len(coords))
                lettuce = 0
                if len(coords) > 0:
                    while lettuce < len(coords):
                        x1 = np.where(std_spectra.warr == (find_nearest(std_spectra.warr,coords[lettuce][0])))
                        excluded[lettuce] = np.asarray(x1)
                        lettuce += 1
                        x2 = np.where(std_spectra.warr == (find_nearest(std_spectra.warr,coords[lettuce][0])))
                        if x2 < x1:
                            x1,x2 = x2,x1
                        mask[x1[0][0]:x2[0][0]+1] = 0 #have to add 1 here to the second index so that we exclude through that index. Most important for when we need to exclude the last point of the array.
                        excluded[lettuce-1] = np.asarray(x1)
                        excluded[lettuce] = np.asarray(x2)
                        lettuce += 1

                excluded =  np.array(excluded).tolist()
                allexcluded[cucumber] = excluded
                indices = np.where(mask !=0.)
                lambdasfit = std_spectra.warr[indices]
                fluxesfit = sens_function[indices]
        
                #Save masked wavelengths
                lambdasnotfit = std_spectra.warr[excluded]
                #print lambdasnotfit
                #print stdfile
                if 'blue' in stdspecfile.lower():
                    std_mask_name = stdfile[0:-4] + '_blue_mask.dat'
                if 'red' in stdspecfile.lower():
                    std_mask_name = stdfile[0:-4] + '_red_mask.dat'
                np.savetxt(std_mask_name,np.transpose(np.array(lambdasnotfit)))
                #exit()

            ##Move back to directory with observed spectra
            #os.chdir(cwd) 
        
        
            #Make sure they are finite
            ind1 = np.isfinite(lambdasfit) & np.isfinite(fluxesfit)
            lambdasfit = lambdasfit[ind1]
            fluxesfit = fluxesfit[ind1]

            print 'Fitting the sensitivity funtion now.'
            order = 4
            repeat = 'yes'
            while repeat == 'yes':
                p = np.polyfit(lambdasfit,fluxesfit,order)
                f = np.poly1d(p)
                smooth_sens = f(lambdasfit)
                residual = fluxesfit - smooth_sens
                plt.close()
                plt.ion()
                g, (ax1,ax2) = plt.subplots(2,sharex=True)
                ax1.plot(lambdasfit,fluxesfit,'b+')
                ax1.plot(lambdasfit,smooth_sens,'r',linewidth=2.0)
                ax1.set_ylabel('Sensitivity Function')
                ax2.plot(lambdasfit,residual,'k+')
                ax2.set_ylabel('Residuals')
                ax1.set_title('Current polynomial order: %s' % order)
                g.subplots_adjust(hspace=0)
                plt.setp([a.get_xticklabels() for a in g.axes[:-1]],visible=False)
                plt.show()
                plt.ioff()
                #Save this sensitivity curve
                '''
                try:
                    temp_file = fits.open(stdspecfile)
                    ADCstat = temp_file[0].header['ADCSTAT']
                except:
                    ADCstat = 'none'
                    pass
                if 'blue' in stdspecfile.lower():
                    resp_name = 'senscurve_' + stdfile[1:-4] + '_' + str(np.round(airstd[cucumber],decimals=3))  + '_' + ADCstat  + '_' + cwd[60:70] + '_blue.txt'
                elif 'red' in stdspecfile.lower():
                    resp_name = 'senscurve_' + stdfile[1:-4] + '_' + str(np.round(airstd[cucumber],decimals=3))  + '_' + ADCstat  + '_' + cwd[60:70] + '_red.txt'
                print resp_name
                #exit()
                np.savetxt(resp_name,np.transpose([lambdasfit,fluxesfit]))
                '''
                repeat = raw_input('Do you want to try again (yes/no)? ')
                if repeat == 'yes':
                    order = raw_input('New order for polynomial: ')

            orderused[cucumber] = order
            senspolys.append(f)

            #Save arrays for diagnostic plots
            if cucumber == 0:
                bigarray = np.zeros([len(lambdasfit),4.*len(standards)])
                artichoke = 0
            bigarray[0:len(lambdasfit),artichoke] = lambdasfit
            bigarray[0:len(fluxesfit),artichoke+1] = fluxesfit
            bigarray[0:len(smooth_sens),artichoke+2] = smooth_sens
            bigarray[0:len(residual),artichoke+3] = residual
            artichoke += 4
                   
            cucumber += 1

        #Save fit and residuals into text file for diagnostic plotting later.
        #Need to save lambdasfit,fluxesfit,smooth_sens,residual for each standard
        #List of standards is found as standards
        now = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M")
        with open('sens_fits_' + now + '.txt','a') as handle:
            header = str(standards) + '\n Set of four columns correspond to wavelength, observed flux, polynomial fit, \n and residuals for each standard listed above. \n You will probably need to strip zeros from the bottoms of some columns.'
            np.savetxt(handle,bigarray,fmt='%f',header = header)    

    #Outline for next steps:
    #Read in both red and blue files
    #compute airmass and compare to airstd
    #choose best standard and flux calibrate both blue and red
    #save files and write to sensitivity_params.txt
      
    specfile = np.genfromtxt(speclist,dtype=str)
    if specfile.size ==1:
        specfile = np.array([specfile])
    length = len(specfile)
    airwd = np.zeros([length])
    bean = 0
    #if length == 1:
    #    redfile = False
    #else:
    #    redfile = True

    avocado = 0
    while avocado < length:
        #Read in the blue and red spectra we want to flux calibrate. Save the airmass
        WD_spectra1,airmass1,exptime1,dispersion1 = st.readspectrum(specfile[avocado])
        if (len(specfile) >= 1) and (avocado+1 < length):
            if 'red' in specfile[avocado+1]:
                redfile = True
            else:
                redfile = False
        else:
            redfile = False
        if redfile:
            WD_spectra2,airmass2,exptime2,dispersion2 = st.readspectrum(specfile[avocado+1])
                
        #Extinction correct WD
        if extinct_correct:
            print 'Extinction correcting spectra.'
            #plt.clf()
            #plt.plot(WD_spectra1.warr,WD_spectra1.opfarr)
            WD_spectra1.opfarr = extinction_correction(WD_spectra1.warr,WD_spectra1.opfarr,airmass1)
            WD_spectra1.farr = extinction_correction(WD_spectra1.warr,WD_spectra1.farr,airmass1)
            #plt.plot(WD_spectra1.warr,WD_spectra1.opfarr)
            #plt.show()

            if redfile:
                #plt.clf()
                #plt.plot(WD_spectra2.warr,WD_spectra2.opfarr)
                WD_spectra2.opfarr = extinction_correction(WD_spectra2.warr,WD_spectra2.opfarr,airmass2)
                WD_spectra2.farr = extinction_correction(WD_spectra2.warr,WD_spectra2.farr,airmass2)
                #zaplt.plot(WD_spectra2.warr,WD_spectra2.opfarr)
                #plt.show()
        airwd[avocado] = airmass1
        if redfile:
            airwd[avocado+1] = airmass2
        #Compare the airmasses to determine the best standard star
        tomato = 0
        while tomato < len(airstd):
            if redfile:
                diff = np.absolute(np.mean([airwd[avocado],airwd[avocado+1]]) - np.mean([airstd[tomato],airstd[tomato+1]]))
            else:
                diff = np.absolute(airwd[avocado] - airstd[tomato])
            if tomato == 0:
                difference = diff
                choice = tomato
            if diff < difference:
                difference = diff
                choice = tomato
            tomato += 2
    
        #To get the flux calibration, perform the following
        #Flux = counts / (Exptime * dispersion * 10**(sens/2.5))
        #Get the sensitivity function at the correct wavelength spacing
        if masterresp:
            header_temp = st.readheader(specfile[avocado])
            ADCstatus = header_temp['ADCSTAT']
            if ADCstatus == 'IN':
                sens_wave1_unscale = master_response_blue_in_pol(WD_spectra1.warr)
                blue_low_index = np.min(np.where(WD_spectra1.warr > 4530.))
                blue_high_index = np.min(np.where(WD_spectra1.warr > 4590.))
                blue_mean_stan = np.mean(sens_wave1_unscale[blue_low_index:blue_high_index])
                if blue_mean_tonight == None:
                    sens_wave1 = sens_wave1_unscale
                else:
                    sens_wave1 = sens_wave1_unscale + (blue_mean_tonight - blue_mean_stan)
                choice = 0
            else:
                sens_wave1_unscale = master_response_blue_out_pol(WD_spectra1.warr)
                blue_low_index = np.min(np.where(WD_spectra1.warr > 4530.))
                blue_high_index = np.min(np.where(WD_spectra1.warr > 4590.))
                blue_mean_stan = np.mean(sens_wave1_unscale[blue_low_index:blue_high_index])
                if blue_mean_tonight == None:
                    sens_wave1 = sens_wave1_unscale
                else:
                    sens_wave1 = sens_wave1_unscale + (blue_mean_tonight - blue_mean_stan)
                choice = 1
            if redfile:
                header_temp = st.readheader(specfile[avocado+1])
                ADCstatus = header_temp['ADCSTAT']
                if ADCstatus == 'IN':
                    sens_wave2_unscale = master_response_red_in_pol(WD_spectra2.warr)
                    red_low_index = np.min(np.where(WD_spectra2.warr > 6090.))
                    red_high_index = np.min(np.where(WD_spectra2.warr > 6190.))
                    red_mean_stan = np.mean(sens_wave2_unscale[red_low_index:red_high_index])
                    if red_mean_tonight == None:
                        sens_wave2 = sens_wave2_unscale
                    else:
                        sens_wave2 = sens_wave2_unscale + (red_mean_tonight - red_mean_stan)
                    choice2 = 2
                else:
                    sens_wave2_unscale = master_response_red_out_pol(WD_spectra2.warr)
                    red_low_index = np.min(np.where(WD_spectra2.warr > 6090.))
                    red_high_index = np.min(np.where(WD_spectra2.warr > 6190.))
                    red_mean_stan = np.mean(sens_wave2_unscale[red_low_index:red_high_index])
                    if red_mean_tonight == None:
                        sens_wave2 = sens_wave2_unscale
                    else:
                        sens_wave2 = sens_wave2_unscale + (red_mean_tonight - red_mean_stan)
                    choice2 = 3
        else:
            sens_wave1 = senspolys[choice](WD_spectra1.warr)
            if redfile:
                sens_wave2 = senspolys[choice+1](WD_spectra2.warr)

        #Perform the flux calibration. We do this on the optimal extraction, non-variance weighted aperture, the sky spectrum, and the sigma spectrum.
        print 'Doing the final flux calibration.'
        #np.savetxt('response_g60-54_extinction_2016-03-17.txt',np.transpose([WD_spectra1.warr,(exptime1 * dispersion1 * 10.**(sens_wave1/2.5))]))#,WD_spectra2.warr,(exptime2 * dispersion2 * 10.**(sens_wave2/2.5))]))
        #exit()
        star_opflux1 = st.cal_spec(WD_spectra1.opfarr,sens_wave1,exptime1,dispersion1)
        star_flux1 = st.cal_spec(WD_spectra1.farr,sens_wave1,exptime1,dispersion1)
        sky_flux1 = st.cal_spec(WD_spectra1.sky,sens_wave1,exptime1,dispersion1)
        sigma_flux1 = st.cal_spec(WD_spectra1.sigma,sens_wave1,exptime1,dispersion1)
        
        if redfile:
            star_opflux2 = st.cal_spec(WD_spectra2.opfarr,sens_wave2,exptime2,dispersion2)
            star_flux2 = st.cal_spec(WD_spectra2.farr,sens_wave2,exptime2,dispersion2)
            sky_flux2 = st.cal_spec(WD_spectra2.sky,sens_wave2,exptime2,dispersion2)
            sigma_flux2 = st.cal_spec(WD_spectra2.sigma,sens_wave2,exptime2,dispersion2)
        
        #plt.clf()
        #plt.plot(WD_spectra.warr,star_opflux)
        #plt.show()

        #Save final spectra if using master response
        if masterresp:
            if avocado == 0:
                diagnostic_array = np.zeros([len(WD_spectra1.warr),2*length])
            diagnostic_array[0:len(WD_spectra1.warr),bean] = WD_spectra1.warr
            bean += 1
            diagnostic_array[0:len(star_opflux1),bean] = star_opflux1
            bean += 1
            if redfile:
                diagnostic_array[0:len(WD_spectra2.warr),bean] = WD_spectra2.warr
                bean += 1
                diagnostic_array[0:len(star_opflux2),bean] = star_opflux2
                bean += 1
        #if avocado == (length -1 ) or (redfile == True and avocado == (length-2)):
        #    print 'Saveing diagnostic file.'
        #    now = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M")
        #    with open('flux_fits_' + now + '.txt','a') as handle:
        #        header = str(specfile) + '\n Each star is formatted as wavelength, flux'
        #        np.savetxt(handle,diagnostic_array,fmt='%.10e',header=header)


        print 'Saving the final spectrum.'
        
        #Save the flux-calibrated spectrum and update the header
        header1 = st.readheader(specfile[avocado])
        header1.set('EX-FLAG',-1) #Extiction correction? 0=yes, -1=no
        header1.set('CA-FLAG',0) #Calibrated to flux scale? 0=yes, -1=no
        header1.set('BUNIT','erg/cm2/s/A') #physical units of the array value
        header1.set('STANDARD',str(standards[choice]),'Flux standard used') #flux standard used for flux-calibration
        
        if redfile:
            header2 = st.readheader(specfile[avocado+1])
            header2.set('EX-FLAG',-1) #Extiction correction? 0=yes, -1=no
            header2.set('CA-FLAG',0) #Calibrated to flux scale? 0=yes, -1=no
            header2.set('BUNIT','erg/cm2/s/A') #physical units of the array value
            if masterresp:
                header2.set('STANDARD',str(standards[choice2]),'Flux standard used') #flux standard used for flux-calibration
            else:
                header2.set('STANDARD',str(standards[choice+1]),'Flux standard used') #flux standard used for flux-calibration

        #Set up size of new fits image
        Ni = 4. #Number of extensions
        Nx1 = len(star_flux1)
        if redfile:
            Nx2 = len(star_flux2)
        Ny = 1. #All 1D spectra

        data1 = np.empty(shape = (Ni,Ny,Nx1))
        data1[0,:,:] = star_opflux1
        data1[1,:,:] = star_flux1
        data1[2,:,:] = sky_flux1
        data1[3,:,:] = sigma_flux1
    
        if redfile:
            data2 = np.empty(shape = (Ni,Ny,Nx2))
            data2[0,:,:] = star_opflux2
            data2[1,:,:] = star_flux2
            data2[2,:,:] = sky_flux2
            data2[3,:,:] = sigma_flux2

        #Add '_flux' to the end of the filename
        loc1 = specfile[avocado].find('.ms.fits')
        if masterresp:
            newname1 = specfile[avocado][0:loc1] + '_flux_' + stdflux[0][1:-4]  + '.ms.fits'
        else:
            newname1 = specfile[avocado][0:loc1] + '_flux_' + stdflux[choice//2][1:-4]  + '.ms.fits'
        clob = False
        mylist = [True for f in os.listdir('.') if f == newname1]
        exists = bool(mylist)

        if exists:
            print 'File %s already exists.' % newname1
            nextstep = raw_input('Do you want to overwrite or designate a new name (overwrite/new)? ')
            if nextstep == 'overwrite':
                clob = True
                exists = False
            elif nextstep == 'new':
                newname1 = raw_input('New file name: ')
                exists = False
            else:
                exists = False
        print 'Saving: ', newname1
        newim1 = fits.PrimaryHDU(data=data1,header=header1)
        newim1.writeto(newname1,clobber=clob)

        if redfile:
            loc2 = specfile[avocado+1].find('.ms.fits')
            if masterresp:
                newname2 = specfile[avocado+1][0:loc2] + '_flux_' + stdflux[0][1:-4] + '.ms.fits'
            else:
                newname2 = specfile[avocado+1][0:loc2] + '_flux_' + stdflux[choice//2][1:-4] + '.ms.fits'
            clob = False
            mylist = [True for f in os.listdir('.') if f == newname2]
            exists = bool(mylist)

            if exists:
                print 'File %s already exists.' % newname2
                nextstep = raw_input('Do you want to overwrite or designate a new name (overwrite/new)? ')
                if nextstep == 'overwrite':
                    clob = True
                    exists = False
                elif nextstep == 'new':
                    newname2 = raw_input('New file name: ')
                    exists = False
                else:
                    exists = False

            newim2 = fits.PrimaryHDU(data=data2,header=header2)
            newim2.writeto(newname2,clobber=clob)
            print 'Saving: ', newname2

        #Finally, save all the used parameters into a file for future reference.
        # specfile,current date, stdspecfile,stdfile,order,size,newname
        f = open('sensitivity_params.txt','a')
        now = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M")
        if masterresp:
            newinfo1 = specfile[avocado] + '\t' + now + '\t' + standards[choice] + '\t' + stdflux[0] + '\t' + str(allexcluded[choice]) + '\t' + str(orderused[choice]) + '\t' + str(size) + '\t' + newname1
        else:
            newinfo1 = specfile[avocado] + '\t' + now + '\t' + standards[choice] + '\t' + stdflux[choice//2] + '\t' + str(allexcluded[choice]) + '\t' + str(orderused[choice]) + '\t' + str(size) + '\t' + newname1
        if redfile:
            if masterresp:
                newinfo2 = specfile[avocado+1] + '\t' + now + '\t' + standards[choice2] + '\t' + stdflux[0] + '\t' + str(allexcluded[choice+1]) + '\t' + str(orderused[choice+1]) + '\t' + str(size) + '\t' + newname2
            else:
                newinfo2 = specfile[avocado+1] + '\t' + now + '\t' + standards[choice+1] + '\t' + stdflux[choice//2] + '\t' + str(allexcluded[choice+1]) + '\t' + str(orderused[choice+1]) + '\t' + str(size) + '\t' + newname2
            f.write(newinfo1 + "\n" + newinfo2 + "\n")
        else:
            f.write(newinfo1 + "\n")
        f.close()

        if redfile:
            avocado += 2
        else:
            avocado += 1

    print 'Done flux calibrating the spectra.'





#Run from command line
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('spec_list')
    parser.add_argument('--flux_list',default=None)
    parser.add_argument('--stan_list',default=None)
    parser.add_argument('--usemaster',type=str2bool,nargs='?',const=False,default=False,help='Activate nice mode.')
    parser.add_argument('--extinct',type=str2bool,nargs='?',const=True,default=True,help='Activate nice mode.')
    args = parser.parse_args()
    #print args.stand_list
    #Read in lists from command line
    #print args.spec_list
    #print args.usemaster, args.extinct
    #stdspecfile = 'wnb.GD50_930_blue.ms.fits'
    #stdfile = 'mgd50.dat'
    #specfile = 'wnb.WD0122p0030_930_blue.ms.fits'
    #flux_calibrate_now(stdlist,fluxlist,speclist,extinct_correct=True)
    flux_calibrate_now(args.stan_list,args.flux_list,args.spec_list,extinct_correct=args.extinct,masterresp=args.usemaster)
