import time, os, sys
from _lib.utils import *

from EquationModel import EquationModel

import pandas as pd


def make_entry_tables(scenarioId):
	st = time.time()
	print('creating entry table', scenarioId)
	
	# preBorderNet = Net('bns/Preborder.xdsl')
	preBorderModel = EquationModel(get_equations('bns/Preborder.json'))
	
	with serverDb() as db:
		
		carriers = db.queryRows("""select * from carrier where scenarioId = ?""", [scenarioId])
		entries_df = pd.DataFrame(carriers, columns=carriers[0].keys() if carriers else [])
		
		for index, entry in entries_df.iterrows():
			for monthId in range(0,12):
				month_name = month(monthId)
				row = db.queryRow(f"""SELECT carrier.carrier, carrier.item, carrier.pathway, carrier.pathwayId, carrier.source,
									units.{month_name} AS units,
									carrierRate.{month_name} AS carrierRate,
									carriersPerUnit.{month_name} AS carriersPerUnit,
									carrierInfectionRate.{month_name} AS infectionRate,
									preborderDetection.detectionRate,
									preborderDetection.treatmentRateForUndetected,
									preborderDetection.treatmentEfficacy
								FROM carrier
								LEFT JOIN units ON units.item = carrier.item AND units.pathwayId = carrier.pathwayId AND units.source = carrier.source AND units.scenarioId = carrier.scenarioId
								LEFT JOIN carrierRate ON carrierRate.carrier = carrier.carrier AND carrierRate.item = carrier.item AND carrierRate.pathwayId = carrier.pathwayId AND carrierRate.source = carrier.source AND carrierRate.scenarioId = carrier.scenarioId
								LEFT JOIN carriersPerUnit ON carriersPerUnit.carrier = carrier.carrier AND carriersPerUnit.item = carrier.item AND carriersPerUnit.pathwayId = carrier.pathwayId AND carriersPerUnit.scenarioId = carrier.scenarioId
								LEFT JOIN carrierInfectionRate ON carrierInfectionRate.carrier = carrier.carrier AND carrierInfectionRate.item = carrier.item AND carrierInfectionRate.pathwayId = carrier.pathwayId AND carrierInfectionRate.source = carrier.source AND carrierInfectionRate.scenarioId = carrier.scenarioId
								LEFT JOIN preborderDetection ON preborderDetection.carrier = carrier.carrier AND preborderDetection.item = carrier.item AND preborderDetection.pathwayId = carrier.pathwayId AND preborderDetection.source = carrier.source AND preborderDetection.scenarioId = carrier.scenarioId
								WHERE carrier.scenarioId = ? AND carrier.carrier = ? AND carrier.item = ? AND carrier.pathway = ? AND carrier.pathwayId = ? AND carrier.source = ?""", [entry['scenarioId'], entry['carrier'], entry['item'], entry['pathway'], entry['pathwayId'], entry['source']])
				

				for node in 'units,carrierRate,carriersPerUnit,infectionRate,detectionRate,treatmentRateForUndetected,treatmentEfficacy'.split(','):
					# preBorderNet.node(node).equation(f'{node}='+str(row[node]))
					preBorderModel.update_equation(node, str(row[node]))

				entries_df.at[index, month_name] = preBorderModel.get('Infected_Carriers').mean()
				
				# preBorderNet.update()
				# entries_df.at[index, month_name] = preBorderNet.node('Infected_Carriers')._equationMean()


				
		entries_df = entries_df.drop(columns=['id','scenarioId'])
		
		outputDir = f'outputs/scenario{scenarioId}'
		outCsvFn = "entries.csv"
		entries_df.to_csv(os.path.join(outputDir, outCsvFn), index=False)
		
		print(entries_df)

		print("Time: {}s".format(time.time() - st))

if __name__=="__main__":
	make_entry_tables(1)