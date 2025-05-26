import _env, csv, time, os, sys, re, csvdb
from bni_smile import *
from bidb import DB
from utils import *
from maputils import *

from bni_smile import *

import pandas as pd

# def create_db(xlsFn):
# 	csvFns = []
# 	xls = pd.ExcelFile(xlsFn)
	
# 	for i, s in enumerate(xls.sheet_names):
# 		df = xls.parse(sheet_name=s, index_col=None, na_values=['NA'])
# 		df.to_csv(os.path.join(outputDir,f'{s}.csv'))
# 		csvFns.append(os.path.join(outputDir,f'{s}.csv'))

# 	try:
# 		os.remove(os.path.join(outputDir,'exposure.sqlite'))
# 	except Exception as e:
# 		print("An exception occurred:", str(e))
	
# 	csvdb.open(csvFns, f'{outputDir}/exposure.sqlite')

# 	for csvFn in csvFns:
# 		os.remove(csvFn)


def item_from_id(itemId):
	with serverDb() as db:
		items = db.queryMap("select id, name from item")
	if itemId in items:
		return items[itemId]
	
def vector_from_id(vectorId, scenarioId):
	with serverDb() as db:
		vectors = db.queryMap("select vectorid, name from vector where scenarioId = ?",[scenarioId])
	if vectorId in vectors:
		return vectors[vectorId]
	else:
		return 'None'
	

def handlePathwayPoint_ArrivesAtCountry(scenarioId, itemId, vectorId, monthId):
	# print(scenarioId, itemId, vectorId, monthId)
	
	outputDir = f'outputs/scenario{scenarioId}'
	outCsvFn = os.path.join(outputDir, "Entries.csv")
	entries_df = pd.read_csv(outCsvFn)
	with serverDb() as db:
		totalNextPests = 0
		# subItems = db.queryRows("select * from entries where itemId = ? and (vectorId = ? OR vectorId IS NULL) and scenarioId = ?",[itemId, vectorId, scenarioId])
		subItems = entries_df[(entries_df['itemId'] == itemId) & ((entries_df['vectorId'] == vectorId) | (entries_df['vectorId'].isna())) & (entries_df['scenarioId'] == scenarioId)]
		
		for _, subItem in subItems.iterrows():
			subItem = subItem.to_dict()
			
			pests = float(subItem[month(monthId).lower()])
			totalNextPests += pests

		return totalNextPests


def runBNs(pestQuantity, escapeNet, pathwayPointNet, pathwayStep, pathwayPoint):
	if pestQuantity == 0:
		return 0.0, 0.0, 0.0, 0.0, 0.0
	
	weight = max(1,pestQuantity)*5 if pestQuantity < 20 else max(1,pestQuantity)*2
	n = weight
	p = pestQuantity/weight

	timeAtSite = pathwayPoint["timeAtSite"] if "timeAtSite" in pathwayPoint else pathwayStep["timeAtSite"]		

	escapeNet.node("DailyEscapeRate").setEquation("DailyEscapeRate="+str(pathwayStep['esc'])) 
	escapeNet.node("MortalityRate").setEquation("MortalityRate="+str(pathwayStep['mort']))
	escapeNet.node("TimeAtSite").setEquation("TimeAtSite=Trim("+str(timeAtSite)+",0,100000)")
	escapeNet.update()
	
	proportionThatEscape = escapeNet.node("EscapesAtSite")._equationMean()
	proportionSurvive = escapeNet.node("Survives")._equationMean()
	
	pathwayPointNet.node("PPQ_n").setEquation("PPQ_n={}".format(n))
	pathwayPointNet.node("PPQ_p").setEquation("PPQ_p={}".format(p))
	pathwayPointNet.node("ProportionToHere").setEquation("ProportionToHere="+str(pathwayPoint['proportionToHere']))
	pathwayPointNet.node("ProportionThatEscapeAtSite").setEquation("ProportionThatEscapeAtSite = "+str(proportionThatEscape))
	pathwayPointNet.node("ProportionChange").setEquation("ProportionChange = "+str(proportionSurvive))
	pathwayPointNet.node("DetectionRate").setEquation("DetectionRate = Trim("+str(pathwayStep["detectionRate"])+",0,1)")
	pathwayPointNet.node("TreatmentRateForUndetected").setEquation("TreatmentRateForUndetected = Trim("+str(pathwayStep["treatmentRateForUndetected"])+",0,1)")
	pathwayPointNet.node("TreatmentEfficacy").setEquation("TreatmentEfficacy = Trim("+str(pathwayStep["treatmentEfficacy"])+",0,1)")
	
	pathwayPointNet.update()

	meanPestQuantityArrives = pathwayPointNet.node("PestQuantityArrives")._equationMean()
	meanPestQuantity = pathwayPointNet.node("PestQuantity")._equationMean()
	meanNextPestQuantity = pathwayPointNet.node("NextPestQuantity")._equationMean()
	meanExposures = pathwayPointNet.node("Exposures")._equationMean()
	probExposure = pathwayPointNet.node("AnyExposure")._equationMean()
	
	return meanPestQuantityArrives, meanPestQuantity, meanNextPestQuantity, meanExposures, probExposure

def updatePathwayStep(scenarioId, itemId, vectorId, monthId, pestQuantity, pathwayStep):
	print("Assessing {}".format(pathwayStep["name"]))
	print("pest q:", pestQuantity)
	
	# granName = 'EA_Name'
	extraFields = ['uExposures']#, 'EA_Name']
	# extraFields = ['uQtyArrv','uQty','uNextQty','uExposures','pExposure']
	# if pathwayStep["shape"] == "polygon":
	# 	extraFields += ['uPeSqKm', 'sdPeSqKm',granName]
		
	inputsDir = 'inputs'
	outputDir = f'outputs/scenario{scenarioId}'
	
	pathwayPoints = csv.DictReader(open(os.path.join(inputsDir,'pathway',pathwayStep["tableName"]+".csv"), newline=''))
	with open(os.path.join(outputDir, item_from_id(itemId).replace(" ","_")+"_"+vector_from_id(vectorId, scenarioId).replace(" ","_")+"_"+pathwayStep["name"].replace(" ","_")+"_"+month(monthId)+".csv"), "w", newline='') as file:
		# print(item_from_id(itemId).replace(" ","_")+"_"+vector_from_id(vectorId, scenarioId).replace(" ","_")+"_"+pathwayStep["name"].replace(" ","_")+"_"+month(monthId)+".csv")
		updatedPathwayPoints = csv.DictWriter(file, pathwayPoints.fieldnames+extraFields)

		updatedPathwayPoints.writeheader()
		
		escapeNet = Net("bns/DEF - Escape At Site Template.xdsl")
		pathwayPointNet = Net("bns/Pathway Point Template - quicker.xdsl")

		totalMeanNextPestQuantity = 0
		for pathwayPoint in pathwayPoints:
			pathwayPoint = dict(pathwayPoint)
			
			meanPestQuantityArrives, meanPestQuantity, meanNextPestQuantity, meanExposures, probExposure = runBNs(pestQuantity, escapeNet, pathwayPointNet, pathwayStep, pathwayPoint)

			# pathwayPoint['uQtyArrv'] = meanPestQuantityArrives
			# pathwayPoint['uQty'] = meanPestQuantity
			# pathwayPoint['uNextQty'] = meanNextPestQuantity
			pathwayPoint['uExposures'] = meanExposures
			# pathwayPoint['pExposure'] = probExposure
				
			# if pathwayStep["shape"] == "polygon":
			# 	if float(granLookup[pathwayPoint['Code']]['area_sqkm']) > 0:
			# 		pathwayPoint['uPeSqKm'] = meanExposures/float(granLookup[pathwayPoint['Code']]['area_sqkm'])
			# 	else:
			# 		pathwayPoint['uPeSqKm'] = 0
			# 	pathwayPoint['sdPeSqKm'] = '0'
				# pathwayPoint['EA_Name'] = granLookup[pathwayPoint['Code']]['EA_Name']

			updatedPathwayPoints.writerow(pathwayPoint)

			totalMeanNextPestQuantity += meanNextPestQuantity

	return totalMeanNextPestQuantity
	


def updatePathwaySteps(scenarioId, itemId, vectorId, monthId, pestQuantity, pathwaySequence):
	for pathwayStep in pathwaySequence:
		pestQuantity = updatePathwayStep(scenarioId, itemId, vectorId, monthId, pestQuantity, pathwayStep)


def runPathway(scenarioId, itemId, vectorId, monthId):
	st = time.time()
	
	# with DB(os.path.join(outputDir,'exposure.sqlite')) as db:
	with serverDb() as db:
		if str(vectorId).isdigit():
			pathwaySequence = db.queryRows("""select *, vectorDailyMortalityRate."""+month(monthId)+""" as mort, vectorDailyEscapeRate."""+month(monthId)+""" * vectorTransmissionRate."""+month(monthId)+""" as esc from pathwayPoint 
					left join vectorPathwayDetection on pathwayPoint.id = vectorPathwayDetection.pathwayPointId
					left join vectorDailyEscapeRate on pathwayPoint.id = vectorDailyEscapeRate.pathwayPointId and vectorPathwayDetection.vectorId = vectorDailyEscapeRate.vectorId and vectorPathwayDetection.scenarioId = vectorDailyEscapeRate.scenarioId
					left join vectorDailyMortalityRate on pathwayPoint.id = vectorDailyMortalityRate.pathwayPointId and vectorPathwayDetection.vectorId = vectorDailyMortalityRate.vectorId and vectorPathwayDetection.scenarioId = vectorDailyMortalityRate.scenarioId
					left join vectorTransmissionRate on pathwayPoint.id = vectorTransmissionRate.pathwayPointId and vectorPathwayDetection.vectorId = vectorTransmissionRate.vectorId and vectorPathwayDetection.scenarioId = vectorTransmissionRate.scenarioId
				where pathwayPoint.itemId = ? and vectorPathwayDetection.vectorId = ? and vectorPathwayDetection.scenarioId = ?""", [itemId, vectorId, scenarioId])
		else:
			pathwaySequence = db.queryRows("""select *, itemDailyMortalityRate."""+month(monthId)+""" as mort, itemDailyEscapeRate."""+month(monthId)+""" as esc from pathwayPoint
					left join itemPathwayDetection on pathwayPoint.id = itemPathwayDetection.pathwayPointId
					left join itemDailyEscapeRate on pathwayPoint.id = itemDailyEscapeRate.pathwayPointId and itemPathwayDetection.scenarioId = itemDailyEscapeRate.scenarioId
					left join itemDailyMortalityRate on pathwayPoint.id = itemDailyMortalityRate.pathwayPointId and itemPathwayDetection.scenarioId = itemDailyMortalityRate.scenarioId
				where pathwayPoint.itemId = ? and itemPathwayDetection.scenarioId = ?""", [itemId, scenarioId])

	# print(pathwaySequence)

	pestQuantity = handlePathwayPoint_ArrivesAtCountry(scenarioId, itemId, vectorId, monthId)
	updatePathwaySteps(scenarioId, itemId, vectorId, monthId, pestQuantity, pathwaySequence)

	print("Time: {}s".format(time.time() - st))
		
def makePointLayer(scenarioId, itemId, vectorId, monthId):
	# All outputs to go into the following directory
	#outputDir = settings['outputsDir']+'/scenario'+str(scenarioId)
	# with DB(os.path.join(outputDir,'exposure.sqlite')) as db:
	

	outputDir = f'outputs/scenario{scenarioId}'
	with serverDb() as db:

		pathwaySequence = db.queryRows("""select * from pathwayPoint where itemId = ?""", [itemId])
		
		for pathwayStep in pathwaySequence:
			csvFn = os.path.join(outputDir, item_from_id(itemId).replace(" ","_")+"_"+vector_from_id(vectorId, scenarioId).replace(" ","_")+"_"+pathwayStep["name"].replace(" ","_")+"_"+month(monthId)+".csv")
			shpFn = re.sub(r'\.csv$', '.shp', csvFn)
			
			if pathwayStep['shape'] == 'point':
					convertCsvToShp(csvFn, shpFn, OrderedDict([
							# ('uQtyArrv', {'type': 'float', 'csvName': 'uQtyArrv'}),
							# ('uQty', {'type': 'float', 'csvName': 'uQty'}),
							# ('uNextQty', {'type': 'float', 'csvName': 'uNextQty'}),
							('uExposures', {'type': 'float', 'csvName': 'uExposures'}),
							# ('pExposure', {'type': 'float', 'csvName': 'pExposure'}),
					]), r'.*')
					#maputils.convertPointShpToSvg(shpFn, svgFn)
			elif pathwayStep['shape'] == 'polygon':
					# Do nothing, already in a CSV format that can be used in both GIS (joined to shape file)
					# and interface
					# XXX Maybe create a pre-joined file that doesn't take up space somehow? No idea if possible...
					pass
			else:
					raise "'Shape' in pathwayPoint table not recognised: {}".format(pathwayStep['shape'])

def aggregateDensityLayersPerPathway(scenarioId, monthId, gran = 0):
	outputDir = f'outputs/scenario{scenarioId}'
	# with DB(csvdb.open([os.path.join(outputDir, "entries.csv")])) as db:
	with serverDb() as db:
		myItems = db.queryRows("""select distinct itemId from units where scenarioId = ?""",[scenarioId])
		myVectors = db.queryRows("""select distinct vectorId from vector where scenarioId = ?""",[scenarioId])
		
	# with DB(os.path.join(outputDir,'exposure.sqlite')) as db:
		gran = ['au','mb','hex'][gran]
		
		#outputDir = settings['outputsDir']+'/scenario'+str(scenarioId)
		csvFns = []

		# For each pathway that was run
		for item in myItems:
			for vector in myVectors:
				itemId = item['itemId']
				vectorId = vector['vectorId']
				pathwaySequence = db.queryRows("""select * from pathwayPoint where itemId = ?""", [itemId])
				# print(pathwaySequence)
				for pathwayStep in pathwaySequence:
					print(item_from_id(itemId).replace(" ","_")+"_"+vector_from_id(vectorId, scenarioId).replace(" ","_")+"_"+pathwayStep["name"].replace(" ","_")+"_"+month(monthId)+".csv")
					csvFn = os.path.join(outputDir, item_from_id(itemId).replace(" ","_")+"_"+vector_from_id(vectorId, scenarioId).replace(" ","_")+"_"+pathwayStep["name"].replace(" ","_")+"_"+month(monthId)+".csv")
					if pathwayStep['shape'] == 'point':
						shpFn = re.sub(r'\.csv$', '.shp', csvFn)
						outCsvFn = re.sub(r'\.csv$', '_{}.csv'.format(gran), csvFn)
						# Make compatible shape file
						bufInt(shpFn, outCsvFn, buffer = 500, gran = gran)
						
					else:
						outCsvFn = csvFn
					csvFns.append(outCsvFn)
		outCsvFn = os.path.join(outputDir, "Exposure_Pests_"+month(monthId)+".csv")
		mergeExposureCsvs(csvFns, outCsvFn)



def make_exposure_maps(scenarioId):	
	with serverDb() as db:
		myItems = db.queryRows("""select distinct itemId from units where scenarioId = ?""",[scenarioId])
		myVectors = db.queryRows("""select distinct vectorId from vector where scenarioId = ?""",[scenarioId])


	#Next two line modified for testing
	# myItems = [{'itemId': 11}]
	# for monthId in [7]:
	for monthId in range(0,12):
		for item in myItems:
			for vector in myVectors:
				itemId = item['itemId']
				vectorId = vector['vectorId']
				print(f'\nRunning: {item_from_id(itemId)} {vector_from_id(vectorId, scenarioId)} {month(monthId)}')
				runPathway(scenarioId, itemId, vectorId, monthId)
				makePointLayer(scenarioId, itemId, vectorId, monthId)
				
		aggregateDensityLayersPerPathway(scenarioId, monthId, 2)
		

# # csvFn = os.path.join('inputs', 'AU2013_GV_Clipped.csv')
csvFn = os.path.join('inputs', '10kmHexClippedNZTM', '10kmHexClippedNZTM.csv')
granLookup = {}
with open(csvFn,'r',newline='') as csvFile:
	granCsv = csv.DictReader(csvFile)
	for row in granCsv:
		granLookup[row['Code']] = row


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
		
# 		with DB(os.path.join(outputDir,'exposure.sqlite')) as db:
# 			items = db.queryMap("select id, item from item")
# 			vectors = db.queryMap("select id, vector from vector")

# 		make_exposure_maps()

