# first line: 10
@memory.cache
def load_distance_matrix_data(coordinates: Sequence[Coordinate]) -> np.ndarray:
    logger.info("Existing distance matrix data not found")
    maps_utils = MapsUtils()
    distance_matrix = maps_utils.get_distance_matrix(coordinates=coordinates)
    return distance_matrix
