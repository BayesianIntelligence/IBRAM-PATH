import _env, csv, time, os, csvdb, sys, argparse
from _lib.bni_smile import *
from bidb import DB
from _lib.utils import *

import pandas as pd

		
def month(mth):
	# Throw error if not int
	m = int(mth)
	if m == -1:
		return "Yearly"

	months = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(" ")
	if m < len(months):
		return months[m]

def make_entry_tables(scenarioId):
	st = time.time()
	print('creating entry table')
	
	preBorderNet = Net('bns/Preborder.xdsl')
		
		
	entries_list = []
	
	with serverDb() as db:
		pathways = [pathway for pathway in db.queryRows("""select ID, ITEM, ITEMID, SOURCE, SUBITEM from units where scenarioId = ?""",[scenarioId])]
		vectors = [vector for vector in db.queryRows("""select name as vector, vectorId from vector where scenarioId = ?""",[scenarioId])]
		
		for pathway in pathways:
			out = dict(pathway)
			for monthId in range(0,12):
				row = db.queryRow("""select u.ITEM, u.ITEMID, u.SOURCE, u.SUBITEM,
											pbid.detectionRate as IDR, pbid.TREATMENTEFFICACY as ITE, pbid.TREATMENTRATEFORUNDETECTED as ITRUD,
											iir."""+month(monthId)+""" as IIR,
											u."""+month(monthId)+""" as Units
											from units as u
											left join itemInfectionRate as iir on u.itemId = iir.itemId and u.source = iir.source and u.subItem = iir.subItem and u.scenarioId = iir.scenarioId
											left join preBorderItemDetection as pbid on u.itemId = pbid.itemid and u.source = pbid.source and u.subItem = pbid.subItem and u.scenarioId = pbid.scenarioId
											where u.itemid = ? and u.source = ? and u.subItem = ? and u.scenarioId = ?""",[pathway['itemId'], pathway['source'], pathway['subItem'], scenarioId])
						
				for node in ['IDR', 'ITE', 'ITRUD', 'IIR', 'Units']:
					preBorderNet.node(node).setEquation(f'{node}='+str(row[node]))
				preBorderNet.update()
				
				out[month(monthId).lower()] = preBorderNet.node('Infected_Units')._equationMean()
				
			entries_list.append(out)
			
			
		for vector in vectors:
			for pathway in pathways:
				out = dict(pathway)
				out.update(dict(vector))
				for monthId in range(0,12):
					row = db.queryRow("""select u.ITEM, u.ITEMID, u.SOURCE, u.SUBITEM, ir.VECTOR, ir.VECTORID,
											pbvd.detectionRate as VDR, pbvd.TREATMENTEFFICACY as VTE, pbvd.TREATMENTRATEFORUNDETECTED as VTRUD,
											ir."""+month(monthId)+""" as IR,
											pbid.detectionRate as IDR, pbid.TREATMENTEFFICACY as ITE, pbid.TREATMENTRATEFORUNDETECTED as ITRUD,
											iir."""+month(monthId)+""" as IIR,
											vir."""+month(monthId)+""" as EVIR,
											ivtr."""+month(monthId)+""" as IVTR,
											vpu."""+month(monthId)+""" as VpU,
											u."""+month(monthId)+""" as Units
											from units as u
											left join infestationRate as ir on u.itemId = ir.itemId and u.source = ir.source and u.subItem = ir.subItem and u.scenarioId = ir.scenarioId
											left join vectorInfectionRate as vir on u.source = vir.source and ir.vectorId = vir.vectorID and u.scenarioId = vir.scenarioId
											left join itemInfectionRate as iir on u.itemId = iir.itemId and u.source = iir.source and u.subItem = iir.subItem and u.scenarioId = iir.scenarioId
											left join vectorsPerUnit as vpu on u.itemId = vpu.itemid and u.subItem = vpu.subItem and ir.vectorId = vpu.vectorID and u.scenarioId = vpu.scenarioId
											left join itemVectorTransmissionRate as ivtr on u.itemId = ivtr.itemid and ir.vectorId = ivtr.vectorID and u.scenarioId = ivtr.scenarioId
											left join preBorderVectorDetection as pbvd on u.itemId = pbvd.itemid and u.source = pbvd.source and u.subItem = pbvd.subItem and ir.vectorId = pbvd.vectorID and u.scenarioId = pbvd.scenarioId
											left join preBorderItemDetection as pbid on u.itemId = pbid.itemid and u.source = pbid.source and u.subItem = pbid.subItem and u.scenarioId = pbvd.scenarioId
											where u.itemid = ? and u.source = ? and u.subItem = ? and ir.vectorid = ? and u.scenarioId = ?""",[pathway['itemId'], pathway['source'], pathway['subItem'], vector['vectorId'], scenarioId])

					for node in ['VDR', 'VTE', 'VTRUD', 'IR', 'IDR', 'ITE', 'ITRUD', 'IIR', 'EVIR', 'IVTR', 'VpU', 'Units']:
						preBorderNet.node(node).setEquation(f'{node}='+str(row[node]))
					preBorderNet.update()
					out[month(monthId).lower()] = preBorderNet.node('Infected_Vectors')._equationMean()
				# print(out)
				entries_list.append(out)
				
	
	
		entries_df = pd.DataFrame(entries_list)
		entries_df['scenarioId'] = scenarioId
		entries_df = entries_df.drop(columns='id')
		
		outputDir = f'outputs/scenario{scenarioId}'
		outCsvFn = os.path.join(outputDir, "Entries.csv")
		
		entries_df.to_csv(outCsvFn, index=False)
		

		
		# db.query('delete from entries where scenarioId = ?', [scenarioId])
		
		# headers = entries_df.columns.tolist()
		# for _, row in entries_df.iterrows():
		# 	db.replace('entries', row.to_dict(), headers)

		print("Time: {}s".format(time.time() - st))


# ap = argparse.ArgumentParser()
# ap.add_argument('--id', type=int, default=None, help='The ID to assign this run')
# args = ap.parse_args()

# make_entry_tables(args.id)
