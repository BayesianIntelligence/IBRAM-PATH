import _env, json, os, xlwt, csv, csvdb

from bidb import DB

# Settings file with directories, etc.
def getSettings():
	with open('settings.json','r') as settingsFile:
		settings = json.load(settingsFile)
	
	# with open('settings.establishments.json', 'r') as settingsFile:
	# 	settings["establishments"] = json.load(settingsFile)
	
	return settings

def getOutputDir(scenarioId):
	settings = getSettings()
	return os.path.join(settings['outputsDir'], 'scenario{}'.format(scenarioId))+'/'

def normalise (vec):
	tot = sum(vec)
	if tot > 0.0:
		return list(map(lambda x: x/tot, vec))
	else:
		return vec

# This is just an input database (because it gets overwritten with new data all the time)
def serverDb(dbFile = 'ibram.sqlite'):
	if not os.path.exists(dbFile):
		dbFile = 'ibram.sqlite'
	db = DB(dbFile)
	db.query('attach "ibram-server.sqlite" as serv')
	return db

def csv2xls(csvfile):	
	#for csvfile in glob.glob(os.path.join('.', '*.csv')):
	wb = xlwt.Workbook()
	ws = wb.add_sheet('data')
	with open(csvfile+'.csv', 'r') as f:
		reader = csv.reader(f)
		for r, row in enumerate(reader):
			for c, val in enumerate(row):
				#print(str(type(val))+' '+str(val))
				try:
					val = float(val)
				except:
					pass
				ws.write(r, c, val)
	wb.save(csvfile + '.xls')
	
# Must specify either no weights, or all weights
def mergeExposureCsvs(csvFns, outCsvFn, weights = None, gran = 0, fields = ['uExposures']):#,'uQtyArrv','uQty','uNextQty','pExposure','uPeSqKm','sdPeSqKm']):
	print(csvFns, outCsvFn)
	if weights is None:  weights = [1 for v in csvFns]
	#rint "WEIGHTS:",weights
	# Join all the layers on the 'code' field
	cdb = DB(csvdb.open(csvFns))
	#print input()
	# extraFields = ['EA_Name']#['AU2013_NAM' if gran==0 else 'MB2013_NAM']
	# extraFieldsStr = ','+(','.join(extraFields))
	tables = []
	for i,csvFn in enumerate(csvFns):
		# tables.append('select Code,'+(','.join(f+'*'+str(weights[i])+' as t_'+f for f in fields))+extraFieldsStr+' from '+csvdb.getTableName(csvFn))
		tables.append('select Code,'+(','.join(f+'*'+str(weights[i])+' as t_'+f for f in fields))+' from '+csvdb.getTableName(csvFn))
	sumFields = ''
	sep = ''
	for field in fields:
		sumFields += sep + 'sum(t_'+field+')'
		sep = ','
	# sql = 'select Code, '+sumFields+extraFieldsStr+' from ('+(' union all '.join(tables))+') group by Code'
	sql = 'select Code, '+sumFields+' from ('+(' union all '.join(tables))+') group by Code'


	#print cdb.queryRows(tables[0])
	# print (sql)
	#pdb.set_trace()
	rs = cdb.query(sql)
	#print [row for row in rs]
	with open(outCsvFn, 'w',newline='') as outCsvFile:
		outCsv = csv.writer(outCsvFile)
		# outCsv.writerow(['Code']+fields+extraFields)
		outCsv.writerow(['Code']+fields)
		for row in rs:
			#print row
			row = [str(v) for v in row]
			#print row
			outCsv.writerow(row)


def month(mth):
	# Throw error if not int
	m = int(mth)
	if m == -1:
		return "Yearly"

	months = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(" ")
	if m < len(months):
		return months[m]