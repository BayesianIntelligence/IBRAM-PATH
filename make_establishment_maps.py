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

# def copy_bn(master, prefix):
# 	net = Net('bns/Location - Copy.xdsl')
# 	vars = [n.name() for n in net.nodes()]
	
# 	def update_equation(eq):
# 		for var in vars:
# 			eq = re.sub(rf'\b{re.escape(var)}\b', f'{prefix}_{var}', eq)
# 		return eq
	
# 	for node in net.nodes():
# 		if node.type() == Node.EQUATION_NODE:
# 			new = master.addNode(f'{prefix}_{node.name()}', Node.EQUATION_NODE)
# 		else:
# 			new = master.addNode(f'{prefix}_{node.name()}', states = node.stateNames())
			
# 	for node in net.nodes():
# 		if node.type() == Node.EQUATION_NODE:
# 			new = master.node(f'{prefix}_{node.name()}')
# 			new.equation(update_equation(node.equation()))
# 		else:
# 			new = master.node(f'{prefix}_{node.name()}')
# 			new.addParents(node.parents())
			
		
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
		masterEquations += copy_equations(get_equations('bns/Location.xdsl'), f"ts{i}_".replace('ts-','ts_'))
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


		# net.write(f'{code}.xdsl')
		# for t in range(-burnIn, runLength):
		# 	print()
		# 	for var in ['pests', 'eradEfficiacy', 'EMR', 'ER', 'establish']:
		# 		print(f'ts{t}_{var}', net.node(f'ts{t}_{var}'.replace('ts-', 'ts_'))._equationMean(), masterModel.get(f'ts{t}_{var}'.replace('ts-', 'ts_')).mean())

		for node in outputs:
			for t in range(runLength):
				# shape_gdf.at[code, f'{node}_{t}'] = net.node(f'ts{t}_{node}')._equationMean()
				shape_gdf.at[code, f'{node}_{t}'] = masterModel.get(f'ts{t}_{node}').mean()


	for node in outputs:
		cols = [f'{node}_{i}' for i in range(runLength)]
		shape_gdf[cols].to_csv(os.path.join(outputDir, f'{node}.csv'))
	
	print("Time: {}s".format(time.time() - st))


if __name__=="__main__":
	make_establishment_maps(8)








# def make_establishment_maps(scenarioId, burnIn = 12, runLength = 24, climateMap = 'Climate Temperate'):
# 	def csv2dict(filename):
# 		with open(filename, newline='') as file:
# 			return {row['Code']: row for row in csv.DictReader(file)}
		
# 	outputDir = f'outputs/scenario{scenarioId}'
	
# 	disIn = dict()
# 	expIn = dict()
# 	for monthId in range(0, 12):
# 		disIn[month(monthId)]=csv2dict(os.path.join(outputDir, "Dispersal_Pests_"+month(monthId)+".csv"))
# 		expIn[month(monthId)]=csv2dict(os.path.join(outputDir, "Exposure_Pests_"+month(monthId)+".csv"))
		
# 	try:
# 		climIn = csv2dict('inputs/climatemaps/'+climateMap+'.csv')
# 	except:
# 		print('inputs/climatemaps/'+climateMap+'.csv')
# 		climIn=None
		
	
# 	habIn=csv2dict('inputs/landcover/land_cover.csv')
# 	area=csv2dict('inputs/10kmHexClippedNZTM/10kmHexClippedNZTM.csv')

# 	template = csv.DictReader(io.open('inputs/10kmHexClippedNZTM/nz_template.csv', newline=''))
# 	outputs = ['CS', 'LS', 'Habitat_Suitability', 'Exposure_Pests_Density', 'Disperse_Pests_Density', 'x_Pests', 'x_Establishment_', 'x_Spread_', 'Economic_Consequences', 'Environmental_Consequences', 'Human_Health_Consequences', 'Social_cultural_Consequences']
# 	outCsvs = dict()
	
# 	for out in outputs:
# 		outCsvs[out] = dict()
# 		for step in range(runLength):
# 			outCsvs[out][step]=csv.DictWriter(io.open(os.path.join(outputDir, out+'_'+str(step)+'.csv'), 'w', newline=''), template.fieldnames)
# 			outCsvs[out][step].writeheader()
			
# 	fieldnames = ['Code', 'AU2013_NAM']
# 	for out in outputs:
# 		for step in range(runLength):
# 			fieldnames += [out+'_'+str(step)+'_uPeSqKm', out+'_'+str(step)+'_sdPeSqKm']


# 	net = rolloutModel(scenarioId, burnIn, runLength)
# 	net._setSamples(1000, 1000)
	
# 	nodeNames = [node.name() for node in net.nodes()]

# 	for i, loc in enumerate(template):
# 		print('location: '+str(i), end="\r")
# 		loc = dict(loc)
		
# 		for step in range(-burnIn, runLength):
# 			initialiseLocationTimeSlice(net, step, i, area, expIn, disIn, climIn, habIn, loc['Code'], nodeNames = nodeNames)
# 		net.update()
			
# 		for out in outputs:
# 			for step in range(runLength):
# 				loc['uPeSqKm'] = net.node('ts'+str(step)+'_'+out)._equationMean()
# 				# loc['sdPeSqKm'] = sdPeSqKm
# 				outCsvs[out][step].writerow(loc)














# Switch(Habitat_Suitability,0,1,1,0.15,2,0.1,3,0.05)

		
	


	# return f"Switch({var_name}," + ",".join(entries) + ")"
	
# for i, v in enumerate(values):
# 		entries.append(f"{i},{v}")
# 	return f"Switch({var_name}," + ",".join(entries) + ")"

	# for index, pathway in consequences_df.iterrows():
	
	
# Switch(LU,0,0,1,0,2,0,3,0,4,0,5,0,6,0,7,0,8,0,9,0,10,0,11,0,12,0)
	
# 		for ele1,ele2 in [('Economic_Spread_Cost', 'ECON_SPREAD'), 
# 							('Environmental_Spread_Cost', 'ENV_SPREAD'), 
# 							('Social_cultural_Spread_Cost', 'SOC_SPREAD'), 
# 							('Human_Health_Spread_Cost', 'HEALTH_SPREAD'),
# 							('Economic_Est_Cost', 'ECON_EST'),
# 							('Environmental_Est_Cost', 'ENV_EST'),
# 							('Social_cultural_Est_Cost', 'SOC_EST'),
# 							('Human_Health_Est_Cost', 'HEALTH_EST')]:
# 			rs = db.query("""select """+ele2+""" as cons from consequences where scenarioId = ? order by landcover""",[scenarioId])

# 			vec = []
# 			for row in rs:
# 				vec.append(row['cons'])
# 			copyEquation(ele1, str(vect2SwitchEq(vec, convert('LU'))))	
	


	




# def make_establishment_maps(scenarioId, steps = 36):
# 	net = rollout(steps)
	
	
# 	with serverDb() as db:
# 		transmissionRate = db.queryRows("""select * from transmissionRate where scenarioId = ?""", [scenarioId])
# 		transmissionRate_df = pd.DataFrame(transmissionRate, columns=transmissionRate[0].keys() if transmissionRate else [])

# 		consequences = db.queryRows("""select * from consequences where scenarioId = ?""", [scenarioId])
# 		consequences_df = pd.DataFrame(consequences, columns=consequences[0].keys() if consequences else [])
		
# 		land_suit = db.queryRows("""select * from landSuitability where scenarioId = ?""", [scenarioId])
# 		land_suit_df = pd.DataFrame(land_suit, columns=land_suit[0].keys() if land_suit else [])
		
# 		host_mort = db.queryRows("""select * from hostMortalityRate where scenarioId = ?""", [scenarioId])
# 		host_mort_df = pd.DataFrame(host_mort, columns=host_mort[0].keys() if host_mort else [])
		
# 		estab_rate = db.queryRows("""select * from establishmentRate where scenarioId = ?""", [scenarioId])
# 		estab_rate_df = pd.DataFrame(estab_rate, columns=estab_rate[0].keys() if estab_rate else [])		
		
# 		estab_mort_rate = db.queryRows("""select * from establishmentMortalityRate where scenarioId = ?""", [scenarioId])
# 		estab_mort_rate_df = pd.DataFrame(estab_mort_rate, columns=estab_mort_rate[0].keys() if estab_mort_rate else [])
		
# 		spread_rate = db.queryRows("""select * from spreadRate where scenarioId = ?""", [scenarioId])
# 		spread_rate_df = pd.DataFrame(spread_rate, columns=spread_rate[0].keys() if spread_rate else [])

# 		estab_detect = db.queryRow("""select * from establishmentDetection where scenarioId = ?""", [scenarioId])


# 		for i in range(0, steps):
# 			eq = []
# 			for index, row in transmissionRate_df.iterrows():
# 				carrier = row['carrier'].replace(' ','_')
# 				net.addNode(f'ts{i}_{carrier}_in'.replace(' ','_'), Node.EQUATION_NODE)
# 				net.addNode(f'ts{i}_{carrier}_transmissionRate'.replace(' ','_'), Node.EQUATION_NODE)
# 				eq.append(f'ts{i}_{carrier}_in*ts{i}_{carrier}_transmissionRate')
# 				net.node(f'ts{i}_pestsEntering').equation(f"ts{i}_pestsEntering={'+'.join(eq)}")
# 				net.node(f'ts{i}_{carrier}_transmissionRate').equation(f"f'ts{i}_{carrier}_transmissionRate=Switch(ts{i}_HS,{','.join(f'{i},{v}' for i, v in enumerate(row[['favourable', 'suitable', 'marginal', 'unsuitable']]))})")
				

# 			for var in 'ECON_EST,ECON_SPREAD,ENV_EST,ENV_SPREAD,SOC_EST,SOC_SPREAD,HEALTH_EST,HEALTH_SPREAD'.split(','):
# 				net.node(f'ts{i}_{var}').equation(f"ts{i}_{var}=Switch(ts{i}_LU,{','.join(f'{i},{v}' for i, v in enumerate(consequences_df[var]))})")
				
# 			net.node(f'ts{i}_LS').equation(f"ts{i}_LS=Switch(ts{i}_LU,{','.join(f'{i},{v}' for i, v in enumerate(land_suit_df['suitability']))})")			
	
# 			net.node(f'ts{i}_HMR').equation(f"ts{i}_HMR=Switch(ts{i}_HS,{','.join(f'{i},{v}' for i, v in enumerate(host_mort_df.loc[0, ['favourable', 'suitable', 'marginal', 'unsuitable']]))})")
# 			net.node(f'ts{i}_ER').equation(f"ts{i}_ER=Switch(ts{i}_HS,{','.join(f'{i},{v}' for i, v in enumerate(estab_rate_df.loc[0, ['favourable', 'suitable', 'marginal', 'unsuitable']]))})")
# 			net.node(f'ts{i}_EMR').equation(f"ts{i}_EMR=Switch(ts{i}_HS,{','.join(f'{i},{v}' for i, v in enumerate(estab_mort_rate_df.loc[0, ['favourable', 'suitable', 'marginal', 'unsuitable']]))})")
# 			net.node(f'ts{i}_SR').equation(f"ts{i}_SR=Switch(ts{i}_HS,{','.join(f'{i},{v}' for i, v in enumerate(spread_rate_df.loc[0, ['favourable', 'suitable', 'marginal', 'unsuitable']]))})")

# 			net.node(f'ts{i}_detectionRate').setEquation(f'ts{i}_detectionRate='+str(estab_detect['detectionRate']))


# 	net.write('master.xdsl')


# def convertString(eq, net, step):
# 	nodeNames = [node.name() for node in net.nodes()]
# 	for nodeName in nodeNames:
# 		eq = eq.replace(nodeName, 'ts'+str(step).replace('-','_')+'_'+nodeName)
	
# 	return eq


# def copyTimeSlice(net, master, step, burnIn):
# 		def convert(node):
# 			return 'ts'+str(step).replace('-','_')+'_'+node
# 		def copyEquation(node, eq):
# 			master.node(convert(node)).setEquation(convert(node)+'='+convertString(eq, net, step))

# 		nodes = net.nodes()
# 		for node in nodes:
# 			master.addNode(convert(node.name()), Node.EQUATION_NODE)
				
# 		copyEquation('Disperse_Pests_Density', 'if(Area<0.1,0,Disperse_Pests_Count/Area)')
# 		copyEquation('Exposure_Pests_Density', 'if(Area<0.1,0,Exposure_Pests_Count/Area)')
# 		copyEquation('x_p_', 'Dieoff')
# 		copyEquation('x_n_', 'Pests__t_1__')
# 		# copyEquation('x_Pests', '(Or(x_p_=0,x_n_=0) ? 0 : x_n_<200 ? Binomial(x_n_,x_p_) : And(x_n_*x_p_>=5,x_n_*(1-x_p_)>=5) ? Normal(x_n_*x_p_,Sqrt(x_n_*x_p_*(1-x_p_))) : Binomial(x_n_/Max(Min(Pow10(Log10(x_n_)-2),Pow10(Log10(1/x_p_)-1)),1),x_p_*Max(Min(Pow10(Log10(x_n_)-2),Pow10(Log10(1/x_p_)-1)),1)))+Disperse_Pests_Density')
# 		copyEquation('x_Pests', 'x_n_*(1-x_p_)+Disperse_Pests_Density')
# 		copyEquation('CI', 'If(GS=1,GI,EI)')
# 		copyEquation('CS', 'If(CI>=20,3,If(CI>=5,2,If(CI>=0.5,1,0)))')
# 		copyEquation('Habitat_Suitability', 'Min(CS,LS)')
# 		copyEquation('Eradication_Efficacy', '1-(1-Eradication_Detection*Eradication_Control)*(1-Eradication_Natural)')
# 		# copyEquation('x_Establishment_', 'If(Or(And(Establishment___t_1__=1,Bernoulli(1-Eradication_Efficacy)),Bernoulli(1-(1-Establishment_Rate)^x_Pests)=1),1,0)')
# 		copyEquation('x_Establishment_', '1-(1-Establishment___t_1__*(1-Eradication_Efficacy))*(1-(1-(1-Establishment_Rate)^x_Pests))')
# 		# copyEquation('x_Spread_', 'If(And(x_Establishment_=1,Bernoulli(Spread_Rate)),1,0)')
# 		copyEquation('x_Spread_', 'x_Establishment_*Spread_Rate')
# 		copyEquation('Economic_Consequences', 'Economic_Est_Cost*x_Establishment_+Economic_Spread_Cost*x_Spread_')
# 		copyEquation('Environmental_Consequences', 'Environmental_Est_Cost*x_Establishment_+Environmental_Spread_Cost*x_Spread_')
# 		copyEquation('Human_Health_Consequences', 'Human_Health_Est_Cost*x_Establishment_+Human_Health_Spread_Cost*x_Spread_')
# 		copyEquation('Social_cultural_Consequences', 'Social_cultural_Est_Cost*x_Establishment_+Social_cultural_Spread_Cost*x_Spread_')

# 		if step > -burnIn:
# 			master.node(convert('Pests__t_1__')).setEquation(convert('Pests__t_1__')+'=ts'+str(step-1).replace('-','_')+'_x_Pests')
# 			master.node(convert('Establishment___t_1__')).setEquation(convert('Establishment___t_1__')+'=ts'+str(step-1).replace('-','_')+'_x_Establishment_')

# def vect2SwitchEq (vec, parent):
# 	eq = 'Switch('+parent
# 	for i,ele in enumerate(vec):
# 		eq=eq+','+str(i)+','+str(ele)
# 	eq = eq+')'
# 	return eq

# def initialiseTimeSlice(scenarioId, net, step):
# 	def convert(node):
# 		return 'ts'+str(step).replace('-','_')+'_'+node
		
# 	def copyEquation(node, eq):
# 		net.node(convert(node)).setEquation(convert(node)+'='+eq)
		
# 	outputDir = f'outputs/scenario{scenarioId}'
		
# 	with serverDb() as db:
# 		rs = db.query("""select * from eradicationDetection where scenarioId = ?""",[scenarioId]).fetchone()
# 		copyEquation('Eradication_Detection', str(rs['Erad_Detect']))
# 		copyEquation('Eradication_Control', str(rs['Erad_Control']))	
		
# 		gs= ['1','1','1','1','Bernoulli(0.5)','0','0','0','Bernoulli(0.5)','1','1','1']
		
# 		rs = db.query("""select * from landsuitability where scenarioId = ?""",[scenarioId])		
# 		vec = []
# 		for row in rs:
# 			vec.append(row['suitability'])
# 		copyEquation('LS', vect2SwitchEq(vec, convert('LU')))
		
			
# 		for ele1,ele2 in [('Economic_Spread_Cost', 'ECON_SPREAD'), 
# 							('Environmental_Spread_Cost', 'ENV_SPREAD'), 
# 							('Social_cultural_Spread_Cost', 'SOC_SPREAD'), 
# 							('Human_Health_Spread_Cost', 'HEALTH_SPREAD'),
# 							('Economic_Est_Cost', 'ECON_EST'),
# 							('Environmental_Est_Cost', 'ENV_EST'),
# 							('Social_cultural_Est_Cost', 'SOC_EST'),
# 							('Human_Health_Est_Cost', 'HEALTH_EST')]:
# 			rs = db.query("""select """+ele2+""" as cons from consequences where scenarioId = ? order by landcover""",[scenarioId])

# 			vec = []
# 			for row in rs:
# 				vec.append(row['cons'])
# 			copyEquation(ele1, str(vect2SwitchEq(vec, convert('LU'))))	
			
			
# 		rs = db.query("""select * from mortalityRate where scenarioId = ?""",[scenarioId]).fetchone()
# 		vec = [float(rs['UNSUITABLE']), float(rs['MARGINAL']), float(rs['SUITABLE']), float(rs['FAVOURABLE'])]
# 		copyEquation('Dieoff', str(vect2SwitchEq(vec, convert('Habitat_Suitability'))))
			
# 		rs = db.query("""select * from establishmentRate where scenarioId = ?""",[scenarioId]).fetchone()
# 		vec = [float(rs['UNSUITABLE']), float(rs['MARGINAL']), float(rs['SUITABLE']), float(rs['FAVOURABLE'])]
# 		copyEquation('Establishment_Rate', str(vect2SwitchEq(vec, convert('Habitat_Suitability'))))
			
# 		rs = db.query("""select * from eradicationRate where scenarioId = ?""",[scenarioId]).fetchone()
# 		vec = [float(rs['UNSUITABLE']), float(rs['MARGINAL']), float(rs['SUITABLE']), float(rs['FAVOURABLE'])]
# 		copyEquation('Eradication_Natural', str(vect2SwitchEq(vec, convert('Habitat_Suitability'))))
			
# 		rs = db.query("""select * from spreadRate where scenarioId = ?""",[scenarioId]).fetchone()
# 		vec = [float(rs['UNSUITABLE']), float(rs['MARGINAL']), float(rs['SUITABLE']), float(rs['FAVOURABLE'])]
# 		copyEquation('Spread_Rate', str(vect2SwitchEq(vec, convert('Habitat_Suitability'))))
	


# def rolloutModel(scenarioId, burnIn, runLength):
# 		master = Net()
# 		net = Net("bns/Location.xdsl")
# 		for step in range(-burnIn, runLength):
# 			copyTimeSlice(net, master, step, burnIn)
# 			initialiseTimeSlice(scenarioId, master, step)
# 		return master
		
	
# def vect2BernEq (vec):
# 	def vect2BernEq1(vec, ele):
# 		if len(vec)==1 or sum(vec)==0:
# 			return str(ele)
# 		else:
# 			return 'If(Bernoulli({}),{},{})'.format(vec[0]/sum(vec),ele,vect2BernEq1(vec[1:],ele+1))
# 	return vect2BernEq1(normalise(vec),0)


# def initialiseLocationTimeSlice(net, step, loc, area, expIn, disIn, climIn, habIn, code, nodeNames = None):

# 	def convert(node):
# 		return 'ts'+str(step).replace('-','_')+'_'+node
# 	def copyEquation(node, eq):
# 		net.node(convert(node)).setEquation(convert(node)+'='+eq)
	
# 	#0 is unmapped = ocean, so added to water
	
# 	LUVec = [ 
# 		float(habIn[code]['v1.0']), 
# 		float(habIn[code]['v2.0']), 
# 		float(habIn[code]['v3.0']), 
# 		float(habIn[code]['v4.0']), 
# 		float(habIn[code]['v5.0']), 
# 		float(habIn[code]['v6.0']), 
# 		float(habIn[code]['v7.0']), 
# 		float(habIn[code]['v8.0']), 
# 		float(habIn[code]['v9.0']), 
# 		float(habIn[code]['v10.0']), 
# 		float(habIn[code]['v11.0']), 
# 		float(habIn[code]['v12.0']), 
# 		float(habIn[code]['v13.0'])]
# 	copyEquation('LU', vect2BernEq(LUVec))
	
# 	if climIn is not None :
# 		clim = climIn[code]
# 		copyEquation('EI', 'Triangular('+clim['EI_min_cor']+', '+clim['EI_avg_cor']+', '+clim['EI_max_cor']+')')
# 		copyEquation('GI', 'Triangular('+clim['GI_min_cor']+', '+clim['GI_avg_cor']+', '+clim['GI_max_cor']+')')
# 	else:
# 		copyEquation('EI', '100')
# 		copyEquation('GI', '100')
			
# 	copyEquation('Disperse_Pests_Count', disIn[month(step%12)][code]['uDisperses'])
# 	copyEquation('Exposure_Pests_Count', expIn[month(step%12)][code]['uExposures'])
# 	copyEquation('Area', area[code]['area_sqkm'])
	



# def make_establishment_maps(scenarioId, burnIn = 12, runLength = 24, climateMap = 'Climate Temperate'):
# 	def csv2dict(filename):
# 		with open(filename, newline='') as file:
# 			return {row['Code']: row for row in csv.DictReader(file)}
		
# 	outputDir = f'outputs/scenario{scenarioId}'
	
# 	disIn = dict()
# 	expIn = dict()
# 	for monthId in range(0, 12):
# 		disIn[month(monthId)]=csv2dict(os.path.join(outputDir, "Dispersal_Pests_"+month(monthId)+".csv"))
# 		expIn[month(monthId)]=csv2dict(os.path.join(outputDir, "Exposure_Pests_"+month(monthId)+".csv"))
		
# 	try:
# 		climIn = csv2dict('inputs/climatemaps/'+climateMap+'.csv')
# 	except:
# 		print('inputs/climatemaps/'+climateMap+'.csv')
# 		climIn=None
		
	
# 	habIn=csv2dict('inputs/landcover/land_cover.csv')
# 	area=csv2dict('inputs/10kmHexClippedNZTM/10kmHexClippedNZTM.csv')

# 	template = csv.DictReader(io.open('inputs/10kmHexClippedNZTM/nz_template.csv', newline=''))
# 	outputs = ['CS', 'LS', 'Habitat_Suitability', 'Exposure_Pests_Density', 'Disperse_Pests_Density', 'x_Pests', 'x_Establishment_', 'x_Spread_', 'Economic_Consequences', 'Environmental_Consequences', 'Human_Health_Consequences', 'Social_cultural_Consequences']
# 	outCsvs = dict()
	
# 	for out in outputs:
# 		outCsvs[out] = dict()
# 		for step in range(runLength):
# 			outCsvs[out][step]=csv.DictWriter(io.open(os.path.join(outputDir, out+'_'+str(step)+'.csv'), 'w', newline=''), template.fieldnames)
# 			outCsvs[out][step].writeheader()
			
# 	fieldnames = ['Code', 'AU2013_NAM']
# 	for out in outputs:
# 		for step in range(runLength):
# 			fieldnames += [out+'_'+str(step)+'_uPeSqKm', out+'_'+str(step)+'_sdPeSqKm']


# 	net = rolloutModel(scenarioId, burnIn, runLength)
# 	net._setSamples(1000, 1000)
	
# 	nodeNames = [node.name() for node in net.nodes()]

# 	for i, loc in enumerate(template):
# 		print('location: '+str(i), end="\r")
# 		loc = dict(loc)
		
# 		for step in range(-burnIn, runLength):
# 			initialiseLocationTimeSlice(net, step, i, area, expIn, disIn, climIn, habIn, loc['Code'], nodeNames = nodeNames)
# 		net.update()
			
# 		for out in outputs:
# 			for step in range(runLength):
# 				loc['uPeSqKm'] = net.node('ts'+str(step)+'_'+out)._equationMean()
# 				# loc['sdPeSqKm'] = sdPeSqKm
# 				outCsvs[out][step].writerow(loc)


