MIP_CONFIG = {

    # data variables
    'data_structure': 'pandas',
    'lat_var': 'lat',
    'lng_var': 'lng',

    # basic variables
    'slack_max': 0,
    'num_vehicles': 1,
    'depot_idx': 0,
    'null_capacity_slack': 0,
    'vehicle_capacity': 999999999999,  # a very large number
    'set_unit_demands': False,
    'fix_start_cumul_to_zero_demand': True,
    'demand': 'Demand',
    'capacity': 'Capacity',
    'use_default_search_params': True,

    # time / demand variables
    'time_per_demand_unit': 3,
    'speed': 1,
    'fix_start_cumul_to_zero_time': True,
}
