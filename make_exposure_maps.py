import time, os, re, glob, math

# from _lib.bni_smile import *
from _lib.utils import *
from _lib.maputils import *

import pandas as pd

from functools import reduce

from EquationModel import EquationModel

def runPathwayPoint(scenarioId, month_name, pathwayPoint, previousPestQuantity):
	print('Running', pathwayPoint['carrier'], pathwayPoint['item'], pathwayPoint['pathwayPoint'], month_name, previousPestQuantity)
	# return previousPestQuantity
		
	inputsDir = f'inputs'
	# escapeNet = Net("bns/Escape.xdsl")
	# pathwayPointNet = Net("bns/PathwayPoint.xdsl")
	escapeModel = EquationModel(get_equations('bns/Escape.xdsl'))
	pathwayPointModel = EquationModel(get_equations('bns/PathwayPoint.xdsl'))
	
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

		# pathwayPointNet.node("proportionToHere").setEquation(f"proportionToHere={point['proportionToHere']}")
		# pathwayPointModel.update_equation('proportionToHere', str(point['proportionToHere']))
		# pathwayPointNet.update()
		
		# nextPestQuantity+=pathwayPointNet.node("nextPestQuantity")._equationMean()
		# points_df.at[index, 'exposures'] = pathwayPointNet.node('exposures')._equationMean()
		# nextPestQuantity+=pathwayPointModel.get('nextPestQuantity').mean()
		# points_df.at[index, 'exposures'] = pathwayPointModel.get('exposures').mean()
		
	print(f"Unique cached values: {len(cache)} out of {len(points_df)} rows")
		
	outCsvFn = os.path.join(f'outputs/scenario{scenarioId}', f"{pathwayPoint['carrier']}_{pathwayPoint['item']}_{pathwayPoint['pathwayPoint']}_{month_name}.csv".replace(" ","_"))
	outShpFn = re.sub(r'\.csv$', '.shp', outCsvFn)
	points_df.to_csv(outCsvFn, index=False)
	
	if pathwayPoint['shape'] == 'point':
		convertCsvToShp(outCsvFn, outShpFn, OrderedDict([('exposures', {'type': 'float', 'csvName': 'exposures'}),]), r'.*')
		bufInt(outShpFn, outCsvFn, buffer = 500, gran = 'hex')
	
	# print(nextPestQuantity)
	return nextPestQuantity
		

# def runPathwayPoint(scenarioId, month_name, pathwayPoint, previousPestQuantity):
# 	# from convert import convertCsvToShp, bufInt  # Ensure these are imported
# 	# from equation_model import EquationModel  # Adjust to your actual import
# 	# from your_escape_model import escapeModel, pathwayPointModel  # Adjust as needed

# 	print('Running', pathwayPoint['carrier'], pathwayPoint['item'], pathwayPoint['pathwayPoint'], month_name, previousPestQuantity)

# 	t0 = time.perf_counter()

# 	inputsDir = 'inputs'
# 	escapeModel = EquationModel(get_equations('bns/Escape.xdsl'))
# 	pathwayPointModel = EquationModel(get_equations('bns/PathwayPoint.xdsl'))

# 	t1 = time.perf_counter()
# 	pathwayPointModel.update_equation("previousPestQuantity", str(previousPestQuantity))
# 	for node in 'treatmentEfficacy,detectionRate,treatmentRateForUndetected'.split(','):
# 		pathwayPointModel.update_equation(node, str(pathwayPoint[node]))
# 	t2 = time.perf_counter()

# 	for node in 'carrierDailyMortalityRate,pathogenDailyMortalityRate,carrierDailyExitRate,timeAtSite'.split(','):
# 		escapeModel.update_equation(node, str(pathwayPoint[node]))
# 	t3 = time.perf_counter()

# 	pathwayPointModel.update_equation('exit', str(escapeModel.get('exit').mean()))
# 	pathwayPointModel.update_equation('survive', str(escapeModel.get('survive').mean()))
# 	t4 = time.perf_counter()

# 	points_df = pd.read_csv(open(os.path.join(inputsDir, 'pathway', pathwayPoint["tableName"] + ".csv"), newline=''))
# 	t5 = time.perf_counter()

# 	# nextPestQuantity = 0
# 	# for index, point in points_df.iterrows():
# 	# 	pathwayPointModel.update_equation('proportionToHere', str(point['proportionToHere']))
# 	# 	nextPestQuantity += pathwayPointModel.get('nextPestQuantity').mean()
# 	# 	points_df.at[index, 'exposures'] = pathwayPointModel.get('exposures').mean()
		
# 	cache = {}
# 	nextPestQuantity = 0
# 	exposures = []

# 	ROUND_DIGITS = 6  # Set based on desired tolerance

# 	for index, point in points_df.iterrows():
# 		prop = round(float(point['proportionToHere']), ROUND_DIGITS)

# 		if prop in cache:
# 			npq, exp = cache[prop]
# 		else:
# 			pathwayPointModel.update_equation('proportionToHere', str(prop))
# 			npq = pathwayPointModel.get('nextPestQuantity').mean()
# 			exp = pathwayPointModel.get('exposures').mean()
# 			cache[prop] = (npq, exp)

# 		nextPestQuantity += npq
# 		exposures.append(exp)

# 	points_df['exposures'] = exposures
	

# 	t6 = time.perf_counter()

# 	outCsvFn = os.path.join(f'outputs/scenario{scenarioId}', f"{pathwayPoint['carrier']}_{pathwayPoint['item']}_{pathwayPoint['pathwayPoint']}_{month_name}.csv".replace(" ", "_"))
# 	outShpFn = re.sub(r'\.csv$', '.shp', outCsvFn)
# 	points_df.to_csv(outCsvFn, index=False)
# 	t7 = time.perf_counter()

# 	if pathwayPoint['shape'] == 'point':
# 		convertCsvToShp(outCsvFn, outShpFn, OrderedDict([('exposures', {'type': 'float', 'csvName': 'exposures'})]), r'.*')
# 		bufInt(outShpFn, outCsvFn, buffer=500, gran='hex')
# 	t8 = time.perf_counter()

# 	print(f"Timings (in seconds):")
# 	print(f"  Setup + InputsDir:          {t1 - t0:.4f}")
# 	print(f"  Update pathway equations:   {t2 - t1:.4f}")
# 	print(f"  Update escape equations:    {t3 - t2:.4f}")
# 	print(f"  Update exit/survive:        {t4 - t3:.4f}")
# 	print(f"  Read CSV:                   {t5 - t4:.4f}")
# 	print(f"  Loop over points_df:        {t6 - t5:.4f}")
# 	print(f"  Write CSV:                  {t7 - t6:.4f}")
# 	print(f"  Convert/Buffer shapefile:   {t8 - t7:.4f}")
# 	print(f"  Total runtime:              {t8 - t0:.4f}")

# 	return nextPestQuantity

def runPathway(scenarioId, itemId, carrier, month_name, pestQuantity):
	with serverDb() as db:
		pathway = db.queryRows(f"""SELECT pd.carrier, pd.item, pd.itemId, pd.pathwayPoint, pd.pathwayPointId, pp.tableName, pp.shape, pp.timeAtSite,
									pd.detectionRate, 
									pd.treatmentRateForUndetected, 
									pd.treatmentEfficacy, 
									cdmr.{month_name} AS carrierDailyMortalityRate, 
									pdmr.{month_name} AS pathogenDailyMortalityRate, 
									cder.{month_name} AS carrierDailyExitRate 
							   FROM pathwayDetection pd 
							   LEFT JOIN pathwayPoint pp ON pp.itemId = pd.itemId AND pp.name = pd.pathwayPoint AND pp.id = pd.pathwayPointId
							   LEFT JOIN carrierDailyMortalityRate cdmr ON cdmr.carrier = pd.carrier AND cdmr.item = pd.item AND cdmr.itemId = pd.itemId AND cdmr.pathwayPoint = pd.pathwayPoint AND cdmr.pathwayPointId = pd.pathwayPointId AND cdmr.scenarioId = pd.scenarioId 
							   LEFT JOIN pathogenDailyMortalityRate pdmr ON pdmr.carrier = pd.carrier AND pdmr.item = pd.item AND pdmr.itemId = pd.itemId AND pdmr.pathwayPoint = pd.pathwayPoint AND pdmr.pathwayPointId = pd.pathwayPointId AND pdmr.scenarioId = pd.scenarioId 
							   LEFT JOIN carrierDailyExitRate cder ON cder.carrier = pd.carrier AND cder.item = pd.item AND cder.itemId = pd.itemId AND cder.pathwayPoint = pd.pathwayPoint AND cder.pathwayPointId = pd.pathwayPointId AND cder.scenarioId = pd.scenarioId 
							   WHERE pd.scenarioId = ? AND pd.carrier = ? AND pd.itemId = ?""", [scenarioId,carrier,itemId])
	
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
			SELECT DISTINCT c.carrier, pp.item, pp.name 
			FROM carrier c
			LEFT JOIN pathwayPoint pp ON pp.itemId = c.itemId
			WHERE scenarioId = ?""", [scenarioId])
		ep_df = pd.DataFrame(exposurePoints, columns=["carrier", "item", "name"])

	for carrier in ep_df['carrier'].unique():
		aggregateLayers(f'{carrier}')
		
	for carrier, item in ep_df[['carrier', 'item']].drop_duplicates().itertuples(index=False):
		aggregateLayers(f'{carrier}_{item}')
		
	for carrier, item, name in ep_df[['carrier', 'item', 'name']].drop_duplicates().itertuples(index=False):
		aggregateLayers(f'{carrier}_{item}_{name}')
		

def make_exposure_maps(scenarioId):	
	st = time.time()
	print('creating exposure maps', scenarioId)
	outputDir = f'outputs/scenario{scenarioId}'
	outCsvFn = os.path.join(outputDir, "entries.csv")
	entries_df = pd.read_csv(outCsvFn)
	
	entries_df = entries_df.groupby(['carrier', 'itemId'], as_index=False)[['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']].sum()
	
	# print(entries_df)
	# return

	for index, pathway in entries_df.iterrows():
		for monthId in range(12):
			month_name = month(monthId)
			runPathway(scenarioId, pathway['itemId'], pathway['carrier'], month_name, pathway[month_name])
					
	aggregateExposureLayers(scenarioId)
	
	print("Time: {}s".format(time.time() - st))


if __name__=="__main__":
	make_exposure_maps(6)
	make_exposure_maps(7)
	





	
# def aggregateExposureLayers(scenarioId, carrier):
# 	outputDir = f'outputs/scenario{scenarioId}'
	
# 	dfs = []
# 	for monthId in range(0,12):
# 		month_name = month(monthId)
# 		files = glob.glob(os.path.join(outputDir, f'{carrier}_*_{month_name}.csv').replace(' ','_'))
		
# 		month_dfs = []
# 		for file in files:
# 			df = pd.read_csv(file)
# 			df['exposures'] = pd.to_numeric(df['exposures'], errors='coerce')
# 			month_dfs.append(df)
# 			os.remove(file)
		
# 		df = pd.concat(month_dfs).groupby(['Code'], as_index=False)['exposures'].sum()
# 		df = df.rename(columns={'exposures': month_name})
# 		dfs.append(df)
		
# 	df = reduce(lambda left, right: pd.merge(left, right, on='Code', how='outer'), dfs)
# 	df.to_csv(os.path.join(outputDir,  f"exposure_{carrier}.csv".replace(' ','_')), index=False)


# def aggregateExposureLayers(scenarioId, carrier, month_name):
# 	outputDir = f'outputs/scenario{scenarioId}'
# 	files = glob.glob(os.path.join(outputDir, f'{carrier}_*_{month_name}.csv').replace(' ','_'))
	
# 	dfs = []
# 	for file in files:
# 		df = pd.read_csv(file)
# 		df['exposures'] = pd.to_numeric(df['exposures'], errors='coerce')
# 		dfs.append(df)
		
# 	aggregated = pd.concat(dfs).groupby(['Code'], as_index=False)['exposures'].sum()
	
# 	outCsvFn = f"Exposures_{carrier}_{month_name}.csv".replace(' ','_')
# 	aggregated.to_csv(os.path.join(outputDir, outCsvFn), index=False)
# 	# print(carrier, month_name, aggregated['exposures'].sum())


	
# def aggregateExposureLayers(scenarioId):
# 	def load_and_aggregate(files, month_name):
# 		month_dfs = []
# 		for file in files:
# 			df = pd.read_csv(file)
# 			df['exposures'] = pd.to_numeric(df['exposures'], errors='coerce')
# 			month_dfs.append(df)
# 		if not month_dfs:
# 			return pd.DataFrame(columns=['Code', month_name])
# 		df = pd.concat(month_dfs).groupby('Code', as_index=False)['exposures'].sum()
# 		return df.rename(columns={'exposures': month_name})	

# 	with serverDb() as db:
# 		exposurePoints = db.queryRows(f"""SELECT DISTINCT c.carrier, pp.item, pp.name FROM carrier c
# 										LEFT JOIN pathwayPoint pp ON pp.itemId = c.itemId
# 										WHERE scenarioId = ?""", [scenarioId])

# 	outputDir = f'outputs/scenario{scenarioId}'
	
# 	for ep in exposurePoints:
# 		carrier, item, name = ep['carrier'], ep['item'], ep['name']
# 		dfs = []
# 		for monthId in range(12):
# 			month_name = month(monthId)
# 			pattern = f"{carrier}_{item}_{name}_*.csv".replace(' ', '_')
# 			files = glob.glob(os.path.join(outputDir, pattern))
# 			dfs.append(load_and_aggregate(files, month_name))
# 		if dfs:
# 			merged_df = reduce(lambda l, r: pd.merge(l, r, on='Code', how='outer'), dfs)
# 			outfile = f"exposure_{carrier}_{item}_{name}.csv".replace(' ', '_')
# 			merged_df.to_csv(os.path.join(outputDir, outfile), index=False)
			
# 	for carrier in sorted({ep['carrier'] for ep in exposurePoints}):
# 		dfs = []
# 		for monthId in range(12):
# 			month_name = month(monthId)
# 			pattern = f"{carrier}_*.csv".replace(' ', '_')
# 			files = glob.glob(os.path.join(outputDir, pattern))
# 			dfs.append(load_and_aggregate(files, month_name))
# 		if dfs:
# 			merged_df = reduce(lambda l, r: pd.merge(l, r, on='Code', how='outer'), dfs)
# 			outfile = f"exposure_{carrier}.csv".replace(' ', '_')
# 			merged_df.to_csv(os.path.join(outputDir, outfile), index=False)

# def aggregateExposureLayers(scenarioId):
# 	def load_and_aggregate(files, month_name):
# 		month_dfs = []
# 		for file in files:
# 			df = pd.read_csv(file)
# 			df['exposures'] = pd.to_numeric(df['exposures'], errors='coerce')
# 			month_dfs.append(df[['Code', 'exposures']])
# 		if not month_dfs:
# 			return pd.DataFrame(columns=['Code', month_name])
# 		df = pd.concat(month_dfs).groupby('Code', as_index=False)['exposures'].sum()
# 		return df.rename(columns={'exposures': month_name})

# 	with serverDb() as db:
# 		rows = db.queryRows(f"""
# 			SELECT DISTINCT c.carrier, pp.item, pp.name 
# 			FROM carrier c
# 			LEFT JOIN pathwayPoint pp ON pp.itemId = c.itemId
# 			WHERE scenarioId = ?
# 		""", [scenarioId])

# 	outputDir = f'outputs/scenario{scenarioId}'

# 	# Group rows by carrier → item → name
# 	grouped = {}
# 	for row in rows:
# 		carrier = row['carrier']
# 		item = row['item']
# 		name = row['name']
# 		grouped.setdefault(carrier, {}).setdefault(item, set()).add(name)

# 	# Loop through carrier → item → name
# 	for carrier, items in grouped.items():
# 		for item, names in items.items():
# 			for name in names:
# 				dfs = []
# 				for monthId in range(12):
# 					month_name = month(monthId)
# 					pattern = f"{carrier}_{item}_{name}_{month_name}.csv".replace(' ', '_')
# 					files = glob.glob(os.path.join(outputDir, pattern))
# 					dfs.append(load_and_aggregate(files, month_name))
# 				dfs = [df for df in dfs if not df.empty]
# 				if dfs:
# 					merged_df = reduce(lambda l, r: pd.merge(l, r, on='Code', how='outer'), dfs)
# 					outfile = f"exposure_{carrier}_{item}_{name}.csv".replace(' ', '_')
# 					merged_df.to_csv(os.path.join(outputDir, outfile), index=False)


# def aggregateExposureLayers(scenarioId):
# 	with serverDb() as db:
# 		exposurePoints = db.queryRows(f"""
# 			SELECT DISTINCT c.carrier, pp.item, pp.name 
# 			FROM carrier c
# 			LEFT JOIN pathwayPoint pp ON pp.itemId = c.itemId
# 			WHERE scenarioId = ?
# 		""", [scenarioId])

# 	outputDir = f'outputs/scenario{scenarioId}'
	
# 	grouped = {}
	
# 	for ep in exposurePoints:
# 		carrier = ep['carrier']
# 		item = ep['item']
# 		name = ep['name']
		
# 		for monthId in range(12):
# 			month_name = month(monthId)
# 			df = pd.read_csv(os.path.join(outputDir, f"{carrier}_{item}_{name}_{month_name}.csv"))
# 			grouped.setdefault(carrier, {}).setdefault(item, set()).add(df)

		
# 	# for carr, val in grouped.items():
# 	# 	print(key, val)


# from functools import reduce

# def aggregateExposureLayers(scenarioId):
# 	def merge_months(dfs_by_month):
# 		# Merge monthly DataFrames (e.g., Jan, Feb...) on 'Code'
# 		dfs = list(dfs_by_month.values())
# 		if not dfs:
# 			return pd.DataFrame()
# 		return reduce(lambda left, right: pd.merge(left, right, on='Code', how='outer'), dfs)

# 	with serverDb() as db:
# 		exposurePoints = db.queryRows(f"""
# 			SELECT DISTINCT c.carrier, pp.item, pp.name 
# 			FROM carrier c
# 			LEFT JOIN pathwayPoint pp ON pp.itemId = c.itemId
# 			WHERE scenarioId = ?
# 		""", [scenarioId])

# 	outputDir = f'outputs/scenario{scenarioId}'

# 	grouped = {}

# 	for ep in exposurePoints:
# 		carrier = ep['carrier']
# 		item = ep['item']
# 		name = ep['name']

# 		for monthId in range(12):
# 			month_name = month(monthId)
# 			csv_fn = f"{carrier}_{item}_{name}_{month_name}.csv".replace(' ', '_')
# 			csv_path = os.path.join(outputDir, csv_fn)

# 			if os.path.exists(csv_path):
# 				df = pd.read_csv(csv_path)
# 				df['exposures'] = pd.to_numeric(df['exposures'], errors='coerce')
# 				df = df[['Code', 'exposures']].groupby('Code', as_index=False).sum()
# 				df = df.rename(columns={'exposures': month_name})

# 				grouped.setdefault(carrier, {}).setdefault(item, {}).setdefault(name, {})[month_name] = df
# 	print(grouped)

# 	# for carrier, item_dict in grouped.items():
# 	# 	carrier_dfs = []
# 	# 	for item, name_dict in item_dict.items():
# 	# 		item_dfs = []
# 	# 		for name, month_dict in name_dict.items():
# 	# 			# 1. Merge monthly DataFrames for this name
# 	# 			merged_name_df = merge_months(month_dict)
# 	# 			if merged_name_df.empty:
# 	# 				continue
# 	# 			item_dfs.append(merged_name_df)
# 	# 			out_fn = f"exposure_{carrier}_{item}_{name}.csv".replace(' ', '_')
# 	# 			merged_name_df.to_csv(os.path.join(outputDir, out_fn), index=False)

# 	# 		# 2. Merge all names for this carrier+item
# 	# 		if item_dfs:
# 	# 			merged_item_df = reduce(lambda l, r: pd.merge(l, r, on='Code', how='outer'), item_dfs)
# 	# 			carrier_dfs.append(merged_item_df)
# 	# 			out_fn = f"exposure_{carrier}_{item}.csv".replace(' ', '_')
# 	# 			merged_item_df.to_csv(os.path.join(outputDir, out_fn), index=False)

# 	# 	# 3. Merge all items for this carrier
# 	# 	if carrier_dfs:
# 	# 		merged_carrier_df = reduce(lambda l, r: pd.merge(l, r, on='Code', how='outer'), carrier_dfs)
# 	# 		out_fn = f"exposure_{carrier}.csv".replace(' ', '_')
# 	# 		merged_carrier_df.to_csv(os.path.join(outputDir, out_fn), index=False)