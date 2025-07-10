import geopandas as gpd

INPUT_PATH = "web_app/static/LAU_RG_01M_2023_4326.geojson"
OUTPUT_PATH = "web_app/static/simplified_regions.geojson"


def main():
    """Simplify LAU regions by dissolving into larger regions."""
    gdf = gpd.read_file(INPUT_PATH)
    # Extract first four characters of LAU_ID as region code
    gdf["region_code"] = gdf["LAU_ID"].str[:4]
    # Dissolve geometries by region_code
    simplified = gdf.dissolve(by="region_code")
    simplified.to_file(OUTPUT_PATH, driver="GeoJSON")


if __name__ == "__main__":
    main()
