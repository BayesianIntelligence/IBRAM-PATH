from __future__ import print_function
from builtins import range
import fiona, csv, json, re, rtree, os, random, time, math
import rasterio, numpy, pyproj
from pyproj import Transformer
from fiona.crs import from_epsg
from rasterio.transform import from_origin
from htm import n, toHtml
from shapely.geometry import Point, Polygon, mapping, shape
from collections import OrderedDict

try:
	basestring
except:
	basestring = str

# Settings file with directories, etc.
with open('settings.json','r') as settingsFile:
	settings = json.load(settingsFile)

def changeLayerProjection(inShpFn, outShpFn, outCrs, inCrs = None):
	with fiona.open(inShpFn) as inShp:
		# Using the transformer class is *much* faster than pyproj.transform
		transformer = Transformer.from_proj(
			pyproj.Proj(inCrs if inCrs else inShp.crs, preserve_units=True),
			pyproj.Proj({'init': 'EPSG:{}'.format(outCrs)}, preserve_units=True)
		)
		
		with fiona.open(outShpFn, 'w', 'ESRI Shapefile', inShp.schema.copy(), crs=from_epsg(outCrs)) as outShp:
			for feature in inShp:
				if feature['geometry']['type'] == 'Polygon':
					outPolygonLinearRing = []
					for point in feature['geometry']['coordinates'][0]: # linear ring location
						inX,inY = point
						outX,outY = transformer.transform(inX, inY)
					feature['geometry']['coordinates'] = [outPolygonLinearRing]
					outShp.write(feature)
				elif feature['geometry']['type'] == 'Point':
					inX,inY = feature['geometry']['coordinates']
					outX,outY = transformer.transform(inX, inY)
					feature['geometry']['coordinates'] = (outX, outY)
					outShp.write(feature)
		

def convertPointShpToSvg(shpFn, svgFn):
	with fiona.open(shpFn, 'r') as inShp:
		minX, minY, maxX, maxY = inShp.bounds
		width, height = (maxX-minX), (maxY-minY)
		minRadius = (maxX - minX)*0.02
		px = (maxX - minX)*(1/1024.0)   # Suitable for 1024x768 display
		
		buf = minRadius*1.5
		svg = n('svg',
			xmlns = 'http://www.w3.org/2000/svg',
			view_Box = '{} {} {} {}'.format(minX-buf,minY-buf,width+2*buf,height+2*buf))
			
		g = n('g', transform='scale(1,-1)')
		svg.append(n('g', transform='translate(0,{})'.format(2*minY+height), c=g))

		sortedExpValues = sorted([f['properties']['uExposures'] for f in inShp])
		minExpValue = sortedExpValues[int(len(sortedExpValues)*0.1)]
		maxExpValue = sortedExpValues[int(len(sortedExpValues)*0.9)]
		
		def boundExposures(feature):
			exp = feature['properties']['uExposures']
			if maxExpValue - minExpValue == 0:  return 0
			
			scaled = (exp - minExpValue)/(maxExpValue - minExpValue)
			scaled = max(min(scaled,1),0)
			
			return scaled
		
		for feature in inShp:
			g.append(n('circle',
				cx = feature['geometry']['coordinates'][0],
				cy = feature['geometry']['coordinates'][1],
				r = minRadius,
				style = 'fill: hsl(0,100%,{}%);'.format(50+50*(1-boundExposures(feature)), 2*px),
				#style = 'fill: red',
				dataAttrs = toHtml(json.dumps(feature['properties'])),
			))
		
		with open(svgFn, 'w', newline='') as svgFile:
			svgFile.write(str(svg))

# Converts a CSV file with X, Y coords into a ESRI .shp file
# Use |attributes| for type and name info, particularly to
# work with .shp file limitations
# |attributes| = {
#   <fieldname>: {'type': <type>, 'name': <attribute-name-in-layer>},
# }
#     -- If attribute order is important, use OrderedDict
# |include| = regex | [regex1, regex2,...] A pattern (or list of patterns) to match against fields.
#     If a csv field name matches one of the patterns, it's included in the
#     layer (if not already specified in |attributes|). It uses a 'str' GIS attribute type.
def convertCsvToShp(csvFn, shpFn, attributes = None, include = None):
	if attributes is None:  attributes = {}
	#rint(csvFn, shpFn)
	csvFieldNames = []
	with open(csvFn, 'r') as csvFile:
		inCsv = csv.DictReader(csvFile)
		csvFieldNames = inCsv.fieldnames
	
	# Extract attribute types and csv names
	props = OrderedDict()
	nameMap = {}
	for key in attributes.keys():
		props[key] = attributes[key]['type']
		nameMap[attributes[key]['csvName']] = key
	
	# Include fields automatically if required. Messy
	# because of 10-char limit restrictions in Shape file .dbfs
	if include is not None:
		if isinstance(include,basestring): include = [include]
		
		for pattern in include:
			for fieldName in csvFieldNames:
				if re.search(pattern, fieldName):
					if fieldName in nameMap:  continue
					
					shortName = fieldName
					if len(fieldName)>10:
						shortName = fieldName[:10]
						if shortName in props:
							shortName = fieldName[:9]
							for i in range(36):
								if i<10:
									shortName = shortName+str(i)
								else:
									shortName = shortName=chr(ord('A')+(i-10))
								if shortName not in props:  break
					props[shortName] = 'str'
					nameMap[fieldName] = shortName
	
	#rint(props)
	
	schema = {'geometry': 'Point', 'properties': props}
	with fiona.collection(shpFn, 'w', 'ESRI Shapefile', schema) as outFile, \
			open(csvFn, 'r') as csvFile:
		csvFl = csv.DictReader(csvFile)
		for row in csvFl:
			try:
				point = Point(float(row['X']), float(row['Y']))
			except:
				print('<strong>ERROR: Could not find point information columns (i.e. X, Y) for:\n "{}"</strong>'.format(csvFn))
				raise
			outFile.write({
				'properties': {nameMap[k]: row[k] for k in nameMap.keys()},
				'geometry': mapping(point),
			})

# Only need to run once. The data will be stored separately from
# the shapes.
def convertPolyShpToSvg(shpFn, svgFn, codeField = 'AU2013', simplify = 500):
	with fiona.open(shpFn, 'r') as inShp:
		minX, minY, maxX, maxY = inShp.bounds
		width, height = (maxX-minX), (maxY-minY)
		minRadius = (maxX - minX)*0.02
		px = (maxX - minX)*(1/1024.0)   # Suitable for 1024x768 display
		
		buf = minRadius*1.5
		svg = n('svg',
			xmlns = 'http://www.w3.org/2000/svg',
			view_Box = '{} {} {} {}'.format(minX-buf,minY-buf,width+2*buf,height+2*buf))
		
		g = n('g', transform='scale(1,-1)')
		svg.append(n('g', transform='translate(0,{})'.format(2*minY+height), c=g))

		svg.append(n('style', '''
			polygon { stroke: #ccc; stroke-width: '''+str(px)+'''; fill: #EDE4C3; }
		'''))
			
		for feature in inShp:
			if not feature['geometry']:  continue
			if feature['geometry']['type']=='Polygon':
				polys = [Polygon(feature['geometry']['coordinates'][0])]
			elif feature['geometry']['type']=='MultiPolygon':
				polys = [Polygon(c) for c in feature['geometry']['coordinates'][0]]
			if simplify:
				polys = [p.simplify(simplify) for p in polys]
			for p in polys:
				g.append(n('polygon',
					points = " ".join('{},{}'.format(c[0],c[1]) for c in p.exterior.coords),
					dataCode = feature['properties'][codeField],
				))
		
		with open(svgFn, 'w', newline='') as svgFile:
			svgFile.write(str(svg))

# Converts a CSV file with X, Y coords into a ESRI .shp file
# Use |attributes| for type and name info, particularly to
# work with .shp file limitations
# |attributes| = {
#   <fieldname>: {'type': <type>, 'name': <attribute-name-in-layer>},
# }
#     -- If attribute order is important, use OrderedDict
# |include| = regex | [regex1, regex2,...] A pattern (or list of patterns) to match against fields.
#     If a csv field name matches one of the patterns, it's included in the
#     layer (if not already specified in |attributes|). It uses a 'str' GIS attribute type.
def convertAreaCsvToShp(csvFn, shpFn, attributes = None, include = None, gran = 'au'):
	if attributes is None:  attributes = {}
	#rint(csvFn, shpFn)
	csvFieldNames = []
	with open(csvFn, 'r') as csvFile:
		inCsv = csv.DictReader(csvFile)
		csvFieldNames = inCsv.fieldnames
	
	# Extract attribute types and csv names
	props = OrderedDict()
	nameMap = {}
	for key in attributes.keys():
		props[key] = attributes[key]['type']
		nameMap[attributes[key]['csvName']] = key
	
	# Include fields automatically if required. Messy
	# because of 10-char limit restrictions in Shape file .dbfs
	if include is not None:
		if isinstance(include,basestring): include = [include]
		
		for pattern in include:
			for fieldName in csvFieldNames:
				if re.search(pattern, fieldName):
					if fieldName in nameMap:  continue
					
					shortName = fieldName
					if len(fieldName)>10:
						shortName = fieldName[:10]
						if shortName in props:
							shortName = fieldName[:9]
							for i in range(36):
								if i<10:
									shortName = shortName+str(i)
								else:
									shortName = shortName=chr(ord('A')+(i-10))
								if shortName not in props:  break
					props[shortName] = 'str'
					nameMap[fieldName] = shortName
	
	#rint(props)
	#rint(nameMap)
	
	# Read in our csv file into memory as a map of Code -> row
	csvData = {}
	with open(csvFn, 'r') as csvFile:
		csvFl = csv.DictReader(csvFile)
		for row in csvFl:
			csvData[row['Code']] = row
	
	if gran == 'au':
		areaShpFn = os.path.join(settings['inputsDir'],'AU2013_GV_Clipped_nomulti.shp')
		codeField = 'AU2013'
	elif gran == 'mb':
		areaShpFn = os.path.join(settings['inputsDir'],'MB2013_GV_Clipped.shp')
		codeField = 'MB2013'
	elif gran == 'sa2':
		areaShpFn = os.path.join(settings['inputsDir'],'maps/SA2_2016_AUST_GDA94_nomulti.shp')
		codeField = 'SA2_MAIN16'

	schema = {'geometry': 'Polygon', 'properties': props}
	with fiona.collection(shpFn, 'w', 'ESRI Shapefile', schema) as outFile, \
			fiona.open(areaShpFn, 'r') as areaShp:
		
		for area in areaShp:
			if area['properties'][codeField] in csvData:
				row = csvData[area['properties'][codeField]]
				outFile.write({
					'properties': {nameMap[k]: row[k] for k in nameMap.keys()},
					'geometry': area['geometry'],
				})

# Takes a point layer input, and convert properties as appropriate to span areas
# Cache granIndex, because making it is slow
granIndex = None
def bufInt(inShpFn, outCsvFn, buffer, gran = 'au',
		# reweightFields = ['uExposures','uQtyArrv','uQty','uNextQty','pExposure'],
		reweightFields = ['uExposures'],
		includeAll = False, extraFields = []):
	global granIndex
	

	if gran == 'hex':
		granShpFn = os.path.join(settings['inputsDir'],'10kmHexClippedNZTM','10kmHexClippedNZTM.shp')
		granCsvFn = os.path.join(settings['inputsDir'],'10kmHexClippedNZTM', '10kmHexClippedNZTM.csv')
		codeField = 'Code'
		nameField = 'EA_Name'
		areaField = 'area_sqkm'
	elif gran == 'au':
		granShpFn = os.path.join(settings['inputsDir'],'AU2013_GV_Clipped_nomulti.shp')
		granCsvFn = os.path.join(settings['inputsDir'], 'AU2013_GV_Clipped.csv')
		codeField = 'AU2013'
		nameField = 'AU2013_NAM'
		areaField = 'area_sqkm'
	elif gran == 'sa2':
		granShpFn = os.path.join(settings['inputsDir'],'maps/SA2_2016_AUST_GDA94_nomulti.shp')
		granCsvFn = os.path.join(settings['inputsDir'], 'maps/SA2_2016_AUST.csv')
		codeField = 'SA2_MAIN16'
		nameField = 'SA2_NAME16'
		areaField = 'AREASQKM16'
	else:
		granShpFn = os.path.join(settings['inputsDir'],'MB2013_GV_Clipped.shp')
		granCsvFn = os.path.join(settings['inputsDir'], 'MB2013_GV_Clipped.csv')
		codeField = 'MB2013'
		nameField = 'MB2013_NAM'
		areaField = 'area_sqkm'

	granLookup = {}
	with open(granCsvFn,'r') as csvFile:
		granCsv = csv.DictReader(csvFile)
		for row in granCsv:
			granLookup[row['Code']] = row
		
	with fiona.open(granShpFn, 'r') as granShp:
		# Create our index for fast look-ups
		if granIndex is None:
			granIndex = rtree.index.Index()
			for feature in granShp:
				if feature['geometry']:
					granIndex.insert(int(feature['id']), shape(feature['geometry']).bounds)

		outLayerByCode = {}
		outHeaders = None

		with fiona.open(inShpFn, 'r') as inShp:
			for feature in inShp:
				# Reweight the properties and add to outLayerByCode
				mainProps = feature['properties']
				if outHeaders is None:
					outHeaders = ['Code','uPeSqKm','sdPeSqKm',nameField] + reweightFields
					if includeAll:
						outHeaders += [k for k in mainProps.keys() if k not in outHeaders]
					elif extraFields:
						outHeaders += extraFields
							
				p = Point(feature['geometry']['coordinates'])
				# Create buffers around the points
				newPoly = Polygon(p.buffer(buffer).exterior)

				# Intersect with the AU reference layer, to create shards
				# Get bounding box intersections first
				intersectIds = list(granIndex.intersection(newPoly.bounds))
				shards = []
				for id in intersectIds:
					id = int(id)
					granPoly = shape(granShp[id]['geometry'])
					#print granPoly
					if newPoly.intersects(granPoly):
						intersectedPoly = newPoly.intersection(granPoly)
						# For now, props should just contain the au/mb code
						newFeature = {
							'code': granShp[id]['properties'][codeField],
							'poly': intersectedPoly
						}
						shards.append( newFeature )

				# Work out the area the shards take up. (Often, but not always,
				# just the original buffered point area.)
				totalArea = 0
				for shard in shards:
					totalArea += shard['poly'].area
				
				#print totalArea
				
				# Reassign the numerical
				# properties according to proportion area for each shard.
				for shard in shards:
					shardProp = shard['poly'].area / totalArea
					#shard['geometry'] = mapping(shard['poly'])
					#del shard['poly']
					
					if shard['code'] not in outLayerByCode:
						outLayerByCode[shard['code']] = {k:0 for k in outHeaders}
						outLayerByCode[shard['code']]['Code'] = shard['code']
					
					for k in outHeaders:
						if k in reweightFields:
							#print 'reweighting', shardProp
							# Reweight required fields
							outLayerByCode[shard['code']][k] += float(mainProps[k])*shardProp
						elif k not in ['Code','uPeSqKm','sdPeSqKm',nameField]:
							# Otherwise, just assign
							outLayerByCode[shard['code']][k] = mainProps[k]
					
		# Add information about the granularity unit
		for code in outLayerByCode.keys():
			outLayerByCode[code]['uPeSqKm'] = outLayerByCode[code]['uExposures']/float(granLookup[code][areaField])
			outLayerByCode[code]['sdPeSqKm'] = '0'
			outLayerByCode[code][nameField] = granLookup[code][nameField]
		
		# Finally, write out the CSV
		with open(outCsvFn, 'w', newline='') as outFile:
			outCsv = csv.DictWriter(outFile, outHeaders)
			#rint('outHeaders:',outHeaders)
			outCsv.writerow(dict(zip(outHeaders,outHeaders)))
			for code in sorted(outLayerByCode.keys()):
				outCsv.writerow(outLayerByCode[code])

# Probably not useful for anything any more
def convertJsonHeatmapToRaster(jsonFn, pointsFn, outRasterFn, radius):
	with fiona.open(pointsFn) as pointsFile:
		pointsBounds = pointsFile.bounds
		pointsCrs = pointsFile.crs
		print(pointsBounds)
	
	with open(jsonFn) as inJson:
		raster = json.load(inJson)
		width = raster['extent'][2]-raster['extent'][0]
		height = raster['extent'][3]-raster['extent'][1]
		width2 = pointsBounds[2] - pointsBounds[0]
		height2 = pointsBounds[3] - pointsBounds[1]
		xScale = width2/width
		yScale = height2/height
		print('w/w:',width2/width)
		rasterData = numpy.reshape(raster['matrix'],(height+1,width+1))
		with rasterio.open(outRasterFn, 'w', driver='GTiff',
			height=(height+1)+radius*2, width=(width+1)+radius*2,
			count=1,
			dtype=numpy.dtype('float64'),
			crs=pointsCrs,
			transform=from_origin(pointsBounds[0]-(radius+0.5)*xScale, pointsBounds[1]+height2+(radius+0.5)*yScale, xScale, yScale),
		) as rasterFile:
			#print(rasterData.tolist())
			rasterFile.write(rasterData/numpy.sum(rasterData), 1)
			
def polyFromBounds(bounds):
	return Polygon([
		[bounds['x'][0], bounds['y'][0]],
		[bounds['x'][0], bounds['y'][1]],
		[bounds['x'][1], bounds['y'][1]],
		[bounds['x'][1], bounds['y'][0]],
	])

def intersectBounds(bounds1, bounds2, snapCellSize = None):
	commonBounds = {'x': [0,0], 'y': [0,0]}
	for dim in ['x','y']:
		commonBounds[dim][0] = max(bounds1[dim][0], bounds2[dim][0])
		commonBounds[dim][1] = min(bounds1[dim][1], bounds2[dim][1])
	# print(commonBounds)
	
	# Now, snap to boundaries, relative to the first bounds. Err on side of making bounds larger.
	newBounds = {'x': [0,0], 'y': [0,0]}
	if snapCellSize:
		for dim in ['x','y']:
			newBounds[dim][0] = bounds1[dim][0] + math.floor((commonBounds[dim][0] - bounds1[dim][0])/snapCellSize)*snapCellSize
			newBounds[dim][1] = bounds1[dim][0] + math.ceil((commonBounds[dim][1] - bounds1[dim][0])/snapCellSize)*snapCellSize
	else:
		newBounds = commonBounds
	
	return newBounds

# Don't use this function directly. Use convertPolyToRaster or convertRasterToPoly instead.
# XXX Fix: feature ids may not necessarily be sequential integers. Remove that assumption from below.
def __convertPolyRaster(polyFileInfo, rasterFileInfo, field, 
		reverse = False, hitPointsFn = None, pointsPerPoly = 100, pointsPerCell = 0, approx = True,
		outCrs = None):
	
	# If raster to poly, read in raster, and get cell size & bounds from raster
	xCellSize = None
	yCellSize = None
	if reverse:
		if 'cellSize' in rasterFileInfo:
			xCellSize = rasterFileInfo['cellSize']#40000
			yCellSize = xCellSize
		with rasterio.open(rasterFileInfo['rasterFn']) as raster:
			# Read band 1 (as numpy 2D array)
			rasterData = raster.read(1)
			# GIS raster data is upside down by default (sort of)
			rasterData = numpy.flip(rasterData,0)
			if xCellSize is None:
				xCellSize = (raster.bounds.right - raster.bounds.left)/raster.width
				# |top| is larger, because GIS coordinates typically go bottom up
				yCellSize = (raster.bounds.top - raster.bounds.bottom)/raster.height
				print(xCellSize, yCellSize)
			
			rasterBounds = {
				'x': [raster.bounds.left, raster.bounds.right],
				'y': [raster.bounds.bottom, raster.bounds.top],
			}

			if outCrs is None and raster.crs:
				# rasterio seems to understand fiona's CRS dict format, so
				# no need to convert. Surprising.
				outCrs = raster.crs
				print("Setting output CRS from raster layer:", raster.crs)
			print("Raster layer bounds:", rasterBounds)
			
			
	# Otherwise, cellSize must be a parameter for the output raster
	else:
		xCellSize = rasterFileInfo['cellSize']
		yCellSize = xCellSize
		rasterBounds = None
		
		

		
	with fiona.open(polyFileInfo['vectorFn'], 'r') as inVec:
		minX, minY, maxX, maxY = inVec.bounds
		vectorBounds = {
			'x': [minX, maxX],
			'y': [minY, maxY],
		}
		
		if outCrs is None:
			outCrs = inVec.crs
			print("Setting output CRS from vector layer:", inVec.crs)
		
		print("Vector layer bounds:", vectorBounds)
		
		if rasterBounds is None:
			commonBounds = vectorBounds
			commonWidth = vectorBounds['x'][1] - vectorBounds['x'][0]
			commonHeight = vectorBounds['y'][1] - vectorBounds['y'][0]
		else:
			print('Computing vector/raster intersection')
			commonBounds = intersectBounds(rasterBounds, vectorBounds, snapCellSize = xCellSize)
			commonWidth = commonBounds['x'][1] - commonBounds['x'][0]
			commonHeight = commonBounds['y'][1] - commonBounds['y'][0]
			print("Common bounds:", commonBounds)

		# Get all features that have a geometry (other features won't figure here)
		allItems = [item for item in inVec if item['geometry']]
		allItemsByFeatureId = dict((int(item['id']),item) for item in allItems)
		allItemsByKey = None
		
		if 'vectorKey' in polyFileInfo:
			vectorKey = polyFileInfo['vectorKey']
			allItemsByKey = {}
			for item in allItems:
				# There may be multiple items with the same key
				allItemsByKey.setdefault(item['properties'][vectorKey], [])
				allItemsByKey[item['properties'][vectorKey]].append(item)
		
		# If there's a data file to join, attach properties to the items
		if 'dataFn' in polyFileInfo:
			dataKey = polyFileInfo['dataKey']

			with open(polyFileInfo['dataFn'], 'r') as csvFile:
				inCsv = csv.DictReader(csvFile)
				
				for row in inCsv:
					for key,value in row.items():
						# Only add properties for items that have been included (i.e. that have geometry)
						if row[dataKey] in allItemsByKey:
							for item in allItemsByKey[ row[dataKey] ]:
								item['properties'][key] = value
				
		
		# Make the rtree index for the vector file, along with a shape cache (because that's expensive to do)
		vecIndex = rtree.index.Index()
		shapeCache = {}
		for feature in allItems:
			featureId = int(feature['id'])
			shapeCache[featureId] = shape(feature['geometry'])
			# if not approx:
				# shapeCache[featureId] = shapeCache[featureId].simplify(50)
			vecIndex.insert(featureId, shapeCache[featureId].bounds)
		
		numPolys = len(allItems)
		points = []
		numXCells = math.ceil(commonWidth / xCellSize)
		numYCells = math.ceil(commonHeight / yCellSize)
		# print(commonHeight, yCellSize, commonHeight/yCellSize)
		# Create our raster map hit counter
		rasterCells = [[0 for x in range(numXCells)] for y in range(numYCells)]
		
		print("Num polygons:", numPolys)
		print("Num raster cells: {} ({}x{})".format(numXCells*numYCells, numXCells, numYCells))
		#print(rasterCells)
		polys = dict((int(item['id']),0) for item in allItems)
		polyIntersections = [[] for i in range(numPolys)]
		
		jointPoints = {}
		polyWithCells = {}
		cellWithPolys = {}
		
		#print(shapeCache)
		
		missedRaster = 0
		
		if pointsPerPoly > 0:
			# Generate n points per poly, and count raster cell and poly intersections
			# (Guarantee at least 1 hit per poly)
			for poly in allItems:
				featureId = int(poly['id'])
				# print('feature:',featureId, poly['id'])
				polyI = featureId
				#polyShape = shape(poly['geometry'])
				polyShape = shapeCache[polyI]
				b = polyShape.bounds
				polyWidth = b[2] - b[0]
				polyHeight = b[3] - b[1]
				for i in range(pointsPerPoly):
					rawX = random.random()
					rawY = random.random()
					x = rawX*polyWidth + b[0]
					y = rawY*polyHeight + b[1]
					if not approx and not polyShape.contains(Point(x, y)):  continue
					
					xCell = int((x-commonBounds['x'][0])/commonWidth * numXCells)
					yCell = int((y-commonBounds['y'][0])/commonHeight * numYCells)
					points.append([x,y])
					
					# Check for valid xCell, yCell (because boundaries may differ)
					if yCell >= 0 and yCell < len(rasterCells) and \
							xCell >= 0 and xCell < len(rasterCells[yCell]):
						rasterCells[yCell][xCell] += 1
					else:
						missedRaster += 1
					
					#print((rawX,rawY),(width,height),(x,y))
					
					#print(len([x for x in vecIndex.nearest((x, y))]))
					#print(allItems[polyId])
					
					# for polyId in vecIndex.intersection((x, y)):
						# poly = shape(inVec[polyId]['geometry'])
						# if poly.contains(Point(x,y)):
							# polys[polyId] += 1
							# polyIntersections[polyId].append((x, y))
					polys[polyI] += 1
					
					# Just assume it will be close enough to being in the poly
					# key = '{}-{},{}'.format(polyI, xCell, yCell)
					# jointPoints.setdefault(key, 0)
					# jointPoints[key] += 1
					polyWithCells.setdefault(polyI, {})
					polyWithCells[polyI].setdefault((xCell,yCell), 0)
					polyWithCells[polyI][(xCell,yCell)] += 1
					cellWithPolys.setdefault((xCell,yCell), {})
					cellWithPolys[(xCell,yCell)].setdefault(polyI, 0)
					cellWithPolys[(xCell,yCell)][polyI] += 1
		
		print('Raster misses:', missedRaster)
		
		if pointsPerCell > 0:
			numberTests = 0
			for xCell in range(numXCells):
				for yCell in range(numYCells):
					for i in range(pointsPerCell):
						rawX = random.random()
						rawY = random.random()
						x = rawX*xCellSize + xCell*xCellSize + commonBounds['x'][0]
						y = rawY*yCellSize + yCell*yCellSize + commonBounds['y'][0]
						
						#print(x,y)
						
						rasterCells[yCell][xCell] += 1
						
						polyIds = [polyId for polyId in vecIndex.intersection((x, y))]
						#polyIds = [random.randint(0,3611)]
						
						if approx:
							polyIds = [random.choice(polyIds)] if len(polyIds) else []
						
						for polyId in polyIds:
							#poly = shape(inVec[polyId]['geometry'])
							poly = shapeCache[polyId]
							numberTests += 1
							if approx or poly.contains(Point(x,y)):
								polys[polyId] += 1
								#print("Found")
								
								# key = '{}-{},{}'.format(polyId, xCell, yCell)
								# jointPoints.setdefault(key, 0)
								# jointPoints[key] += 1
								polyWithCells.setdefault(polyId, {})
								polyWithCells[polyId].setdefault((xCell,yCell), 0)
								polyWithCells[polyId][(xCell,yCell)] += 1
								cellWithPolys.setdefault((xCell,yCell), {})
								cellWithPolys[(xCell,yCell)].setdefault(polyId, 0)
								cellWithPolys[(xCell,yCell)][polyId] += 1
			print("NumberTests:",numberTests)
		
		
		# for polyId, count in enumerate(polys):
			# if count>10:
				# print(polyId, count)
				# print(allItems[polyId]['properties']['AU2013'],allItems[polyId]['properties']['AU2013_NAM'])
				# print('Intersection points:')
				# for point in polyIntersections[polyId]:
					# print('\t', point)
		
		# Now that we have counts for hits against polys, cells, and polys+cells, we calculate what
		# proportion of intersecting polys need to be added to each cell

	# Write out the hit points file if requested (mainly useful for debugging)
	if hitPointsFn:
		schema = {
			'geometry': 'Point',
			'properties': {'hit': 'float'},
		}
		with fiona.open(hitPointsFn, 'w', crs=outCrs, driver='ESRI Shapefile', schema = schema) as output:
			for point in points:
				shpPoint = Point(point[0], point[1])
				output.write({
					'geometry': mapping(shpPoint),
					'properties': {'hit': 1},
				})
	
	if reverse:
		# Already have rasterData from the beginning of the func
		
		# Create our output polygon file of data
		
		asDistribution = polyFileInfo.get('outputDistribution', False)
		
		if asDistribution:
			# Use a dictionary, because raster vals might be non-sequential
			outPolys = dict((int(item['id']),{}) for item in allItems)
		else:
			outPolys = dict((int(item['id']),0) for item in allItems)
		
		xCellsDiff = int((commonBounds['x'][0] - rasterBounds['x'][0])/xCellSize)
		yCellsDiff = int((commonBounds['y'][0] - rasterBounds['y'][0])/yCellSize)
		# print(xCellsDiff,yCellsDiff)
		# print(commonBounds['x'][0], rasterBounds['x'][0])
		# print(len(rasterCells), len(rasterCells[0]))
		# print(rasterData.shape)
		
		#outPolys = []
		#for i in range(numPolys):
		#	outPolys.append([0,0,0,0])
		for polyId,poly in polys.items():
			polyCells = polyWithCells.get(polyId, {})
			for (xCell,yCell),count in polyCells.items():
				cellAndPolyCount = count
				
				# Check for valid xCell, yCell
				if yCell >= 0 and yCell < len(rasterCells) and \
						xCell >= 0 and xCell < len(rasterCells[yCell]):
					cellCount = rasterCells[yCell][xCell]
					
					propOfCell = float(cellAndPolyCount)/cellCount
					
					
					inXCell = xCell - xCellsDiff
					inYCell = yCell - yCellsDiff
					
					fieldValue = rasterData[inYCell, inXCell]
					
					if asDistribution:
						# Each cell counts as a 'vote' for that fieldValue, but partial overlap count as partial vote
						outPolys[polyId].setdefault(fieldValue, 0)
						outPolys[polyId][fieldValue] += propOfCell
					else:
						outPolys[polyId] += propOfCell * fieldValue
						#use max val
						#outPolys[polyId] = max(outPolys[polyId], fieldValue)
		
		print("Raster total for field: {}. Polys total for field: {}.".format(numpy.sum(rasterData), sum(outPolys)))
		
		# Aggregate (sum) based on vectorKey
		polyMap = {}
		aggregatedPolys = {}
		# polyCount = {}
		for polyId, polyValue in outPolys.items():
			item = allItemsByFeatureId[polyId]['properties']
			vectorKeyValue = item[polyFileInfo['vectorKey']] # e.g. the actual AU2013 value, like 500100
			polyMap[vectorKeyValue] = item[polyFileInfo['vectorKeyName']]
			
			if asDistribution:
				aggregatedPolys.setdefault(vectorKeyValue, {})
				for fieldValue,count in polyValue.items():
					aggregatedPolys[vectorKeyValue].setdefault(fieldValue, 0)
					aggregatedPolys[vectorKeyValue][fieldValue] += count
			else:
				aggregatedPolys.setdefault(vectorKeyValue, 0)
				aggregatedPolys[vectorKeyValue] += polyValue
				#use max val
				#aggregatedPolys[vectorKeyValue] = max(aggregatedPolys[vectorKeyValue], polyValue)

		if asDistribution:
			# Normalise
			for polyId, polyDistrib in aggregatedPolys.items():
				totalCount = sum(polyDistrib.values())
				for i,count in polyDistrib.items():
					polyDistrib[i] = count/totalCount
		
		if 'outCsvFn' in polyFileInfo:
			with open(polyFileInfo['outCsvFn'], 'w', newline='') as csvFile:
				#outCsv = csv.DictWriter(csvFile, [polyFileInfo['vectorKey'], field])
				fieldNames = ['Code', polyFileInfo['vectorKeyName']]
				if asDistribution == 'flat':
					allKeys = set()
					for polyValue in aggregatedPolys.values():
						allKeys.update('v{}'.format(v) for v in polyValue.keys())
					fieldNames.extend(sorted(allKeys))
				else:
					fieldNames.append(field)
				outCsv = csv.DictWriter(csvFile, fieldNames)
				outCsv.writeheader()
				
				# for polyId, polyValue in enumerate(outPolys):
				for vectorKeyValue in sorted(aggregatedPolys.keys()):
					polyValue = aggregatedPolys[vectorKeyValue]
					row = {
						#polyFileInfo['vectorKey']: vectorKeyValue,
						'Code': vectorKeyValue,
						polyFileInfo['vectorKeyName']: polyMap[vectorKeyValue],
					}
					if asDistribution == 'flat':
						row.update(("v{}".format(k),v) for k,v in polyValue.items())
					else:
						row[field] = polyValue
					outCsv.writerow(row)
			
	else:
		# Create our raster map data
		raster = [[0 for x in range(numXCells)] for y in range(numYCells)]
		totalCellAndPoly = 0
		totalPoly = 0
		polyTotals = {}
		for xCell in range(numXCells):
			for yCell in range(numYCells):
				cellCount = rasterCells[yCell][xCell]
				cellPolys = cellWithPolys.get((xCell,yCell), {})
				for polyId,count in cellPolys.items():
					itemProps = allItemsByFeatureId[polyId]['properties']
					cellAndPolyCount = count
					polyCount = polys[polyId]
					
					propOfPoly = float(cellAndPolyCount)/polyCount
					
					if propOfPoly>1.0:
						print('propOfPoly:', propOfPoly)
					
					polyTotals.setdefault(polyId, 0)
					polyTotals[polyId] += propOfPoly
					
					# print('polyInfo:', polyId, 't:', polyTotals[polyId], 'c:', polyCount)
					# print('cellAndPolyCount:', cellAndPolyCount)
					# print()
						
					
					totalCellAndPoly += cellAndPolyCount
					totalPoly += polyCount
					
					fieldValue = float(itemProps.get(field, 0))
					if allItemsByKey:
						itemsWithSameKey = allItemsByKey[ itemProps[vectorKey] ]
						thisItemArea = shapeCache[polyId].area
						fullArea = 0
						fieldVals = []
						for item in itemsWithSameKey:
							fieldVals.append(itemProps[field])
							fullArea += shapeCache[int(item['id'])].area
						#print(fieldVals)
						
						thisItemPropArea = float(thisItemArea)/fullArea
						
						fieldValue *= thisItemPropArea
					#print(itemProps, propOfPoly, fieldValue)
					raster[yCell][xCell] += propOfPoly * fieldValue
	
		# print('cap:',totalCellAndPoly)
		# print('p:',totalPoly)
		# print('pp:',len(polyTotals), polyTotals)
		# print(polys)
		# print(rasterCells)
		# print(raster)
	
		allCells = []
		for row in raster:
			allCells.extend(row)
			
		itemFieldValues = [float(item['properties'].get(field,0)) for item in allItems]
		print("Raster total for field: {}. Polys total for field: {}.".format(sum(allCells), sum(itemFieldValues)))
	
		# Write out a raster, if requested
		if 'rasterFn' in rasterFileInfo:
			rasterOut = numpy.array(raster)
			with rasterio.open(rasterFileInfo['rasterFn'], 'w', driver='GTiff',
				height=len(raster), width=len(raster[0]),
				count=1,
				dtype=numpy.dtype('float64'),
				crs=outCrs,
				# The negative y pixel size is how it's supposed to work apparently
				transform=from_origin(commonBounds['x'][0], commonBounds['y'][1], xCellSize, yCellSize),
				) as rasterFile:
					print(xCellSize,yCellSize)
					rasterFile.write(numpy.flip(rasterOut,0), 1)
				
		
		# Write out gridded points file if requested
		if 'pointsFn' in rasterFileInfo:
			print('Writing points file {}.'.format(rasterFileInfo['pointsFn']))
			print('Preparing...')
			schema = {
				'geometry': 'Point',
				'properties': {field: 'float', 'cellArea': 'float'},
			}
			with fiona.open(rasterFileInfo['pointsFn'], 'w', crs=outCrs, driver='ESRI Shapefile', schema = schema) as output:
				records = []
				count = 0
				for xCell in range(numXCells):
					for yCell in range(numYCells):
						x = commonBounds['x'][0] + xCell*xCellSize + xCellSize/2
						y = commonBounds['y'][1] - (numYCells-yCell)*yCellSize + yCellSize/2
						#point = Point(x, y)
						if raster[yCell][xCell] > 0:
							count = count+1
							records.append({
								'geometry': {
									'type': 'Point',
									'coordinates': (x, y)
								},
								'properties': {
									field: raster[yCell][xCell],
									'cellArea': xCellSize*xCellSize
								},
							})
				print('Writing...')
				print('Count: '+str(count))
				output.writerecords(records)
				print('Done.')

# Converts a polygon file (plus an optional joined csv data file) into a raster, based on
# the specified field
def convertPolyToRaster(polyFileInfo, outRasterFileInfo, field, **kwargs):
	kwargs['reverse'] = False
	__convertPolyRaster(polyFileInfo, outRasterFileInfo, field, **kwargs)

def convertRasterToPoly(rasterFileInfo, outPolyFileInfo, field, **kwargs):
	kwargs['reverse'] = True
	__convertPolyRaster(outPolyFileInfo, rasterFileInfo, field, **kwargs)

if __name__ == "__main__":
	t = time.time()
	# Temp
	#convertAuShpToSvg('J:/GIS DataBase/NZ Area Units/AU2013_GV_Clipped_nomulti.shp', 'J:/GIS Database/NZ Area Units/AU2013_GV_Clipped.svg')
	# inFn = 'outputs/Run 61 - 2016-03-13 21-43-36/Phytophthora - Visitors/Visitors_Phytophthora_Airport_post-inspect_Yearly_updated.shp'
	# outFn = 'outputs/Run 61 - 2016-03-13 21-43-36/Phytophthora - Visitors/Visitors_Phytophthora_Airport_post-inspect_Yearly_updated_au.csv'
	# bufInt(inFn, outFn, 500)
	#convertPolyShpToSvg('inputs/maps/SA2_2016_AUST_GDA94_nomulti.shp', 'inputs/maps/SA2_2016_AUST.svg', 'SA2_MAIN16')
	#convertPolyShpToSvg('inputs/nzoutline_nomulti.shp', 'inputs/nzoutline.svg', 'UA13_V2')
	
	# Example 1 (selected)
	
	# Convert polygons to raster (but output point grid instead of raster)
	# convertPolyToRaster(
		# {'vectorFn': 'temp/selected.shp'},
		# {'pointsFn': 'temp/selected_points.shp', 'rasterFn': 'temp/selected.tiff', 'cellSize': 5000},
		# 'exposure_8',
		# hitPointsFn = 'temp/hits.shp'
	# )
	# shpProjFn = 'temp/selected_points_wgs84_3.shp'
	# changeLayerProjection('temp/selected_points.shp', shpProjFn, 4326)
	# import subprocess
	# radius = 10
	# subprocess.call(['python', '-u', 'heatmap.py', shpProjFn, '--width', '80', '-o', 'temp/dispersal.tiff', '-r', str(radius)])
	# # Read in the JSON, use the original generated points for the bounds/CRS information, and then output to a new tiff file
	# # Make sure to pass in the radius from above
	# convertJsonHeatmapToRaster('temp/dispersal.tiff.json', 'temp/selected_points.shp', 'temp/dispersal.out.tiff', radius = radius)

	
	# Example 2 (selected)
	
	# # Convert polygons to raster tiff
	# convertPolyToRaster(
		# {'vectorFn': 'temp/selected.shp'},
		# {'rasterFn': 'temp/selected.tiff', 'cellSize': 5000},
		# 'exposure_8'
	# )
	# # And go back (only tiff supported as input for now)
	# convertRasterToPoly(
		# {'rasterFn': 'temp/selected.tiff'},
		# {'vectorFn': 'temp/selected.shp', 'vectorKey': 'AU2013', 'vectorKeyName': 'AU2013_NAM', 'outCsvFn': 'temp/selected_out.csv'},
		# 'exposure_8'
	# )
	
	
	# Example 3 (random)
	
	# Do all of NZ
	# convertPolyToRaster(
		# {'vectorFn': 'inputs/AU2013_GV_Clipped_nomulti.shp', 'dataFn': 'temp/exposure_random.csv', 'vectorKey': 'AU2013', 'dataKey': 'Code'},
		# {'rasterFn': 'temp/exposure_random.tiff', 'cellSize': 5000},
		# 'uExposures',
		# pointsPerPoly = 1000,
		# # pointsPerCell is slow, and doesn't buy almost any additional accuracy on poly -> raster
		# pointsPerCell = 0,
		# # Leave approx = true. Too slow otherwise
		# approx = True
	# )
	# convertRasterToPoly(
		# {'rasterFn': 'temp/exposure_random.tiff'},
		# {'vectorFn': 'inputs/AU2013_GV_Clipped_nomulti.shp', 'vectorKey': 'AU2013', 'outCsvFn': 'temp/exposure_random_out.csv'},
		# 'uExposures',
		# pointsPerPoly = 1000,
		# # pointsPerCell still slow, but (almost) guarantees one point per cell. Improves accuracy slightly (but maybe where it counts)
		# pointsPerCell = 1,
		# # Leave approx = true. Too slow otherwise
		# approx = True
	# )
	
	
	# Example 4 (sequence, top to bottom)
	
	# Do all of NZ, with values = sequence of AU (roughly, lowest top of NZ, largest bottom of NZ)
	# convertPolyToRaster(
		# {'vectorFn': 'inputs/AU2013_GV_Clipped_nomulti.shp', 'dataFn': 'temp/exposure_sequence.csv', 'vectorKey': 'AU2013', 'dataKey': 'Code'},
		# {'rasterFn': 'temp/exposure_sequence.tiff', 'cellSize': 1000,
			# # Note, takes a long while to write out points file for some reason. (Hmm, maybe because it's about 160MB.)
			# 'pointsFn': 'temp/exposure_sequence_points.shp'
		# },
		# 'uExposures',
		# pointsPerPoly = 1000,
		# pointsPerCell = 0,
		# approx = True
	# )
	# convertRasterToPoly(
		# {'rasterFn': 'temp/exposure_sequence.tiff'},
		# {'vectorFn': 'inputs/AU2013_GV_Clipped_nomulti.shp', 'vectorKey': 'AU2013', 'outCsvFn': 'temp/exposure_sequence_out.csv'},
		# 'uExposures',
		# pointsPerPoly = 1000,
		# pointsPerCell = 1,
		# approx = True
	# )
	# convertRasterToPoly(
		# {'rasterFn': 'temp/cleaned.tif'},
		# {'vectorFn': 'temp/SA2_2016_AUST_GDA94_nomulti.shp', 'vectorKey': 'SA2_MAIN16', 'vectorKeyName': 'SA2_NAME16', 'outCsvFn': 'temp/out.csv', 'outputDistribution': 'flat'},
		# 'LUS',
		# pointsPerPoly = 100,
		# pointsPerCell = 0,
		# approx = True
	# )
	
	# Example 5 (Australia)
	
	# convertPolyToRaster(
	# 	{'vectorFn': 'temp/SA2_2016_AUST_GDA94_nomulti.shp', 'dataFn': 'temp/AGM - All Items - 1-110-1 2-110-1 3-110-1.csv', 'vectorKey': 'SA2_MAIN16', 'dataKey': 'Code'},
	# 	{'rasterFn': 'temp/poly_to_raster_aus_agm.tiff', 'cellSize': 5000},
	# 	'uExposures',
	# 	pointsPerPoly = 1000,
	# 	# pointsPerCell is slow, and doesn't buy almost any additional accuracy on poly -> raster
	# 	pointsPerCell = 0,
	# 	# Leave approx = true. Too slow otherwise
	# 	approx = True
	# )

	# print("Time taken: {:.3f}s".format(time.time()-t))
	

if __name__ == "__main__":
	shpFn = 'inputs/10kmHexClippedNZTM/nzoutline.shp'
	svgFn = 'inputs/10kmHexClippedNZTM/nzoutline.svg'
	convertPolyShpToSvg(shpFn, svgFn, codeField = 'Code', simplify = 500)
	
	# import pandas as pd

	# file_path = 'inputs/10kmHexClippedNZTM/10kmHexClippedNZTM.csv'
	# df = pd.read_csv(file_path)
	# df['Code'] = df['Code'].astype(str)
	# df = df[['Code','EA_Name']]
	# json_2d_array = df.values.tolist()
	# df.to_json('inputs/10kmHexClippedNZTM/10kmHexClippedNZTM.json', orient='values', indent=2)
