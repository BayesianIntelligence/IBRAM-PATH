import time, os, sys
from _lib.utils import *

from EquationModel import EquationModel

import pandas as pd


def make_entry_tables(scenarioId):
	st = time.time()
	print('creating entry table', scenarioId)
	
	# preBorderNet = Net('bns/Preborder.xdsl')
	preBorderModel = EquationModel(get_equations('bns/Preborder.xdsl'))
	
	with serverDb() as db:
		
		carriers = db.queryRows("""select * from carrier where scenarioId = ?""", [scenarioId])
		entries_df = pd.DataFrame(carriers, columns=carriers[0].keys() if carriers else [])
		
		for index, entry in entries_df.iterrows():
			for monthId in range(0,12):
				month_name = month(monthId)
				row = db.queryRow(f"""SELECT carrier.carrier, carrier.subItem, carrier.item, carrier.itemId, carrier.source,
									units.{month_name} AS units,
									carrierRate.{month_name} AS carrierRate,
									carriersPerUnit.{month_name} AS carriersPerUnit,
									carrierInfectionRate.{month_name} AS infectionRate,
									preborderDetection.detectionRate,
									preborderDetection.treatmentRateForUndetected,
									preborderDetection.treatmentEfficacy
								FROM carrier
								LEFT JOIN units ON units.subItem = carrier.subItem AND units.itemId = carrier.itemId AND units.source = carrier.source AND units.scenarioId = carrier.scenarioId
								LEFT JOIN carrierRate ON carrierRate.carrier = carrier.carrier AND carrierRate.subItem = carrier.subItem AND carrierRate.itemId = carrier.itemId AND carrierRate.source = carrier.source AND carrierRate.scenarioId = carrier.scenarioId
								LEFT JOIN carriersPerUnit ON carriersPerUnit.carrier = carrier.carrier AND carriersPerUnit.subItem = carrier.subItem AND carriersPerUnit.itemId = carrier.itemId AND carriersPerUnit.scenarioId = carrier.scenarioId
								LEFT JOIN carrierInfectionRate ON carrierInfectionRate.carrier = carrier.carrier AND carrierInfectionRate.subItem = carrier.subItem AND carrierInfectionRate.itemId = carrier.itemId AND carrierInfectionRate.source = carrier.source AND carrierInfectionRate.scenarioId = carrier.scenarioId
								LEFT JOIN preborderDetection ON preborderDetection.carrier = carrier.carrier AND preborderDetection.subItem = carrier.subItem AND preborderDetection.itemId = carrier.itemId AND preborderDetection.source = carrier.source AND preborderDetection.scenarioId = carrier.scenarioId
								WHERE carrier.scenarioId = ? AND carrier.carrier = ? AND carrier.subItem = ? AND carrier.item = ? AND carrier.itemId = ? AND carrier.source = ?""", [entry['scenarioId'], entry['carrier'], entry['subItem'], entry['item'], entry['itemId'], entry['source']])
				

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