"""
File Name: DataExercise.py

Author: Nick Klabjan

Description: Takes in data from an excel sheet and writes it to a .json file.

__________________________________PROGRAM COMMENTS_____________________________________
- program can take in two arguments if desired of specified work hours
    - if no arguments are passed in to program, then default work hours are 9-5
"""
import sys
import xlrd
import json
from collections import OrderedDict

import phocus.utils.constants as constants
from phocus.utils.maps import lat_lon, AmbiguousAddressError

EXCEL_PATH = constants.DATA_PATH / "Elena Routing 2018 - Optimizer Analysis.xlsx"
OUTPUT_PATH = constants.OUTPUT_PATH / "Elena.Routing.2018.json"
KEY_VALUES = ['doctor_name', 'address', 'city', 'state', 'lat',
             'lon', 'is_repeat', 'blackout_windows', 'start', 'end']
# list of tuples with corresponding dates relative to their column number
DATES = [("2018-01-01T", 8), ("2018-01-02T", 9), ("2018-01-03T", 10), ("2018-01-04T", 11), ("2018-01-05T", 12)]
# constant state name for the file
STATE = "New York"


class DataExercise:
    """Takes data from an excel spread sheet and converts that data into a .json file."""

    def __init__(self, startWorkHour, endWorkHour):
        """Default constructor that opens up the excel spreed
        sheet, which allows data to be accessed
        """
        # list of availability for each doctor
        self.list_of_availability = []
        # opens excel spreed sheet
        self.wb = xlrd.open_workbook(EXCEL_PATH)
        # grabs the first worksheet
        self.sh = self.wb.sheet_by_index(0)
        # list to hold the different dictionaries for each doctor
        self.list_of_doctors = []
        # allows use to convert postal addresses to latitude and longitude coordinate
        # keeps track of the address that geocode couldn't detect
        self.failedGeocodingCount = 0
        # sets the start hour of a typical work day
        self.sWorkHour = startWorkHour
        # sets the end hour of a typical work day
        self.eWorkHour = endWorkHour

    def create_dict_and_json(self):
        """Creates a dictionary of data and writes it to a .json file.
        """
        # iterates throw each row in worksheet
        for row in range(9, self.sh.nrows):
            self.list_of_availability = []
            # creates a dictionary for the doctors
            doctors = OrderedDict()
            # grabs the values for that row
            rowvalues = self.sh.row_values(row)

            # formats all names to look the same
            rowvalues[2] = rowvalues[2].strip()
            # rowValues[1] contains doctor's name
            doctors[KEY_VALUES[0]] = rowvalues[2]
            # rowValues[1] contains street address
            doctors[KEY_VALUES[1]] = rowvalues[3]
            # rowValues[3] contains city
            doctors[KEY_VALUES[2]] = rowvalues[4]
            doctors[KEY_VALUES[3]] = STATE

            if not (rowvalues[3] and rowvalues[4]):
                print('Skipping %s because missing address or city: %s, %s' % (rowvalues[2], rowvalues[3], rowvalues[4]))
                continue
            try:
                coord = lat_lon(', '.join((rowvalues[3], rowvalues[4], 'NY')))
            except AmbiguousAddressError as esp:
                print("Doctor Name: %s. %s" % (rowvalues[2], esp.args[0]))
            else:
                doctors[KEY_VALUES[4]] = coord.lat
                doctors[KEY_VALUES[5]] = coord.long

                # traverses the list of dates and column numbers
                for k in DATES:
                    self.one_day(rowvalues, k[0], k[1])

                doctors[KEY_VALUES[7]] = self.list_of_availability
                # adds each doctor's dictionary to a list
                self.list_of_doctors.append(doctors)
        # prints list of dictionaries to json file
        self.print_to_json(self.list_of_doctors)

    def one_day(self, rowvalues, date, colNumber):
        """Gathers the availability data for each doctor and each individual day
        and sets the times to their respective keys of either 'start' or 'end'
        """
        # dictionary to store availibility times for each each day
        availability = OrderedDict()
        # dictionary to store second set of availability times for each day when given two times
        availabilitytime2 = OrderedDict()

        # if times include 'QL', 'Q', 'EO', '1st, 3rd', '/', and '(', then remove those specific characters
        if ":" in rowvalues[colNumber]:
            rowvalues[colNumber] = rowvalues[colNumber].replace(':', '')
        if "1st, 3rd" in rowvalues[colNumber]:
            rowvalues[colNumber] = rowvalues[colNumber].replace('1st, 3rd ', '')
        elif "QL" in rowvalues[colNumber]:
            rowvalues[colNumber] = rowvalues[colNumber].replace('QL', '')
        elif "Q" in rowvalues[colNumber]:
            rowvalues[colNumber] = rowvalues[colNumber].replace('Q', '')
        elif "EO" in rowvalues[colNumber]:
            rowvalues[colNumber] = rowvalues[colNumber].replace('EO ', '')
        elif "(" in rowvalues[colNumber]:
            newstring = rowvalues[colNumber].replace('(', '')
            rowvalues[colNumber] = newstring.replace(')', '')
        elif "/" in rowvalues[colNumber]:
            time1 = rowvalues[colNumber].split('/')
            rowvalues[colNumber] = time1[0]

        # if the doctor prefers a specific time
        if '*' in rowvalues[colNumber]:
            # if that specific data is in two lines
            if "\n" in rowvalues[colNumber]:
                list_of_times = rowvalues[colNumber].split("\n")
                listtimes = list_of_times[0].split("-")
            # if that specific data is on one line and ends with '*'
            elif "\n" not in rowvalues[colNumber] and rowvalues[colNumber].endswith('*'):
                rowvalues[colNumber] = rowvalues[colNumber].replace('*', '')
                listtimes = rowvalues[colNumber].split('-')
            # if that specific data is on one line and doesn't end with '*'
            else:
                list_of_times = rowvalues[colNumber].split(' ')
                listtimes = list_of_times[0].split('-')

            self.helper_one_day(listtimes, availability, availabilitytime2, date)

        if ',' in rowvalues[colNumber]:
            availability[KEY_VALUES[8]] = date + "13:00:00.000Z"
            availability[KEY_VALUES[9]] = date + "15:00:00.000Z"
            self.list_of_availability.append(availability)

        # if the doctor's availability is in the PM
        elif "PM" == rowvalues[colNumber]:
            self.create_blackout_key(8, availability, date)
            availability[KEY_VALUES[9]] = date + "12:00:00.000Z"
            self.list_of_availability.append(availability)

        # if the doctor's availability time is in the AM
        elif "AM" == rowvalues[colNumber]:
            availability[KEY_VALUES[8]] = date + "12:00:00.000Z"
            self.create_blackout_key(9, availability, date)
            self.list_of_availability.append(availability)

        # if it is a "normal" time, ie. without any of these special cases
        elif rowvalues[colNumber] == "3rd" or rowvalues[colNumber] == "x" \
                or rowvalues[colNumber] == "X":
            self.create_blackout_key(8, availability, date)
            self.create_blackout_key(9, availability, date)
            self.list_of_availability.append(availability)

        elif "" is rowvalues[colNumber] or "ALL DAY" == rowvalues[colNumber]:
            return

        else:
            times = rowvalues[colNumber].split("-")
            self.helper_one_day(times, availability, availabilitytime2, date)

    def create_times(self, availability, key, str1, date):
        """Assigns the values that should correspond to the keys 'start' and 'end'.
        """
        if key is 8:
            # if str1 has no minutes and hour is length one
            if len(str1) is 1:
                if 12 >= int(str1) >= 6:
                    militaryhour = str1
                    availability[KEY_VALUES[key]] = date + "0" + militaryhour + ":00:00.000Z"
                else:
                    militaryhour = str(12 + int(str1))
                    availability[KEY_VALUES[key]] = date + militaryhour + ":00:00.000Z"

            # if str1 has no minutes and hour is length two
            elif len(str1) is 2:
                availability[KEY_VALUES[key]] = date + str1 + ":00:00.000Z"

            # if str1 has minutes and hour is length one
            elif len(str1) == 3:
                militarymin = str1[-2:]
                militaryhour = str1[:-2]
                # if the hour is below 6 add 12 to it
                if int(militaryhour) < 6:
                    militaryhour = str(int(militaryhour) + 12)
                    availability[KEY_VALUES[key]] = date + militaryhour + ":" + militarymin + ":00.000Z"
                else:
                    availability[KEY_VALUES[key]] = date + "0" + militaryhour + ":" + militarymin + ":00.000Z"

            # if str1 has minutes and hour is length two
            else:
                militarymin = str1[-2:]
                militaryhour = str1[:-2]
                availability[KEY_VALUES[key]] = date + militaryhour + ":" + militarymin + ":00.000Z"

        if key is 9:
            # if str1 has no minutes and hour is length one
            if len(str1) == 1:
                if 12 >= int(str1) >= 8:
                    militaryhour = str1
                    availability[KEY_VALUES[key]] = date + "0" + militaryhour + ":00:00.000Z"
                else:
                    militaryhour = str(12 + int(str1))
                    availability[KEY_VALUES[key]] = date + militaryhour + ":00:00.000Z"

            # if str1 has no minutes and hour is length two
            elif len(str1) == 2:
                availability[KEY_VALUES[key]] = date + str1 + ":00:00.000Z"

            # if str1 has minutes and hour is length one
            elif len(str1) == 3:
                militarymin = str1[-2:]
                militaryhour = str1[:-2]
                # if the hour is below 6 add 12 to it
                if int(militaryhour) < 8:
                    militaryhour = str(int(militaryhour) + 12)
                    availability[KEY_VALUES[key]] = date + militaryhour + ":" + militarymin + ":00.000Z"
                else:
                    availability[KEY_VALUES[key]] = date + "0" + militaryhour + ":" + militarymin + ":00.000Z"

            # if str1 has minutes and hour is length two
            else:
                militarymin = str1[-2:]
                militaryhour = str1[:-2]
                availability[KEY_VALUES[key]] = date + militaryhour + ":" + militarymin + ":00.000Z"

    def create_blackout_key(self, key, availability, date):
        """Will only create start and end keys with argument work hours"""
        if key is 8:
            if len(self.sWorkHour) is 1:
                availability[KEY_VALUES[key]] = date + "0" + self.sWorkHour + ":00:00.000Z"
            elif len(self.sWorkHour) is 2:
                availability[KEY_VALUES[key]] = date + self.eWorkHour + ":00:00.000Z"
            elif len(self.sWorkHour) is 3:
                stringMinutes = self.sWorkHour[-2:]
                stringHour = self.sWorkHour[:-2]
                availability[KEY_VALUES[key]] = date + "0" + stringHour + ":" + stringMinutes + ":00.000Z"
            else:
                stringMinutes = self.sWorkHour[-2:]
                stringHour = self.sWorkHour[:-2]
                availability[KEY_VALUES[key]] = date + stringHour + ":" + stringMinutes + ":00.000Z"
        else:
            if len(self.eWorkHour) is 1:
                intHour = int(self.eWorkHour) + 12
                availability[KEY_VALUES[key]] = date + str(intHour) + ":00:00.000Z"
            elif len(self.eWorkHour) is 2:
                availability[KEY_VALUES[key]] = date + self.eWorkHour + ":00:00.000Z"
            elif len(self.eWorkHour) is 3:
                stringMinutes = self.eWorkHour[-2:]
                stringHour = self.eWorkHour[:-2]
                intHour = int(stringHour) + 12
                availability[KEY_VALUES[key]] = date + str(intHour) + ":" + stringMinutes + ":00.000Z"
            elif len(self.eWorkHour) is 4:
                stringMinutes = self.eWorkHour[-2:]
                stringHour = self.eWorkHour[:-2]
                intHour = int(stringHour) + 12
                availability[KEY_VALUES[key]] = date + str(intHour) + ":" + stringMinutes + ":00.000Z"

    def helper_one_day(self, times, availability, availabilitytime2, date):

        """Decides how to create the start and end keys by calling create_times or create_blackout_key"""
        if self.hour(times[0]) > self.hour(self.sWorkHour) or 1 <= self.hour(times[0]) <= 5:
            self.create_blackout_key(8, availability, date)
            self.create_times(availability, 9, times[0], date)
            self.list_of_availability.append(availability)
        elif self.hour(times[0]) == self.hour(self.sWorkHour):
            if self.minutes(times[0]) > self.minutes(self.sWorkHour):
                self.create_blackout_key(8, availability, date)
                self.create_times(availability, 9, times[0], date)
                self.list_of_availability.append(availability)

        if self.hour(times[1]) < self.hour(self.eWorkHour) or 9 <= self.hour(times[1]) <= 12:
            self.create_times(availabilitytime2, 8, times[1], date)
            self.create_blackout_key(9, availabilitytime2, date)
            self.list_of_availability.append(availabilitytime2)
        elif self.hour(times[1]) == self.hour(self.eWorkHour):
            if self.minutes(times[1]) < self.minutes(self.eWorkHour):
                self.create_times(availabilitytime2, 8, times[1], date)
                self.create_blackout_key(9, availabilitytime2, date)
                self.list_of_availability.append(availabilitytime2)

    def hour(self, str1):
        """Returns the hour as an int of a time"""
        if len(str1) is 1 or len(str1) is 2:
            return int(str1)
        elif len(str1) is 3 or len(str1) is 4:
            return int(str1[:-2])

    def minutes(self, str1):
        """Returns the minutes as an int of a time"""
        if len(str1) is 1 or len(str1) is 2:
            return 0
        elif len(str1) is 3 or len(str1) is 4:
            return int(str1[-2:])

    def print_to_json(self, doctors):
        """Prints the dictionary to a .json file.
        """
        # transforms list to json text format
        j = json.dumps(doctors, sort_keys=False, indent=4)
        # opens a .json file and writes json text to it
        with open(OUTPUT_PATH, 'w') as file:
            file.write(j)


def main():
    # if two times are given
    if len(sys.argv) is 3:
        if ":" in sys.argv[1]:
            sys.argv[1] = sys.argv[1].replace(":", "")
        if ":" in sys.argv[2]:
            sys.argv[2] = sys.argv[2].replace(":", "")
        data = DataExercise(sys.argv[1], sys.argv[2])
    # if no arguments are given
    elif len(sys.argv) is 1:
        data = DataExercise("830", "6")
    else:
        raise RuntimeError("Invalid Number of Arguments!")
    data.create_dict_and_json()


if __name__ == "__main__":
    main()
