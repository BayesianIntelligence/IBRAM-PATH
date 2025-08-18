import geopandas as gpd
import pandas as pd


def resample_poly(inShpFn, outShpFn, inCsvFn, outCsvFn, joinKey, outFields):
	shpIn = gpd.read_file(inShpFn).to_crs("EPSG:2193")
	csvIn = pd.read_csv(inCsvFn).rename(columns={"Code": "Join_Code"})

	shpIn[joinKey] = shpIn[joinKey].astype(str)
	csvIn["Join_Code"] = csvIn["Join_Code"].astype(str)

	shpIn = shpIn.merge(csvIn, left_on=joinKey, right_on="Join_Code", how="left")
	shpOut = gpd.read_file(outShpFn).to_crs("EPSG:2193")

	intersection = gpd.overlay(shpOut, shpIn, how="intersection")
	intersection["intersect_area"] = intersection.geometry.area
	intersection["in_area"] = intersection.groupby(joinKey)["intersect_area"].transform("sum")
	intersection["area_weight"] = intersection["intersect_area"] / intersection["in_area"]

	shpOut = shpOut.set_index("Code")

	for field in outFields:
		intersection["out_weighted"] = intersection["area_weight"] * intersection[field]
		hex_vals = intersection.groupby("Code", as_index=False)["out_weighted"].sum()
		hex_vals = hex_vals.rename(columns={"out_weighted": field})
		shpOut = shpOut.join(hex_vals.set_index("Code"), on="Code")

	shpOut = shpOut.reset_index().fillna(0)
	shpOut[["Code"] + outFields].to_csv(outCsvFn, index=False)
	
def sample_at_centroids(input_shp, output_shp, csv_data, out_csv, join_key, value_fields):
	# Load input map (must cover all of NZ)
	source = gpd.read_file(input_shp).to_crs("EPSG:2193")

	# Load output polygons (e.g. hexes)
	target = gpd.read_file(output_shp).to_crs("EPSG:2193")

	# Load attribute values (e.g. from CSV) to merge into source polygons
	csv_df = pd.read_csv(csv_data).rename(columns={"Code": "Join_Code"})
	source[join_key] = source[join_key].astype(str)
	csv_df["Join_Code"] = csv_df["Join_Code"].astype(str)
	source = source.merge(csv_df, left_on=join_key, right_on="Join_Code", how="left")

	# Generate centroids for output polygons
	centroids = target.copy()
	centroids["geometry"] = centroids.geometry.centroid

	# Spatial join: assign input values to centroids
	joined = gpd.sjoin(centroids, source[value_fields + ["geometry"]], how="left", predicate="within")

	# Merge results back to target polygons by index
	for field in value_fields:
		target[field] = joined[field].values

	# Export
	target[["Code"] + value_fields].to_csv(out_csv, index=False)

	

port_df = pd.read_csv('pathwayPoints/old/port.csv')
item_port_df = pd.read_csv('pathwayPoints/old/itemPorts.csv')

merged_df = item_port_df.merge(port_df, left_on="portId", right_on="id")
merged_df[merged_df['item'] == 'Returning Residents'].to_csv('pathwayPoints/Passenger_ports_residents.csv')
merged_df[merged_df['item'] == 'Visitors'].to_csv('pathwayPoints/Passenger_ports_visitors.csv')
merged_df[merged_df['item'] == 'Furniture'].to_csv('pathwayPoints/Fruit_ports.csv')


outShpFn = "maps/7kmHexNZ.shp"
outField = "proportionToHere"

inShpFn = "maps/statistical-area-2-2018-clipped-generalised.shp"
joinKey = "SA22018_V1"



inCsvFn = "pathwayPoints/old/population_jun2018_sa2.csv"
outCsvFn = "pathwayPoints/Passenger_endpoints_residents.csv"

resample_poly(inShpFn, outShpFn, inCsvFn, outCsvFn, joinKey, [outField])

inCsvFn = "pathwayPoints/old/population_jun2018_sa2.csv"
outCsvFn = "pathwayPoints/Fruit_endpoints.csv"

resample_poly(inShpFn, outShpFn, inCsvFn, outCsvFn, joinKey, [outField])

inShpFn = "maps/AU2013_GV_Clipped_nomulti.shp"
joinKey = 'AU2013'



inCsvFn = "pathwayPoints/old/Passenger_endpoints_visitors_au.csv"
outCsvFn = "pathwayPoints/Passenger_endpoints_visitors.csv"

resample_poly(inShpFn, outShpFn, inCsvFn, outCsvFn, joinKey, [outField])

inCsvFn = "pathwayPoints/old/Fruit_shops.csv"
outCsvFn = "pathwayPoints/Fruit_shops.csv"

resample_poly(inShpFn, outShpFn, inCsvFn, outCsvFn, joinKey, [outField])




outFields = 'EI_min_cor,EI_max_cor,EI_avg_cor,GI_min_cor,GI_max_cor,GI_avg_cor'.split(',')

inCsvFn = "climateMaps/old/Climate Temperate.csv"
outCsvFn = "climateMaps/Climate Temperate.csv"

sample_at_centroids(inShpFn, outShpFn, inCsvFn, outCsvFn, joinKey, outFields)


outFields = 'v0.0,v1.0,v10.0,v11.0,v12.0,v13.0,v2.0,v3.0,v4.0,v5.0,v6.0,v7.0,v8.0,v9.0'.split(',')


inCsvFn = "land_cover/old/land_cover.csv"
outCsvFn = "land_cover/land_cover.csv"

resample_poly(inShpFn, outShpFn, inCsvFn, outCsvFn, joinKey, outFields)