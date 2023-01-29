import struct 
import os
import numpy as np
import json
import copy
import time

import xfmreadout.utils as utils
import xfmreadout.colour as colour
import xfmreadout.fitting as fitting
import xfmreadout.byteops as byteops
import xfmreadout.bufferops as bufferops
import xfmreadout.parser as parser




#CLASSES
class Xfmap:
    """
    Object wrapping binary file to be read
        holds: params read directly from file
        loads: byte stream from file, holds pointer
        methods to parse pixel header and body, manage memory via chunks
            bufferops.py module contains subsidiary code to parse binary
    """
    def __init__(self, config, fi, fo):

        #assign input file object for reading
        try:
            self.infile = open(fi, mode='rb') # rb = read binary
            if config['WRITESUBMAP']:
                self.outfile = open(fo, mode='wb')   #wb = write binary
        except FileNotFoundError:
            print("FATAL: incorrect filepath/files not found")

        #get total size of file to parse
        self.fullsize = os.path.getsize(fi)
        self.chunksize = int(config['chunksize'])*int(config['MBCONV'])
        self.fidx=self.infile.tell()

        if self.fidx != 0:
            raise ValueError(f"File pointer at {self.fidx} - Expected 0 (start of file)")

        """
        #generate initial bytestream
        #self.stream = self.infile.read()         
        self.stream = self.infile.read(self.chunksize)   
        self.streamlen=len(self.stream)

        #pointers
        self.idx=0      #byte pointer
        self.pxidx=0    #pixel pointer
        self.rowidx=0   #row pointer
        self.pxstart=0  #pointer for start of pixel

        self.fullidx = self.idx
        self.chunkidx = self.idx        
        """

        #read the beginning of the file into buffer
        buffer = bufferops.MapBuffer(self.infile, self.chunksize)

        #read the JSON header and store position of first pixel
        self.headerdict, self.datastart, buffer = bufferops.readjsonheader(buffer, 0)
        
        #try to assign values from header
        try:
            self.xres = int(self.headerdict['File Header']['Xres'])           #map size x
            self.yres = int(self.headerdict['File Header']['Yres'])           #map size y
            self.xdim = float(self.headerdict['File Header']['Width (mm)'])     #map dimension x
            self.ydim = float(self.headerdict['File Header']['Height (mm)'])    #map dimension y
            self.nchannels = int(self.headerdict['File Header']['Chan']) #no. channels
            self.gain = float(self.headerdict['File Header']['Gain (eV)']/1000) #gain in kV
            self.deadtime = float(self.headerdict['File Header']['Deadtime (%)'])
            self.dwell = float(self.headerdict['File Header']['Dwell (mS)'])   #dwell in ms
            self.timeconst = float(config['time_constant']) #pulled from config, ideally should be in header
        except:
            raise ValueError("FATAL: failure reading values from header")
               
        #initialise arrays
        self.chan = np.arange(0,self.nchannels)     #channel series
        self.energy = self.chan*self.gain           #energy series
        self.xarray = np.arange(0, self.xdim, self.xdim/self.xres )   #position series x  
        self.yarray = np.arange(0, self.ydim, self.ydim/self.yres )   #position series y
            #NB: real positions likely better represented by centres of pixels eg. 0+(xdim/xres), xdim-(xdim/xres) 
            #       need to ask IXRF how this is handled by Iridium

        #derived vars
        self.npx = self.xres*self.yres        #expected number of pixels
        self.PXHEADERLEN=config['PXHEADERLEN'] 

        self.detarray = bufferops.getdetectors(buffer, self.datastart, self.PXHEADERLEN)
        self.maxdet = max(self.detarray)

        time.sleep(5)
        self.resetfile()
        return

    def resetfile(self):
        self.infile.seek(0)

    def closefiles(self, config):
        self.infile.close()
        if config['WRITESUBMAP']:
            self.outfile.close()






















    def parse(self, config, pxseries):

        print(f"pixels expected: {self.npx}")
        print("---------------------------")

        if config['WRITESUBMAP']:
            bufferops.writefileheader(config, self)

        #https://stackoverflow.com/questions/16073396/breaking-while-loop-with-function
        try:
            while True:
                
                headstream, self.idx = bufferops.getstream(self,self.idx,self.PXHEADERLEN)

                pxlen, xidx, yidx, det, dt = bufferops.readpxheader(headstream, config, self.PXHEADERLEN, self)

                readlength=pxlen-self.PXHEADERLEN

                pxseries = pxseries.receiveheader(self.pxidx, pxlen, xidx, yidx, det, dt)
            
                locstream, self.idx = bufferops.getstream(self,self.idx,readlength)

                if config['PARSEMAP']:
                    chan, counts = bufferops.readpxdata(locstream, config, readlength)

                    #fill gaps in spectrum 
                    #   (ie. assign all zero-count chans = 0)
                    chan, counts = utils.gapfill(chan,counts, config['NCHAN'])

                    #warn if recieved channel list is different length to chan array
                    if len(chan) != len(self.chan):
                        print("WARNING: unexpected length of channel list")

                    #store pixel sum
                    pxsum=int(np.sum(counts))
                    pxseries.sum[det,self.pxidx]=pxsum    #sum normalised for dwelltime

                    #assign counts into data array
                    pxseries.data[det,self.pxidx,:]=counts

                if config['WRITESUBMAP'] and utils.pxinsubmap(config, xidx, yidx):
                        bufferops.writepxheader(config, self, pxseries, det)
                        bufferops.writepxrecord(locstream, readlength, self)

                self.fullidx=self.chunkidx+self.idx

                #if on last detector for this pixel, increment counters and check end
                if det == max(self.detarray):
                    #stop when pixel index greater than expected no. pixels
                    if (self.pxidx >= (self.npx-1)):
                        print(f"\nENDING AT: Row {self.rowidx}/{self.yres} at pixel {self.pxidx}")
                        raise parser.MapDone

                    #print pixel index at end of every row
                    if self.pxidx % self.xres == (self.xres-1): 
                        print(f"\rRow {self.rowidx}/{self.yres-1} at pixel {self.pxidx}, byte {self.fullidx} ({100*self.fullidx/self.fullsize:.1f} %)", end='')
                        self.rowidx+=1

                    self.pxidx+=1    #next pixel
        except parser.MapDone:
            #store no. pixels and rows read successfully
            pxseries.npx=self.pxidx+1
            pxseries.nrows=self.rowidx+1 

            return pxseries

    def nextchunk(self):
        #NB: chunkdx likely broken after refactor
        self.chunkidx = self.chunkidx + self.idx

        self.stream = self.infile.read(self.chunksize)

        if len(self.stream) != self.streamlen:
            print("\n NOTE: final chunk")

        self.streamlen=len(self.stream)
        self.idx=0

        if not self.stream:
            print(f"\n WARNING: Attempting to load chunk beyond EOF - dimensions in header may be incorrect.")
            raise parser.MapDone




class PixelSeries:
    def __init__(self, config, xfmap, npx, detarray):

        self.source=xfmap

        #assign number of detectors
        self.ndet=max(detarray)+1

        #initialise pixel value arrays
        self.pxlen=np.zeros((self.ndet,npx),dtype=np.uint16)
        self.xidx=np.zeros((self.ndet,npx),dtype=np.uint16)
        self.yidx=np.zeros((self.ndet,npx),dtype=np.uint16)
        self.det=np.zeros((self.ndet,npx),dtype=np.uint16)
        self.sum=np.zeros((self.ndet,npx),dtype=np.uint32)        
        self.dt=np.zeros((self.ndet,npx),dtype=np.float32)

        #create colour-associated attrs even if not doing colours
        self.rvals=np.zeros(npx)
        self.gvals=np.zeros(npx)
        self.bvals=np.zeros(npx)
        self.totalcounts=np.zeros(npx)

        #initialise whole data containers (WARNING: large)
        if config['PARSEMAP']: 
            self.data=np.zeros((self.ndet,npx,config['NCHAN']),dtype=np.uint16)
#            if config['DOBG']: self.corrected=np.zeros((xfmap.npx,config['NCHAN']),dtype=np.uint16)
        else:
        #create a small dummy array just in case
            self.data=np.zeros((1024,config['NCHAN']),dtype=np.uint16)

        self.npx=0
        self.nrows=0

    def receiveheader(self, pxidx, pxlen, xcoord, ycoord, det, dt):
        self.pxlen[det,pxidx]=pxlen
        self.xidx[det,pxidx]=xcoord
        self.yidx[det,pxidx]=ycoord
        self.det[det,pxidx]=det
        self.dt[det,pxidx]=dt
        
        return self

    def flatten(self, data, detarray):
        """
        sum all detectors into single data array
        NB: i think this creates another dataset in memory while running
        """
        flattened = data[0]
        if len(detarray) > 1:
            for i in detarray[1:]:
                flattened+=data[i]
        
        return flattened

    def exportpxstats(self, config, dir):
        """
        write the pixel header statistics to csv
        """
        np.savetxt(os.path.join(dir, "pxstats_pxlen.txt"), self.pxlen, fmt='%i', delimiter=",")
        np.savetxt(os.path.join(dir, "pxstats_xidx.txt"), self.xidx, fmt='%i', delimiter=",")
        np.savetxt(os.path.join(dir, "pxstats_yidx.txt"), self.yidx, fmt='%i', delimiter=",")
        np.savetxt(os.path.join(dir, "pxstats_detector.txt"), self.det, fmt='%i', delimiter=",")
        np.savetxt(os.path.join(dir, "pxstats_dt.txt"), self.dt, fmt='%f', delimiter=",")    
        
        if config['PARSEMAP']:
            np.savetxt(os.path.join(dir, "pxstats_sum.txt"), self.sum, fmt='%d', delimiter=",")    


    def exportpxdata(self, config, dir):
        """
        writes the spectrum-by-pixel data to csv
        """
        print("saving spectrum-by-pixel to file")
        np.savetxt(os.path.join(dir,  config['outfile'] + ".dat"), self.data, fmt='%i')   

    def readpxdata(self, config, dir):
        """
        read data from csv
            does not currently return as much information as the full parse
        """
        print("loading from file", config['outfile'])
        self.data = np.loadtxt(os.path.join(dir, config['outfile']), dtype=np.uint16, delimiter=",")
        self.pxlen=np.loadtxt(os.path.join(dir, "pxlen.txt"), dtype=np.uint16, delimiter=",")
        self.xidx=np.loadtxt(os.path.join(dir, "xidx.txt"), dtype=np.uint16, delimiter=",")
        self.yidx=np.loadtxt(os.path.join(dir, "yidx.txt"), dtype=np.uint16, delimiter=",")
        self.det=np.loadtxt(os.path.join(dir, "detector.txt"), dtype=np.uint16, delimiter=",")
        self.dt=np.loadtxt(os.path.join(dir, "dt.txt"), dtype=np.float32, delimiter=",")
        
        print("loaded successfully", config['outfile']) 

        return self