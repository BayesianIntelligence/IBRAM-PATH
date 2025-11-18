import os, re, time, sys

from _lib.utils import *
# from _lib.bni_smile import Net, Node

import pandas as pd
import geopandas as gpd


from EquationModel import EquationModel



def make_discrete_draw(probabilities):
	values = list(range(len(probabilities)))

	cum = 0
	parts = []
	for i, (p, v) in enumerate(zip(probabilities, values)):
		cum += p
		test = f"np.random.uniform(0,1) < {cum}"
		parts.append((test, v))
		
	expr = str(parts[-1][1])
	for cond, val in reversed(parts[:-1]):
		expr = f"({val} if {cond} else {expr})"
	
	return expr

			
		
def copy_equations(equations, prefix):
	vars = [eq.split("=", 1)[0].strip() for eq in equations]
	pattern = r'\b(' + '|'.join(re.escape(var) for var in vars) + r')\b'

	prefixed_equations = []
	for eq in equations:
		var, expr = eq.split("=", 1)
		var = var.strip()
		expr = expr.strip()
		new_expr = re.sub(pattern, lambda m: prefix + m.group(1), expr)
		prefixed_equations.append(f"{prefix}{var} = {new_expr}")
	


	return prefixed_equations
		

def rollout(scenarioId, burnIn, runLength):
	masterEquations = []
	# master = Net()
	# master._setSamples(1000, 1000)
	
	for i in range(-burnIn,runLength):
		masterEquations += copy_equations(get_equations('bns/Location.json'), f"ts{i}_".replace('ts-','ts_'))
		# copy_bn(master, f"ts{i}".replace('ts-','ts_'))
		# master.node(f'ts{i}_pestsPast'.replace('ts-','ts_')).equation(f'ts{i}_pestsPast=ts{i-1}_pests'.replace('ts-','ts_'))
		# master.node(f'ts{i}_establishPast'.replace('ts-','ts_')).equation(f'ts{i}_establishPast=ts{i-1}_establish'.replace('ts-','ts_'))

	masterModel = EquationModel(masterEquations)
	
	for i in range(-burnIn+1,runLength):
		masterModel.update_equation(f'ts{i}_pestsPast'.replace('ts-','ts_'), f'ts{i-1}_pests'.replace('ts-','ts_'))
		masterModel.update_equation(f'ts{i}_establishPast'.replace('ts-','ts_'), f'ts{i-1}_establish'.replace('ts-','ts_'))
		
	with serverDb() as db:
		def load_df(table):
			rows = db.queryRows(f"SELECT * FROM {table} WHERE scenarioId = ?", [scenarioId])
			return pd.DataFrame(rows, columns=rows[0].keys() if rows else [])

		transmissionRate_df = load_df("transmissionRate")
		consequences_df = load_df("consequences")
		land_suit_df = load_df("landSuitability")
		host_mort_df = load_df("hostMortalityRate")
		estab_rate_df = load_df("establishmentRate")
		estab_mort_rate_df = load_df("establishmentMortalityRate")
		spread_rate_df = load_df("spreadRate")
		estab_detect = db.queryRow("SELECT * FROM establishmentDetection WHERE scenarioId = ?", [scenarioId])
		
	land_suit_df = pd.concat([pd.DataFrame([{'landcoverId': 0}]), land_suit_df], ignore_index=True).fillna(0)
	consequences_df = pd.concat([pd.DataFrame([{'landcoverId': 0}]), consequences_df], ignore_index=True).fillna(0)

	gs= ['1','1','1','1','Bernoulli(0.5)','0','0','0','Bernoulli(0.5)','1','1','1']
	suit_keys = ['favourable', 'suitable', 'marginal', 'unsuitable']
	consequence_vars = 'econEstab,econSpread,environEstab,environSpread,healthEstab,healthSpread,socialEstab,socialSpread'.split(',')
	for i in range(-burnIn,runLength):

		eq = []
		for _, row in transmissionRate_df.iterrows():
			carrier = row['carrier'].replace(' ', '_')
			in_node = f'ts{i}_{carrier}_in'.replace('ts-','ts_')
			tr_node = f'ts{i}_{carrier}_transmissionRate'.replace('ts-','ts_')
			# master.addNode(in_node, Node.EQUATION_NODE)
			# master.addNode(tr_node, Node.EQUATION_NODE)
			masterModel.update_equation(in_node, '0')
			masterModel.update_equation(tr_node, '0')

			eq.append(f'{in_node}*{tr_node}')

			tr_values = ','.join(f'{j},{row[k]}' for j, k in enumerate(suit_keys))
			# master.node(tr_node).equation(f"{tr_node}=Switch(ts{i}_hs,{tr_values})".replace('ts-','ts_'))	
			masterModel.update_equation(tr_node, f'Switch(ts{i}_hs,{tr_values})'.replace('ts-','ts_'))	
		# master.node(f'ts{i}_pestsEntering'.replace('ts-','ts_')).equation(f"ts{i}_pestsEntering={' + '.join(eq)}".replace('ts-','ts_'))
		masterModel.update_equation(f'ts{i}_pestsEntering'.replace('ts-','ts_'), f"{' + '.join(eq)}".replace('ts-','ts_'))
		
		# master.node(f'ts{i}_GS'.replace('ts-','ts_')).equation(f'ts{i}_GS={gs[i%12]}'.replace('ts-','ts_'))
		# master.node(f'ts{i}_ls'.replace('ts-','ts_')).equation(f"ts{i}_ls=Switch(ts{i}_LU,{','.join(f'{i},{v}' for i, v in enumerate(land_suit_df['suitability']))})".replace('ts-','ts_'))			
		masterModel.update_equation(f'ts{i}_GS'.replace('ts-','ts_'), f'{gs[i%12]}'.replace('ts-','ts_'))
		masterModel.update_equation(f'ts{i}_ls'.replace('ts-','ts_'), f"Switch(ts{i}_LU,{','.join(f'{i},{v}' for i, v in enumerate(land_suit_df['suitability']))})".replace('ts-','ts_'))			

		for label, df in zip(['HMR', 'ER', 'EMR', 'SR'], [ host_mort_df, estab_rate_df, estab_mort_rate_df, spread_rate_df]):
			vals = ','.join(f'{j},{df.loc[0, k]}' for j, k in enumerate(suit_keys))
			# master.node(f'ts{i}_{label}'.replace('ts-','ts_')).equation(f"ts{i}_{label}=Switch(ts{i}_hs,{vals})".replace('ts-','ts_'))
			masterModel.update_equation(f'ts{i}_{label}'.replace('ts-','ts_'), f"Switch(ts{i}_hs,{vals})".replace('ts-','ts_'))
			

		for node in 'treatmentEfficacy,detectionRate,treatmentRateForUndetected'.split(','):
			# master.node(f'ts{i}_{node}'.replace('ts-','ts_')).equation(f"ts{i}_{node}={estab_detect[node]}".replace('ts-','ts_'))
			masterModel.update_equation(f'ts{i}_{node}'.replace('ts-','ts_'), f"{estab_detect[node]}".replace('ts-','ts_'))
		
		for var in consequence_vars:
			values = ','.join(f'{j},{consequences_df[var][j]}' for j in range(len(consequences_df)))
			# master.node(f'ts{i}_{var}'.replace('ts-','ts_')).equation(f"ts{i}_{var}=Switch(ts{i}_LU,{values})".replace('ts-','ts_'))
			masterModel.update_equation(f'ts{i}_{var}'.replace('ts-','ts_'),f"Switch(ts{i}_LU,{values})".replace('ts-','ts_'))
		
	return masterModel
	
def make_establishment_maps(scenarioId):
	st = time.time()
	print('creating establishment maps', scenarioId)	
	
	inputDir = f'inputs'
	outputDir = f'outputs/scenario{scenarioId}'
	outputs = 'pests,establish,spread,econConseq,environConseq,healthConseq,socialConseq,ls,hs,cs'.split(',')
	
	with serverDb() as db:
		carriers = [row['carrier'].replace(' ','_') for row in db.queryRows("SELECT carrier FROM carrierDispersal WHERE scenarioId = ?", [scenarioId])]
		project = db.queryRow("""select * from scenario s left join project p on s.projectId=p.id where s.id = ?""", [scenarioId])

	climateMap = project['climateMap'] or 'Climate Temperate'
	burnIn = project['burnIn'] or 12
	runLength = project['runLength'] or 24
	climIn = pd.read_csv(os.path.join(inputDir, f'climatemaps/{climateMap}.csv')).set_index('Code')
	landIn = pd.read_csv(os.path.join(inputDir, f'landcover/land_cover.csv')).set_index('Code')
	landCols = sorted(landIn.columns, key=lambda x: float(x[1:]))

	carrierIn = {carrier: pd.read_csv(os.path.join(outputDir,  f"dispersal_{carrier}.csv")).set_index('Code') for carrier in carriers}
	
	shape_gdf = gpd.read_file('inputs/maps/7kmHexNZ.shp')
	new_cols = {f'{node}_{i}'.replace('ts-','ts_'): 0 for node in outputs for i in range(runLength)}
	new_data = pd.DataFrame(new_cols, index=shape_gdf.index)
	shape_gdf = pd.concat([shape_gdf, new_data], axis=1).set_index('Code')
	
	masterModel = rollout(scenarioId, burnIn, runLength)

	total = len(shape_gdf)
	for idx, (code, loc) in enumerate(shape_gdf.iterrows(), start=1):
		print(f'Progress: {((idx / total) * 100):.1f}%', end='\r')
		
		# if code != '8173': continue
		# print(code)
		
		for t in range(-burnIn, runLength):
			for carrier in carriers:
				dispersal = carrierIn[carrier].at[int(code), month(t)]
				# net.node(f'ts{t}_{carrier}_in'.replace('ts-', 'ts_')).equation(f'ts{t}_{carrier}_in={dispersal:.10f}'.replace('ts-', 'ts_'))
				masterModel.update_equation(f'ts{t}_{carrier}_in'.replace('ts-', 'ts_'), f'{dispersal:.10f}'.replace('ts-', 'ts_'))

			EI_min = climIn.at[int(code),'EI_min_cor']
			EI_avg = climIn.at[int(code),'EI_avg_cor']
			EI_max = climIn.at[int(code),'EI_max_cor']
			# net.node(f'ts{t}_EI'.replace('ts-', 'ts_')).equation(f"ts{t}_EI=Triangular({EI_min}, {EI_avg}, {EI_max})".replace('ts-', 'ts_'))
			masterModel.update_equation(f'ts{t}_EI'.replace('ts-', 'ts_'), f"Triangular({EI_min}, {EI_avg}, {EI_max})".replace('ts-', 'ts_'))
			
			GI_min = climIn.at[int(code),'GI_min_cor']
			GI_avg = climIn.at[int(code),'GI_avg_cor']
			GI_max = climIn.at[int(code),'GI_max_cor']
			# net.node(f'ts{t}_GI'.replace('ts-', 'ts_')).equation(f"ts{t}_GI=Triangular({GI_min}, {GI_avg}, {GI_max})".replace('ts-', 'ts_'))
			# net.node(f'ts{t}_LU'.replace('ts-', 'ts_')).cpt([normalise(landIn.loc[int(code), landCols].values.tolist())])
			masterModel.update_equation(f'ts{t}_GI'.replace('ts-', 'ts_'), f"Triangular({GI_min}, {GI_avg}, {GI_max})".replace('ts-', 'ts_'))
			masterModel.update_equation(f'ts{t}_LU'.replace('ts-', 'ts_'), make_discrete_draw(normalise(landIn.loc[int(code), landCols].values.tolist())))
			# masterModel.update_equation(f'ts{t}_LU'.replace('ts-', 'ts_'), f"round(Uniform(0,13))")
			




		for node in outputs:
			for t in range(runLength):
				# shape_gdf.at[code, f'{node}_{t}'] = net.node(f'ts{t}_{node}')._equationMean()
				shape_gdf.at[code, f'{node}_{t}'] = masterModel.get(f'ts{t}_{node}').mean()
				
		# if masterModel.get(f'ts{0}_{node}').mean() > 0.0:
		# 	masterModel.writeNet()
		# 	sys.exit()


	for node in outputs:
		cols = [f'{node}_{i}' for i in range(runLength)]
		shape_gdf[cols].to_csv(os.path.join(outputDir, f'{node}.csv'))
	
	print("Time: {}s".format(time.time() - st))


if __name__=="__main__":
	make_establishment_maps(1)






