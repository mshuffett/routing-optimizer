# -*- coding: utf-8 -*-
import base64
import datetime
import io
import logging

import dash
import dash_auth
import dash_core_components as dcc
import dash_html_components as html
import dash_table_experiments as dt
import pandas as pd
from dash.dependencies import Output, Input, State

from phocus.model.solution import load_all_solutions
from phocus.utils import bootstrap_project
from phocus.viz.maps import plot_locations


USER_PASS = ('phocus', 'optimal-path')
PASSWORDS = [USER_PASS]

logger = logging.getLogger(__name__)


def generate_table(dataframe, max_rows=100000, style=None, numbered=False, id=None):
    header_cols = [html.Th(col) for col in dataframe.columns]
    if numbered:
        header_cols = [html.Th('#')] + header_cols

    table_rows = []
    for i in range(min(len(dataframe), max_rows)):
        row = [html.Th(str(i + 1), className='row-num')] if numbered else []
        for col in dataframe.columns:
            row.append(html.Td(str(dataframe.iloc[i][col])))
        table_rows.append(html.Tr(row))

    return html.Table(
        [
            html.Thead([html.Tr(header_cols)]),
            html.Tbody(table_rows)
        ],
        style=style,
        className='table data-table table-sm table-bordered',
        id=id
    )


def card(children, header=None, body_id=None, hidden=False, **kwargs):
    card_children = []

    if header:
        card_children.append(html.Div(header, className='card-header'))
    card_children.append(html.Div(id=body_id, className='card-body', children=children))

    className = 'card'
    if hidden:
        className += ' d-none'

    return html.Div(card_children, className=className, **kwargs)


class ResultRenderer:
    def __init__(self, title, id, solution, solution_name):
        self.title = title
        self.id = id
        self.solution = solution
        self.solution_name = solution_name
        self.hover_row_id = self.id + '-hover-row'
        self._locations = None

    @property
    def locations(self):
        return self.solution.route

    @property
    def container(self):
        locations_df = pd.DataFrame([vars(loc) for loc in self.solution.route])
        table_id = self.id + '-table'
        locations_table = generate_table(locations_df, numbered=True, id=table_id)
        table_div = html.Div([locations_table],
                             style={'overflowY': 'scroll', 'height': '400px'},
                             className='table-div')

        return html.Div(
            className='container-fluid',
            children=[
                html.Div(className='row', children=[
                    html.Div(className='col-auto', children=[
                        self._kpis_html()
                    ]),
                    html.Div(className='col', style={'margin-bottom': '10px'}, children=[
                        dcc.Graph(id=self.id, figure=plot_locations(self.locations, text_format='{doctor_name} | Node {i}'))
                    ]),
                    html.Div(className='col', children=[
                        table_div
                    ]),
                ]),
            ],
            **{'data-solutionName': self.solution_name})

    @property
    def html(self):
        return card(self.container, header=self.title)

    def _kpis_html(self):
        return card([
            html.H4("Metrics", className='card-title'),
            html.Table([
                html.Tbody([
                    html.Tr([
                        html.Th(title),
                        html.Td(str(body))
                    ])
                    for title, body in self.solution.metrics.items()
                ])
            ], className='table table-sm table-bordered',
            )])


app = dash.Dash()

auth = dash_auth.BasicAuth(
    app,
    PASSWORDS
)
app.css.append_css({"external_url": "https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0-beta.3/css/bootstrap.min.css"})
app.scripts.append_script({"external_url": "https://code.jquery.com/jquery-3.2.1.slim.min.js"})
app.scripts.append_script({"external_url": "https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.12.9/umd/popper.min.js"})
app.scripts.append_script(
    {"external_url": "https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0-beta.3/js/bootstrap.min.js"})


def solution_name(solution):
    return '%s %s' % (solution.model_name, solution.run_datetime)


def solution_from_name(name):
    for sol in load_all_solutions():
        if solution_name(sol) == name:
            return sol


solutions = load_all_solutions()
solution_names = [solution_name(solution) for solution in solutions]

header = html.Div(
            dcc.Dropdown(
                id='solution-dropdown',
                options=[{'label': name, 'value': name} for name in solution_names],
                value=solution_names[0],
            )
        ),

app.layout = html.Div(className='container-fluid', children=[
    html.H1(
        children='Phocus Dashboard',
        style={
            'textAlign': 'center',
        },
        className='mb-4'
    ),
    html.Div([
        dcc.Tabs(
            tabs=[
                {'label': 'New Run', 'value': 'new-run'},
                {'label': 'Past Runs', 'value': 'past-runs'},
            ],
            value='new-run',
            id='tabs'
        ),
        html.Div(id='tab-output')
    ], style={
        'fontFamily': 'Sans-Serif',
        'margin-left': 'auto',
        'margin-right': 'auto'
    }),
    card([
        html.Div([
            html.H4('Model Parameters'),
            html.Label(
                htmlFor='model-name',
                children='Model Run Name'
            ),
            dcc.Input(
                type='text',
                value='',
                id='model-name',
            ),
            html.Label(
                htmlFor='start-datetime',
                children='Start Datetime'
            ),
            dcc.Input(
                placeholder='2018-01-01T08:00:00+00:00',
                type='text',
                value='',
                id='start-datetime',
            ),
            html.Label(
                htmlFor='planning-days',
                children='Planning Days'
            ),
            dcc.Input(
                placeholder='5',
                type='text',
                value='',
                id='planning-days',
            ),
            html.Label(
                htmlFor='service-time',
                children='Service Time Minutes'
            ),
            dcc.Input(
                placeholder='20',
                type='text',
                value='',
                id='service-time',
            ),
            html.Label(
                htmlFor='time-limit',
                children='Time Limit Seconds'
            ),
            dcc.Input(
                placeholder='5',
                type='text',
                value='',
                id='time-limit',
            ),
        ],
            style={
                'width': '100%',
                'margin': '10px'
            }
        ),
        html.Div([
            dcc.Upload(
                id='upload-data',
                children=html.Div([
                    'Drag and Drop or ',
                    html.A('Select Files')
                ]),
                style={
                    'width': '100%',
                    'height': '60px',
                    'lineHeight': '60px',
                    'borderWidth': '1px',
                    'borderStyle': 'dashed',
                    'borderRadius': '5px',
                    'textAlign': 'center',
                    'margin': '10px'
                },
                # Allow multiple files to be uploaded
                multiple=True
            ),
            html.Div(id='output-data-upload'),
            html.Div(dt.DataTable(rows=[{}]), style={'display': 'none'})
        ]),
        html.Button('Submit', id='button', style={'margin': '0 auto', 'display': 'block'}),
    ],
        id='new-run-card',
        body_id='new-run-card-body',
    ),
    card(
        [],
        header=html.Div([
            dcc.Dropdown(
                id='solution-dropdown',
                options=[{'label': name, 'value': name} for name in solution_names],
                value=solution_names[0],
            )]
        ),
        id='solution-card',
        body_id='solution-card-body',
        hidden=True,
    ),
    dcc.Interval(
        id='interval-component',
        interval=1 * 1000,  # in milliseconds
        n_intervals=0
    ),
])


def toggle_hidden(classes):
    classes = classes[:]
    for i, c in enumerate(classes):
        if c == 'd-none':
            del classes[i]
            return classes

    classes.append('d-none')
    return classes


def show(classes: str):
    classes = set(classes.split(' '))
    classes.discard('d-none')
    return ' '.join(classes)


def hide(classes: str):
    classes = set(classes.split(' '))
    classes.add('d-none')
    return ' '.join(classes)


@app.callback(
    Output('solution-card', 'className'),
    [Input('tabs', 'value')],
    [State('solution-card', 'className')]
)
def display_solution_card(value, classes):
    if value == 'past-runs':
        return show(classes)
    else:
        return hide(classes)


@app.callback(
    Output('new-run-card', 'className'),
    [Input('tabs', 'value')],
    [State('new-run-card', 'className')]
)
def display_new_run_card(value, classes):
    if value == 'new-run':
        return show(classes)
    else:
        return hide(classes)


@app.callback(
    Output('solution-dropdown', 'options'),
    [Input('interval-component', 'n_intervals')],
    [State('solution-dropdown', 'options')]
)
def update_dropdown_live(n, options):
    current_solutions = load_all_solutions()
    current_solution_names = {solution_name(solution) for solution in current_solutions}
    return [{'label': name, 'value': name} for name in sorted(current_solution_names)]


@app.callback(
    Output('solution-card-body', 'children'),
    [Input('solution-dropdown', 'value')]
)
def update_output_live(value):
    solution = solution_from_name(value)
    result = ResultRenderer(value, 'cp-result', solution, value)
    return [result.container]


def parse_contents(contents, filename, date):
    content_type, content_string = contents.split(',')

    decoded = base64.b64decode(content_string)
    try:
        if 'csv' in filename:
            # Assume that the user uploaded a CSV file
            df = pd.read_csv(
                io.StringIO(decoded.decode('utf-8')))
        elif 'xls' in filename:
            # Assume that the user uploaded an excel file
            df = pd.read_excel(io.BytesIO(decoded))
    except Exception as e:
        print(e)
        return html.Div([
            'There was an error processing this file.'
        ])

    return html.Div([
        html.H5(filename),
        html.H6(datetime.datetime.fromtimestamp(date)),

        # Use the DataTable prototype component:
        # github.com/plotly/dash-table-experiments
        dt.DataTable(rows=df.to_dict('records')),

        html.Hr(),  # horizontal line

        # For debugging, display the raw contents provided by the web browser
        html.Div('Raw Content'),
        html.Pre(contents[0:200] + '...', style={
            'whiteSpace': 'pre-wrap',
            'wordBreak': 'break-all'
        })
    ])


@app.callback(Output('output-data-upload', 'children'),
              [Input('upload-data', 'contents'),
               Input('upload-data', 'filename'),
               Input('upload-data', 'last_modified')])
def update_output(list_of_contents, list_of_names, list_of_dates):
    if list_of_contents is not None:
        children = [
            parse_contents(c, n, d) for c, n, d in
            zip(list_of_contents, list_of_names, list_of_dates)]
        return children


app.css.append_css({
    'external_url': 'https://codepen.io/chriddyp/pen/bWLwgP.css'
})

if __name__ == '__main__':
    bootstrap_project()
    app.run_server(debug=True)
