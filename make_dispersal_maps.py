import  _env, os, csv, time, glob
from bidb import DB
from utils import *
from maputils import *
from myheatmap import *


import pandas as pd


# def create_db(xlsFn):
# 	csvFns = []
# 	xls = pd.ExcelFile(xlsFn)
	
# 	for i, s in enumerate(xls.sheet_names):
# 		df = xls.parse(sheet_name=s, index_col=None, na_values=['NA'])
# 		df.to_csv(os.path.join(outputDir,f'{s}.csv'))
# 		csvFns.append(os.path.join(outputDir,f'{s}.csv'))

# 	try:
# 		os.remove(os.path.join(outputDir,'dispersal.sqlite'))
# 	except Exception as e:
# 		print("An exception occurred:", str(e))
	
# 	csvdb.open(csvFns, f'{outputDir}/dispersal.sqlite')

# 	for csvFn in csvFns:
# 		os.remove(csvFn)
		

			
def makeLandSuit(scenarioId):
	outputDir = f'outputs/scenario{scenarioId}'
	
	with open('inputs/landcover/land_cover.csv', newline='') as file:
		lu = {row['Code']: row for row in csv.DictReader(file)}
	ls={}
	
	# with DB(os.path.join(outputDir,'dispersal.sqlite')) as db:	
	with serverDb() as db:
		# rs = db.query("""select landcover.id as landcover, suitability from landsuitability inner join landcover on landSuitability.landcover = landcover.name""")
		rs = db.query("""select * from landsuitability where scenarioId = ?""",[scenarioId])
		suit_map = {}
		for i, row in enumerate(rs):
			suit_map[float(i)] = float(row['suitability'])
		# print(suit_map)
	
	for code in lu.keys():
		LUVec = []
		for i in range(1, 14):
			LUVec.append(float(lu[code]['v'+str(i)+'.0']))
		LUVec = normalise(LUVec)
		suit = 0
		for i,ele in enumerate(LUVec):
			suit+=ele*suit_map[i]
		ls[code] = suit
		
	with open(os.path.join(outputDir, 'land_suit.csv'), 'w') as f:
		f.write("%s,%s\n"%('Code','Suitability'))
		for key in ls.keys():
			f.write("%s,%s\n"%(key,ls[key]))

			
def make_dispersal_maps(scenarioId, sd = 0.1):	
	outputDir = f'outputs/scenario{scenarioId}'
	cellSize = 1000
	
	makeLandSuit(scenarioId)
	csvLSFn = os.path.join(outputDir, 'land_suit.csv')
	rasLSFn = os.path.join(outputDir, 'land_suit.tiff')
	
		
	convertPolyToRaster(
		# {'vectorFn': 'inputs/AU2013_GV_Clipped_nomulti.shp', 'dataFn': csvLSFn, 'vectorKey': 'AU2013', 'dataKey': 'Code'},
		{'vectorFn': 'inputs/10kmHexClippedNZTM/10kmHexClippedNZTM.shp', 'dataFn': csvLSFn, 'vectorKey': 'Code', 'dataKey': 'Code'},
		{'rasterFn': rasLSFn, 'cellSize': cellSize },
		'Suitability',
		pointsPerPoly = 1000,
		pointsPerCell = 0,
		approx = True
	)
	
	
	for monthId in range(0, 12):
		print('Updating Dispersal '+month(monthId))
		
		csvExpFn = os.path.join(outputDir, 'Exposure_Pests_'+month(monthId)+'.csv')
		csvDisFn = os.path.join(outputDir, 'Dispersal_Pests_'+month(monthId)+'.csv')
		rasExpFn = os.path.join(outputDir, 'Exposure_Pests_'+month(monthId)+'.tiff')
		rasDisFn = os.path.join(outputDir, 'Dispersal_Pests_'+month(monthId)+'.tiff')
		
		st = time.time()
			
		convertPolyToRaster(
			# {'vectorFn': 'inputs/AU2013_GV_Clipped_nomulti.shp', 'dataFn': csvExpFn, 'vectorKey': 'AU2013', 'dataKey': 'Code'},
			{'vectorFn': 'inputs/10kmHexClippedNZTM/10kmHexClippedNZTM.shp', 'dataFn': csvExpFn, 'vectorKey': 'Code', 'dataKey': 'Code'},
			{'rasterFn': rasExpFn, 'cellSize': cellSize },
			'uExposures',
			pointsPerPoly = 1000,
			pointsPerCell = 0,
			approx = True
		)		
		
		print("Poly to Raster time: {}s".format(time.time() - st))
		st = time.time()
		
		generateHeatMap(
				{'rasterFn': rasLSFn},
				{'rasterFn': rasExpFn},
				{'rasterFn': rasDisFn},
				sd = sd #radius/3
		)
		
		print("HeatMap time: {}s".format(time.time() - st))
		st = time.time()
		
		convertRasterToPoly(
			{'rasterFn': rasDisFn},
			# {'vectorFn': 'inputs/AU2013_GV_Clipped_nomulti.shp', 'vectorKey': 'AU2013', 'vectorKeyName': 'AU2013_NAM', 'outCsvFn': csvDisFn},
			{'vectorFn': 'inputs/10kmHexClippedNZTM/10kmHexClippedNZTM.shp', 'vectorKey': 'Code', 'vectorKeyName': 'EA_Name', 'outCsvFn': csvDisFn},
			'uDisperses',
			pointsPerPoly = 1000,
			pointsPerCell = 0,
			approx = True
		)	
		
		print("Raster to Poly time: {}s".format(time.time() - st))

		st = time.time()
		


# if __name__ == "__main__":
# 	for case in [
# 		# 'scenario11', #Plum Pox
# 		# 'scenario12', #CL_viroid
# 		# 'Xylella',
# 		# 'scenario10', #Liberibacter
# 		# 'scenario9', # 'SOD',
# 		# 'scenario2' # 'Guignardia'
# 		'Liberibacter',
# 		'Liberibacter_NoVec',
# 		'Guignardia',
# 		'Guignardia_NoTreat',
# 		'Guignardia_Climate',
# 		]:
# 		outputDir = f'outputs/{case}'
# 		inputsDir = 'inputs'

# 		create_db(os.path.join(outputDir,'pest_parameters.xls'))	
		
# 		sd = 0.1
			
# 		make_dispersal_maps(sd)