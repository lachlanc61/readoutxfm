import sys
import os
import numpy as np

import logging
from logging.handlers import TimedRotatingFileHandler

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import xfmkit.utils as utils
import xfmkit.argops as argops
import xfmkit.rgbspectrum as rgbspectrum
import xfmkit.clustering as clustering
import xfmkit.visualisations as vis
import xfmkit.dtops as dtops
import xfmkit.parser as parser
import xfmkit.diagops as diagops
import xfmkit.config as configuration

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
PACKAGE_CONFIG='xfmkit/config.yaml'

#-----------------------------------
#INITIALISE
#-----------------------------------

def logging_setup():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    log_file = configuration.get('logging', 'log_file', default = "/home/lachlan/log/xfmkit.log")

    filehandler = TimedRotatingFileHandler(log_file, when='midnight',backupCount=7)
    filehandler.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    filehandler.setFormatter(formatter)
    
    logger.addHandler(filehandler)

    return logger


def entry_raw():
    """
    entrypoint wrapper getting args from sys
    """
    args_in = sys.argv[1:]  #NB: exclude 0 == script name

    logger = logging_setup()

    read_raw(args_in)



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

        #if using log file
        if args.log_file is not None:
            realtime, livetime, triggers, events, icr, ocr, dt_evt, dt_rt = diagops.dtfromdiag(dirs.logf)

        #if data is present
        if (np.max(pixelseries.data) > 0) and pixelseries.parsed == True:
            print("--------------")
            print("GENERATING PLOTS")
            dtops.dtplots(config, dirs.plots, pixelseries.dt, pixelseries.sum, pixelseries.dtmod, xfmap.xres, xfmap.yres, pixelseries.ndet, args.index_only)

            pixelseries.rgbarray, pixelseries.rvals, pixelseries.gvals, pixelseries.bvals \
                = rgbspectrum.calccolours(config, pixelseries, xfmap, pixelseries.flattened, dirs)       #flattened / corrected
            print("--------------")
            print("PLOTTING COMPLETE")
        dt_avg = dtops.dt_stats(pixelseries.dt)
     
    else:
        pixelseries.rgbarray = None
    #perform clustering
    if args.classify_spectra:
        pixelseries.categories, embedding = clustering.run( pixelseries.flattened, dirs.embeddings, force_embed=args.force, force_clust=args.force, overwrite=config['OVERWRITE_EXPORTS'] )
        
        pixelseries.classavg = clustering.get_classavg( pixelseries.flattened, pixelseries.categories, dirs.embeddings, force=args.force, overwrite=config['OVERWRITE_EXPORTS'])

        palette = vis.plot_clusters(pixelseries.categories, pixelseries.classavg, embedding, pixelseries.dimensions)
    else:
        pixelseries.categories = None
        pixelseries.classavg = None

    print("Processing complete")

    return pixelseries, xfmap, #dt_log

if __name__ == '__main__':
    entry_raw()      

    sys.exit()