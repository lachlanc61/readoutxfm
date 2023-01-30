import numpy as np

import xfmreadout.bufferops as bufferops
import xfmreadout.utils as utils



class MapDone(Exception): pass

def endpx(pxidx, idx, buffer, xfmap, pixelseries):
    #print pixel index at end of every row
    row=pixelseries.yidx[0,pxidx]+1

    if pxidx % xfmap.xres == (xfmap.xres-1): 
        print(f"\rRow {row}/{xfmap.yres} at pixel {pxidx}, byte {buffer.fidx+idx} ({100*(buffer.fidx+idx)/xfmap.fullsize:.1f} %)", end='')
        pass
    #stop when pixel index greater than expected no. pixels
    if (pxidx >= (xfmap.npx-1)):
        print(f"\nENDING AT: Row {row}/{xfmap.yres} at pixel {pxidx}")
        raise MapDone

    pxidx+=1

    return pxidx


def initparse(xfmap):
    """
    unused for now
    """
    xfmap.resetfile()
    buffer = bufferops.MapBuffer(xfmap.infile, xfmap.chunksize)
    idx = xfmap.datastart
    pxheaderlen = xfmap.PXHEADERLEN    

    return buffer, idx, pxheaderlen

def indexmap(xfmap, pixelseries):
    """
    parse the pixel headers
    - get pixel statistics
    index the file
    """

    print("BEGIN INDEXING")
    try:
        indexlist=np.zeros((pixelseries.ndet,xfmap.npx),dtype=np.uint64)

        xfmap.resetfile()
        buffer = bufferops.MapBuffer(xfmap.infile, xfmap.chunksize)
        idx = xfmap.datastart
        pxheaderlen = xfmap.PXHEADERLEN    

        pxidx=0
        while True:

            headstream, idx, buffer = bufferops.getstream(buffer, idx, pxheaderlen)
            
            pxlen, xidx, yidx, det, dt = bufferops.readpxheader(headstream)

            indexlist[det, pxidx] = buffer.fidx+idx-pxheaderlen

            pixelseries = pixelseries.receiveheader(pxidx, pxlen, xidx, yidx, det, dt)
            
            #use getstream to step to the next pixel and handle end-of-buffer events
            __, idx, buffer = bufferops.getstream(buffer, idx, pxlen-pxheaderlen)

            if det == xfmap.maxdet:
                pxidx = endpx(pxidx, idx, buffer, xfmap, pixelseries)

    except MapDone:
        pixelseries.npx=pxidx+1
        pixelseries.nrows=pixelseries.yidx[0,pxidx]+1 
        buffer.wait()
        xfmap.resetfile()
        return pixelseries, indexlist



def parse(xfmap, pixelseries, indexlist):
    """
    read in the map data after indexing

    NB. no longer getting sum from parser, do this in postana using pixelseries.data
    """
    try:
        xfmap.resetfile()
        buffer = bufferops.MapBuffer(xfmap.infile, xfmap.chunksize)
        idx = xfmap.datastart
        pxheaderlen = xfmap.PXHEADERLEN
        bytesperchan = xfmap.BYTESPERCHAN

        for pxidx in range(pixelseries.npx):
            for det in range(pixelseries.ndet):

                if not det == pixelseries.det[det,pxidx]:
                    raise ValueError(f"Detector mistmatch at (det,pixel) = ({det},{pxidx})")
                
                start=indexlist[det,pxidx]
                pxlength=pixelseries.pxlen[det,pxidx]

                try:
                #should be able to parallelize pullstream + readpx+gapfill + assign
                    if start+pxlength <= buffer.fidx + buffer.len:
                        stream = bufferops.pullstream(buffer, start, pxlength, pxheaderlen)
                    else:
                        #join
                        stream, ___, buffer=bufferops.getstream(buffer, int(start-buffer.fidx), pxlength)

                    chan, counts = bufferops.readpxdata(stream, len(stream), bytesperchan)
                    chan, counts = utils.gapfill(chan,counts, xfmap.nchannels)  #<-should probably go in readpxdata
                except ValueError:
                    print(f"{det}, {pxidx}")
                    exit()
                finally:
                    pixelseries.data[det,pxidx,:]=counts
            ___ = endpx(pxidx, idx, buffer, xfmap, pixelseries)
    except MapDone:
        if not pixelseries.npx == pxidx+1:
            raise ValueError(f"Index mistmatch ({pixelseries.npx}) vs ({pxidx})")
        if not pixelseries.nrows == pixelseries.yidx[0,pxidx]+1:
            raise ValueError(f"Index mistmatch ({pixelseries.nrows}) vs ({pixelseries.yidx[0,pxidx]+1})")
        buffer.wait()
        xfmap.resetfile()
        return pixelseries


def writemap(xfmap, pixelseries):
    """
    write a map or submap
        cropping coordinates and updating headers/pxheaders
            and/or
        filling/predicting/correcting deadtimes when missing
    """
    pass