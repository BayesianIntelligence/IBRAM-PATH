import _env, os, argparse, shutil, glob

import utils
from bidb import DB

from make_entry_table import make_entry_tables
from make_exposure_maps import make_exposure_maps
from make_dispersal_maps import make_dispersal_maps
from make_establishment_maps import make_establishment_maps

serverDb = utils.serverDb

ap = argparse.ArgumentParser()
ap.add_argument('--id', type=int, default=None, help='The ID to assign this run')
args = ap.parse_args()


scenarioId = args.id
	
outputDir = f'outputs/scenario{scenarioId}'
if os.path.exists(outputDir):
	shutil.rmtree(outputDir)
os.makedirs(outputDir, exist_ok=True)

print(outputDir)

with serverDb() as db:
	scenario = db.queryRow("""select * from scenario where id = ?""", [scenarioId])
	project = db.queryRow("""select * from project where id = ?""", [scenario['projectId']])
	
	sd = project['dispersalSd']
	burnIn = project['burnIn']
	runLength = project['runLength']
	climateMap = project['climateMap'] or 'Climate Temperate'
		
	db.replace('scenario', {'complete': None, 'status': 'Making Entry Table', 'id': scenarioId}, 'id')
	make_entry_tables(scenarioId)
	
	db.replace('scenario', {'complete': None, 'status': 'Making Exposure Maps', 'id': scenarioId}, 'id')
	make_exposure_maps(scenarioId)
	
	db.replace('scenario', {'complete': None, 'status': 'Making Dispersal Maps', 'id': scenarioId}, 'id')
	make_dispersal_maps(scenarioId, sd)
	
	db.replace('scenario', {'complete': None, 'status': 'Making Establishment Maps', 'id': scenarioId}, 'id')
	make_establishment_maps(scenarioId, burnIn, runLength, climateMap)

	for ext in ['tiff', 'dbf', 'shp', 'shx', 'cpg']:
		for file in glob.glob(os.path.join(outputDir, f'*.{ext}')):
			os.remove(file)

	db.replace('scenario', {'complete': True, 'status': 'Updated', 'id': scenarioId, 'processId': None}, 'id')

	