# first line: 37
@memory.cache
def gmaps_distance_matrix(
    origins,
    destinations,
    departure_time=NEXT_MONDAY_8_AM_EASTERN,
    origin_offset=None,
    origin_end=None,
    dest_offset=None,
    dest_end=None,
):
    client = get_client()

    @retry(wait=wait_random_exponential(multiplier=1, max=60), stop=stop_after_delay(5 * 60))
    def distance_matrix_with_retry():
        return client.distance_matrix(
            origins=origins,
            destinations=destinations,
            departure_time=departure_time,
        ), origin_offset, origin_end, dest_offset, dest_end

    return distance_matrix_with_retry()
