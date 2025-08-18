import geopandas as gpd
from shapely.geometry import Polygon
import numpy as np
from math import sqrt, cos, sin, pi
import matplotlib.pyplot as plt

def make_hexagon(xc, yc, r):
	angles = np.linspace(0, 2 * pi, 7)
	return Polygon([(xc + r * cos(a), yc + r * sin(a)) for a in angles])

def hex_grid(bounds, hex_diameter_m):
	r = hex_diameter_m / 2
	h = sqrt(3) * r
	w = 2 * r
	x_step = 3 / 4 * w
	y_step = h
	xmin, ymin, xmax, ymax = bounds
	cols = int((xmax - xmin) / x_step) + 1
	rows = int((ymax - ymin) / y_step) + 1

	hexes = []
	for row in range(rows):
		for col in range(cols):
			x = xmin + col * x_step
			y = ymin + row * y_step
			if col % 2 == 1:
				y += y_step / 2
			hexes.append(make_hexagon(x, y, r))

	return gpd.GeoDataFrame(geometry=hexes, crs="EPSG:2193")


if __name__ == "__main__":
	# Load original NZ outline and apply buffer to each polygon individually
	nz_raw = gpd.read_file("maps/nzoutline.shp").to_crs("EPSG:2193")
	nz_raw["geometry"] = nz_raw.geometry.buffer(-1000)

	# Filter out small artifacts
	nz_outline = nz_raw[nz_raw.area > 1e6]
	nz_outline = nz_outline.explode(index_parts=False).reset_index(drop=True)

	# Save buffered outline
	nz_outline.to_file("maps/nzoutline_buffered.shp")
	print("Buffered outline saved.")

	# Generate hex grid and clip to buffered NZ outline
	hexes = hex_grid(nz_outline.total_bounds, hex_diameter_m=7000)
	clipped = gpd.overlay(hexes, nz_outline, how="intersection")
	clipped = clipped[clipped.area > 1e6]

	# Add or overwrite metadata fields
	clipped["Code"] = range(1, len(clipped) + 1)
	clipped["area"] = clipped.geometry.area

	# Move 'Code' to the front
	cols = ["Code"] + [c for c in clipped.columns if c != "Code"]
	clipped = clipped[cols]

	# Generate centroid-based names
	centroids_proj = clipped.geometry.centroid
	centroids_latlon = gpd.GeoSeries(centroids_proj, crs="EPSG:2193").to_crs("EPSG:4326")
	clipped["Name"] = centroids_latlon.apply(lambda p: f"{p.y:.4f},{p.x:.4f}")
	clipped["Code"] = clipped["Code"].astype(str)

	# Save outputs
	clipped.to_file("maps/7kmHexNZ.shp")
	clipped.to_csv("maps/7kmHexNZ.csv")
	print("Hex grid saved.")
