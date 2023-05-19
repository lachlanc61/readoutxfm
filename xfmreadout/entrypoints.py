import time
import sys
import os
import numpy as np

import xfmreadout.utils as utils
import xfmreadout.argops as argops
import xfmreadout.colour as colour
import xfmreadout.clustering as clustering
import xfmreadout.visualisations as vis
import xfmreadout.structures as structures
import xfmreadout.dtops as dtops
import xfmreadout.parser as parser
import xfmreadout.diagops as diagops
import xfmreadout.processops as processops

"""
Parses spectrum-by-pixel maps from IXRF XFM

- parses binary .GeoPIXE files
- extracts pixel parameters
- extracts pixel data
- classifies data via eg. UMAP, HDBSCAN
- displays classified maps
- produces average spectrum per class

./data has example datasets
"""
#-----------------------------------
#vars
#-----------------------------------
PACKAGE_CONFIG='xfmreadout/config.yaml'

#-----------------------------------
#INITIALISE
#-----------------------------------

def entry_raw():
    """
    entrypoint wrapper gettings args from sys
    """
    args_in = sys.argv[1:]  #NB: exclude 0 == script name
    read_raw(args_in)

def entry_processed():
    """
    entrypoint wrapper gettings args from sys
    """
    args_in = sys.argv[1:]  #NB: exclude 0 == script name
    read_processed(args_in)

def read_raw(args_in):
    """
    parse map according to args_in
    
    return pixelseries, xfmap and analysis results
    """
    
    #create input config from args and config files
    config =utils.initcfg(PACKAGE_CONFIG)

    #get command line arguments
    args = argops.readargs(args_in, config)

    #initialise read file and directory structure 
    config, dirs = utils.initfiles(args, config)

    #perform parse
    xfmap, pixelseries = parser.read(config, args, dirs)

    #ANALYSIS

    #perform post-analysis:
    #   create and show colourmap, deadtime/sum reports
    if args.analyse:
        #uncomment to fit baselines
        #pixelseries.corrected=fitting.calc_corrected(pixelseries.flattened, pixelseries.energy, pixelseries.npx, pixelseries.nchan)

        #dtops.export(dirs.exports, pixelseries.dtmod, pixelseries.flatsum)

        if args.log_file is not None:
            realtime, livetime, triggers, events, icr, ocr, dt_evt, dt_rt = diagops.dtfromdiag(dirs.logf)
            print(dt_evt)

        dtops.dtplots(config, dirs.plots, pixelseries.dt, pixelseries.sum, pixelseries.dtmod[:,0], pixelseries.dtflat, \
            pixelseries.flatsum, xfmap.xres, xfmap.yres, pixelseries.ndet, args.index_only)

        pixelseries.rgbarray, pixelseries.rvals, pixelseries.gvals, pixelseries.bvals \
            = colour.calccolours(config, pixelseries, xfmap, pixelseries.flattened, dirs)       #flattened / corrected
    else:
        rgbarray = None
    #perform clustering
    if args.classify_spectra:
        pixelseries.categories, pixelseries.classavg, embedding, clusttimes = clustering.run( pixelseries.flattened, dirs.transforms, force_embed=args.force, overwrite=config['OVERWRITE_EXPORTS'] )
        
        vis.plot_clusters(pixelseries.categories, pixelseries.classavg, embedding, pixelseries.dimensions)
#        clustering.complete(pixelseries.categories, pixelseries.classavg, embedding, clusttimes, xfmap.energy, xfmap.xres, xfmap.yres, config['nclust'], dirs.plots)
        #colour.plot_colourmap_explainer(pixelseries.energy, pixelseries.classavg[1:1], pixelseries.rvals, pixelseries.gvals, pixelseries.bvals, dirs)
    else:
        categories = None
        classavg = None

    print("Processing complete")

    return pixelseries, xfmap, #dt_log


def read_processed(args_in):
    """
    read exported tiffs from geopixe
    
    perform clustering and visualisation
    """
    #create input config from args and config files
    config =utils.initcfg(PACKAGE_CONFIG)

    #get command line arguments
    args = argops.readargs_processed(args_in, config)

    image_directory=args.input_directory
    output_directory=os.path.join(image_directory, "outputs")

    data, elements, dims = processops.compile(image_directory)

    print(f"-----{elements[10]} tracker: {np.max(data[:,10])}")
    categories, classavg, embedding, clusttimes = clustering.run(data, image_directory)
    print(f"-----{elements[10]} tracker: {np.max(data[:,10])}")

    vis.plot_clusters(categories, classavg, embedding, dims)

    for i in range(len(elements)):
        print(f"{elements[i]}, max: {np.max(data[:,i]):.2f}, 98: {np.quantile(data[:,i],0.98):.2f}, avg: {np.average(data[:,i]):.2f}")


if __name__ == '__main__':
    entry_raw()      

    sys.exit()