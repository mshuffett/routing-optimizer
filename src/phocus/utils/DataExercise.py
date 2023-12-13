"""
File Name: DataExercise.py

Author: Nick Klabjan

Description: Takes in data from an excel sheet and writes it to a .json file.

__________________________________ASSUMPTIONS_____________________________________
1. I included the latitudes and longitudes, but in some cases geocode does not recognize the address, and therefore,
   I did not include that specific information for those doctors' longitudes and latitudes
2. Since times are not labeled with AM and PM...
    - I assumed for start times between 6 and 12 inclusive to be AM and times less than 6 to be PM
    - I assumed for end times between 8 and 12 inclusive to be AM and times less than 8 to be PM
3. If time availability consists of 'EO' (every other week), I assumed they were available for this week (Jan 1 - Jan 5)
4. If times are surrounded by parenthesis, or include either 'QL', 'Q', '1st, 3rd', '3rd' and since the key in
   excel doesn't have
   these, I just delete these characters from the times and proceed as a normal availability time
5. If the doctor has a prime time to visit them, I did not include the prime time anywhere in the .json file, but
   just kept track of their availability like normal
6. If an availability is "PM", the assumed time is 12-6 and if "AM", assumed time is 7-12
7. One end time is '6/6:30' and I used 6 as the end time
"""

import xlrd
import json
from uszipcode import ZipcodeSearchEngine
from geopy.geocoders import Nominatim
from collections import OrderedDict

# constant Excel Spread Sheet name
from phocus.utils.constants import DATA_PATH, ELENA_RAW_DATA_PATH

firstSheet = 0
# list of key values for dictionary
keyValues = ['doctor_name', 'address', 'city', 'state', 'lat',
             'lon', 'is_repeat', 'blackout_windows', 'start', 'end']
# list of tuples with corresponding dates relative to their column number
dates = [("2018-01-01T", 5), ("2018-01-02T", 6), ("2018-01-03T", 7), ("2018-01-04T", 8), ("2018-01-05T", 9)]
# whether or not you want to turn on geocoding or not
geocoding = True


class DataExercise:
    """Takes data from an excel spread sheet and converts that data into a .json file."""

    def __init__(
            self,
            excel_path=ELENA_RAW_DATA_PATH,
            output_path=DATA_PATH / 'time_window_locations.json',
    ):
        """Default constructor that opens up the excel spreed
        sheet, which allows data to be accessed
        """
        # list of availability for each doctor
        self.list_of_availability = []
        # opens excel spreed sheet
        self.wb = xlrd.open_workbook(excel_path)
        # grabs the first worksheet
        self.sh = self.wb.sheet_by_index(firstSheet)
        # list to hold the different dictionaries for each doctor
        self.list_of_doctors = []
        # allows use to convert postal addresses to latitude and longitude coordinates
        self.geolocator = Nominatim()
        # allows us to find the state the zip code belongs to
        self.search = ZipcodeSearchEngine()
        self.failedGeocodingCount = 0

        self.output_path = output_path

    def create_dict_and_json(self):
        """Creates a dictionary of data and writes it to a .json file.
        """
        # iterates throw each row in worksheet
        for row in range(1, self.sh.nrows):
            self.list_of_availability = []
            # creates a dictionary for the doctors
            doctors = OrderedDict()
            # grabs the values for that row
            rowvalues = self.sh.row_values(row)
            # rowValues[0] contains doctor's name
            try:
                doctors[keyValues[0]] = str(int(rowvalues[0]))
            except Exception:
                print(rowvalues)
            # rowValues[1] contains street address
            doctors[keyValues[1]] = rowvalues[1]
            # rowValues[3] contains city
            doctors[keyValues[2]] = rowvalues[3]

            # converts zip code to a string
            zipString = str(int(rowvalues[4]))
            # creates a dictionary of information regarding that zip code
            zipcode = self.search.by_zipcode(zipString)
            # adds the zipcode's matching state to dictionary
            doctors[keyValues[3]] = zipcode["State"]

            # grabs the entire address
            address = rowvalues[1] + " " + rowvalues[3] + "," + zipcode["State"] + " " + zipString
            # calls geocoding method that transforms address to latitude and longitude
            if geocoding:
                self.geocoding(address, doctors)

            # traverses the list of dates and column numbers
            for k in dates:
                self.one_day(rowvalues, k[0], k[1])

            doctors[keyValues[7]] = self.list_of_availability
            # adds each doctor's dictionary to a list
            self.list_of_doctors.append(doctors)
        # prints list of dictionaries to json file
        self.print_to_json(self.list_of_doctors)

        if geocoding:
            print("Number of failed geocoding calls: " + str(self.failedGeocodingCount))

    def one_day(self, rowvalues, date, colNumber):
        """Gathers the availability data for each doctor and each individual day
        and sets the times to their respective keys of either 'start' or 'end'
        """
        # dictionary to store availibility times for each each day
        availability = OrderedDict()

        # dictionary to store second set of availability times for each day when given two times
        availabilitytime2 = OrderedDict()

        # if times include 'QL', 'Q', 'EO', '1st, 3rd', '/', and '(', then remove those specific characters
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
        elif rowvalues[colNumber] == "3rd":
            return

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

            # calls method to create the values that correspond to the keys "start" and "end"
            self.create_start_end_times(availability, listtimes[0], listtimes[1], date)

        # if the doctor's availability time has to be split up
        elif 'X' in rowvalues[colNumber]:
            twotimes = rowvalues[colNumber].split(' X')
            firsttime = twotimes[0].split('-')
            secondtime = twotimes[1].split('-')

            # calls method to create the values that correspond to the keys "start" and "end"
            self.create_start_end_times(availability, firsttime[0], secondtime[0], date)
            self.create_start_end_times(availabilitytime2, secondtime[1], firsttime[1], date)
        # if the doctor's availability time is in the PM

        elif "PM" == rowvalues[colNumber]:
            availability[keyValues[8]] = date + "12Z"
            availability[keyValues[9]] = date + "18Z"
            self.list_of_availability.append(availability)

        # if the doctor's availability time is in the PM
        elif "AM" == rowvalues[colNumber]:
            availability[keyValues[8]] = date + "7Z"
            availability[keyValues[9]] = date + "12Z"
            self.list_of_availability.append(availability)

        # if the the time availibility is all day
        elif "ALL DAY" == rowvalues[colNumber]:
            availability[keyValues[8]] = date + "9Z"
            availability[keyValues[9]] = date + "17Z"
            self.list_of_availability.append(availability)

        # if it is a "normal" time, ie. without any of these special cases
        elif rowvalues[colNumber] is not "":
            # split time using '-' as deliminator
            timelist = rowvalues[colNumber].split('-')
            # calls method to create the values that correspond to the keys "start" and "end"
            self.create_start_end_times(availability, timelist[0], timelist[1], date)

    def create_start_end_times(self, availability, str1, str2, date):
        """Assigns the values that should correspond to the keys 'start' and 'end'.
        """
        # if str1 has no minutes
        if len(str1) == 1 or len(str1) == 2:
            if 12 >= int(str1) >= 6:
                militaryhour = str1
            else:
                militaryhour = str(12 + int(str1))
            availability[keyValues[8]] = date + militaryhour + "Z"

        # if len of str1 is 3 or 4
        elif len(str1) == 3 or len(str1) == 4:
            militarymin = str1[-2:]
            militaryhour = str1[:-2]
            # if the hour is below 6 add 12 to it
            if int(militaryhour) < 6:
                militaryhour = str(int(militaryhour) + 12)
            availability[keyValues[8]] = date + militaryhour + ":" + militarymin + "Z"

        # if str2 has no minutes
        if len(str2) == 1 or len(str2) == 2:
            if 12 >= int(str2) >= 8:
                militaryhour = str2
            else:
                militaryhour = str(12 + int(str2))
            availability[keyValues[9]] = date + militaryhour + "Z"

        # if len of str2 is 3 or 4
        elif len(str2) == 3 or len(str2) == 4:
            militarymin = str2[-2:]
            militaryhour = str2[:-2]
            # if the hour is below 8 add 12 to it
            if int(militaryhour) < 8:
                militaryhour = str(int(militaryhour) + 12)
            availability[keyValues[9]] = date + militaryhour + ":" + militarymin + "Z"

        self.list_of_availability.append(availability)

    def geocoding(self, address, doctors):
        """Calculates the latitude and longitude for the corresponding address.
        """
        try:
            # changes address to latitude and longitude coordinates
            location = self.geolocator.geocode(address)
        except:
            self.failedGeocodingCount += 1
            return
        # if the location "exists" according to geocode
        if location is not None:
            # adds latitude of the address to dictionary
            doctors[keyValues[4]] = location.latitude
            # adds longitude of the address to dictionary
            doctors[keyValues[5]] = location.longitude
        else:
            self.failedGeocodingCount += 1

    def print_to_json(self, doctors):
        """Prints the dictionary to a .json file.
        """
        # transforms list to json text format
        j = json.dumps(doctors, sort_keys=False, indent=4)
        # opens a .json file and writes json text to it
        with open(self.output_path, 'w') as file:
            file.write(j)


def main():
    data = DataExercise()
    data.create_dict_and_json()


if __name__ == "__main__":
    main()
