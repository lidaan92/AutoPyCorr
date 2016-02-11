import matplotlib.pyplot as plt
import matplotlib.colors
import numpy as np
from scipy.interpolate import RectBivariateSpline as RBS
import cv2
import gdal
import gdalconst as gdc  # constants for gdal - e.g. GA_ReadOnly, GA_Update ( http://www.gdal.org )
import atexit 
import os
import sys
from time import clock
import datetime as dt
import progressbar as pb
import argparse
import subprocess as sp  # use sp for running gdal commands for 4326 reprojection, kmlsuperoverlay production, modifying kmz to add colorbar
import xml.etree.ElementTree as ET   # us ET for modifying the xml of the kmz to add colorbar
import osr

class GeoImg:
	"""geocoded image input and info
		a=GeoImg(in_file_name,indir='.')
			a.img will contain image
			a.parameter etc..."""
	def __init__(self, in_filename,in_dir='.',datestr=None,datefmt='%m/%d/%y'):
		self.filename = in_filename
		self.in_dir_path = in_dir  #in_dir can be relative...
		self.in_dir_abs_path=os.path.abspath(in_dir)  # get absolute path for later ref if needed
		self.gd=gdal.Open(self.in_dir_path + os.path.sep + self.filename)
		self.srs=osr.SpatialReference(wkt=self.gd.GetProjection())
		self.gt=self.gd.GetGeoTransform()
		self.proj=self.gd.GetProjection()
		self.intype=self.gd.GetDriver().ShortName
		self.min_x=self.gt[0]
		self.max_x=self.gt[0]+self.gd.RasterXSize*self.gt[1]
		self.min_y=self.gt[3]+self.gt[5]*self.gd.RasterYSize
		self.max_y=self.gt[3]
		self.pix_x_m=self.gt[1]
		self.pix_y_m=self.gt[5]
		self.num_pix_x=self.gd.RasterXSize
		self.num_pix_y=self.gd.RasterYSize
		self.XYtfm=np.array([self.min_x,self.max_y,self.pix_x_m,self.pix_y_m]).astype('float')
		if (datestr is not None):
			self.imagedatetime=dt.datetime.strptime(datestr,datefmt)
		elif (self.filename[0]=='L'):	# looks landsat like - try parsing the date from filename (contains day of year)
			self.sensor=self.filename[0:3]
			self.path=int(self.filename[3:6])
			self.row=int(self.filename[6:9])
			self.year=int(self.filename[9:13])
			self.doy=int(self.filename[13:16])
			self.imagedatetime=dt.date.fromordinal(dt.date(self.year-1,12,31).toordinal()+self.doy)
		else:
			self.imagedatetime=None  # need to throw error in this case...or get it from metadata
		self.img=self.gd.ReadAsArray().astype(np.float32)   # works for L8 and earlier - and openCV correlation routine needs float or byte so just use float...
# 		self.img=self.gd.ReadAsArray().astype(np.uint8)		# L7 and earlier - doesn't work with plt.imshow...
		self.img_ov2=self.img[0::2,0::2]
		self.img_ov10=self.img[0::10,0::10]
		self.srs=osr.SpatialReference(wkt=self.gd.GetProjection())
	def imageij2XY(self,ai,aj,outx=None,outy=None):
		it = np.nditer([ai,aj,outx,outy],
						flags = ['external_loop', 'buffered'],
						op_flags = [['readonly'],['readonly'],
									['writeonly', 'allocate', 'no_broadcast'],
									['writeonly', 'allocate', 'no_broadcast']])
		for ii,jj,ox,oy in it:
			ox[...]=(self.XYtfm[0]+((ii+0.5)*self.XYtfm[2]));
			oy[...]=(self.XYtfm[1]+((jj+0.5)*self.XYtfm[3]));
		return np.array(it.operands[2:4])
	def XY2imageij(self,ax,ay,outi=None,outj=None):
		it = np.nditer([ax,ay,outi,outj],
						flags = ['external_loop', 'buffered'],
						op_flags = [['readonly'],['readonly'],
									['writeonly', 'allocate', 'no_broadcast'],
									['writeonly', 'allocate', 'no_broadcast']])
		for xx,yy,oi,oj in it:
			oi[...]=((xx-self.XYtfm[0])/self.XYtfm[2])-0.5;  # if python arrays started at 1, + 0.5
			oj[...]=((yy-self.XYtfm[1])/self.XYtfm[3])-0.5;  # " " " " "
		return np.array(it.operands[2:4])

def secondsToStr(t):
    return "%d:%02d:%02d.%03d" % \
        reduce(lambda ll,b : divmod(ll[0],b) + ll[1:],
            [(t*1000,),1000,60,60])
            
t_line = "="*40
def t_log(s, elapsed=None):
    print t_line
    print secondsToStr(clock()), '-', s
    if elapsed:
        print "Elapsed time: %s" % elapsed
    print t_line
    print
    
def endlog():
    end = clock()
    elapsed = end-start
    t_log("End Program", secondsToStr(elapsed))
    
def timelog():
    end = clock()
    elapsed = end-start
    t_log("time elapsed: ", secondsToStr(elapsed))
    
def now():
    return secondsToStr(clock())
    
# Note these "XY" routines are actually any projection's cartesian coordinates to np.array indicies
# def XY2imageij(projXY,XYtfm):
# 	image_ij=np.zeros(2)
# 	image_ij[0]=((projXY[0]-XYtfm[0])/XYtfm[2])-0.5;  # if python started at 1, + 0.5
# 	image_ij[1]=((projXY[1]-XYtfm[1])/XYtfm[3])-0.5;  # if python started at 1, + 0.5
# 	return image_ij
# 	
# def imageij2XY(ij,XYtfm):
# 	projXY=np.zeros(2)
# 	projXY[0]=XYtfm[0]+((ij[0]+0.5)*XYtfm[2]);
# 	projXY[1]=XYtfm[1]+((ij[1]+0.5)*XYtfm[3]);
# 	return projXY
# 
	
# set up command line arguments
parser = argparse.ArgumentParser( \
    description="""uses image to image correlation to detect offsets in surface features; 
    				produces map of offsets in units of pixels and/or velocity in m/day or m/year""",
    epilog='>>  <<',
    formatter_class=argparse.RawDescriptionHelpFormatter)

parser.add_argument('-imgdir', 
                    action='store', 
                    type=str, 
                    default='.', 
                    help='single source dir for both images [.]')
parser.add_argument('-img1dir', 
                    action='store', 
                    type=str, 
                    default='.', 
                    help='source dir for image 1 [.]')
parser.add_argument('-img2dir', 
                    action='store', 
                    type=str, 
                    default='.', 
                    help='source dir for image 2 [.]')
parser.add_argument('-img1datestr', 
                    action='store', 
                    type=str, 
                    help='date string for image 1 [None - set from L8 filename]')
parser.add_argument('-img2datestr', 
                    action='store', 
                    type=str, 
                    help='date string for image 2 [None - set from L8 filename]')
parser.add_argument('-datestrfmt', 
                    action='store', 
                    type=str,
                    default='%m/%d/%y',  
                    help='date string format for img1datestr and img2datestr [None - set from L8 filename]')                    
parser.add_argument('img1_name', 
                    action='store', 
                    type=str, 
                    help='image 1 filename')
parser.add_argument('img2_name', 
                    action='store', 
                    type=str, 
                    help='image 2 filename')
parser.add_argument('-out_name_base', 
                    action='store', 
                    type=str,
                    default='temp_out', 
                    help='output file name base [temp_out]')
parser.add_argument('-bbox', 
                    action='store', 
                    type=float, 
                    metavar=('min_x','min_y','max_x','max_y'), 
                    nargs=4, 
                    help='bbox for feature tracking area in projection m - minx miny maxx maxy - defaults to entire common area between images')
parser.add_argument('-plotvmin', 
                    action='store', 
                    type=float, 
                    default=0, 
                    help='min vel for colormap [0]')
parser.add_argument('-plotvmax', 
                    action='store', 
                    type=float, 
                    default=10, 
                    help='max vel for colormap [10]')
parser.add_argument('-plot_2_mult', 
                    action='store', 
                    type=float, 
                    default=0.2, 
                    help='plot_2_mult (vmax for second plot will be plot_2_mult * plotvmax - to show detail on low end... [0.2]')
# parser.add_argument('-trackvmax', 
#                     action='store', 
#                     type=float, 
#                     help='max vel that will be tracked [if not specified, defaults to plotvmax - 10]')
parser.add_argument('-half_source_chip', 
                    action='store',
                    default=10,  
                    type=int, 
                    help='half size of source (small) chip [10]')
parser.add_argument('-half_target_chip', 
                    action='store',
                    default=40,  
                    type=int, 
                    help='half size of target (large or search) chip [40]')
parser.add_argument('-inc', 
                    action='store', 
                    type=int, 
                    default=20, 
                    help='inc(rement) or chip center grid spacing in pixels (must be even) [20]')
parser.add_argument('-gs_min', 
                    action='store', 
                    type=int, 
                    default=0, 
                    help='grayscale min val [0]')
parser.add_argument('-gs_max', 
                    action='store', 
                    type=int, 
                    default=None, # if not specified, matplotlib will determine value from data
                    help='grayscale max val for background image [determined by matplotlib imshow]')
parser.add_argument('-dcam', 
                    action='store', 
                    type=float, 
                    default=0.05, 
                    help='min difference between corr peaks 1 and 2 for mask [0.05]')
parser.add_argument('-cam', 
                    action='store', 
                    type=float, 
                    default=0.1, 
                    help='corr peak max value for dcam & cam mask [0.1]')
parser.add_argument('-cam1', 
                    action='store', 
                    type=float, 
                    default=0.2, 
                    help='corr peak value max for or mask [0.2]')
parser.add_argument('-alphaval', 
                    action='store', 
                    type=float, 
                    default=0.5, 
                    help='alpha (transparency) value for overlay (0 - 1, 1 opaque) [0.5]')
parser.add_argument('-of', 
                    action='store', 
                    type=str, 
                    default='GTiff', 
                    help='output format string (GDAL short format name - presently only GTiff and ENVI supported) [GTiff]')
# the rest of the parameters are flags - if raised, set to true, otherwise false
parser.add_argument('-v', 
                    action='store_true',  
                    default=False, 
                    help='verbose - extra diagnostic and image info [False if not raised]')
parser.add_argument('-vf', 
                    action='store_true',
                    default=False, 
                    help='verbose figures - extra diagnostic figures (correlation etc) [False if not raised]')
parser.add_argument('-mpy', 
                    action='store_true',
                    default=False, 
                    help='meters per year - [meters per day if not raised]')
parser.add_argument('-kmz', 
                    action='store_true',
                    default=False, 
                    help='output kmz with colorbar in addition to GTiff - [no kmz produced if not raised]')
parser.add_argument('-log10', 
                    action='store_true',
                    default=False, 
                    help='output second rgba color image that is log10(v) (and second kmz with colorbar in addition to GTiff if requested) - [only linear color image produced]')
parser.add_argument('-no_gtif', 
                    action='store_true',
                    default=False, 
                    help='do not output default GTiff - [geoTiff always produced if not raised]')
parser.add_argument('-only_vel_colormap', 
                    action='store_true',
                    default=False, 
                    help='only output colormapped GTiff of speed (no vx,vy,correlations...) - [full output suite of vx,vy,correlation,etc.]')
parser.add_argument('-nlf', 
                    action='store_true',
                    default=False, 
                    help='do not output log file that contains command line etc - [output command line in out_name_base_summary.txt]')
parser.add_argument('-npb', 
                    action='store_true',
                    default=False, 
                    help='suppress progress bar in terminal output - [progress bar used]')
parser.add_argument('-sf',
                    action='store_true',
                    default=False,
                    help='output and save diagnostic figures to .png [False if not raised]')
parser.add_argument('-pixfigs',
                    action='store_true',
                    default=False,
                    help='show pix offsets [False if not raised]')
args = parser.parse_args()

if(args.v):
	print '#', args

out_name_base=args.out_name_base

# set up source directories
if(args.imgdir != "."): # single source directory specified
	if((args.img1dir != ".") | (args.img2dir != ".")):
		sys.exit('Error: -imgdir (specifying a single source directory for both images) cannot be used with -img1dir or -img2dir')
	else:
		image1dir=args.imgdir
		image2dir=args.imgdir
else:    # -imgdir not used - set directories to img1dir and img2dir
	image1dir=args.img1dir
	image2dir=args.img2dir
	
if not(args.nlf):
	outsf=open(out_name_base + "_log.txt",'w')
	outsf.write('# log from %s\n'% sys.argv[0])
	outsf.write(" ".join(sys.argv) + "\n")


start = clock()
atexit.register(endlog)
t_log("Start Program")

# check parameter flags that are not compatible together, inform, and exit
if (args.no_gtif & args.kmz):
	sys.exit('Error: -no_gtif cannot be used with -kmz (kmz needs gtif for reprojection)')

# read images and parse dates - note default is to parse date from L8 image names if possible
img1=GeoImg(args.img1_name,in_dir=image1dir,datestr=args.img1datestr,datefmt=args.datestrfmt)
if '_hp' in args.img1_name:
	img1_lp=GeoImg(args.img1_name.replace('hp','lp'),in_dir=image1dir,datestr=args.img1datestr,datefmt=args.datestrfmt)
	hp_images=True
	print "working with hp images"
else:
	hp_images=False
	print "NOT working with hp images"
t_log("read image 1")

if (args.v):
	dataset=img1.gd
	print 'Image 1: %s'%img1.filename
	print 'Driver: ', dataset.GetDriver().ShortName,'/', \
			  dataset.GetDriver().LongName
	print 'Size is ',dataset.RasterXSize,'x',dataset.RasterYSize, \
			  'x',dataset.RasterCount
	print 'Projection is ',dataset.GetProjection()
	geotransform = dataset.GetGeoTransform()
	if not geotransform is None:
		print 'Origin = (',geotransform[0], ',',geotransform[3],')'
		print 'Pixel Size = (',geotransform[1], ',',geotransform[5],')'
		band = dataset.GetRasterBand(1)
	print 'Band Type=',gdal.GetDataTypeName(band.DataType)
	bmin = band.GetMinimum()
	bmax = band.GetMaximum()
	if bmin is None or bmax is None:
		(bmin,bmax) = band.ComputeRasterMinMax(1)
		print 'Min=%.3f, Max=%.3f' % (bmin,bmax)
	if band.GetOverviewCount() > 0:
		print 'Band has ', band.GetOverviewCount(), ' overviews.'
	if not band.GetRasterColorTable() is None:
		print 'Band has a color table with ', \
		band.GetRasterColorTable().GetCount(), ' entries.'
	print '\n'

img2=GeoImg(args.img2_name,in_dir=image2dir,datestr=args.img2datestr,datefmt=args.datestrfmt)
t_log("read image 2")
if (args.v):
	dataset=img2.gd
	print 'Image 2: %s'%img2.filename
	print 'Driver: ', dataset.GetDriver().ShortName,'/', \
			  dataset.GetDriver().LongName
	print 'Size is ',dataset.RasterXSize,'x',dataset.RasterYSize, \
			  'x',dataset.RasterCount
	print 'Projection is ',dataset.GetProjection()
	geotransform = dataset.GetGeoTransform()
	if not geotransform is None:
		print 'Origin = (',geotransform[0], ',',geotransform[3],')'
		print 'Pixel Size = (',geotransform[1], ',',geotransform[5],')'
		band = dataset.GetRasterBand(1)
	print 'Band Type=',gdal.GetDataTypeName(band.DataType)
	bmin = band.GetMinimum()
	bmax = band.GetMaximum()
	if bmin is None or bmax is None:
		(bmin,bmax) = band.ComputeRasterMinMax(1)
		print 'Min=%.3f, Max=%.3f' % (bmin,bmax)
	if band.GetOverviewCount() > 0:
		print 'Band has ', band.GetOverviewCount(), ' overviews.'
	if not band.GetRasterColorTable() is None:
		print 'Band has a color table with ', \
		band.GetRasterColorTable().GetCount(), ' entries.'
	print '\n'

del_t=img2.imagedatetime - img1.imagedatetime
del_t_days=del_t.total_seconds()/(24.0*3600.0)
del_t_years=del_t_days/(365.25)

# switch from m/d to m/yr if -mpy 
if (args.mpy):
	del_t_str='m/yr'
	del_t_val=del_t_years
else:
	del_t_str='m/d'
	del_t_val=del_t_days

print "time separation in days: %f years: %f - using %s"%(del_t_days,del_t_years,del_t_str)
if not(args.nlf):
	outsf.write("time separation in days: %f years: %f - using %s\n"%(del_t_days,del_t_years,del_t_str))


# offset pixels to subtract from ij_1 to get ij_2 coordinates (how far the two image arrays are offset based on their geolocation)
offset_2_1=img1.XY2imageij(*img2.imageij2XY(*[0,0])) 

# either work in specified bounding box, or find largest box of common pixels between the two images and use that
if (args.bbox is None):
	# 	find largest common x,y using original XY (geo cartesian coordinates) box between images
	# image coordinates are for bounding box (outer edge of pixels)
	com_max_x=np.min([img1.max_x, img2.max_x])
	com_max_y=np.min([img1.max_y, img2.max_y])
	com_min_x=np.max([img1.min_x, img2.min_x])
	com_min_y=np.max([img1.min_y, img2.min_y])
else: # read area from command line specified bounding box (still XY etc.)
	com_max_x=args.bbox[2]
	com_max_y=args.bbox[3]
	com_min_x=args.bbox[0]
	com_min_y=args.bbox[1]

bbox=[com_min_x, com_min_y, com_max_x, com_max_y]
# plotvmin and plotvmax - speeds for colorbar in plots... - ?maybe set to None for autoscaling?
plotvmin=args.plotvmin
plotvmax=args.plotvmax
plot_2_mult=args.plot_2_mult # vmax for second plot will be plot_2_mult * plotvmax - to show detail on low end...

half_source_chip=args.half_source_chip # must be < half_target_chip
half_target_chip=args.half_target_chip  
inc=args.inc
if ((inc/2.0) != int(inc/2.0)):
	print '-inc must be an even integer number of pixels for output geolocation to register properly; currently inc=%f'%(inc)
	sys.exit(-1)
	
# if ((np.remainder(half_target_chip,inc) != 0) | (inc > half_target_chip)):
# 	print 'half_target must be positive integer multiple of inc for buffer and geolocation of output arrays'
# 	sys.exit(-1)

subpixel_gridstep=0.1
mgx,mgy=np.meshgrid(np.arange(-1,1.0 + (0.1*subpixel_gridstep),subpixel_gridstep),np.arange(-1,1.0 + (0.1*subpixel_gridstep),subpixel_gridstep),indexing='xy')  # sub-pixel mesh
rbs_halfsize=3 # size of peak area used for spline for subpixel peak loc
rbs_order=4    # polynomial order for subpixel rbs interpolation of peak location


# use this box to find overlap range in i and j (array coordinates) for both images
com_ul_i_j_img1=img1.XY2imageij(*(com_min_x,com_max_y))+0.5
com_ul_i_j_img2=img2.XY2imageij(*(com_min_x,com_max_y))+0.5
com_lr_i_j_img1=img1.XY2imageij(*(com_max_x,com_min_y))-0.5
com_lr_i_j_img2=img2.XY2imageij(*(com_max_x,com_min_y))-0.5


# image pixels in bbox for img1 as a slice are img1.img[c1_minj:c1_maxjp1,c1_mini:c1_maxip1]
# remember (Mark) that a python slice [3:5] returns elements 3 and 4, indexed from 0

c1_minj=com_ul_i_j_img1[1]
c1_maxjp1=(com_lr_i_j_img1[1]+1) # may be one more than the max index, for use in slices
c1_mini=com_ul_i_j_img1[0]
c1_maxip1=(com_lr_i_j_img1[0]+1) # same

c2_minj=com_ul_i_j_img2[1]
c2_maxjp1=(com_lr_i_j_img2[1]+1) # same
c2_mini=com_ul_i_j_img2[0]
c2_maxip1=(com_lr_i_j_img2[0]+1) # same

com_num_pix_i=c1_maxip1-c1_mini  # number of pixels per line in common (overlap) area
com_num_pix_j=c1_maxjp1-c1_minj  # number of lines in common (overlap) area 

if(args.v):
	print 'numpix %f numlines %f in box'%(com_num_pix_i,com_num_pix_j)
	print 'ul X %f Y %f of box'%(com_min_x,com_max_y)
	print 'ul image1 i %f j%f  image2 i %f j%f'%(c1_mini,c1_minj,c2_mini,c2_minj)
	print 'lr X %f Y %f of box'%(com_max_x,com_min_y)
	print 'lr image1 i %f j%f  image2 i %f j%f'%(c1_maxip1,c1_maxjp1,c2_maxip1,c2_maxjp1)

# fig=plt.figure()
# ax1=plt.subplot(121,axisbg=(0.1,0.15,0.15))
# ax1_img=plt.imshow(img1.img_ov10,interpolation='nearest',cmap='gray',extent=[img1.min_x,img1.max_x,img1.min_y,img1.max_y])
# ax2=plt.subplot(122,axisbg=(0.1,0.15,0.15))
# ax2_img=plt.imshow(img2.img_ov10,interpolation='nearest',cmap='gray',extent=[img2.min_x,img2.max_x,img2.min_y,img2.max_y])
# plt.ion()
# plt.show()

if (args.vf):
	# show bounding box on image 1
	ovdec=10
	bb_x=[bbox[0],bbox[0],bbox[2],bbox[2],bbox[0]]
	bb_y=[bbox[1],bbox[3],bbox[3],bbox[1],bbox[1]]
	fig=plt.figure()
	ax1=plt.subplot(111,axisbg=(0.1,0.15,0.15))
	ax1_img=plt.imshow(img1.img_ov10,interpolation='nearest',cmap='gray',extent=[img1.min_x,img1.max_x,img1.min_y,img1.max_y])
	plt.title('bounding box plotted on image1 from date %s'%(img1.imagedatetime.isoformat()))
	plt.plot(bb_x,bb_y,'r')
	plt.ion()
	plt.show()
	# now common area of both images
	ovdec=10.0
	fig=plt.figure()
	ax1=plt.subplot(121,axisbg=(0.1,0.15,0.15))
	ax1_img=plt.imshow(img1.img_ov10[np.floor(c1_minj/ovdec):np.floor(c1_maxjp1/ovdec),np.floor(c1_mini/ovdec):np.floor(c1_maxip1/ovdec)],
				interpolation='nearest',cmap='gray',vmin=args.gs_min,vmax=args.gs_max,extent=[com_min_x,com_max_x,com_min_y,com_max_y])
	ax2=plt.subplot(122,axisbg=(0.1,0.15,0.15))
	ax2_img=plt.imshow(img2.img_ov10[np.floor(c2_minj/ovdec):np.floor(c2_maxjp1/ovdec),np.floor(c2_mini/ovdec):np.floor(c2_maxip1/ovdec)],
				interpolation='nearest',cmap='gray',vmin=args.gs_min,vmax=args.gs_max,extent=[com_min_x,com_max_x,com_min_y,com_max_y])
	
	plt.show()
if (args.sf):
        # show bounding box on image 1
	ovdec=10
	bb_x=[bbox[0],bbox[0],bbox[2],bbox[2],bbox[0]]
	bb_y=[bbox[1],bbox[3],bbox[3],bbox[1],bbox[1]]
	fig=plt.figure()
	ax1=plt.subplot(111,axisbg=(0.1,0.15,0.15))
	ax1_img=plt.imshow(img1.img_ov10,interpolation='nearest',cmap='gray',extent=[img1.min_x,img1.max_x,img1.min_y,img1.max_y])
	plt.title('bounding box plotted on image1 from date %s'%(img1.imagedatetime.isoformat()))
	plt.plot(bb_x,bb_y,'r')
	plt.ion()
	plt.show()
	plt.savefig('fig_1_'+str(img1.filename)+'_'+str(img2.filename)+'.png')
	
	# now common area of both images
	ovdec=10.0
	fig=plt.figure()
	ax1=plt.subplot(121,axisbg=(0.1,0.15,0.15))
	ax1_img=plt.imshow(img1.img_ov10[np.floor(c1_minj/ovdec):np.floor(c1_maxjp1/ovdec),np.floor(c1_mini/ovdec):np.floor(c1_maxip1/ovdec)],
				interpolation='nearest',cmap='gray',vmin=args.gs_min,vmax=args.gs_max,extent=[com_min_x,com_max_x,com_min_y,com_max_y])
	ax2=plt.subplot(122,axisbg=(0.1,0.15,0.15))
	ax2_img=plt.imshow(img2.img_ov10[np.floor(c2_minj/ovdec):np.floor(c2_maxjp1/ovdec),np.floor(c2_mini/ovdec):np.floor(c2_maxip1/ovdec)],
				interpolation='nearest',cmap='gray',vmin=args.gs_min,vmax=args.gs_max,extent=[com_min_x,com_max_x,com_min_y,com_max_y])

	plt.show()
        plt.savefig('fig_2_'+str(img1.filename)+'_'+str(img2.filename)+'.png')



# r_i_1=range(int(c1_mini),int((c1_maxip1-1)),inc) # range over common area
# r_j_1=range(int(c1_minj),int((c1_maxjp1-1)),inc)
# 
# r_i_2=range(int(c2_mini),int((c2_maxip1-1)),inc) # range over common area
# r_j_2=range(int(c2_minj),int((c2_maxjp1-1)),inc)

# number of chip_grid positions is integer of ((num_pix_i/inc) - 0.5), same for j
half_inc_rim=int(inc/2.0)  # inc was checked to be even (above) so int is redundant
# num_grid_i=int((com_num_pix_i - inc)/inc) + 1		
# num_grid_j=int((com_num_pix_j - inc)/inc) + 1
num_grid_i=int(com_num_pix_i/inc)		
num_grid_j=int(com_num_pix_j/inc)

ul_i_1_chip_grid=int(c1_mini + half_inc_rim)
ul_j_1_chip_grid=int(c1_minj + half_inc_rim)
lr_i_1_chip_grid=int(c1_mini + half_inc_rim + ((num_grid_i-1) * inc))
lr_j_1_chip_grid=int(c1_minj + half_inc_rim + ((num_grid_j-1) * inc))

ul_i_2_chip_grid=int(c2_mini + half_inc_rim)
ul_j_2_chip_grid=int(c2_minj + half_inc_rim)
lr_i_2_chip_grid=int(c2_mini + half_inc_rim + ((num_grid_i-1) * inc))
lr_j_2_chip_grid=int(c2_minj + half_inc_rim + ((num_grid_j-1) * inc))

# ul_i_2_chip_grid=int(c2_mini + half_target_chip)
# ul_j_2_chip_grid=int(c2_minj + half_target_chip)
# lr_i_2_chip_grid=int(c2_mini + half_target_chip + (num_grid_i * inc))
# lr_j_2_chip_grid=int(c2_minj + half_target_chip + (num_grid_j * inc))

r_i_1=range(ul_i_1_chip_grid,lr_i_1_chip_grid+1,inc) # range over common area
r_j_1=range(ul_j_1_chip_grid,lr_j_1_chip_grid+1,inc)

r_i_2=range(ul_i_2_chip_grid,lr_i_2_chip_grid+1,inc) # range over common area
r_j_2=range(ul_j_2_chip_grid,lr_j_2_chip_grid+1,inc)

# find required size of buffer around chip center positons so that target chip centered there remains in bbox
min_ind_i_1=np.min(np.nonzero(np.array(r_i_1)>half_target_chip))# this is width of the rim of zeros on left or top in the correlation arrays
min_ind_j_1=np.min(np.nonzero(np.array(r_j_1)>half_target_chip))# this is width of the rim of zeros on left or top in the correlation arrays
min_ind_i_2=np.min(np.nonzero(np.array(r_i_2)>half_target_chip))# this is width of the rim of zeros on left or top in the correlation arrays
min_ind_j_2=np.min(np.nonzero(np.array(r_j_2)>half_target_chip))# this is width of the rim of zeros on left or top in the correlation arrays
min_ind_i = np.max([min_ind_i_1,min_ind_i_2])
min_ind_j = np.max([min_ind_j_1,min_ind_j_2])
#
max_ind_i_1=np.max(np.nonzero(half_target_chip<=(com_num_pix_i - np.array(r_i_1))))  # maximum allowed i index (buffer right edge of grid to accomodate target chip size)
max_ind_j_1=np.max(np.nonzero(half_target_chip<=(com_num_pix_j - np.array(r_j_1))))  # maximum allowed i index (buffer bottom edge of grid to accomodate target chip size)
max_ind_i_2=np.max(np.nonzero(half_target_chip<=(com_num_pix_i - np.array(r_i_2))))  # maximum allowed i index (buffer right edge of grid to accomodate target chip size)
max_ind_j_2=np.max(np.nonzero(half_target_chip<=(com_num_pix_j - np.array(r_j_2))))  # maximum allowed i index (buffer bottom edge of grid to accomodate target chip size)
max_ind_i=np.min([max_ind_i_1,max_ind_i_2])  # maximum allowed i index (buffer right edge of grid to accomodate target chip size)
max_ind_j=np.min([max_ind_j_1,max_ind_j_2])  # maximum allowed i index (buffer bottom edge of grid to accomodate target chip size)

peak_block_halfsize=3 # this is the size of the area zeroed out before looking for the second highest peak
cent_loc=half_target_chip-half_source_chip  # Note cent_loc is array i,j of chip center because indexing is zero based

# the -0.5 in what follows shifts from the ij of the element to it's upper left corner (chip center)
r_grid=np.meshgrid(np.array(r_i_1)-0.5,np.array(r_j_1)-0.5,indexing='xy')
chip_center_grid_xy=img1.imageij2XY(*r_grid)
# note output_array_ul_corner will be the same as [com_min_x, com_max_y] but is derived here just to check coordinates
output_array_ul_corner=chip_center_grid_xy[:,0,0]-((inc/2.0)*img1.pix_x_m,(inc/2.0)*img1.pix_y_m)
output_array_pix_x_m=inc*img1.pix_x_m
output_array_pix_y_m=inc*img1.pix_y_m


# allocate arrays for results 
#  corr_arr				- correlation surface
#  del_corr_arr 		- delta correlation surface (peak1_corr - peak2_corr in correlation (-1 - 1) units),
#  offset_dist_ij_arr	- match offset distance for chip center in ij (array index) units
#  sp_dist_i			- sub_pixel offset from peak fit - add to integer pixel offset from correlation (not necessary to save this array - for diagnostics, etc.)
#  sp_dist_j			- sub_pixel offset from peak fit - add to integer pixel offset from correlation (not necessary to save this array - for diagnostics, etc.)
#  del_i				- full offset in i (correlation peak offset + subpixel offset, except when peak too close to an edge of correlation surface...then no sub-pixel
#  del_j				- full offset in j (correlation peak offset + subpixel offset, except when peak too close to an edge of correlation surface...then no sub-pixel
corr_arr=np.zeros((r_j_2.__len__(),r_i_2.__len__()), dtype=np.float32)
del_corr_arr=np.zeros((r_j_2.__len__(),r_i_2.__len__()), dtype=np.float32)
offset_dist_ij_arr=np.zeros((r_j_2.__len__(),r_i_2.__len__()), dtype=np.float32)
sp_dist_i=np.zeros((r_j_2.__len__(),r_i_2.__len__()), dtype=np.float32)
sp_dist_j=np.zeros((r_j_2.__len__(),r_i_2.__len__()), dtype=np.float32)
d2idx2=np.zeros((r_j_2.__len__(),r_i_2.__len__()), dtype=np.float32)
d2jdx2=np.zeros((r_j_2.__len__(),r_i_2.__len__()), dtype=np.float32)
d2dx2_mean=np.zeros((r_j_2.__len__(),r_i_2.__len__()), dtype=np.float32)
del_i=np.zeros((r_j_2.__len__(),r_i_2.__len__()), dtype=np.float32)
del_j=np.zeros((r_j_2.__len__(),r_i_2.__len__()), dtype=np.float32)

if not(args.npb):
	widgets = ['Correlating: ', pb.Percentage(), ' ', pb.Bar(marker=pb.RotatingMarker()),' ', pb.ETA()]
	pbar = pb.ProgressBar(widgets=widgets, maxval=r_i_2.__len__()).start()
numcorr=0
# for i in range(buffer_size_l_t,r_i_2.__len__()-buffer_size_r):
# 	for j in range(buffer_size_l_t,r_j_2.__len__()-buffer_size_b):
for i in range(min_ind_i,max_ind_i+1):
	for j in range(min_ind_j,max_ind_j+1):
		chip_src=img1.img[(r_j_1[j]-half_source_chip):(r_j_1[j]+half_source_chip),(r_i_1[i]-half_source_chip):(r_i_1[i]+half_source_chip)]
		minsrc=np.min(chip_src)
		if hp_images:  # if working with hp images (mean 0) then check for mask in lp image...
			minsrc=np.min(img1_lp.img[(r_j_1[j]-half_source_chip):(r_j_1[j]+half_source_chip),(r_i_1[i]-half_source_chip):(r_i_1[i]+half_source_chip)])
		if(minsrc>0.0):  # there are non-zero pixels, so out of mask (image can't have pixel values less than zero...)
			numcorr+=1
			chip_tar=img2.img[(r_j_2[j]-half_target_chip):(r_j_2[j]+half_target_chip),(r_i_2[i]-half_target_chip):(r_i_2[i]+half_target_chip)]
			resultCv=cv2.matchTemplate(chip_src, chip_tar, cv2.TM_CCOEFF_NORMED)
			mml=cv2.minMaxLoc(resultCv)
			peak1_corr=mml[1]
			peak1_loc=mml[3]
# 			peak1_corr=cv2.minMaxLoc(resultCv)[1]
# 			peak1_loc=cv2.minMaxLoc(resultCv)[3]
			tempres_peak1_zeroed=resultCv.copy()
			tempres_peak1_zeroed[(peak1_loc[1]-peak_block_halfsize):(peak1_loc[1]+peak_block_halfsize+1),(peak1_loc[0]-peak_block_halfsize):(peak1_loc[0]+peak_block_halfsize+1)]=0
			corr_arr[j,i]=peak1_corr
			del_corr_arr[j,i]=peak1_corr - cv2.minMaxLoc(tempres_peak1_zeroed)[1]
			# now if peak is far enough from the edges of the correlation surface, fit locale of peak with a spline and find sub-pixel offset at 1/10th of a pixel level
			if((np.array([n-rbs_halfsize for n in peak1_loc])>=np.array([0,0])).all() & (np.array([(n+rbs_halfsize) for n in peak1_loc ])<np.array(list(resultCv.shape))).all()):
				rbs_p=RBS(range(-rbs_halfsize,rbs_halfsize+1),range(-rbs_halfsize,rbs_halfsize+1),resultCv[(peak1_loc[1]-rbs_halfsize):(peak1_loc[1]+rbs_halfsize+1),(peak1_loc[0]-rbs_halfsize):(peak1_loc[0]+rbs_halfsize+1)],kx=rbs_order,ky=rbs_order)
				rbs_surf=rbs_p.ev(mgx.flatten(),mgy.flatten())
				mml=cv2.minMaxLoc(rbs_surf.reshape(21,21))
				mmi=mml[3][1]
				mmj=mml[3][0]
				sp_deli=mgx[mmj,mmi]
				sp_delj=mgy[mmj,mmi]
				deli=(peak1_loc[0]+sp_deli)-cent_loc
				delj=(peak1_loc[1]+sp_delj)-cent_loc
				if ((mmi!=0) & (mmj!=0) & (mmi!=20) & (mmj!=20)):  # peak not at edge - can calculate second derivatives
					peak_vec_i=rbs_surf.reshape(21,21)[mmi,:]
					peak_vec_j=rbs_surf.reshape(21,21)[:,mmj]
					d2idx2_t=(peak_vec_i[mmj+1]+peak_vec_i[mmj-1]- 2*peak_vec_i[mmj])/(subpixel_gridstep**2.0)
					d2jdx2_t=(peak_vec_j[mmi+1]+peak_vec_j[mmi-1]- 2*peak_vec_j[mmi])/(subpixel_gridstep**2.0)
				else: # subpixel peak at edge of rbs_surf - can't calculate second derivative
					d2idx2_t=999
					d2jdx2_t=999
			else: # peak is too close to an edge of correlation surface, don't do sub-pixel fit.
				sp_deli=0.0
				sp_delj=0.0
				deli=peak1_loc[0]-cent_loc
				delj=peak1_loc[1]-cent_loc
				d2idx2_t=999
				d2jdx2_t=999
# 		offset_dist_ij_arr[j,i]=np.sqrt(np.sum(np.power((cent_loc-peak1_loc[0],cent_loc-peak1_loc[1]),2.0)))
			offset_dist_ij_arr[j,i]=np.sqrt(np.sum(np.power((deli,delj),2.0)))
			del_i[j,i]=deli
			del_j[j,i]=delj
			sp_dist_i[j,i]=sp_deli
			sp_dist_j[j,i]=sp_delj
			d2idx2[j,i]=d2idx2_t
			d2jdx2[j,i]=d2jdx2_t
		else: # all pixels zero in chip_src - mask this one
			corr_arr[j,i]=-2.0
			del_corr_arr[j,i]=-2.0
			offset_dist_ij_arr[j,i]=0.0
			del_i[j,i]=0
			del_j[j,i]=0
			sp_dist_i[j,i]=0
			sp_dist_j[j,i]=0
			d2idx2[j,i]=0
			d2jdx2[j,i]=0
		d2dx2_mean[j,i]=(d2idx2[j,i] + d2jdx2[j,i])/2.0
  	if not(args.npb):
  		pbar.update(i)
if not(args.npb):
	pbar.finish()

t_log('Done with image to image correlation: ' + np.str(numcorr) + ' correlations of ' + np.str(r_i_2.__len__()*r_j_2.__len__()) + ' possible')


if (args.vf):  # include correlation and delcorr figures
	ovdec=10.0
	fig=plt.figure()
	ax=plt.subplot(121,axisbg=(0.1,0.15,0.15))
	ax1_img=plt.imshow(img1.img_ov10[np.floor(c1_minj/ovdec):np.floor(c1_maxjp1/ovdec),np.floor(c1_mini/ovdec):np.floor(c1_maxip1/ovdec)],
				interpolation='nearest',cmap='gray',vmin=args.gs_min,vmax=args.gs_max,extent=[com_min_x,com_max_x,com_min_y,com_max_y])
	# ax_img=plt.imshow(img1.img,interpolation='nearest',cmap='gray',extent=[img1.min_x,img1.max_x,img1.min_y,img1.max_y])
	ax_img1=plt.imshow((offset_dist_ij_arr*img1.pix_x_m)/del_t_val,vmin=plotvmin,vmax=plotvmax,alpha=0.25,interpolation='nearest',
						cmap='jet',extent=[com_min_x,com_max_x,com_min_y,com_max_y])
	plt.colorbar()
	plt.title('vel %s'%(del_t_str))
	ax2=plt.subplot(122,axisbg=(0.1,0.15,0.15))
	ax2_img=plt.imshow(img1.img_ov10[np.floor(c1_minj/ovdec):np.floor(c1_maxjp1/ovdec),np.floor(c1_mini/ovdec):np.floor(c1_maxip1/ovdec)],
				interpolation='nearest',cmap='gray',vmin=args.gs_min,vmax=args.gs_max,extent=[com_min_x,com_max_x,com_min_y,com_max_y])
	# ax_img2=plt.imshow(img2.img,interpolation='nearest',cmap='gray',extent=[img2.min_x,img2.max_x,img2.min_y,img2.max_y])
	ax_img3=plt.imshow(del_corr_arr,alpha=0.25,interpolation='nearest',vmin=0.0,
						cmap='jet',extent=[com_min_x,com_max_x,com_min_y,com_max_y])
	plt.colorbar()
	plt.title('del_corr_arr')
	# # 
	# # 
	fig=plt.figure()
	ax=plt.subplot(121,axisbg=(0.1,0.15,0.15))
	ax1_img=plt.imshow(img1.img_ov10[np.floor(c1_minj/ovdec):np.floor(c1_maxjp1/ovdec),np.floor(c1_mini/ovdec):np.floor(c1_maxip1/ovdec)],
				interpolation='nearest',cmap='gray',vmin=args.gs_min,vmax=args.gs_max,extent=[com_min_x,com_max_x,com_min_y,com_max_y])
	# ax_img=plt.imshow(img1.img,interpolation='nearest',cmap='gray',extent=[img1.min_x,img1.max_x,img1.min_y,img1.max_y])
	ax_img1=plt.imshow((offset_dist_ij_arr*img1.pix_x_m)/del_t_val,vmin=plotvmin,vmax=plotvmax,alpha=0.25,interpolation='nearest',
						cmap='jet',extent=[com_min_x,com_max_x,com_min_y,com_max_y])
	plt.colorbar()
	plt.title('vel %s'%(del_t_str))
	ax2=plt.subplot(122,axisbg=(0.1,0.15,0.15))
	ax2_img=plt.imshow(img1.img_ov10[np.floor(c1_minj/ovdec):np.floor(c1_maxjp1/ovdec),np.floor(c1_mini/ovdec):np.floor(c1_maxip1/ovdec)],
				interpolation='nearest',cmap='gray',vmin=args.gs_min,vmax=args.gs_max,extent=[com_min_x,com_max_x,com_min_y,com_max_y])
	# ax_img2=plt.imshow(img2.img,interpolation='nearest',cmap='gray',extent=[img2.min_x,img2.max_x,img2.min_y,img2.max_y])
	ax_img3=plt.imshow(corr_arr,alpha=0.25,interpolation='nearest',vmin=0.0,
						cmap='jet',extent=[com_min_x,com_max_x,com_min_y,com_max_y])
	plt.colorbar()
	plt.title('corr_arr')

dcam=args.dcam
cam=args.cam
cam1=args.cam1
vv=np.ma.masked_where(((del_corr_arr<dcam)&(corr_arr<cam))|(corr_arr<cam1)|(((offset_dist_ij_arr*img1.pix_x_m)/del_t_val)>plotvmax),((offset_dist_ij_arr*img1.pix_x_m)/del_t_val))
vx=np.ma.masked_where(((del_corr_arr<dcam)&(corr_arr<cam))|(corr_arr<cam1),((del_i*img1.pix_x_m)/del_t_val))
vy=np.ma.masked_where(((del_corr_arr<dcam)&(corr_arr<cam))|(corr_arr<cam1),((del_j*img1.pix_y_m)/del_t_val))


ovdec=10.0

fig=plt.figure()
ax=plt.subplot(111,axisbg=(0.1,0.15,0.15))
ax1_img=plt.imshow(img1.img_ov10[np.floor(c1_minj/ovdec):np.floor(c1_maxjp1/ovdec),np.floor(c1_mini/ovdec):np.floor(c1_maxip1/ovdec)],
                     interpolation='nearest',cmap='gray',vmin=args.gs_min,vmax=args.gs_max,extent=[com_min_x,com_max_x,com_min_y,com_max_y])
ax_img1=plt.imshow(vv,alpha=args.alphaval,interpolation='nearest',vmin=plotvmin,vmax=plotvmax,
                                     cmap='jet',extent=[com_min_x,com_max_x,com_min_y,com_max_y])
plt.title('%s to %s vel in %s'%(args.img1_name,args.img2_name,del_t_str))
plt.colorbar()                    

if (args.sf):  # include correlation and delcorr figures
	ovdec=10.0
	fig=plt.figure()
	ax=plt.subplot(121,axisbg=(0.1,0.15,0.15))
	ax1_img=plt.imshow(img1.img_ov10[np.floor(c1_minj/ovdec):np.floor(c1_maxjp1/ovdec),np.floor(c1_mini/ovdec):np.floor(c1_maxip1/ovdec)],
				interpolation='nearest',cmap='gray',vmin=args.gs_min,vmax=args.gs_max,extent=[com_min_x,com_max_x,com_min_y,com_max_y])
	# ax_img=plt.imshow(img1.img,interpolation='nearest',cmap='gray',extent=[img1.min_x,img1.max_x,img1.min_y,img1.max_y])
	ax_img1=plt.imshow((offset_dist_ij_arr*img1.pix_x_m)/del_t_val,vmin=plotvmin,vmax=plotvmax,alpha=0.25,interpolation='nearest',
						cmap='jet',extent=[com_min_x,com_max_x,com_min_y,com_max_y])
	plt.colorbar()
	plt.title('vel %s'%(del_t_str))           
	ax2=plt.subplot(122,axisbg=(0.1,0.15,0.15))
	ax2_img=plt.imshow(img1.img_ov10[np.floor(c1_minj/ovdec):np.floor(c1_maxjp1/ovdec),np.floor(c1_mini/ovdec):np.floor(c1_maxip1/ovdec)],
				interpolation='nearest',cmap='gray',vmin=args.gs_min,vmax=args.gs_max,extent=[com_min_x,com_max_x,com_min_y,com_max_y])
	# ax_img2=plt.imshow(img2.img,interpolation='nearest',cmap='gray',extent=[img2.min_x,img2.max_x,img2.min_y,img2.max_y])
	ax_img3=plt.imshow(del_corr_arr,alpha=0.25,interpolation='nearest',vmin=0.0,
						cmap='jet',extent=[com_min_x,com_max_x,com_min_y,com_max_y])
	plt.colorbar()
	plt.title('del_corr_arr')
        plt.savefig('fig_3_'+str(img1.filename)+'_'+str(img2.filename)+'.png')            
	# # 
	# # 
	fig=plt.figure()
	ax=plt.subplot(121,axisbg=(0.1,0.15,0.15))
	ax1_img=plt.imshow(img1.img_ov10[np.floor(c1_minj/ovdec):np.floor(c1_maxjp1/ovdec),np.floor(c1_mini/ovdec):np.floor(c1_maxip1/ovdec)],
				interpolation='nearest',cmap='gray',vmin=args.gs_min,vmax=args.gs_max,extent=[com_min_x,com_max_x,com_min_y,com_max_y])
	# ax_img=plt.imshow(img1.img,interpolation='nearest',cmap='gray',extent=[img1.min_x,img1.max_x,img1.min_y,img1.max_y])
	ax_img1=plt.imshow((offset_dist_ij_arr*img1.pix_x_m)/del_t_val,vmin=plotvmin,vmax=plotvmax,alpha=0.25,interpolation='nearest',
						cmap='jet',extent=[com_min_x,com_max_x,com_min_y,com_max_y])
	plt.colorbar()
	plt.title('vel %s'%(del_t_str))
        ax2=plt.subplot(122,axisbg=(0.1,0.15,0.15))
	ax2_img=plt.imshow(img1.img_ov10[np.floor(c1_minj/ovdec):np.floor(c1_maxjp1/ovdec),np.floor(c1_mini/ovdec):np.floor(c1_maxip1/ovdec)],
				interpolation='nearest',cmap='gray',vmin=args.gs_min,vmax=args.gs_max,extent=[com_min_x,com_max_x,com_min_y,com_max_y])
	# ax_img2=plt.imshow(img2.img,interpolation='nearest',cmap='gray',extent=[img2.min_x,img2.max_x,img2.min_y,img2.max_y])
	ax_img3=plt.imshow(corr_arr,alpha=0.25,interpolation='nearest',vmin=0.0,
						cmap='jet',extent=[com_min_x,com_max_x,com_min_y,com_max_y])
	plt.colorbar()
	plt.title('corr_arr')
        plt.savefig('fig_4_'+str(img1.filename)+'_'+str(img2.filename)+'.png')            

dcam=args.dcam
cam=args.cam
cam1=args.cam1
vv=np.ma.masked_where(((del_corr_arr<dcam)&(corr_arr<cam))|(corr_arr<cam1)|(((offset_dist_ij_arr*img1.pix_x_m)/del_t_val)>plotvmax),((offset_dist_ij_arr*img1.pix_x_m)/del_t_val))
vx=np.ma.masked_where(((del_corr_arr<dcam)&(corr_arr<cam))|(corr_arr<cam1),((del_i*img1.pix_x_m)/del_t_val))
vy=np.ma.masked_where(((del_corr_arr<dcam)&(corr_arr<cam))|(corr_arr<cam1),((del_j*img1.pix_y_m)/del_t_val))


ovdec=10.0

fig=plt.figure()
ax=plt.subplot(111,axisbg=(0.1,0.15,0.15))
ax1_img=plt.imshow(img1.img_ov10[np.floor(c1_minj/ovdec):np.floor(c1_maxjp1/ovdec),np.floor(c1_mini/ovdec):np.floor(c1_maxip1/ovdec)],
                     interpolation='nearest',cmap='gray',vmin=args.gs_min,vmax=args.gs_max,extent=[com_min_x,com_max_x,com_min_y,com_max_y])
ax_img1=plt.imshow(vv,alpha=args.alphaval,interpolation='nearest',vmin=plotvmin,vmax=plotvmax,
                                     cmap='jet',extent=[com_min_x,com_max_x,com_min_y,com_max_y])
plt.title('%s to %s vel in %s'%(args.img1_name,args.img2_name,del_t_str))
plt.colorbar()
plt.savefig('fig_5_'+str(img1.filename)+'_'+str(img2.filename)+'.png')                    

if (args.vf):  # make vel figure with plot_2_mult change of maxv - enhances slower speeds
	fig=plt.figure()
	ax=plt.subplot(111,axisbg=(0.1,0.15,0.15))
	ax1_img=plt.imshow(img1.img_ov10[np.floor(c1_minj/ovdec):np.floor(c1_maxjp1/ovdec),np.floor(c1_mini/ovdec):np.floor(c1_maxip1/ovdec)],
						 interpolation='nearest',cmap='gray',vmin=args.gs_min,vmax=args.gs_max,extent=[com_min_x,com_max_x,com_min_y,com_max_y])
	ax_img1=plt.imshow(vv,alpha=args.alphaval,interpolation='nearest',vmin=plotvmin,vmax=plot_2_mult*plotvmax,
										 cmap='jet',extent=[com_min_x,com_max_x,com_min_y,com_max_y])
	plt.title('%s to %s vel in %s'%(args.img1_name,args.img2_name,del_t_str))
	plt.colorbar()

if (args.sf):  # make vel figure with plot_2_mult change of maxv - enhances slower speeds
	fig=plt.figure()
	ax=plt.subplot(111,axisbg=(0.1,0.15,0.15))
	ax1_img=plt.imshow(img1.img_ov10[np.floor(c1_minj/ovdec):np.floor(c1_maxjp1/ovdec),np.floor(c1_mini/ovdec):np.floor(c1_maxip1/ovdec)],
						 interpolation='nearest',cmap='gray',vmin=args.gs_min,vmax=args.gs_max,extent=[com_min_x,com_max_x,com_min_y,com_max_y])
	ax_img1=plt.imshow(vv,alpha=args.alphaval,interpolation='nearest',vmin=plotvmin,vmax=plot_2_mult*plotvmax,
										 cmap='jet',extent=[com_min_x,com_max_x,com_min_y,com_max_y])
	plt.title('%s to %s vel in %s'%(args.img1_name,args.img2_name,del_t_str))
	plt.colorbar()
        plt.savefig('fig_6_'+str(img1.filename)+'_'+str(img2.filename)+'.png')     

mapjet=plt.get_cmap('jet')
mmvv=vv.copy()
mmvv[(mmvv>plotvmax) & (~mmvv.mask)]=plotvmax
vv_zo=mmvv/plotvmax
vv_rgba=mapjet(vv_zo) # this produces a 4-band 0.0-1.0 image array using the jet colormap
#print vv_rgba.shape
(out_lines,out_pixels,out_bands)=vv_rgba.shape
if (args.vf):
	plt.figure()
	ax2=plt.subplot(131,axisbg=(0.1,0.15,0.15))
	plt.imshow(vv_rgba)
	ax2=plt.subplot(132,axisbg=(0.1,0.15,0.15))
	plt.imshow(vv_rgba[:,:,1],cmap='gray')
	ax2=plt.subplot(133,axisbg=(0.1,0.15,0.15))
	plt.imshow(vv_rgba[:,:,3],cmap='gray')
        plt.savefig('fig_7_'+str(img1.filename)+'_'+str(img2.filename)+'.png')

if (args.sf):
	plt.figure()
	ax2=plt.subplot(131,axisbg=(0.1,0.15,0.15))
	plt.imshow(vv_rgba)
	ax2=plt.subplot(132,axisbg=(0.1,0.15,0.15))
	plt.imshow(vv_rgba[:,:,1],cmap='gray')
	ax2=plt.subplot(133,axisbg=(0.1,0.15,0.15))
	plt.imshow(vv_rgba[:,:,3],cmap='gray')                    

        
if (args.log10):	# prepare a log10 version of the speed for output below
	mmvv=vv.copy()
	mmvv[(mmvv>plotvmax) & (~mmvv.mask)]=plotvmax
	mmvv.mask[(mmvv==0) & (~mmvv.mask)]= True
	lmmvv=np.log10(mmvv)
# 	min_lmmvv=np.min(lmmvv)
	min_lmmvv=np.log10(0.1)
	max_lmmvv=np.log10(plotvmax)
	range_lmmvv=max_lmmvv - min_lmmvv
	lvv_zo=(lmmvv - min_lmmvv)/(range_lmmvv)
	lvv_rgba=mapjet(lvv_zo) # this produces a 4-band 0.0-1.0 image array using the jet colormap



if (args.pixfigs):	# show pixel offsets
	fig=plt.figure()
	ax=plt.subplot(121,axisbg=(0.1,0.15,0.15))
	ax1_img=plt.imshow(img1.img_ov10[np.floor(c1_minj/ovdec):np.floor(c1_maxjp1/ovdec),np.floor(c1_mini/ovdec):np.floor(c1_maxip1/ovdec)],
						 interpolation='nearest',cmap='gray',vmin=args.gs_min,vmax=args.gs_max,extent=[com_min_x,com_max_x,com_min_y,com_max_y])
	ax_img1=plt.imshow(del_i,alpha=args.alphaval,interpolation='nearest',vmin=-3,vmax=3,
										 cmap='jet',extent=[com_min_x,com_max_x,com_min_y,com_max_y])
	plt.title('del_i pixels')
	plt.colorbar()
	ax=plt.subplot(122,axisbg=(0.1,0.15,0.15))
	ax1_img=plt.imshow(img1.img_ov10[np.floor(c1_minj/ovdec):np.floor(c1_maxjp1/ovdec),np.floor(c1_mini/ovdec):np.floor(c1_maxip1/ovdec)],
						 interpolation='nearest',cmap='gray',vmin=args.gs_min,vmax=args.gs_max,extent=[com_min_x,com_max_x,com_min_y,com_max_y])
	ax_img1=plt.imshow(del_j,alpha=args.alphaval,interpolation='nearest',vmin=-3,vmax=3,
										 cmap='jet',extent=[com_min_x,com_max_x,com_min_y,com_max_y])
	plt.title('del_j pixels')
	plt.colorbar()
plt.savefig('fig_8_'+str(img1.filename)+'_'+str(img2.filename)+'.png')



##########################################################################################
# output section - write out various output files
##########################################################################################

if not(args.no_gtif):   ###### This flag is not presently used, as GTiff forms basis for all output right now...
	format = "GTiff"
	driver = gdal.GetDriverByName( format )
	metadata = driver.GetMetadata()
	dst_filename = out_name_base + '.tif'
	dst_ds = driver.Create( dst_filename, out_pixels, out_lines, out_bands, gdal.GDT_Byte )
	if (args.v):
		if metadata.has_key(gdal.DCAP_CREATE) and metadata[gdal.DCAP_CREATE] == 'YES':
			print 'Driver %s supports Create() method.' % format
		if metadata.has_key(gdal.DCAP_CREATECOPY) and metadata[gdal.DCAP_CREATECOPY] == 'YES':
			print 'Driver %s supports CreateCopy() method.' % format
		img1.proj
		dst_ds
		print [com_min_x,com_max_x,com_min_y,com_max_y]
	print 'out image %s %s %d, %d, %d'%(dst_filename, format, out_pixels, out_lines, out_bands)
	if not(args.nlf):
		outsf.write('out image %s %s %d, %d, %d\n'%(dst_filename, format, out_pixels, out_lines, out_bands))
	# dst_ds.SetGeoTransform( [ com_min_x, inc * img1.pix_x_m, 0, com_max_y, 0, inc * img1.pix_y_m ] ) # note pix_y_m typically negative
	dst_ds.SetGeoTransform( [ output_array_ul_corner[0], output_array_pix_x_m, 0, output_array_ul_corner[1], 0, output_array_pix_y_m ] ) # note pix_y_m typically negative
	dst_ds.SetProjection( img1.proj )
	dst_ds.GetRasterBand(1).WriteArray( (vv_rgba[:,:,0]*255).astype('ubyte') )
	dst_ds.GetRasterBand(2).WriteArray( (vv_rgba[:,:,1]*255).astype('ubyte') )
	dst_ds.GetRasterBand(3).WriteArray( (vv_rgba[:,:,2]*255).astype('ubyte') )
	dst_ds.GetRasterBand(4).WriteArray( (vv_rgba[:,:,3]*255).astype('ubyte') )
	dst_ds = None # done, close the dataset
	if(args.kmz):
		# figure out appropriate resolution in lon,lat (epsg:4326) space
		pix_per_chip=3 # google earth interpolates (no nearest neighbor), so need multiple pixels per chip to make it look good (not smeared out)
		kmz_pix_size_lat=(img1.pix_x_m * inc)/(pix_per_chip * 110000.0) #  110000 meters per degree of lat
		kmz_pix_size_lon=kmz_pix_size_lat * np.sin((np.pi/180.0)*  70.0) #  110000 meters per degree of lat - using 70 as default until I can figure out where to get scene center lat...
		a = np.array([[plotvmin,plotvmax]])  # make colorbar image in a figure
		plt.figure(figsize=(1.5, 8))
		img = plt.imshow(a, cmap="jet")
		plt.gca().set_visible(False)
		cax = plt.axes([0.1, 0.05, 0.5, 0.85])
		plt.colorbar(orientation="vertical", cax=cax)
		plt.title('ice flow\nspeed\n(%s)'%(del_t_str))  # del_t_str is either m/d or m/yr
		plt.ion()
		plt.show()
		outcbname=out_name_base+'_colorbar.png'
		plt.savefig(outcbname)
		sp.call(["rm", out_name_base+"_4326.tif", "tmp.kml"])  # clear older tries
		sp.check_call(["gdalwarp", "-t_srs","epsg:4326","-tr","%f"%(kmz_pix_size_lat),"%f"%(kmz_pix_size_lon),"-r","near","-wo","SOURCE_EXTRA=120",out_name_base+".tif",out_name_base+"_4326.tif"])
		sp.check_call(["gdal_translate","-of","kmlsuperoverlay","-co","FORMAT=PNG",out_name_base+"_4326.tif",out_name_base+".kmz"])
		sp.check_call(["unzip", out_name_base+".kmz", "tmp.kml"])
		in_kml_tree=ET.parse('tmp.kml')
		root=in_kml_tree.getroot()
		b=ET.Element(root.tag[:-3]+'Folder')  # make a new node to be the root folder - the tag drops the "kml" (-3) but keeps the namespace url...
		b.attrib['id']=out_name_base  # the name of the folder you see in GE
		b.append(root[0])  # now put the original root node that was read in into the folder, so the colorbar node (below) can go in the folder at the same level
		#now make xml node defining the colorbar entry in folder and pointing to colorbar figure
		c=ET.fromstring('<ns0:ScreenOverlay xmlns:ns0="http://earth.google.com/kml/2.1"><name>Legend: '+out_name_base+'_colorbar</name><Icon> <href>'+out_name_base+'''_colorbar.png</href>
						</Icon>
						<overlayXY x="0" y="0" xunits="fraction" yunits="fraction"/>
						<screenXY x="5" y="5" xunits="pixels" yunits="pixels"/>
						<rotationXY x="0.5" y="0.5" xunits="fraction" yunits="fraction"/>
						<size x="0" y="0" xunits="pixels" yunits="pixels"/>
			</ns0:ScreenOverlay>
			''')  
		b.append(c)  #
		root[0]=b
		newtree=ET.ElementTree(root)
		newtree.write('tmp.kml')
		sp.check_call(["zip", "-u", out_name_base+".kmz", "tmp.kml", out_name_base+"_colorbar.png"])
		sp.check_call(["rm", "tmp.kml"])  # done with modified tmp.kml, erase it
		if not(args.nlf):
			outsf.write('out kmz %s'%(out_name_base+".kmz\n"))
	if(args.log10):
		dst_filename = out_name_base + '_log10.tif'
		dst_ds = driver.Create( dst_filename, out_pixels, out_lines, out_bands, gdal.GDT_Byte )
		print 'out image %s %s %d, %d, %d'%(dst_filename, format, out_pixels, out_lines, out_bands)
		if not(args.nlf):
				outsf.write('out image %s %s %d, %d, %d\n'%(dst_filename, format, out_pixels, out_lines, out_bands))
		# dst_ds.SetGeoTransform( [ com_min_x, inc * img1.pix_x_m, 0, com_max_y, 0, inc * img1.pix_y_m ] ) # note pix_y_m typically negative
		dst_ds.SetGeoTransform( [ output_array_ul_corner[0], output_array_pix_x_m, 0, output_array_ul_corner[1], 0, output_array_pix_y_m ] ) # note pix_y_m typically negative
		dst_ds.SetProjection( img1.proj )
		dst_ds.GetRasterBand(1).WriteArray( (lvv_rgba[:,:,0]*255).astype('ubyte') )
		dst_ds.GetRasterBand(2).WriteArray( (lvv_rgba[:,:,1]*255).astype('ubyte') )
		dst_ds.GetRasterBand(3).WriteArray( (lvv_rgba[:,:,2]*255).astype('ubyte') )
		dst_ds.GetRasterBand(4).WriteArray( (lvv_rgba[:,:,3]*255).astype('ubyte') )
		dst_ds = None # done, close the dataset
		if(args.kmz):
			# figure out appropriate resolution in lon,lat (epsg:4326) space
			# 			pix_per_chip=3 # google earth interpolates (no nearest neighbor), so need multiple pixels per chip to make it look good (not smeared out)
			# 			kmz_pix_size_lat=(img1.pix_x_m * inc)/(pix_per_chip * 110000.0) #  110000 meters per degree of lat
			# 			kmz_pix_size_lon=kmz_pix_size_lat * np.sin((np.pi/180.0)*  70.0) #  110000 meters per degree of lat - using 70 as default until I can figure out where to get scene center lat...
			a = np.array([[0.1,plotvmax]])  # make colorbar image in a figure
			plt.figure(figsize=(1.5, 8))
			img = plt.imshow(a, cmap="jet",norm=matplotlib.colors.LogNorm())
			plt.gca().set_visible(False)
			cax = plt.axes([0.1, 0.05, 0.5, 0.85])
			plt.colorbar(orientation="vertical", cax=cax)
			plt.title('ice flow\nspeed\n(%s)'%(del_t_str))  # del_t_str is either m/d or m/yr
			plt.ion()
			plt.show()
			outcbname=out_name_base+'_log10_colorbar.png'
			plt.savefig(outcbname)
			sp.call(["rm", out_name_base+"_log10_4326.tif", "tmp.kml"])  # clear older tries
			sp.check_call(["gdalwarp", "-t_srs","epsg:4326","-tr","%f"%(kmz_pix_size_lat),"%f"%(kmz_pix_size_lon),"-r","near","-wo","SOURCE_EXTRA=120",out_name_base+"_log10.tif",out_name_base+"_log10_4326.tif"])
			sp.check_call(["gdal_translate","-of","kmlsuperoverlay","-co","FORMAT=PNG",out_name_base+"_log10_4326.tif",out_name_base+"_log10.kmz"])
			sp.check_call(["unzip", out_name_base+"_log10.kmz", "tmp.kml"])
			in_kml_tree=ET.parse('tmp.kml')
			root=in_kml_tree.getroot()
			b=ET.Element(root.tag[:-3]+'Folder')  # make a new node to be the root folder - the tag drops the "kml" (-3) but keeps the namespace url...
			b.attrib['id']=out_name_base  # the name of the folder you see in GE
			b.append(root[0])  # now put the original root node that was read in into the folder, so the colorbar node (below) can go in the folder at the same level
			#now make xml node defining the colorbar entry in folder and pointing to colorbar figure
			c=ET.fromstring('<ns0:ScreenOverlay xmlns:ns0="http://earth.google.com/kml/2.1"><name>Legend: '+out_name_base+'_log10_colorbar</name><Icon> <href>'+out_name_base+'''_log10_colorbar.png</href>
						</Icon>
						<overlayXY x="0" y="0" xunits="fraction" yunits="fraction"/>
						<screenXY x="5" y="5" xunits="pixels" yunits="pixels"/>
						<rotationXY x="0.5" y="0.5" xunits="fraction" yunits="fraction"/>
						<size x="0" y="0" xunits="pixels" yunits="pixels"/>
					</ns0:ScreenOverlay>
					''')  
			b.append(c)  #
			root[0]=b
			newtree=ET.ElementTree(root)
			newtree.write('tmp.kml')
			sp.check_call(["zip", "-u", out_name_base+"_log10.kmz", "tmp.kml", out_name_base+"_log10_colorbar.png"])
			sp.check_call(["rm", "tmp.kml"])  # done with modified tmp.kml, erase it
			if not(args.nlf):
				outsf.write('out log10 kmz %s'%(out_name_base+"log10.kmz\n"))


	if not(args.only_vel_colormap):		# output full suite of float geoTiffs (default behavior) - otherwise only get only color mapped speed above
		dst_filename = out_name_base + '_vx.tif'
		(out_lines,out_pixels)=vx.shape
		out_bands=1
		dst_ds = driver.Create( dst_filename, out_pixels, out_lines, out_bands, gdal.GDT_Float32 )
		print 'out image %s %s %d, %d, %d'%(dst_filename, format, out_pixels, out_lines, out_bands)
		if not(args.nlf):
			outsf.write('out image %s %s %d, %d, %d\n'%(dst_filename, format, out_pixels, out_lines, out_bands))
		dst_ds.SetGeoTransform( [ output_array_ul_corner[0], output_array_pix_x_m, 0, output_array_ul_corner[1], 0, output_array_pix_y_m ] ) # note pix_y_m typically negative
		dst_ds.SetProjection( img1.proj )
		dst_ds.GetRasterBand(1).WriteArray( (vx).astype('float32') )
		dst_ds = None # done, close the dataset
	
		dst_filename = out_name_base + '_vy.tif'
		(out_lines,out_pixels)=vy.shape
		out_bands=1
		dst_ds = driver.Create( dst_filename, out_pixels, out_lines, out_bands, gdal.GDT_Float32 )
		print 'out image %s %s %d, %d, %d'%(dst_filename, format, out_pixels, out_lines, out_bands)
		if not(args.nlf):
			outsf.write('out image %s %s %d, %d, %d\n'%(dst_filename, format, out_pixels, out_lines, out_bands))
		dst_ds.SetGeoTransform( [ output_array_ul_corner[0], output_array_pix_x_m, 0, output_array_ul_corner[1], 0, output_array_pix_y_m ] ) # note pix_y_m typically negative
		dst_ds.SetProjection( img1.proj )
		dst_ds.GetRasterBand(1).WriteArray( (vy).astype('float32') )
		dst_ds = None # done, close the dataset
	
		dst_filename = out_name_base + '_vv.tif'
		(out_lines,out_pixels)=vv.shape
		out_bands=1
		dst_ds = driver.Create( dst_filename, out_pixels, out_lines, out_bands, gdal.GDT_Float32 )
		print 'out image %s %s %d, %d, %d'%(dst_filename, format, out_pixels, out_lines, out_bands)
		if not(args.nlf):
			outsf.write('out image %s %s %d, %d, %d\n'%(dst_filename, format, out_pixels, out_lines, out_bands))
		dst_ds.SetGeoTransform( [ output_array_ul_corner[0], output_array_pix_x_m, 0, output_array_ul_corner[1], 0, output_array_pix_y_m ] ) # note pix_y_m typically negative
		dst_ds.SetProjection( img1.proj )
		dst_ds.GetRasterBand(1).WriteArray( (vv).astype('float32') )
		dst_ds = None # done, close the dataset
	
		dst_filename = out_name_base + '_corr.tif'
		(out_lines,out_pixels)=corr_arr.shape
		out_bands=1
		dst_ds = driver.Create( dst_filename, out_pixels, out_lines, out_bands, gdal.GDT_Float32 )
		print 'out image %s %s %d, %d, %d'%(dst_filename, format, out_pixels, out_lines, out_bands)
		if not(args.nlf):
			outsf.write('out image %s %s %d, %d, %d\n'%(dst_filename, format, out_pixels, out_lines, out_bands))
		dst_ds.SetGeoTransform( [ output_array_ul_corner[0], output_array_pix_x_m, 0, output_array_ul_corner[1], 0, output_array_pix_y_m ] ) # note pix_y_m typically negative
		dst_ds.SetProjection( img1.proj )
		dst_ds.GetRasterBand(1).WriteArray( (corr_arr).astype('float32') )
		dst_ds = None # done, close the dataset
	
		dst_filename = out_name_base + '_delcorr.tif'
		(out_lines,out_pixels)=del_corr_arr.shape
		out_bands=1
		dst_ds = driver.Create( dst_filename, out_pixels, out_lines, out_bands, gdal.GDT_Float32 )
		print 'out image %s %s %d, %d, %d'%(dst_filename, format, out_pixels, out_lines, out_bands)
		if not(args.nlf):
			outsf.write('out image %s %s %d, %d, %d\n'%(dst_filename, format, out_pixels, out_lines, out_bands))
		dst_ds.SetGeoTransform( [ output_array_ul_corner[0], output_array_pix_x_m, 0, output_array_ul_corner[1], 0, output_array_pix_y_m ] ) # note pix_y_m typically negative
		dst_ds.SetProjection( img1.proj )
		dst_ds.GetRasterBand(1).WriteArray( (del_corr_arr).astype('float32') )
		dst_ds = None # done, close the dataset
	
		dst_filename = out_name_base + '_pixel_offset_dist.tif'
		(out_lines,out_pixels)=offset_dist_ij_arr.shape
		out_bands=1
		dst_ds = driver.Create( dst_filename, out_pixels, out_lines, out_bands, gdal.GDT_Float32 )
		print 'out image %s %s %d, %d, %d'%(dst_filename, format, out_pixels, out_lines, out_bands)
		if not(args.nlf):
			outsf.write('out image %s %s %d, %d, %d\n'%(dst_filename, format, out_pixels, out_lines, out_bands))
		dst_ds.SetGeoTransform( [ output_array_ul_corner[0], output_array_pix_x_m, 0, output_array_ul_corner[1], 0, output_array_pix_y_m ] ) # note pix_y_m typically negative
		dst_ds.SetProjection( img1.proj )
		dst_ds.GetRasterBand(1).WriteArray( (offset_dist_ij_arr).astype('float32') )
		dst_ds = None # done, close the dataset
	
		dst_filename = out_name_base + '_pixel_offset_i.tif'
		(out_lines,out_pixels)=del_i.shape
		out_bands=1
		dst_ds = driver.Create( dst_filename, out_pixels, out_lines, out_bands, gdal.GDT_Float32 )
		print 'out image %s %s %d, %d, %d'%(dst_filename, format, out_pixels, out_lines, out_bands)
		if not(args.nlf):
			outsf.write('out image %s %s %d, %d, %d\n'%(dst_filename, format, out_pixels, out_lines, out_bands))
		dst_ds.SetGeoTransform( [ output_array_ul_corner[0], output_array_pix_x_m, 0, output_array_ul_corner[1], 0, output_array_pix_y_m ] ) # note pix_y_m typically negative
		dst_ds.SetProjection( img1.proj )
		dst_ds.GetRasterBand(1).WriteArray( (del_i).astype('float32') )
		dst_ds = None # done, close the dataset
	
		dst_filename = out_name_base + '_pixel_offset_j.tif'
		(out_lines,out_pixels)=del_j.shape
		out_bands=1
		dst_ds = driver.Create( dst_filename, out_pixels, out_lines, out_bands, gdal.GDT_Float32 )
		print 'out image %s %s %d, %d, %d'%(dst_filename, format, out_pixels, out_lines, out_bands)
		if not(args.nlf):
			outsf.write('out image %s %s %d, %d, %d\n'%(dst_filename, format, out_pixels, out_lines, out_bands))
		dst_ds.SetGeoTransform( [ output_array_ul_corner[0], output_array_pix_x_m, 0, output_array_ul_corner[1], 0, output_array_pix_y_m ] ) # note pix_y_m typically negative
		dst_ds.SetProjection( img1.proj )
		dst_ds.GetRasterBand(1).WriteArray( (del_j).astype('float32') )
		dst_ds = None # done, close the dataset
	
		dst_filename = out_name_base + '_sp_dist_i.tif'
		(out_lines,out_pixels)=sp_dist_i.shape
		out_bands=1
		dst_ds = driver.Create( dst_filename, out_pixels, out_lines, out_bands, gdal.GDT_Float32 )
		print 'out image %s %s %d, %d, %d'%(dst_filename, format, out_pixels, out_lines, out_bands)
		if not(args.nlf):
			outsf.write('out image %s %s %d, %d, %d\n'%(dst_filename, format, out_pixels, out_lines, out_bands))
		dst_ds.SetGeoTransform( [ output_array_ul_corner[0], output_array_pix_x_m, 0, output_array_ul_corner[1], 0, output_array_pix_y_m ] ) # note pix_y_m typically negative
		dst_ds.SetProjection( img1.proj )
		dst_ds.GetRasterBand(1).WriteArray( (sp_dist_i).astype('float32') )
		dst_ds = None # done, close the dataset
	
		dst_filename = out_name_base + '_sp_dist_j.tif'
		(out_lines,out_pixels)=sp_dist_j.shape
		out_bands=1
		dst_ds = driver.Create( dst_filename, out_pixels, out_lines, out_bands, gdal.GDT_Float32 )
		print 'out image %s %s %d, %d, %d'%(dst_filename, format, out_pixels, out_lines, out_bands)
		if not(args.nlf):
			outsf.write('out image %s %s %d, %d, %d\n'%(dst_filename, format, out_pixels, out_lines, out_bands))
		dst_ds.SetGeoTransform( [ output_array_ul_corner[0], output_array_pix_x_m, 0, output_array_ul_corner[1], 0, output_array_pix_y_m ] ) # note pix_y_m typically negative
		dst_ds.SetProjection( img1.proj )
		dst_ds.GetRasterBand(1).WriteArray( (sp_dist_j).astype('float32') )
		dst_ds = None # done, close the dataset
	
		dst_filename = out_name_base + '_d2idx2.tif'
		(out_lines,out_pixels)=d2idx2.shape
		out_bands=1
		dst_ds = driver.Create( dst_filename, out_pixels, out_lines, out_bands, gdal.GDT_Float32 )
		print 'out image %s %s %d, %d, %d'%(dst_filename, format, out_pixels, out_lines, out_bands)
		if not(args.nlf):
			outsf.write('out image %s %s %d, %d, %d\n'%(dst_filename, format, out_pixels, out_lines, out_bands))
		dst_ds.SetGeoTransform( [ output_array_ul_corner[0], output_array_pix_x_m, 0, output_array_ul_corner[1], 0, output_array_pix_y_m ] ) # note pix_y_m typically negative
		dst_ds.SetProjection( img1.proj )
		dst_ds.GetRasterBand(1).WriteArray( (d2idx2).astype('float32') )
		dst_ds = None # done, close the dataset
	
		dst_filename = out_name_base + '_d2jdx2.tif'
		(out_lines,out_pixels)=d2jdx2.shape
		out_bands=1
		dst_ds = driver.Create( dst_filename, out_pixels, out_lines, out_bands, gdal.GDT_Float32 )
		print 'out image %s %s %d, %d, %d'%(dst_filename, format, out_pixels, out_lines, out_bands)
		if not(args.nlf):
			outsf.write('out image %s %s %d, %d, %d\n'%(dst_filename, format, out_pixels, out_lines, out_bands))
		dst_ds.SetGeoTransform( [ output_array_ul_corner[0], output_array_pix_x_m, 0, output_array_ul_corner[1], 0, output_array_pix_y_m ] ) # note pix_y_m typically negative
		dst_ds.SetProjection( img1.proj )
		dst_ds.GetRasterBand(1).WriteArray( (d2jdx2).astype('float32') )
		dst_ds = None # done, close the dataset

		dst_filename = out_name_base + '_d2dx2_mean.tif'
		(out_lines,out_pixels)=d2dx2_mean.shape
		out_bands=1
		dst_ds = driver.Create( dst_filename, out_pixels, out_lines, out_bands, gdal.GDT_Float32 )
		print 'out image %s %s %d, %d, %d'%(dst_filename, format, out_pixels, out_lines, out_bands)
		if not(args.nlf):
			outsf.write('out image %s %s %d, %d, %d\n'%(dst_filename, format, out_pixels, out_lines, out_bands))
		dst_ds.SetGeoTransform( [ output_array_ul_corner[0], output_array_pix_x_m, 0, output_array_ul_corner[1], 0, output_array_pix_y_m ] ) # note pix_y_m typically negative
		dst_ds.SetProjection( img1.proj )
		dst_ds.GetRasterBand(1).WriteArray( (d2dx2_mean).astype('float32') )
		dst_ds = None # done, close the dataset


###### Note that at present you must output the geotiff above before making another format.  Also, this is only for color mapped speed right now...
if not(args.of=='GTiff'):  # default behavior is to always save a geotiff - this section uses gdal to convert this geotiff to an additional format
	if(args.of == 'ENVI'):
		print "using gdal_translate to produce ENVI image: %s"%(out_name_base+".img")
		sp.check_call(["gdal_translate","-of",args.of,out_name_base+".tif",out_name_base+".img"])
		if not(args.nlf):
			outsf.write('out image %s %s %d, %d, %d\n'%(out_name_base+".img", 'ENVI', out_pixels, out_lines, out_bands))
	else:
		print "Error: output format %s not recognized/set up"%(args.format)
		if not(args.nlf):
			outsf.write("Error: output format %s not recognized/set up"%(args.format))


if not(args.nlf):
	outsf.close()
