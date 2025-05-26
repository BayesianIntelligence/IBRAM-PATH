import sqlite3, csv, re, os

gOpen = open

def open(csvFns):
	db = sqlite3.connect(':memory:')
	
	for csvFn in csvFns:
		add(db, csvFn)
	
	return db

def getTableName(csvFn):
	csvFn = os.path.basename(csvFn)
	tableName = re.sub(r'\.csv$', '', csvFn)
	tableName = re.sub(r'^[^a-zA-Z_]', '', tableName)
	tableName = re.sub(r'[^a-zA-Z0-9_]', '', tableName)
	return tableName

def add(db, csvFn):
	with gOpen(csvFn, 'r', newline='') as csvFile:
		inCsv = csv.reader(csvFile)
		
		tableName = getTableName(csvFn)
		
		fieldNames = next(inCsv)
		
		for i,f in enumerate(fieldNames):
			num = 0
			while f in fieldNames[:i]:
				f = fieldNames[i] + str(num)
				num += 1
			fieldNames[i] = f
		
		fields = ''
		fieldPlaces = ''
		sep = ''
		for field in fieldNames:
			fields += sep + field
			fieldPlaces += sep + '?'
			sep = ','
		
		db.execute('create table '+tableName+' ('+fields+')')
		
		for row in inCsv:
			db.execute('insert into '+tableName+' ('+fields+') values ('+fieldPlaces+')', row)

