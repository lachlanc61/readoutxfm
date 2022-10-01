#-----------------------------------
#CONSTANTS/FLAGS
#-----------------------------------
#global variables
FTYPE=".GeoPIXE"    #valid: ".GeoPIXE"

PXHEADERLEN=16  #pixel header size
PXFLAG="DP"
NCHAN=4096
ESTEP=0.01
CHARENCODE = 'utf-8'

DOCOLOURS=True  #run colourmap1
DOCLUST=True    #run clustering
SEPSUMSPEC=True #
SAVEPXSPEC=True #save pixel spectra
DOBG=False      #apply background fitting
LOWBGADJUST=True    #tweak background for low signal data
SHORTRUN=False  #stop after first X% of pixels


CMAP='Set1' #default colourmap for clusters
MAPX=256    #default map x dim
MAPY=126    #default map y dim

#debug flags
DEBUG=False     #debug flag (pixels)
DEBUG2=False    #second-level debug flag (channels)

#recalc flags
FORCEPARSE=True     #always parse datafile
FORCERED=True       #always recalc dimensionality reduction
FORCEKMEANS=True    #always recalc kmeans 

#-----------------------------------
#VARIABLES
#-----------------------------------

#workdir and inputfile
wdirname='data'     #working directory relative to script
odirname='out'      #output directory relative to script

#infile = "geo_nfpy11.GeoPIXE"
#infile = "geo_ln_chle.GeoPIXE"
#infile = "geo_dwb12-2.GeoPIXE"
infile = "geo2.GeoPIXE"    #assign input file
outfile="pxspec"

#instrument config
detid="A"   #detector ID - not needed for single detector maps

shortpct=10     #% of lines to run in short config

nclust=10       #no of clusters

#figure params (currently not used)
figx=20         #cm width of figure
figy=10         #cm height of figure
smallfont = 8   #default small font
medfont = 10    #default medium font
lgfont = 12     #default large font
lwidth = 1      #default linewidth
bwidth = 1      #default border width