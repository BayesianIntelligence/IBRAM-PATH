from __future__ import print_function
from builtins import range
import fiona, csv, json, re, rtree, os, random, time
import rasterio, numpy, pyproj, math
from pyproj import Transformer
from fiona.crs import from_epsg
from rasterio.transform import from_origin
from htm import n, toHtml
from shapely.geometry import Point, Polygon, mapping, shape
from collections import OrderedDict
from maputils import *

class GaussianKernel:
	def __init__(self, sd):
		self.sd = sd
		self.radius = math.ceil(3 * sd)
		self.initialize_heat_cache()

	def heat(self, distance):
		if distance >= self.radius:
			return 0.0
		return math.e ** (-0.5 * (distance / self.sd) **2 )
		
	def initialize_heat_cache(self):
		self.cache = {}
		for x in range(-self.radius, self.radius + 1):
			for y in range(-self.radius, self.radius + 1):
				self.cache[(x, y)] = self.heat(distance(x, y))
		tot = sum(self.cache.values())
		for (x,y),val in self.cache.items():
			self.cache[(x,y)] = val/tot
				
def distance(x, y):
	return math.hypot(x, y)
				
def generateHeatMap(lsRasterFileInfo, expRasterFileInfo, outRasterFileInfo, sd):
	kernal = GaussianKernel(sd)
	
	with rasterio.open(lsRasterFileInfo['rasterFn']) as lsRaster, rasterio.open(expRasterFileInfo['rasterFn']) as expRaster:
		# Read band 1 (as numpy 2D array)
		expRasterData = expRaster.read(1)
		lsRasterData = lsRaster.read(1)
		newRasterData = numpy.zeros((lsRaster.height, lsRaster.width))
		
	for x in range(lsRaster.height):
		for y in range(lsRaster.width):
			if expRasterData[x][y] > 0.0:
				mask = {}
				for dx in range(-kernal.radius, kernal.radius + 1):
					for dy in range(-kernal.radius, kernal.radius + 1):
						try:
							mask[(dx,dy)] = kernal.cache[(dx,dy)]*lsRasterData[x+dx][y+dy]
						except:
							pass
				tot = sum(mask.values())
				if tot > 0.0:
					for key,val in mask.items():
						mask[key] = val/tot
			
				for dx in range(-kernal.radius, kernal.radius + 1):
					for dy in range(-kernal.radius, kernal.radius + 1):
						try:
							newRasterData[x+dx][y+dy] += expRasterData[x][y]*mask[(dx,dy)]
						except:
							pass
				
	with rasterio.open(outRasterFileInfo['rasterFn'], 'w', driver='GTiff',
					height=lsRaster.height, width=lsRaster.width,
					count=lsRaster.count,
					dtype=numpy.dtype('float64'),
					crs=lsRaster.crs,
					transform=lsRaster.transform,
					nodata=lsRaster.nodata,
				) as rasterFile:
					rasterFile.write(newRasterData, 1)
				

if __name__ == "__main__":
	t = time.time()
	
	outputDir = 'outputs/scenario1/'
	radius = 10
	
	csvLSFn = os.path.join('inputs/', 'land_suit.csv')
	rasLSFn = os.path.join('inputs/', 'land_suit.tiff')		
	csvExpFn = os.path.join(outputDir, 'Exposure_Pests_'+'Jan'+'.csv')
	csvDisFn = os.path.join(outputDir, 'Dispersal_Pests_'+'Jan'+'.csv')
	rasExpFn = os.path.join(outputDir, 'Exposure_Pests_'+'Jan'+'.tiff')
	rasDisFn = os.path.join(outputDir, 'Dispersal_Pests_'+'Jan'+'.tiff')
	
	# convertPolyToRaster(
		# {'vectorFn': 'inputs/AU2013_GV_Clipped_nomulti.shp', 'dataFn': csvLSFn, 'vectorKey': 'AU2013', 'dataKey': 'Code'},
		# {'rasterFn': rasLSFn, 'cellSize': cellSize },
		# 'Suitability',
		# pointsPerPoly = 1000,
		# pointsPerCell = 0,
		# approx = True
	# )
	
	generateHeatMap(
		{'rasterFn': rasLSFn},
		{'rasterFn': rasExpFn},
		{'rasterFn': rasDisFn},
		sd = radius/3
	)
		
	# convertPolyToRaster(
		# {'vectorFn': 'inputs/AU2013_GV_Clipped_nomulti.shp', 'dataFn': csvLSFn, 'vectorKey': 'AU2013', 'dataKey': 'Code'},
		# {'rasterFn': rasLSFn, 'cellSize': cellSize },
		# 'Suitability',
		# pointsPerPoly = 1000,
		# pointsPerCell = 0,
		# approx = True
	# )
				
	# convertPolyToRaster(
		# {'vectorFn': 'inputs/AU2013_GV_Clipped_nomulti.shp', 'dataFn': 'outputs/scenario5/Exposure_Pests_Jan.csv', 'vectorKey': 'AU2013', 'dataKey': 'Code'},
		# {'rasterFn': 'outputs/scenario5/Exposure_Pests_Jan.tiff', 'cellSize': 10000 },
		# 'uExposures',
		# pointsPerPoly = 1000,
		# pointsPerCell = 0,
		# approx = True
	# )
				
	# generateHeatMap( 				
			# {'rasterFn': 'outputs/scenario5/Exposure_Pests_Jan.tiff'},
			# {'rasterFn': 'outputs/scenario5/Disperse_Pests_Jan.tiff'}
	# )

	# convertRasterToPoly(
		# {'rasterFn': 'outputs/scenario5/Disperse_Pests_Jan.tiff'},
		# {'vectorFn': 'inputs/AU2013_GV_Clipped_nomulti.shp', 'vectorKey': 'AU2013', 'outCsvFn': 'outputs/scenario5/Disperse_Pests_Jan.csv'},
		# 'uDisperses',
		# pointsPerPoly = 1000,
		# pointsPerCell = 1,
		# approx = True
	# )		