import _env, csvdb, os, io, sys, csv
from bidb import DB

from utils import *
from bni_smile import *

import pandas as pd

def convertString(eq, net, step):
	nodeNames = [node.name() for node in net.nodes()]
	for nodeName in nodeNames:
		eq = eq.replace(nodeName, 'ts'+str(step).replace('-','_')+'_'+nodeName)
	
	return eq


def copyTimeSlice(net, master, step, burnIn):
		def convert(node):
			return 'ts'+str(step).replace('-','_')+'_'+node
		def copyEquation(node, eq):
			master.node(convert(node)).setEquation(convert(node)+'='+convertString(eq, net, step))

		nodes = net.nodes()
		for node in nodes:
			master.addNode(convert(node.name()), Node.EQUATION_NODE)
				
		copyEquation('Disperse_Pests_Density', 'if(Area<0.1,0,Disperse_Pests_Count/Area)')
		copyEquation('Exposure_Pests_Density', 'if(Area<0.1,0,Exposure_Pests_Count/Area)')
		copyEquation('x_p_', 'Dieoff')
		copyEquation('x_n_', 'Pests__t_1__')
		# copyEquation('x_Pests', '(Or(x_p_=0,x_n_=0) ? 0 : x_n_<200 ? Binomial(x_n_,x_p_) : And(x_n_*x_p_>=5,x_n_*(1-x_p_)>=5) ? Normal(x_n_*x_p_,Sqrt(x_n_*x_p_*(1-x_p_))) : Binomial(x_n_/Max(Min(Pow10(Log10(x_n_)-2),Pow10(Log10(1/x_p_)-1)),1),x_p_*Max(Min(Pow10(Log10(x_n_)-2),Pow10(Log10(1/x_p_)-1)),1)))+Disperse_Pests_Density')
		copyEquation('x_Pests', 'x_n_*(1-x_p_)+Disperse_Pests_Density')
		copyEquation('CI', 'If(GS=1,GI,EI)')
		copyEquation('CS', 'If(CI>=20,3,If(CI>=5,2,If(CI>=0.5,1,0)))')
		copyEquation('Habitat_Suitability', 'Min(CS,LS)')
		copyEquation('Eradication_Efficacy', '1-(1-Eradication_Detection*Eradication_Control)*(1-Eradication_Natural)')
		# copyEquation('x_Establishment_', 'If(Or(And(Establishment___t_1__=1,Bernoulli(1-Eradication_Efficacy)),Bernoulli(1-(1-Establishment_Rate)^x_Pests)=1),1,0)')
		copyEquation('x_Establishment_', '1-(1-Establishment___t_1__*(1-Eradication_Efficacy))*(1-(1-(1-Establishment_Rate)^x_Pests))')
		# copyEquation('x_Spread_', 'If(And(x_Establishment_=1,Bernoulli(Spread_Rate)),1,0)')
		copyEquation('x_Spread_', 'x_Establishment_*Spread_Rate')
		copyEquation('Economic_Consequences', 'Economic_Est_Cost*x_Establishment_+Economic_Spread_Cost*x_Spread_')
		copyEquation('Environmental_Consequences', 'Environmental_Est_Cost*x_Establishment_+Environmental_Spread_Cost*x_Spread_')
		copyEquation('Human_Health_Consequences', 'Human_Health_Est_Cost*x_Establishment_+Human_Health_Spread_Cost*x_Spread_')
		copyEquation('Social_cultural_Consequences', 'Social_cultural_Est_Cost*x_Establishment_+Social_cultural_Spread_Cost*x_Spread_')

		if step > -burnIn:
			master.node(convert('Pests__t_1__')).setEquation(convert('Pests__t_1__')+'=ts'+str(step-1).replace('-','_')+'_x_Pests')
			master.node(convert('Establishment___t_1__')).setEquation(convert('Establishment___t_1__')+'=ts'+str(step-1).replace('-','_')+'_x_Establishment_')

def vect2SwitchEq (vec, parent):
	eq = 'Switch('+parent
	for i,ele in enumerate(vec):
		eq=eq+','+str(i)+','+str(ele)
	eq = eq+')'
	return eq

def initialiseTimeSlice(scenarioId, net, step):
	def convert(node):
		return 'ts'+str(step).replace('-','_')+'_'+node
		
	def copyEquation(node, eq):
		net.node(convert(node)).setEquation(convert(node)+'='+eq)
		
	outputDir = f'outputs/scenario{scenarioId}'
		
	with serverDb() as db:
		rs = db.query("""select * from eradicationDetection where scenarioId = ?""",[scenarioId]).fetchone()
		copyEquation('Eradication_Detection', str(rs['Erad_Detect']))
		copyEquation('Eradication_Control', str(rs['Erad_Control']))	
		
		gs= ['1','1','1','1','Bernoulli(0.5)','0','0','0','Bernoulli(0.5)','1','1','1']
		
		rs = db.query("""select * from landsuitability where scenarioId = ?""",[scenarioId])		
		vec = []
		for row in rs:
			vec.append(row['suitability'])
		copyEquation('LS', vect2SwitchEq(vec, convert('LU')))
		
			
		for ele1,ele2 in [('Economic_Spread_Cost', 'ECON_SPREAD'), 
							('Environmental_Spread_Cost', 'ENV_SPREAD'), 
							('Social_cultural_Spread_Cost', 'SOC_SPREAD'), 
							('Human_Health_Spread_Cost', 'HEALTH_SPREAD'),
							('Economic_Est_Cost', 'ECON_EST'),
							('Environmental_Est_Cost', 'ENV_EST'),
							('Social_cultural_Est_Cost', 'SOC_EST'),
							('Human_Health_Est_Cost', 'HEALTH_EST')]:
			rs = db.query("""select """+ele2+""" as cons from consequences where scenarioId = ? order by landcover""",[scenarioId])

			vec = []
			for row in rs:
				vec.append(row['cons'])
			copyEquation(ele1, str(vect2SwitchEq(vec, convert('LU'))))	
			
			
		rs = db.query("""select * from mortalityRate where scenarioId = ?""",[scenarioId]).fetchone()
		vec = [float(rs['UNSUITABLE']), float(rs['MARGINAL']), float(rs['SUITABLE']), float(rs['FAVOURABLE'])]
		copyEquation('Dieoff', str(vect2SwitchEq(vec, convert('Habitat_Suitability'))))
			
		rs = db.query("""select * from establishmentRate where scenarioId = ?""",[scenarioId]).fetchone()
		vec = [float(rs['UNSUITABLE']), float(rs['MARGINAL']), float(rs['SUITABLE']), float(rs['FAVOURABLE'])]
		copyEquation('Establishment_Rate', str(vect2SwitchEq(vec, convert('Habitat_Suitability'))))
			
		rs = db.query("""select * from eradicationRate where scenarioId = ?""",[scenarioId]).fetchone()
		vec = [float(rs['UNSUITABLE']), float(rs['MARGINAL']), float(rs['SUITABLE']), float(rs['FAVOURABLE'])]
		copyEquation('Eradication_Natural', str(vect2SwitchEq(vec, convert('Habitat_Suitability'))))
			
		rs = db.query("""select * from spreadRate where scenarioId = ?""",[scenarioId]).fetchone()
		vec = [float(rs['UNSUITABLE']), float(rs['MARGINAL']), float(rs['SUITABLE']), float(rs['FAVOURABLE'])]
		copyEquation('Spread_Rate', str(vect2SwitchEq(vec, convert('Habitat_Suitability'))))
	


def rolloutModel(scenarioId, burnIn, runLength):
		master = Net()
		net = Net("bns/Location.xdsl")
		for step in range(-burnIn, runLength):
			copyTimeSlice(net, master, step, burnIn)
			initialiseTimeSlice(scenarioId, master, step)
		return master
		
	
def vect2BernEq (vec):
	def vect2BernEq1(vec, ele):
		if len(vec)==1 or sum(vec)==0:
			return str(ele)
		else:
			return 'If(Bernoulli({}),{},{})'.format(vec[0]/sum(vec),ele,vect2BernEq1(vec[1:],ele+1))
	return vect2BernEq1(normalise(vec),0)


def initialiseLocationTimeSlice(net, step, loc, area, expIn, disIn, climIn, habIn, code, nodeNames = None):

	def convert(node):
		return 'ts'+str(step).replace('-','_')+'_'+node
	def copyEquation(node, eq):
		net.node(convert(node)).setEquation(convert(node)+'='+eq)
	
	#0 is unmapped = ocean, so added to water
	
	LUVec = [ 
		float(habIn[code]['v1.0']), 
		float(habIn[code]['v2.0']), 
		float(habIn[code]['v3.0']), 
		float(habIn[code]['v4.0']), 
		float(habIn[code]['v5.0']), 
		float(habIn[code]['v6.0']), 
		float(habIn[code]['v7.0']), 
		float(habIn[code]['v8.0']), 
		float(habIn[code]['v9.0']), 
		float(habIn[code]['v10.0']), 
		float(habIn[code]['v11.0']), 
		float(habIn[code]['v12.0']), 
		float(habIn[code]['v13.0'])]
	copyEquation('LU', vect2BernEq(LUVec))
	
	if climIn is not None :
		clim = climIn[code]
		copyEquation('EI', 'Triangular('+clim['EI_min_cor']+', '+clim['EI_avg_cor']+', '+clim['EI_max_cor']+')')
		copyEquation('GI', 'Triangular('+clim['GI_min_cor']+', '+clim['GI_avg_cor']+', '+clim['GI_max_cor']+')')
	else:
		copyEquation('EI', '100')
		copyEquation('GI', '100')
			
	copyEquation('Disperse_Pests_Count', disIn[month(step%12)][code]['uDisperses'])
	copyEquation('Exposure_Pests_Count', expIn[month(step%12)][code]['uExposures'])
	copyEquation('Area', area[code]['area_sqkm'])
	


def make_establishment_maps(scenarioId, burnIn = 12, runLength = 24, climateMap = 'Climate Temperate'):
	def csv2dict(filename):
		with open(filename, newline='') as file:
			return {row['Code']: row for row in csv.DictReader(file)}
		
	outputDir = f'outputs/scenario{scenarioId}'
	
	disIn = dict()
	expIn = dict()
	for monthId in range(0, 12):
		disIn[month(monthId)]=csv2dict(os.path.join(outputDir, "Dispersal_Pests_"+month(monthId)+".csv"))
		expIn[month(monthId)]=csv2dict(os.path.join(outputDir, "Exposure_Pests_"+month(monthId)+".csv"))
		
	try:
		climIn = csv2dict('inputs/climatemaps/'+climateMap+'.csv')
	except:
		print('inputs/climatemaps/'+climateMap+'.csv')
		climIn=None
		
	
	habIn=csv2dict('inputs/landcover/land_cover.csv')
	area=csv2dict('inputs/10kmHexClippedNZTM/10kmHexClippedNZTM.csv')

	template = csv.DictReader(io.open('inputs/10kmHexClippedNZTM/nz_template.csv', newline=''))
	outputs = ['CS', 'LS', 'Habitat_Suitability', 'Exposure_Pests_Density', 'Disperse_Pests_Density', 'x_Pests', 'x_Establishment_', 'x_Spread_', 'Economic_Consequences', 'Environmental_Consequences', 'Human_Health_Consequences', 'Social_cultural_Consequences']
	outCsvs = dict()
	
	for out in outputs:
		outCsvs[out] = dict()
		for step in range(runLength):
			outCsvs[out][step]=csv.DictWriter(io.open(os.path.join(outputDir, out+'_'+str(step)+'.csv'), 'w', newline=''), template.fieldnames)
			outCsvs[out][step].writeheader()
			
	fieldnames = ['Code', 'AU2013_NAM']
	for out in outputs:
		for step in range(runLength):
			fieldnames += [out+'_'+str(step)+'_uPeSqKm', out+'_'+str(step)+'_sdPeSqKm']


	net = rolloutModel(scenarioId, burnIn, runLength)
	net._setSamples(1000, 1000)
	
	nodeNames = [node.name() for node in net.nodes()]

	for i, loc in enumerate(template):
		print('location: '+str(i), end="\r")
		loc = dict(loc)
		
		for step in range(-burnIn, runLength):
			initialiseLocationTimeSlice(net, step, i, area, expIn, disIn, climIn, habIn, loc['Code'], nodeNames = nodeNames)
		net.update()
			
		for out in outputs:
			for step in range(runLength):
				loc['uPeSqKm'] = net.node('ts'+str(step)+'_'+out)._equationMean()
				# loc['sdPeSqKm'] = sdPeSqKm
				outCsvs[out][step].writerow(loc)
