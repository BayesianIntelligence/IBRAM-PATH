import sys, re, json, csv, optparse, math, time, os

# mb,au field
mb_field = 0
au_field = 1

# read mb_au mappings
map_file = "mb/MB_AU_mapping.csv"
print("Populating MB and AU from ", str(map_file))


inFile = open(map_file)
reader = csv.DictReader(inFile)
mb_au = [[]]
test = {}
field_names = []
for i in range(0,len(reader.fieldnames)):
	field_names.append(reader.fieldnames[i])
	mb_au.append([])

print(field_names)

for row in reader:
	j = 0
	for field in field_names:
		mb_au[j].append(row[field])
		j += 1

for i in range(0, len(mb_au[mb_field])):
	test[mb_au[mb_field][i]] = mb_au[au_field][i]

# open each file and change code from mesh block to area unit
for file_name in os.listdir('mb'):
	if file_name.endswith(".csv"):# and re.search(r'residents', file_name):
		if file_name.endswith("_mb.csv") or file_name.endswith("_au.csv"):
			continue
		f_name = file_name.split(".csv")
		in_file = open(f'mb/{file_name}')
		reader_1 = csv.DictReader(in_file)
		# check to make sure we have a code column
		# if no, then don't do anything
		t_field_names = []
		code_found = False
		

		for i in range(0,len(reader_1.fieldnames)):
				t_field_names.append(reader_1.fieldnames[i])
				if t_field_names[i] == 'Code':
					code_found = True
		if not code_found:
			continue

		print('Converting', file_name)

		# now write the appropriate files				
		mbFile = open(f"mb/{f_name[0]}_mb.csv", 'w', newline='', encoding='utf-8')
		auFile = open(f"mb/{f_name[0]}_au.csv", 'w', newline='', encoding='utf-8')

		writer_1 = csv.writer(mbFile)
		writer_2 = csv.writer(auFile)
		print(t_field_names)
		writer_1.writerow(t_field_names)
		writer_2.writerow(t_field_names)
		au_rows = {}
		code_field = -1
		for row in reader_1:
				row_to_write_mb = []
				row_to_write_au = []
				for field in t_field_names:
					row_to_write_mb.append(row[field])
					if field == 'Code':
						# save index of code field
						if code_field == -1: code_field = len(row_to_write_au)
						# search for the area unit
						val = int(row[field])
						row_to_write_au.append(test[row[field]] if row[field] in test else test[min(test.keys(), key=lambda k: abs(int(k)-val))])
					else:
						row_to_write_au.append(row[field])
				writer_1.writerow(row_to_write_mb)
				#writer_2.writerow(row_to_write_au)
				code = row_to_write_au[code_field]
				if code not in au_rows:
					au_rows[code] = [None]*len(row_to_write_au)
				for i,val in enumerate(row_to_write_au):
					if i != code_field:
						# summing works for all MB files we have thus far, if we have numbers
						is_float = False
						try:
							val = float(val)
							is_float = True
						except: pass
						if is_float:
							try:
								# try to sum
								au_rows[code][i] += val
							except:
								# if we fail, assign instead
								au_rows[code][i] = val
						else:
							if au_rows[code][i] is None:
								au_rows[code][i] = val
					else:
						au_rows[code][i] = code
							
				
		for code in sorted(au_rows.keys()):
			writer_2.writerow(au_rows[code])
						
