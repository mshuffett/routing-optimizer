import logging
from datetime import datetime, timedelta

import copy

from phocus.model.location import Location
from phocus.model.solution import Solution
from phocus.utils import bootstrap_project
from phocus.utils.files import real_long_island_data
from phocus.utils.distance_matrix_loader import load_distance_matrix_data
from phocus.utils.maps import Coordinate

HOME = Location('Elena', '900 Madison St', 40.624505, -73.697592, 'Hewlett Neck', 'NY')

logger = logging.getLogger(__name__)


def elena_location_indices():
    """Find the indices corresponding to Elena's doctors"""
    names = [
        HOME.doctor_name,
        'Condreras Susan',
        'Feldman',
        'Leo',
        'Nambiar, Seema',
        'Karen Olivieri',
        'Gustavson Leah',
        'Sanzar Muhhamad',
        'Frendo ',
        'Alan Weisman',
        'Kalonaros, Vasilios',
        'Modi ',
        'Wishner',
        'Moriarty/Michelle',
        'Yagoot, Khan',
        'Ednalino',
        'Robert, McCord',
        'Quraishi',
        'Alongi',
        HOME.doctor_name,
        'Weissberg',
        'Kalmar, Robert',
        'Kalmar, Mat',
        'Jacob',
        'Paci James',
        'Rizzi Angelo',
        'Jane Thitima Herfel',
        'Godhwani, Sanjay',
        'Tan',
        'Stubel',
        'Scarpinatto',
        'Johnson, Sara',
        'Ramsammy',
        HOME.doctor_name,
        'Carpentieri Adam',
        'Albert, Sunil',
        'Faisal, Malik',
        'Cappellino',
        'Abraham',
        'Heinisch',
        'Shapiro Eric',
        'Yadira, Pena',
        'Stephanie, Agguire',
        'Kohane',
        'Levine, Cary / AnnMarie',
        'Collin',
        'Andrianova Marina',
        'Jeffrey Perry',
        'Plavnik',
        'Burducea',
        'Alejo',
        HOME.doctor_name,
        "Barbara Somers",
        "Emily Malinowski",
        "jenna Larocca",
        "Hussain Mohammad",
        "Jasjit Singh",
        "Cipolla Thomas",
        "Morrison *",
        "spain",
        "Waxman Larry",
        "Blau",
        "Alejo",
        "Rachael O'Mara",
        "Coleen Schneider",
        "Thomas Jan",
        "Benhuri",
        "Juan Goez",
        HOME.doctor_name,
        "Gruber / craig",
        "Dascalu",
        "Vuong",
        "Ruffo",
        "Austriacu",
        "Ruotolo Charles",
        "Spain",
        "Groth, Timothy",
        "Krishnan, Raj",
        "Chernoff",
        "Anne McGrath",
        "Morgan Smyth",
        "Dorman Christine",
        "Makarovsky, Ilya",
        "Alison Graziano",
        "Ellis Merlan",
        "Erica Papathomas",
        "Martin Schick",
        HOME.doctor_name,
    ]
    locations = real_long_island_data()
    location_names = [loc.doctor_name for loc in locations]
    found_names = [name for name in names if name in location_names]
    indices = [location_names.index(name) for name in found_names]
    return indices


def make_elena_solution():
    locations = real_long_island_data()
    coordinates = list(map(lambda loc: Coordinate(lat=loc.lat, long=loc.lon), locations))
    distance_matrix = load_distance_matrix_data(coordinates)
    indices = elena_location_indices()
    doctors_visited = len(indices) - 6
    metrics = {'doctors_visited': doctors_visited}

    route_indices = [(copy.copy(locations[i]), i) for i in indices]
    route = [x[0] for x in route_indices]

    prev_node = None
    total_travel_time = 0
    for location, i in route_indices:
        if prev_node is not None:
            total_travel_time += int(distance_matrix[prev_node, i])
            location.travel_to_time = int(distance_matrix[prev_node, i])
        prev_node = i

    metrics['travel_time'] = total_travel_time
    metrics['avg_travel_time'] = total_travel_time / doctors_visited
    solution = Solution('Elena', datetime.now(), route, metrics=metrics)
    solution.save('elena.json')

    current_datetime = datetime(2018, 1, 1, hour=9)
    day_travel_seconds = 0
    day_visits = 0
    for loc in route[1:]:
        if loc.doctor_name == HOME.doctor_name:
            logger.info('Total travel time for %s was %s', current_datetime, day_travel_seconds)
            logger.info('%d doctors visited', day_visits)
            logger.info('Inferred visit time is %s minutes', (8 * 60 * 60 - day_travel_seconds) / day_visits / 60)
            current_datetime += timedelta(days=1)
            day_travel_seconds = 0
            day_visits = 0
        else:
            loc.arrival_time = str(current_datetime)
            day_travel_seconds += loc.travel_to_time
            day_visits += 1


if __name__ == '__main__':
    bootstrap_project()
    make_elena_solution()
