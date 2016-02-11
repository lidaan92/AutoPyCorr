import atexit 
import os
import sys
from time import clock
import argparse
import matplotlib.pyplot as plt
import numpy as np
import gdal
import gdalconst as gdc  # constants for gdal - e.g. GA_ReadOnly, GA_Update ( http://www.gdal.org )
# from scipy.ndimage.filters import convolve
from scipy.ndimage.filters import gaussian_filter
import osr
import datetime as dt

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
    
# set up command line arguments
parser = argparse.ArgumentParser( \
    description="""Generates low pass and high pass geotiffs from specified landsat image.  Uses 1-d gaussian on one dimension 
    and then on the other.  Output data type is float32.""",
    epilog='>>  <<',
    formatter_class=argparse.RawDescriptionHelpFormatter)

parser.add_argument('-imgdir', 
                    action='store', 
                    type=str, 
                    default='.', 
                    help='single source dir for both images [.]')
parser.add_argument('img_name', 
                    action='store', 
                    type=str, 
                    help='image 1 filename')
parser.add_argument('-lp_ext', 
                    action='store', 
                    type=str, 
                    default='_lp', 
                    help='extension to base imagefile name for low pass output [_lp]')
parser.add_argument('-hp_ext', 
                    action='store', 
                    type=str, 
                    default='_hp', 
                    help='extension to base imagefile name for high pass output [_hp]')
parser.add_argument('-gfilt_sigma', 
                    action='store', 
                    type=float, 
                    default=3.0, 
                    help='gaussian filter sigma (Standard deviation for Gaussian kernel) [3.0]')
# the rest of the parameters are flags - if raised, set to true, otherwise false - not all implemented yet!!!
parser.add_argument('-v', 
                    action='store_true',  
                    default=False, 
                    help='verbose - extra diagnostic and image info [False if not raised]')
parser.add_argument('-vf', 
                    action='store_true',
                    default=False, 
                    help='verbose figures -  diagnostic figures shown (original + lp + hp) [False if not raised]')
parser.add_argument('-nlf', 
                    action='store_true',
                    default=False, 
                    help='do not output log file that contains command line etc - [output command line in out_name_base_summary.txt]')
parser.add_argument('-sf',
                    action='store_true',
                    default=False,
                    help='output and save diagnostic figures to .png [False if not raised]')
parser.add_argument('-no_outfile',
                    action='store_true',
                    default=False,
                    help='stop creation of output geotiffs [False if not raised]')
parser.add_argument('-nsidc_out_names',
                    action='store_true',
                    default=False,
                    help='sets out_name_base and out dirs to nsidc structure [False if not raised]')
args = parser.parse_args()

out_name_base=os.path.splitext(args.img_name)[0]+'_filt_%3.1f'%(args.gfilt_sigma)

if(args.v):
	print '#', args

start = clock()
atexit.register(endlog)
t_log("Start Program")

img1=GeoImg(args.img_name,in_dir=args.imgdir)
t_log("read image")

if (args.v):
	dataset=img1.gd
	print 'Image: %s'%img1.filename
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

########################################################################
if (args.nsidc_out_names):  # use nsidc name conventions and out directories
       out_parent_dir=args.imgdir+'/../filter/'
       if not os.path.exists(out_parent_dir):
               os.makedirs(out_parent_dir)
               
if (args.nsidc_out_names):
        file_name_base=out_parent_dir + out_name_base

else:   # output to current directory using out_name_base provided on command line
        file_name_base=out_name_base

if not(args.nsidc_out_names):
        file_name_base=out_name_base
#########################################################################
        

if not(args.nlf):
	outsf=open(file_name_base + "_log.txt",'w')
	outsf.write('# log from %s\n'% sys.argv[0])
	outsf.write("command: " + " ".join(sys.argv) + "\n")
	args_as_dict=vars(args)
	for key,val in args_as_dict.items():
		outsf.write(key + " = " + str(val) + "\n")

if(args.vf):
	fig_size=[14,10]
	ulx=6000
	uly=5000
	fig=plt.figure(figsize=fig_size)
	ax1=plt.subplot(111,axisbg=(0.1,0.15,0.15))
	ax1_img=plt.imshow(img1.img[uly:uly+1000,ulx:ulx+1000],interpolation='nearest',
						cmap='gray',extent=[ulx,ulx+1000,uly,uly+1000])
	plt.title(out_name_base)
	plt.ion()
	plt.show()


lp_arr=img1.img.copy()
gaussian_filter(lp_arr, args.gfilt_sigma, output=lp_arr)
t_log("done with low pass image")

if(args.vf):
	fig=plt.figure(figsize=fig_size)
	ax1=plt.subplot(111,axisbg=(0.1,0.15,0.15))
	ax1_img=plt.imshow(lp_arr[uly:uly+1000,ulx:ulx+1000],interpolation='nearest',
						cmap='gray',extent=[ulx,ulx+1000,uly,uly+1000])
	plt.title('%s low pass'%(out_name_base))
	plt.show()


hp_arr=img1.img - lp_arr
t_log("done with high pass image")

if(args.vf):
	fig=plt.figure(figsize=fig_size)
	ax1=plt.subplot(111,axisbg=(0.1,0.15,0.15))
	ax1_img=plt.imshow(hp_arr[uly:uly+1000,ulx:ulx+1000],interpolation='nearest',
						cmap='gray',extent=[ulx,ulx+1000,uly,uly+1000])
	plt.title('%s high pass'%(out_name_base))
	plt.show()

if not(args.no_outfile):   ###### This flag is not presently used, as GTiff forms basis for all output right now...
	format = "GTiff"
	driver = gdal.GetDriverByName( format )
	metadata = driver.GetMetadata()
	if (args.v):
		if metadata.has_key(gdal.DCAP_CREATE) and metadata[gdal.DCAP_CREATE] == 'YES':
			print 'Driver %s supports Create() method.' % format
		if metadata.has_key(gdal.DCAP_CREATECOPY) and metadata[gdal.DCAP_CREATECOPY] == 'YES':
			print 'Driver %s supports CreateCopy() method.' % format
		img1.proj

	dst_filename = file_name_base + '_lp.tif'
	(out_lines,out_pixels)=lp_arr.shape
	out_bands=1
	dst_ds = driver.Create( dst_filename, out_pixels, out_lines, out_bands, gdal.GDT_Float32 )
	print 'out image %s %s %d, %d, %d'%(dst_filename, format, out_pixels, out_lines, out_bands)
	if not(args.nlf):
		outsf.write('out image %s %s %d, %d, %d\n'%(dst_filename, format, out_pixels, out_lines, out_bands))
	dst_ds.SetGeoTransform( img1.gt ) # note pix_y_m typically negative
	dst_ds.SetProjection( img1.proj )
	dst_ds.GetRasterBand(1).WriteArray( (lp_arr).astype('float32') )
	dst_ds = None # done, close the dataset
	
	dst_filename = file_name_base + '_hp.tif'
	(out_lines,out_pixels)=hp_arr.shape
	out_bands=1
	dst_ds = driver.Create( dst_filename, out_pixels, out_lines, out_bands, gdal.GDT_Float32 )
	print 'out image %s %s %d, %d, %d'%(dst_filename, format, out_pixels, out_lines, out_bands)
	if not(args.nlf):
		outsf.write('out image %s %s %d, %d, %d\n'%(dst_filename, format, out_pixels, out_lines, out_bands))
	dst_ds.SetGeoTransform( img1.gt ) # note pix_y_m typically negative
	dst_ds.SetProjection( img1.proj )
	dst_ds.GetRasterBand(1).WriteArray( (hp_arr).astype('float32') )
	dst_ds = None # done, close the dataset


