import _env
import pandas as pd
from openpyxl import Workbook

import utils

serverDb = utils.serverDb

with serverDb() as db:
	pathwayPoint_df = pd.read_sql_query("SELECT item as ITEM, itemId as ITEMID, name as PATHWAYPOINT, id as PATHWAYPOINTID FROM pathwayPoint", db.conn)
	landCover_df = pd.read_sql_query("SELECT name as LANDCOVER, id as LANDCOVERID FROM landCover", db.conn)


months = ['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC']
detection = ['DETECTIONRATE','TREATMENTRATEFORUNDETECTED','TREATMENTEFFICACY']
suitablity = ['FAVOURABLE','SUITABLE','MARGINAL','UNSUITABLE']
conseq = ['ECON_EST','ECON_SPREAD','ENV_EST','ENV_SPREAD','SOC_EST','SOC_SPREAD','HEALTH_EST','HEALTH_SPREAD']


df = pd.read_csv('driver.csv')
df = df[['CARRIER', 'SUBITEM','ITEM', 'SOURCE']]
df = df.merge(pathwayPoint_df, how='left', on='ITEM')
for var in months+detection+['SD']+suitablity:
	df[var] = None
for var in ['SUITABILITY']+conseq:
	landCover_df[var] = None
df.columns = [col.upper() for col in df.columns]
landCover_df.columns = [col.upper() for col in landCover_df.columns]


base_cols = {
	'carriers': ['CARRIER', 'SUBITEM','ITEM', 'ITEMID', 'SOURCE'],
	'units': ['SUBITEM','ITEM', 'ITEMID', 'SOURCE'] + months,
	'carrierRate': ['CARRIER', 'SUBITEM', 'ITEM', 'ITEMID', 'SOURCE'] + months,
	'carrierInfectionRate': ['CARRIER', 'SUBITEM', 'ITEM', 'ITEMID', 'SOURCE'] + months,
	'carriersPerUnit': ['CARRIER', 'SUBITEM', 'ITEM', 'ITEMID'] + months,
	'preborderDetection': ['CARRIER', 'SUBITEM', 'ITEM', 'ITEMID', 'SOURCE'] + detection,
	'pathwayDetection': ['CARRIER', 'ITEM', 'ITEMID', 'PATHWAYPOINT', 'PATHWAYPOINTID'] + detection,
	'carrierMortalityRate': ['CARRIER', 'ITEM', 'ITEMID', 'PATHWAYPOINT', 'PATHWAYPOINTID'] + months,
	'pathogenMortalityRate': ['CARRIER', 'ITEM', 'ITEMID', 'PATHWAYPOINT', 'PATHWAYPOINTID'] + months,
	'carrierExitRate': ['CARRIER', 'ITEM', 'ITEMID', 'PATHWAYPOINT', 'PATHWAYPOINTID'] + months,
	'carrierDispersal': ['CARRIER', 'SD'],
	'transmissionRate': ['CARRIER'] + suitablity,
}

landCover_cols = {
	'landSuitability': ['LANDCOVER','LANDCOVERID','SUITABILITY'],
	'consequences': ['LANDCOVER','LANDCOVERID']+conseq
}




dataframes = {
	name: df[cols].drop_duplicates().reset_index(drop=True)
	for name, cols in base_cols.items()
}

dataframes.update({
	'hostMortalityRate': pd.DataFrame(columns=suitablity),
	'establishmentRate': pd.DataFrame(columns=suitablity),
	'establishmentDetection': pd.DataFrame(columns=detection),
	'establishmentMortalityRate': pd.DataFrame(columns=suitablity),
	'spreadRate': pd.DataFrame(columns=suitablity)
})

dataframes.update({
	name: landCover_df[cols].drop_duplicates().reset_index(drop=True)
	for name, cols in landCover_cols.items()
})

wb = Workbook()
wb.remove(wb.active)

for sheet_name, df in dataframes.items():
	ws = wb.create_sheet(title=sheet_name)
	ws.append(df.columns.tolist())
	for row in df.itertuples(index=False):
		ws.append(list(row))

wb.save("output.xlsx")
