import time, os, re, glob, math

# from _lib.bni_smile import *
from _lib.utils import *
from _lib.maputils import *

import pandas as pd

from functools import reduce

from EquationModel import EquationModel

def runPathwayPoint(scenarioId, month_name, pathwayPoint, previousPestQuantity):
	print('Running', pathwayPoint['carrier'], pathwayPoint['pathway'], pathwayPoint['pathwayPoint'], month_name, previousPestQuantity)
	# return previousPestQuantity
		
	inputsDir = f'inputs'
	# escapeNet = Net("bns/Escape.xdsl")
	# pathwayPointNet = Net("bns/PathwayPoint.xdsl")
	escapeModel = EquationModel(get_equations('bns/Escape.json'))
	pathwayPointModel = EquationModel(get_equations('bns/PathwayPoint.json'))
	
	# pathwayPointNet.node("previousPestQuantity").setEquation(f'previousPestQuantity={previousPestQuantity}')
	pathwayPointModel.update_equation("previousPestQuantity", str(previousPestQuantity))
	
	for node in 'treatmentEfficacy,detectionRate,treatmentRateForUndetected'.split(','):
		# pathwayPointNet.node(node).setEquation(f'{node}='+str(pathwayPoint[node]))
		pathwayPointModel.update_equation(node, str(pathwayPoint[node]))
	
	for node in 'carrierDailyMortalityRate,pathogenDailyMortalityRate,carrierDailyExitRate,timeAtSite'.split(','):
		# escapeNet.node(node).setEquation(f'{node}='+str(pathwayPoint[node]))
		escapeModel.update_equation(node, str(pathwayPoint[node]))
	
	# escapeNet.update()
	
	# pathwayPointNet.node("exit").setEquation(f'exit={escapeNet.node("exit")._equationMean()}')
	# pathwayPointNet.node("survive").setEquation(f'survive={escapeNet.node("survive")._equationMean()}')
	pathwayPointModel.update_equation('exit', str(escapeModel.get('exit').mean()))
	pathwayPointModel.update_equation('survive', str(escapeModel.get('survive').mean()))

	points_df = pd.read_csv(open(os.path.join(inputsDir,'pathway',pathwayPoint["tableName"]+".csv"), newline=''))


	cache = {}
	nextPestQuantity = 0
	for index, point in points_df.iterrows():
		prop = round(float(point['proportionToHere']), 6)

		if prop in cache:
			npq, exp = cache[prop]
		else:
			pathwayPointModel.update_equation('proportionToHere', str(prop))
			npq = pathwayPointModel.get('nextPestQuantity').mean()
			exp = pathwayPointModel.get('exposures').mean()
			cache[prop] = (npq, exp)

		nextPestQuantity += npq
		points_df.at[index, 'exposures'] = exp

		
	print(f"Unique cached values: {len(cache)} out of {len(points_df)} rows")
		
	outCsvFn = os.path.join(f'outputs/scenario{scenarioId}', f"{pathwayPoint['carrier']}_{pathwayPoint['pathway']}_{pathwayPoint['pathwayPoint']}_{month_name}.csv".replace(" ","_"))
	outShpFn = re.sub(r'\.csv$', '.shp', outCsvFn)
	points_df.to_csv(outCsvFn, index=False)
	
	if pathwayPoint['shape'] == 'point':
		convertCsvToShp(outCsvFn, outShpFn, OrderedDict([('exposures', {'type': 'float', 'csvName': 'exposures'}),]), r'.*')
		bufInt(outShpFn, outCsvFn, buffer = 500, gran = 'hex')
	
	return nextPestQuantity
		

def runPathway(scenarioId, pathwayId, carrier, month_name, pestQuantity):
	with serverDb() as db:
		pathway = db.queryRows(f"""SELECT pd.carrier, pd.pathway, pd.pathwayId, pd.pathwayPoint, pd.pathwayPointId, pp.tableName, pp.shape, pp.timeAtSite,
									pd.detectionRate, 
									pd.treatmentRateForUndetected, 
									pd.treatmentEfficacy, 
									cdmr.{month_name} AS carrierDailyMortalityRate, 
									pdmr.{month_name} AS pathogenDailyMortalityRate, 
									cder.{month_name} AS carrierDailyExitRate 
							   FROM pathwayDetection pd 
							   LEFT JOIN pathwayPoint pp ON pp.pathwayId = pd.pathwayId AND pp.name = pd.pathwayPoint AND pp.id = pd.pathwayPointId
							   LEFT JOIN carrierDailyMortalityRate cdmr ON cdmr.carrier = pd.carrier AND cdmr.pathway = pd.pathway AND cdmr.pathwayId = pd.pathwayId AND cdmr.pathwayPoint = pd.pathwayPoint AND cdmr.pathwayPointId = pd.pathwayPointId AND cdmr.scenarioId = pd.scenarioId 
							   LEFT JOIN pathogenDailyMortalityRate pdmr ON pdmr.carrier = pd.carrier AND pdmr.pathway = pd.pathway AND pdmr.pathwayId = pd.pathwayId AND pdmr.pathwayPoint = pd.pathwayPoint AND pdmr.pathwayPointId = pd.pathwayPointId AND pdmr.scenarioId = pd.scenarioId 
							   LEFT JOIN carrierDailyExitRate cder ON cder.carrier = pd.carrier AND cder.pathway = pd.pathway AND cder.pathwayId = pd.pathwayId AND cder.pathwayPoint = pd.pathwayPoint AND cder.pathwayPointId = pd.pathwayPointId AND cder.scenarioId = pd.scenarioId 
							   WHERE pd.scenarioId = ? AND pd.carrier = ? AND pd.pathwayId = ?""", [scenarioId,carrier,pathwayId])
	
	for pathwayPoint in pathway:
		pestQuantity = runPathwayPoint(scenarioId, month_name, pathwayPoint, pestQuantity)

	
def aggregateExposureLayers(scenarioId):
	outputDir = f'outputs/scenario{scenarioId}'
	
	def aggregateLayers(prefix):
		dfs = []
		for monthId in range(0,12):
			month_name = month(monthId)
			pattern = f'{prefix}*_{month_name}.csv'.replace(' ','_')
			files = glob.glob(os.path.join(outputDir, pattern))
			
			month_dfs = []
			for file in files:
				# print(file)
				df = pd.read_csv(file)
				df['exposures'] = pd.to_numeric(df['exposures'], errors='coerce')
				month_dfs.append(df)
			df = pd.concat(month_dfs).groupby(['Code'], as_index=False)['exposures'].sum()
			df = df.rename(columns={'exposures': month_name})
			dfs.append(df)
		df = reduce(lambda left, right: pd.merge(left, right, on='Code', how='outer'), dfs)
		df.to_csv(os.path.join(outputDir,  f"exposure_{prefix}.csv".replace(' ','_')), index=False)

	
	with serverDb() as db:
		exposurePoints = db.queryRows(f"""
			SELECT DISTINCT c.carrier, pp.pathway, pp.name 
			FROM carrier c
			LEFT JOIN pathwayPoint pp ON pp.pathwayId = c.pathwayId
			WHERE scenarioId = ?""", [scenarioId])
		ep_df = pd.DataFrame(exposurePoints, columns=["carrier", "pathway", "name"])

	for carrier in ep_df['carrier'].unique():
		aggregateLayers(f'{carrier}')
		
	for carrier, pathway in ep_df[['carrier', 'pathway']].drop_duplicates().itertuples(index=False):
		aggregateLayers(f'{carrier}_{pathway}')
		
	for carrier, pathway, name in ep_df[['carrier', 'pathway', 'name']].drop_duplicates().itertuples(index=False):
		aggregateLayers(f'{carrier}_{pathway}_{name}')
		

def make_exposure_maps(scenarioId):	
	st = time.time()
	print('creating exposure maps', scenarioId)
	outputDir = f'outputs/scenario{scenarioId}'
	outCsvFn = os.path.join(outputDir, "entries.csv")
	entries_df = pd.read_csv(outCsvFn)
	
	entries_df = entries_df.groupby(['carrier', 'pathwayId'], as_index=False)[['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']].sum()
	
	# print(entries_df)
	# return

	for index, pathway in entries_df.iterrows():
		for monthId in range(12):
			month_name = month(monthId)
			runPathway(scenarioId, pathway['pathwayId'], pathway['carrier'], month_name, pathway[month_name])
					
	aggregateExposureLayers(scenarioId)
	
	print("Time: {}s".format(time.time() - st))


if __name__=="__main__":
	make_exposure_maps(6)
	make_exposure_maps(7)
	