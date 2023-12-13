import csv
from pathlib import Path
from typing import Optional, Sequence, Iterator, Counter

from phocus.utils.decorators import auto_assign_arguments
from phocus.utils.constants import HCP_DATA_PATH
from phocus.utils.maps import MapsUtils
from phocus.utils.mixins import Base


class HCP(Base):
    """Healthcare provider"""
    @auto_assign_arguments
    def __init__(self, **kwargs):
        pass

    @property
    def lat(self):
        try:
            return self._lat
        except AttributeError:
            self._lat, self._lon = MapsUtils().get_lat_long(', '.join((self.street_address, self.city, self.state, self.zip)))
            return self._lat

    @property
    def lon(self):
        try:
            return self._lon
        except AttributeError:
            self._lat, self._lon = MapsUtils().get_lat_long(', '.join((self.street_address, self.city, self.state, self.zip)))
            return self._lon


class HCPFileReader:
    """Reads file with HCP data in it"""
    def __init__(self, path: Path):
        self.path = path

    def read_iter(self) -> Iterator[HCP]:
        """An iterator of reading one HCP at at time"""
        with open(self.path) as f:
            reader = csv.DictReader(f)
            for hcp in reader:
                yield HCP(**hcp)

    def validate(self, hcps: Sequence[HCP]):
        """Validate the hcps"""
        counter = Counter(hcp.imsid for hcp in hcps)
        if counter.most_common(1)[0][1] > 1:
            raise RuntimeError('Expected IMSIDs to be unique but %s had %d entries', *counter.most_common(1))

    def read(self) -> Sequence[HCP]:
        hcps = list(self.read_iter())
        self.validate(hcps)
        return hcps


class ActualRoute:
    """An actual route that was taken"""
    def __init__(
        self,
        rep_id: str,
        rep_name: str,
        route: Optional[Sequence[HCP]] = None
    ):
        self.rep_id = rep_id
        self.rep_name = rep_name
        self.route = route if route else []


if __name__ == '__main__':
    reader = HCPFileReader(HCP_DATA_PATH)
    hcps = reader.read()
    print(list(hcp for hcp in hcps if hcp.imsid == '1619234'))
