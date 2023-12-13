import json
from datetime import date, timedelta
from pathlib import Path
from typing import Sequence

import colorlover as cl
import numpy as np
from plotly.graph_objs import *

from phocus.model.location import Location


def save_fig(fig):
    output_dir: Path = Path(__file__).resolve().parents[1] / 'output'
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / 'figure.json').open(mode='w') as f:
        json.dump(fig, f)


def scattermapbox_for_locations(locations, name, text):
    return Scattermapbox(
        lat=[loc.lat for loc in locations],
        lon=[loc.lon for loc in locations],
        mode='markers+lines',
        marker=Marker(
            color=cl.scales['11']['qual']['Paired']
        ),
        text=text,
        name=name,
    )


def plot_locations(locations: Sequence[Location], zoom=8.5, endpt_size=20, title='', text_format: str = None,
                   start_date=date(2018, 1, 1)):
    all_text = [text_format.format(doctor_name=loc.doctor_name, i=i) for i, loc in enumerate(locations, 1)]
    mapbox_access_token = "pk.eyJ1IjoibXNodWZmZXR0IiwiYSI6ImNqY2gwdHBpZzJjYzIyeW1taXQ5ZDNwcTUifQ.Dm3DRhiJvlj36urSvZel5Q"
    origin = locations[0]
    current_day = [origin]
    locations_by_day = [current_day]
    current_day_text = [all_text[0]]
    text_by_day = [current_day_text]
    days = []

    for loc, text in zip(locations[1:], all_text[1:]):
        current_day.append(loc)
        current_day_text.append(text)
        if (loc.doctor_name, loc.address, loc.lat, loc.lon) == (origin.doctor_name, origin.address, origin.lat, origin.lon):
            current_day = [loc]
            locations_by_day.append(current_day)
            current_day_text = [text]
            text_by_day.append(current_day_text)

    text_by_day.pop()
    locations_by_day.pop()  # Remove extra day at the end

    current_date = start_date
    for _ in locations_by_day:
        days.append(current_date)
        current_date += timedelta(days=1)

    map_boxes = [scattermapbox_for_locations(day_locations, location_date, text)
                 for day_locations, location_date, text in zip(locations_by_day, days, text_by_day)]
    data = Data(map_boxes)
    layout = Layout(
        title=title,
        # autosize=True,
        autosize=False,
        width=950,
        height=500,
        hovermode='closest',
        margin=Margin(t=0, b=0, l=0, r=0),
        mapbox=dict(
            accesstoken=mapbox_access_token,
            bearing=0,
            style='streets',
            center=dict(
                lat=np.mean([loc.lat for loc in locations]),
                lon=np.mean([loc.lon for loc in locations]),
            ),
            pitch=0,
            zoom=zoom
        ),
    )

    fig = dict(data=data, layout=layout)
    return fig
