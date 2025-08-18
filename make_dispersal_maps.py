
import os, time

import geopandas as gpd
import pandas as pd
import numpy as np
from scipy.spatial.distance import cdist

from functools import reduce

from _lib.utils import *


def apply_gaussian_dispersion(scenarioId, carrier, sigma):
	print('Running', carrier)
	outputDir = f'outputs/scenario{scenarioId}'
	exposureCsvFn = f"exposure_{carrier}.csv".replace(' ','_')
	
	# Load and prepare inputs
	shape_gdf = gpd.read_file('inputs/maps/7kmHexNZ.shp')
	exposure_df = pd.read_csv(os.path.join(outputDir, exposureCsvFn))
	
	# Ensure 'Code' columns are strings for merging
	shape_gdf['Code'] = shape_gdf['Code'].astype(str)
	exposure_df['Code'] = exposure_df['Code'].astype(str)

	# Merge to get spatial info
	merged = shape_gdf.merge(exposure_df, on='Code', how='left').fillna(0)

	# Use centroids for dispersal distance
	centroids = merged.geometry.centroid
	coords = np.array([[pt.x, pt.y] for pt in centroids])
	dist_matrix = cdist(coords, coords)

	# Apply Gaussian kernel
	kernel = np.exp(-0.5 * (dist_matrix / sigma) ** 2)
	kernel /= kernel.sum(axis=1, keepdims=True)  # Normalize
	
	for monthId in range(0,12):
		month_name = month(monthId)

		original_exposures = merged[month_name].values.reshape(-1, 1)

		dispersed = kernel @ original_exposures

		# Rescale to preserve total exposure
		total_original = original_exposures.sum()
		total_dispersed = dispersed.sum()
		if total_dispersed > 0:
			dispersed *= (total_original / total_dispersed)	

		merged[month_name] = dispersed.flatten()
		
	cols = 'Code,Jan,Feb,Mar,Apr,May,Jun,Jul,Aug,Sep,Oct,Nov,Dec'.split(',')
	merged[cols].to_csv(os.path.join(outputDir,  f"dispersal_{carrier}.csv".replace(' ','_')), index=False)
	


def make_dispersal_maps(scenarioId):	
	st = time.time()
	print('creating dispersal maps', scenarioId)
	
	with serverDb() as db:
		carriers = db.queryRows("SELECT * FROM carrierDispersal WHERE scenarioId = ?", [scenarioId])

	for carrier in carriers:
		apply_gaussian_dispersion(scenarioId, carrier['carrier'], sigma=carrier['sd']*100000)
	
	print("Time: {}s".format(time.time() - st))

if __name__=="__main__":
	make_dispersal_maps(1)
	









# def month(mth):
# 	# Throw error if not int
# 	m = int(mth)
# 	if m == -1:
# 		return "Yearly"

# 	months = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(" ")
# 	if m < len(months):
# 		return months[m]
	

# def apply_gaussian_dispersion(scenarioId, carrier, month_name, sigma):
# 	print('Running', carrier, month_name)
# 	outputDir = f'outputs/scenario{scenarioId}'
# 	exposureCsvFn = f"Exposures_{carrier}_{month_name}.csv".replace(' ','_')
	
# 	# Load and prepare inputs
# 	shape_gdf = gpd.read_file('inputs/10kmHexClippedNZTM/10kmHexClippedNZTM.shp')
# 	exposure_df = pd.read_csv(os.path.join(outputDir, exposureCsvFn))
	
# 	# Ensure 'Code' columns are strings for merging
# 	shape_gdf['Code'] = shape_gdf['Code'].astype(str)
# 	exposure_df['Code'] = exposure_df['Code'].astype(str)

# 	# Merge to get spatial info
# 	merged = shape_gdf.merge(exposure_df, on='Code', how='left').fillna({'exposures': 0})

# 	# Use centroids for dispersal distance
# 	centroids = merged.geometry.centroid
# 	coords = np.array([[pt.x, pt.y] for pt in centroids])
# 	dist_matrix = cdist(coords, coords)

# 	# Apply Gaussian kernel
# 	kernel = np.exp(-0.5 * (dist_matrix / sigma) ** 2)
# 	kernel /= kernel.sum(axis=1, keepdims=True)  # Normalize
	
# 	original_exposures = merged['exposures'].values.reshape(-1, 1)
# 	dispersed = kernel @ original_exposures

# 	# Rescale to preserve total exposure
# 	total_original = original_exposures.sum()
# 	total_dispersed = dispersed.sum()
# 	if total_dispersed > 0:
# 		dispersed *= (total_original / total_dispersed)	

# 	merged['dispersed'] = dispersed.flatten()

# 	return merged[['Code', 'dispersed']]


# def make_dispersal_maps(scenarioId):	
# 	print('creating dispersal maps')
# 	outputDir = f'outputs/scenario{scenarioId}'
	
# 	with serverDb() as db:
# 		carriers = db.queryRows("SELECT * FROM carrierDispersal WHERE scenarioId = ?", [scenarioId])

# 	for carrier in carriers:
# 		dfs = []
# 		for monthId in range(0,12):
# 			month_name = month(monthId)
# 			df = apply_gaussian_dispersion(scenarioId, carrier['carrier'], month_name, sigma=carrier['sd']*100000)
# 			df = df.rename(columns={'dispersed': month_name})
# 			dfs.append(df)
# 		df = reduce(lambda left, right: pd.merge(left, right, on='Code', how='outer'), dfs)
# 		df.to_csv(os.path.join(outputDir,  f"Dispersal_{carrier['carrier']}.csv".replace(' ','_')), index=False)


	# carrierIn = {}
	# for carrier in carriers:
	# 	dfs = []
	# 	for monthId in range(0,12):
	# 		month_name = month(monthId)
	# 		df = pd.read_csv(os.path.join(outputDir, f"Dispersal_{carrier}_{month_name}.csv"))
	# 		df = df.rename(columns={'dispersed': month_name})
	# 		dfs.append(df)
	# 	carrierIn[carrier] = reduce(lambda left, right: pd.merge(left, right, on='Code', how='outer'), dfs).set_index('Code')



# def apply_gaussian_dispersion(scenarioId, carrier, month_name, land_suit_df, sigma):
# 	print('Running', carrier, month_name)
# 	outputDir = f'outputs/scenario{scenarioId}'
# 	exposureCsvFn = f"Exposures_{carrier}_{month_name}.csv".replace(' ','_')
# 	dispersedCsvFn = f"Dispersal_{carrier}_{month_name}.csv".replace(' ','_')
	
# 	# Load and prepare inputs
# 	shape_gdf = gpd.read_file('inputs/10kmHexClippedNZTM/10kmHexClippedNZTM.shp')
# 	exposure_df = pd.read_csv(os.path.join(outputDir, exposureCsvFn))
	
# 	# Ensure 'Code' columns are strings for merging
# 	shape_gdf['Code'] = shape_gdf['Code'].astype(str)
# 	exposure_df['Code'] = exposure_df['Code'].astype(str)
# 	land_suit_df['Code'] = land_suit_df['Code'].astype(str)

# 	# Merge exposures and land suitability
# 	merged = shape_gdf.merge(exposure_df, on='Code', how='left').fillna({'exposures': 0})
# 	merged = merged.merge(land_suit_df, on='Code', how='left').fillna({'land_suitability': 0})

# 	# Compute Gaussian distance kernel
# 	centroids = merged.geometry.centroid
# 	coords = np.array([[pt.x, pt.y] for pt in centroids])
# 	dist_matrix = cdist(coords, coords)
# 	kernel = np.exp(-0.5 * (dist_matrix / sigma) ** 2)

# 	# Apply suitability weighting (destination cell suitability)
# 	suitability = merged['land_suitability'].values
# 	suitability_matrix = np.tile(suitability, (kernel.shape[0], 1))
# 	weighted_kernel = kernel * suitability_matrix

# 	# Normalize rows
# 	row_sums = weighted_kernel.sum(axis=1, keepdims=True)
# 	row_sums[row_sums == 0] = 1  # avoid divide-by-zero
# 	weighted_kernel /= row_sums

# 	# Disperse
# 	original_exposures = merged['exposures'].values.reshape(-1, 1)
# 	dispersed = weighted_kernel @ original_exposures
# 	merged['dispersed'] = dispersed.flatten()
# 	merged['diff'] = merged['dispersed'] - merged['exposures']

# 	# Export
# 	merged[['Code', 'exposures', 'land_suitability', 'dispersed', 'diff']].to_csv(os.path.join(outputDir, dispersedCsvFn), index=False)
	
# 	print(carrier, month_name, merged['exposures'].sum(), merged['dispersed'].sum(), merged['diff'].sum())
	
# import geopandas as gpd
# import pandas as pd
# import numpy as np
# from shapely.geometry import Point
# from scipy.spatial.distance import cdist

# def make_land_suitability_map(scenarioId):
# 	with serverDb() as db:
# 		rows = db.query("SELECT * FROM landsuitability WHERE scenarioId = ?", [scenarioId])
# 		suit_map = {row['landcoverId']: float(row['suitability']) for i, row in enumerate(rows)}

# 	# Load land cover proportions
# 	land_cover_df = pd.read_csv('inputs/landcover/land_cover.csv')

# 	# Calculate weighted suitability
# 	def compute_suitability(row):
# 		return sum(row.get(f'v{i}.0', 0) * suit_map.get(i, 0) for i in range(1, 13))

# 	land_cover_df['land_suitability'] = land_cover_df.apply(compute_suitability, axis=1)
	
# 	return land_cover_df[['Code', 'land_suitability']]
	


# def makeLandSuit(scenarioId):
# 	outputDir = f'outputs/scenario{scenarioId}'
	
# 	with open('inputs/landcover/land_cover.csv', newline='') as file:
# 		lu = {row['Code']: row for row in csv.DictReader(file)}
# 	ls={}
	
# 	# with DB(os.path.join(outputDir,'dispersal.sqlite')) as db:	
# 	with serverDb() as db:
# 		# rs = db.query("""select landcover.id as landcover, suitability from landsuitability inner join landcover on landSuitability.landcover = landcover.name""")
# 		rs = db.query("""select * from landsuitability where scenarioId = ?""",[scenarioId])
# 		suit_map = {}
# 		for i, row in enumerate(rs):
# 			suit_map[float(i)] = float(row['suitability'])
# 		# print(suit_map)
	
# 	for code in lu.keys():
# 		LUVec = []
# 		for i in range(1, 14):
# 			LUVec.append(float(lu[code]['v'+str(i)+'.0']))
# 		LUVec = normalise(LUVec)
# 		suit = 0
# 		for i,ele in enumerate(LUVec):
# 			suit+=ele*suit_map[i]
# 		ls[code] = suit
		
# 	with open(os.path.join(outputDir, 'land_suit.csv'), 'w') as f:
# 		f.write("%s,%s\n"%('Code','Suitability'))
# 		for key in ls.keys():
# 			f.write("%s,%s\n"%(key,ls[key]))

# import  _env, os, csv, time, glob
# from bidb import DB
# from utils import *
# from maputils import *
# from myheatmap import *


# import pandas as pd
			
# def makeLandSuit(scenarioId):
# 	outputDir = f'outputs/scenario{scenarioId}'
	
# 	with open('inputs/landcover/land_cover.csv', newline='') as file:
# 		lu = {row['Code']: row for row in csv.DictReader(file)}
# 	ls={}
	
# 	# with DB(os.path.join(outputDir,'dispersal.sqlite')) as db:	
# 	with serverDb() as db:
# 		# rs = db.query("""select landcover.id as landcover, suitability from landsuitability inner join landcover on landSuitability.landcover = landcover.name""")
# 		rs = db.query("""select * from landsuitability where scenarioId = ?""",[scenarioId])
# 		suit_map = {}
# 		for i, row in enumerate(rs):
# 			suit_map[float(i)] = float(row['suitability'])
# 		# print(suit_map)
	
# 	for code in lu.keys():
# 		LUVec = []
# 		for i in range(1, 14):
# 			LUVec.append(float(lu[code]['v'+str(i)+'.0']))
# 		LUVec = normalise(LUVec)
# 		suit = 0
# 		for i,ele in enumerate(LUVec):
# 			suit+=ele*suit_map[i]
# 		ls[code] = suit
		
# 	with open(os.path.join(outputDir, 'land_suit.csv'), 'w') as f:
# 		f.write("%s,%s\n"%('Code','Suitability'))
# 		for key in ls.keys():
# 			f.write("%s,%s\n"%(key,ls[key]))

			
# def make_dispersal_maps(scenarioId, sd = 0.1):	
# 	outputDir = f'outputs/scenario{scenarioId}'
# 	cellSize = 1000
	
# 	makeLandSuit(scenarioId)
# 	csvLSFn = os.path.join(outputDir, 'land_suit.csv')
# 	rasLSFn = os.path.join(outputDir, 'land_suit.tiff')
	
		
# 	convertPolyToRaster(
# 		# {'vectorFn': 'inputs/AU2013_GV_Clipped_nomulti.shp', 'dataFn': csvLSFn, 'vectorKey': 'AU2013', 'dataKey': 'Code'},
# 		{'vectorFn': 'inputs/10kmHexClippedNZTM/10kmHexClippedNZTM.shp', 'dataFn': csvLSFn, 'vectorKey': 'Code', 'dataKey': 'Code'},
# 		{'rasterFn': rasLSFn, 'cellSize': cellSize },
# 		'Suitability',
# 		pointsPerPoly = 1000,
# 		pointsPerCell = 0,
# 		approx = True
# 	)
	
	
# 	for monthId in range(0, 12):
# 		print('Updating Dispersal '+month(monthId))
		
# 		csvExpFn = os.path.join(outputDir, 'Exposure_Pests_'+month(monthId)+'.csv')
# 		csvDisFn = os.path.join(outputDir, 'Dispersal_Pests_'+month(monthId)+'.csv')
# 		rasExpFn = os.path.join(outputDir, 'Exposure_Pests_'+month(monthId)+'.tiff')
# 		rasDisFn = os.path.join(outputDir, 'Dispersal_Pests_'+month(monthId)+'.tiff')
		
# 		st = time.time()
			
# 		convertPolyToRaster(
# 			# {'vectorFn': 'inputs/AU2013_GV_Clipped_nomulti.shp', 'dataFn': csvExpFn, 'vectorKey': 'AU2013', 'dataKey': 'Code'},
# 			{'vectorFn': 'inputs/10kmHexClippedNZTM/10kmHexClippedNZTM.shp', 'dataFn': csvExpFn, 'vectorKey': 'Code', 'dataKey': 'Code'},
# 			{'rasterFn': rasExpFn, 'cellSize': cellSize },
# 			'uExposures',
# 			pointsPerPoly = 1000,
# 			pointsPerCell = 0,
# 			approx = True
# 		)		
		
# 		print("Poly to Raster time: {}s".format(time.time() - st))
# 		st = time.time()
		
# 		generateHeatMap(
# 				{'rasterFn': rasLSFn},
# 				{'rasterFn': rasExpFn},
# 				{'rasterFn': rasDisFn},
# 				sd = sd #radius/3
# 		)
		
# 		print("HeatMap time: {}s".format(time.time() - st))
# 		st = time.time()
		
# 		convertRasterToPoly(
# 			{'rasterFn': rasDisFn},
# 			# {'vectorFn': 'inputs/AU2013_GV_Clipped_nomulti.shp', 'vectorKey': 'AU2013', 'vectorKeyName': 'AU2013_NAM', 'outCsvFn': csvDisFn},
# 			{'vectorFn': 'inputs/10kmHexClippedNZTM/10kmHexClippedNZTM.shp', 'vectorKey': 'Code', 'vectorKeyName': 'EA_Name', 'outCsvFn': csvDisFn},
# 			'uDisperses',
# 			pointsPerPoly = 1000,
# 			pointsPerCell = 0,
# 			approx = True
# 		)	
		
# 		print("Raster to Poly time: {}s".format(time.time() - st))

# 		st = time.time()
		