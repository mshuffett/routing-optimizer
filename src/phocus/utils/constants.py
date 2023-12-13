from pathlib import Path

PHOCUS_PATH = Path(__file__).resolve().parents[1]
DATA_PATH = PHOCUS_PATH / 'data'
TEST_DATA_PATH = DATA_PATH / 'test_data'
OUTPUT_PATH = PHOCUS_PATH.parents[1] / 'output'
ELENA_RAW_DATA_PATH = DATA_PATH / 'Elena Routing 2018.xlsx'
LONG_ISLAND_LOCATIONS_CSV_PATH = DATA_PATH / 'long_island_locs.csv'
DATA_EXERCISE_JSON_PATH = OUTPUT_PATH / 'Data_Exercise.json'
CANDICE_JSON_PATH = OUTPUT_PATH / 'Candice_HCP_Data_Sheet_3.json'
CANDICE_APPLES_TO_APPLES_JSON_PATH = OUTPUT_PATH / 'Candice.Routing.2018.json'
NEW_ELENA_JSON_PATH = OUTPUT_PATH / 'Elena.Routing.2018.json'
CALIBRATION_DATA_PATH = DATA_PATH / 'Calibration Data Input_Actual Visit.xlsx'
HCP_DATA_PATH = DATA_PATH / 'HCP Data Full Universe.csv'
CACHE_DIR: Path = OUTPUT_PATH / 'cache'
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# API PARAMS
START_LOCATION = 'startLocation'
END_LOCATION = 'endLocation'
LOCATIONS = 'locations'