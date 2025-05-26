"""

A journal of all changes made to the database schema. Can be re-run
at any time to ensure that the database is up-to-date.

"""
from __future__ import print_function

from builtins import range
import _env, sys, re, json, os, argparse, glob, shutil, utils
from bidb import DB

from openpyxl import load_workbook

serverDb = utils.serverDb

class DbSetup:
	version = None
	
	def __init__(self):
		try:
			os.remove('ibram.sqlite')
		except:
			pass
		self.db = DB('ibram.sqlite')
	
	def run(self, statements):
		running = False
		bumpVersion = False
		prevVersion = None
		newVersion = None
		
		for statement in statements:
			params = None
			if isinstance(statement,list):
				params = statement[1:]
				statement = statement[0]
		
			addedStatement = re.match(r"ADDED\s+(.*)", statement)
			# START/STOP is for manually controlling statement execution. Best
			# to use ADDED <date-version>, unless in mid-development.
			if statement == "START":
				running = True
			elif statement == "STOP":
				running = False
			elif addedStatement:
				# This is for versioning. Suggest putting ISO-ish date, but any string
				# higher than the previous string will do.
				newVersion = addedStatement.group(1)
				rs = None
				try:
					rs = self.db.query("select version from dbversion")
				except:
					# Table not defined, create it. (Well, maybe some other
					# error, but if there is, this will throw that error too.)
					self.db.query("create table dbversion (version text)")
					self.db.query("insert into dbversion (version) values ('')")
					rs = self.db.query("select version from dbversion")
			
				row = rs.fetchone()
				if str(row["version"]) < newVersion:
					if prevVersion is not None:
						print("prevVersion:", prevVersion)
						self.db.query("update dbversion set version = ?", [prevVersion])
					print("Updating to", newVersion)
					running = True
					bumpVersion = True
				else:
					running = False
				prevVersion = newVersion
			elif running:
				if params:
					print(statement, params)
					self.db.query(statement, params)
				else:
					print(statement)
					self.db.query(statement)
				
		if bumpVersion:
			self.db.query("update dbversion set version = ?", [newVersion])
		
		
	def s_body(self):
		self.run([
			# This database will be recreated *every* time, so there's no schema to preserve
			# when upgrading. As such, just make the date below the last modified date
			# on every change.
				
			"START",
			"CREATE TABLE project (id integer primary key, name text, burnIn integer, runLength integer, climateMap text, dispersalSd double)",
			"CREATE TABLE scenario (id integer primary key, name text, projectId integer, isBase boolean, active boolean, status text, processId integer, complete boolean, startTime datetime, runtime double)",
			"CREATE TABLE item (id integer primary key, name text)",			
			"CREATE TABLE pathwayPoint (id integer primary key, name text, item text, itemId integer, tableName text, shape text, timeAtSite text)",
			"CREATE TABLE climateMap (id integer primary key, name text, fileName text)",
			"CREATE TABLE landCover (id integer primary key, name text)",

			"CREATE TABLE vector (id integer primary key, scenarioId integer, vectorId, name text)",
			"CREATE TABLE units (id integer primary key, scenarioId integer, item text, itemId integer, subItem text, source text, jan double, feb double, mar double, apr double, may double, jun double, jul double, aug double, sep double, oct double, nov double, dec double)",
			"CREATE TABLE infestationRate (id integer primary key, scenarioId integer, item text, itemId integer, subItem text, source text, vector text, vectorId integer, jan double, feb double, mar double, apr double, may double, jun double, jul double, aug double, sep double, oct double, nov double, dec double)",
			"CREATE TABLE vectorInfectionRate (id integer primary key, scenarioId integer, source text, vector text, vectorId integer, jan double, feb double, mar double, apr double, may double, jun double, jul double, aug double, sep double, oct double, nov double, dec double)",
			"CREATE TABLE itemInfectionRate (id integer primary key, scenarioId integer, item text, itemId integer, subItem text, source text, jan double, feb double, mar double, apr double, may double, jun double, jul double, aug double, sep double, oct double, nov double, dec double)",
			"CREATE TABLE itemVectorTransmissionRate (id integer primary key, scenarioId integer, item text, itemId integer, vector text, vectorId integer, jan double, feb double, mar double, apr double, may double, jun double, jul double, aug double, sep double, oct double, nov double, dec double)",
			"CREATE TABLE preBorderVectorDetection (id integer primary key, scenarioId integer, item text, itemId integer, subItem text, source text, vector text, vectorId integer, detectionRate double, treatmentRateForUndetected double, treatmentEfficacy double)",
			"CREATE TABLE preBorderItemDetection (id integer primary key, scenarioId integer, item text, itemId integer, subItem text, source text, detectionRate double, treatmentRateForUndetected double, treatmentEfficacy double)",
			"CREATE TABLE vectorsPerUnit (id integer primary key, scenarioId integer, item text, itemId integer, subItem text, vector text, vectorId integer, jan double, feb double, mar double, apr double, may double, jun double, jul double, aug double, sep double, oct double, nov double, dec double)",
			"CREATE TABLE vectorPathwayDetection (id integer primary key, scenarioId integer, item text, itemId integer, vector text, vectorId integer, pathwayPoint text, pathwayPointId integer, detectionRate double, treatmentRateForUndetected double, treatmentEfficacy double)",
			"CREATE TABLE itemPathwayDetection (id integer primary key, scenarioId integer, item text, itemId integer, pathwayPoint text, pathwayPointId integer, detectionRate double, treatmentRateForUndetected double, treatmentEfficacy double)",
			"CREATE TABLE vectorDailyEscapeRate (id integer primary key, scenarioId integer, item text, itemId integer, vector text, vectorId integer, pathwayPoint text, pathwayPointId integer, jan double, feb double, mar double, apr double, may double, jun double, jul double, aug double, sep double, oct double, nov double, dec double)",
			"CREATE TABLE itemDailyEscapeRate (id integer primary key, scenarioId integer, item text, itemId integer, pathwayPoint text, pathwayPointId integer, jan double, feb double, mar double, apr double, may double, jun double, jul double, aug double, sep double, oct double, nov double, dec double)",
			"CREATE TABLE vectorDailyMortalityRate (id integer primary key, scenarioId integer, item text, itemId integer, vector text, vectorId integer, pathwayPoint text, pathwayPointId integer, jan double, feb double, mar double, apr double, may double, jun double, jul double, aug double, sep double, oct double, nov double, dec double)",
			"CREATE TABLE itemDailyMortalityRate (id integer primary key, scenarioId integer, item text, itemId integer, pathwayPoint text, pathwayPointId integer, jan double, feb double, mar double, apr double, may double, jun double, jul double, aug double, sep double, oct double, nov double, dec double)",
			"CREATE TABLE vectorTransmissionRate (id integer primary key, scenarioId integer, item text, itemId integer, vector text, vectorId integer, pathwayPoint text, pathwayPointId integer, jan double, feb double, mar double, apr double, may double, jun double, jul double, aug double, sep double, oct double, nov double, dec double)",
			"CREATE TABLE mortalityRate (id integer primary key, scenarioId integer, favourable double, suitable double, marginal double, unsuitable double)",
			"CREATE TABLE establishmentRate (id integer primary key, scenarioId integer, favourable double, suitable double, marginal double, unsuitable double)",
			"CREATE TABLE spreadRate (id integer primary key, scenarioId integer, favourable double, suitable double, marginal double, unsuitable double)",
			"CREATE TABLE eradicationRate (id integer primary key, scenarioId integer, favourable double, suitable double, marginal double, unsuitable double)",
			"CREATE TABLE landSuitability (id integer primary key, scenarioId integer, landcover text, suitability text)",
			"CREATE TABLE consequences (id integer primary key, scenarioId integer, landcover text, ECON_EST double, ECON_SPREAD double, ENV_EST double, ENV_SPREAD double, SOC_EST double, SOC_SPREAD double, HEALTH_EST double, HEALTH_SPREAD double)", 
			"CREATE TABLE eradicationDetection (id integer primary key, scenarioId integer, erad_detect float, erad_control float)",


			# "CREATE TABLE entries (id integer primary key, scenarioId integer, item text, itemId integer, subItem text, source text, vector text, vectorId integer, jan double, feb double, mar double, apr double, may double, jun double, jul double, aug double, sep double, oct double, nov double, dec double)",
			
		])

ap = argparse.ArgumentParser()
ap.add_argument('input', nargs='?', default=None, help='The path to the parameters file')
args = ap.parse_args()

dbSetup = DbSetup()
dbSetup.s_body()

if args.input is not None:
	with serverDb() as db:
		wb = load_workbook(args.input)
		db.loadDataFromExcel(wb)


