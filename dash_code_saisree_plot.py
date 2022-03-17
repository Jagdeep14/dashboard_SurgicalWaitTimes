from io import BytesIO
from turtle import down

import pandas as pd
import numpy as np

import altair as alt

import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc

import base64
from PIL import Image


class SurgicalPlots:
    def __init__(self):
        
        # read in data        
        path = 'data/final_filtered.xlsx'
        qdata = pd.read_excel(path)
        #print(qdata.columns)
        qdata=qdata.drop(['Unnamed: 0'],axis=1)

        # convert <5 string to median value of 3
        qdata = qdata.replace('<5', 3)
        self.qdata = qdata

        # drop rows with NAs and defining portions
        clean = qdata.dropna()
        count = qdata.iloc[:,0:7]
        main = qdata

        # drop "All" data
        
        self.count = count
        all = clean.query('procedure == "All Procedures" & hospital == "All Facilities" & health_authority == "All Health Authorities"')

        qdata['wating'] = pd.to_numeric(qdata['waiting'])
        qdata['completed'] = pd.to_numeric(qdata['waiting'])
        authority = count.groupby(['health_authority', 'year', 'quarter']).sum().reset_index()
        # authority data with calculated complete case ratio
        authority_comp_prop = authority.copy()
        authority_comp_prop['ratio'] = authority_comp_prop['completed']/(authority_comp_prop['completed']+authority_comp_prop['waiting'])
        self.authority_comp_prop = authority_comp_prop

       
        # Cataract Surgery is a unique high volume procedure often performed in seperate OR facilities and will be excluded from a part of the analysis.
        self.no_cataract = main.query('procedure != "Cataract Surgery"')

    
    def filtering(self,health_authority,year):
        # rename health authority
        if(health_authority=="Provincial"):
            health_authority="Provincial Health Services Authority"

        # filter health authority        
        no_cataract_authority=  self.no_cataract[self.no_cataract['health_authority']==health_authority]
        
        # grouping by procedure 
        procedure = no_cataract_authority.groupby(['procedure', 'year', 'quarter']).mean().reset_index()
        
        # subsett from 2017 to current year
        procedure = procedure[(procedure['year']>=year[0])&(procedure['year']<=year[1])]
        procedure['time'] = procedure['year'].map(str)+procedure['quarter']
        procedure_unite = procedure.drop(columns = ['year','quarter'])

        # most treated and less treated surgeries
        procedure_order = procedure_unite.groupby('procedure').mean().reset_index()
        procedure_order = procedure_order.sort_values('wait_time_90')

        # fastest and slowest procedures
        self.fastest = procedure_order.head(5)
        self.slowest = procedure_order.tail(5)

        # round off numbers to 2 decimal places
        self.fastest=self.fastest.round(2)
        self.slowest=self.slowest.round(2)

    def pace_procedures(self,health_authority,year,pace):              
        self.filtering(health_authority,year)  
          
        colors=['lightsteelblue','paleturquoise','red','red','red']    
        if(pace=="Fastest"):
            result=self.fastest
            axis_range=np.arange(0,14,2)
            sort_order=self.fastest['wait_time_90'].to_list()
        else:
            result=self.slowest
            axis_range=np.arange(0,150,10)
            sort_order=self.slowest['wait_time_90'].to_list()
        print(pace,result.head())
        procedure_time_chart = alt.Chart(result,width=500,height=200).mark_bar(size=20,
                                                        point={"filled": False, "fill": "white"}, opacity=0.7).encode(
                                                        x=alt.X('wait_time_90',title="Wait time(in weeks)",axis=alt.Axis(values=axis_range,grid=False)),
                                                        y=alt.Y('procedure', scale=alt.Scale(zero=False),sort=sort_order,axis=alt.Axis(labels=False,grid=False)),
                                                        color=alt.Color('procedure',legend=None,scale=alt.Scale(range=colors)),
                                                        tooltip=['procedure','wait_time_90'])
        procedure_time_text_time_chart = alt.Chart(result,width=500,height=200).mark_bar(size=20,
                                                        point={"filled": False, "fill": "white"}, opacity=0.7).encode(
                                                        x=alt.X('wait_time_90',axis=alt.Axis(values=axis_range)),
                                                        y=alt.Y('procedure', scale=alt.Scale(zero=False),sort=sort_order,axis=alt.Axis(labels=False)),                                                        
                                                        )
        procedure_time_text_procedure_chart = alt.Chart(result,width=500,height=200).mark_bar(size=20,
                                                        point={"filled": False, "fill": "white"}, opacity=0.7).encode(
                                                        x=alt.X('wait_time_90',axis=alt.Axis(values=axis_range)),
                                                        y=alt.Y('procedure', scale=alt.Scale(zero=False),sort=sort_order,axis=alt.Axis(labels=False)),                                                        
                                                        )
        text_time=procedure_time_text_time_chart+procedure_time_text_time_chart.mark_text(dx=15,color='black',size=10).encode(text="wait_time_90")
        text_procedure=procedure_time_text_procedure_chart+procedure_time_text_procedure_chart.mark_text(align='left',dx=-165,color='black',size=10).encode(text="procedure")
        procedure_time_chart=procedure_time_chart+text_time+text_procedure 
        procedure_time_chart=procedure_time_chart.configure_view(strokeWidth=0)
        return procedure_time_chart.interactive().to_html()

    # data grouped by hospital for selected health authority and date range
    def data_by_hosp(self, health_authority,year, hospname):       

        hosp_data = self.count[self.count['health_authority']==health_authority]
        hosp_data = hosp_data.groupby(['hospital', 'year', 'quarter'])['waiting','completed'].sum().reset_index()
        
        hosp_data = hosp_data[(hosp_data['year']>=year[0]) & (hosp_data['year']<=year[1])]
        
        hosp_data_melted = hosp_data.melt(id_vars=['hospital','year','quarter'])
       
      
        hosp_data_melted['time'] = hosp_data_melted['year'].map(str)+hosp_data_melted['quarter']
        
        hosp_data_melted = hosp_data_melted.drop(columns = ['year','quarter'])

        #create hospital dropdown list
        self.hosp_list = hosp_data_melted.hospital.unique()

        #waiting and completed cases for chosen hospital
        self.one_hospital = hosp_data_melted[hosp_data_melted['hospital'] == hospname]
       

    def wait_complete_plot(self,health_authority, year, hospname):  
         
        
        self.data_by_hosp(health_authority,year, hospname) 
        wc_plot = alt.Chart(self.one_hospital).mark_bar(size=10).encode(
                            x=alt.X('variable', axis=alt.Axis(title=None, labels=False, ticks=False)),
                            y=alt.Y('value', scale=alt.Scale(zero=False), axis=alt.Axis(grid=False)),
                            color=alt.Color('variable'),
                            column = alt.Column('time', header=alt.Header(title=None, labelOrient='bottom', labelAngle=90))
        ).configure_view(stroke='transparent'
        ).properties(height=350
        ).configure_facet(spacing=7
        )       
        return wc_plot.to_html()

    # data grouped by health authority for a date range
    def data_compprop(self, year, health_authority):
        #data subseted by health authority
        compprop_authority = self.authority_comp_prop[self.authority_comp_prop['health_authority']==health_authority]   

        #data selected for a date range
        compprop_authority_year = compprop_authority[(compprop_authority['year']>=year[0])&(compprop_authority['year']<=year[1])]    
        self.compprop = compprop_authority_year
        
    #complete proportion plot
    def comp_prop_plot(self, year, health_authority):   
        self.data_compprop(year, health_authority) 
#        print(self.compprop)
        compprop_plot = alt.Chart(self.compprop,width=500,height=400).mark_line().encode(
                            x=alt.X('year:N'),
                            y=alt.Y('ratio:Q', scale=alt.Scale(zero=False)),
                            color=alt.Color('quarter'))
        compprop_plot = compprop_plot+compprop_plot.mark_circle()
        compprop_plot=compprop_plot.configure_view(stroke='transparent'
        )
        return compprop_plot.to_html()

surgical_plots = SurgicalPlots()


map_data = alt.Data(url='https://raw.githubusercontent.com/Jagdeep14/shapefile_data/main/HA_2018.geojson', format=alt.DataFormat(property='features',type='json'))

def map_plot(authority = 'Interior'):
    # plot1 is only for provincial authority
    if authority == "Provincial":
        plot1 = alt.Chart(map_data, width = 370, height = 350).mark_geoshape(stroke = "black", opacity = 0.5, fill = "blue"
        ).encode(
            tooltip = "properties.HA_Name:N"
        ).project(
            type='identity', reflectY=True
        ).configure_view(
        strokeWidth=0
    )
        return plot1.to_html()
    # Plot2 is for all other authorities other than provincial
    else:
        plot2 = alt.Chart(map_data, width = 370, height = 350).mark_geoshape(stroke = "black"
        ).encode(
            color= alt.Color("properties.HA_Name:N", legend = None),
            opacity=alt.condition(alt.datum['properties']['HA_Name'] == authority, alt.value(1), alt.value(0.3)),
            tooltip = "properties.HA_Name:N"
        ).project(
            type='identity', reflectY=True
        ).configure_view(
        strokeWidth=0
    )
        return plot2.to_html()
    

# All the score cards
wait_cases_card = dbc.Card(
    [
        dbc.CardHeader("Total waiting cases"),
        dbc.CardBody(
            [
                html.P("This is some card text",
                       className="text-center", id="wait_cases_text")
            ]
        ),
    ],
    style={"width": "10rem", 'display': 'inline-block',
           "justify-content": "center", "border": "10px lightgray solid"}
)
completed_cases_card = dbc.Card(
    [
        dbc.CardHeader("Total completed cases"),
        dbc.CardBody(
            [
                html.P("This is some card text",
                       className="text-center", id="completed_cases_text")
            ]
        ),
    ],
    style={"width": "10rem", 'display': 'inline-block', "border": "10px lightgray solid"}
)
wait_50_card = dbc.Card(
    [
        dbc.CardHeader("Mean waiting time (weeks) - 50 %le"),
        dbc.CardBody(
            [
                html.P("This is some card text", className="text-center",
                       id="mean_waiting_time_50%_text")
            ]
        ),
    ],
    style={"width": "10rem", 'display': 'inline-block',
           'align-items': 'center', 'justify-content': 'center', "border": "10px lightgray solid"}
)
wait_90_card = dbc.Card(
    [
        dbc.CardHeader("Mean waiting time (weeks) - 90 %le"),
        dbc.CardBody(
            [
                html.P("This is some card text", className="text-center",
                       id="mean_waiting_time_90%_text")
            ]
        ),
    ],
    style={"width": "10rem", 'display': 'inline-block',
           'align-items': 'center', 'justify-content': 'center', "border": "10px lightgray solid"}
)

# year slider
yr_slider=html.Div([
        dcc.RangeSlider(
            id="year_slider",min=2015, max=2021,
            step=1, marks={i: f'{i}' for i in range(2009, 2022)},
            value=[2017, 2021]
            )        
        ])

# health authority radio buttons
ha_buttons = html.Div([
    dcc.Dropdown(
        id="health_authority_buttons",
        options=[
            {"label": "Interior", "value": "Interior"},
            {"label": "Fraser", "value": "Fraser"},
            {"label": "Vancouver Coastal", "value": "Vancouver Coastal"},
            {"label": "Vancouver Island", "value": "Vancouver Island"},
            {"label": "Northern", "value": "Northern"},
            {"label": "Provincial", "value": "Provincial"},
        ],
        value='Interior')],
        style = {'stroke-width': '20px'})

# hospital dropdown
hosp_dropdown=html.Div([
            dcc.Dropdown(
                id='hospital_dropdown',
                options=[],
                value=[],
                clearable=False
            )
        ],style={"width":"100%"})

# pace button
fast_slow_button = html.Div([
    dcc.RadioItems(
        id="fastest_slowest_treatments_buttons",
        options=[
            {"label": "Fastest", "value": "Fastest"},
            {"label": "Slowest", "value": "Slowest"},
        ],
        value="Fastest",
        labelStyle = {"cursor": "pointer", "margin-left":"20px"})
])

# Download button
download_button = html.Div([
    html.Button("Download-csv", id="btn-download"),
    dcc.Download(id="download-df-csv")
])

# 1st plot - proportion of completed cases
proportion_cases = html.Div([
    html.Iframe(
        id="comp_prop_plot_id",
        srcDoc=surgical_plots.comp_prop_plot(
            health_authority="Interior", year=[2017, 2022]),
        style={'border-width': '0', 'width': '100%', 'height': '400px'}
    )
])

# 2nd plot - BC map
plot_map_object = html.Div([html.Iframe(
    id='map',
    srcDoc=map_plot(authority='Interior'),
    style={'border-width': '0', 'width': '100%', 'height': '500px'})
])

# 3rd plot - procedure plot
procedure_plot = html.Div([
    html.Iframe(
        id="procedure_plot_id",
        srcDoc=surgical_plots.pace_procedures(
            health_authority="Interior", year=[2017, 2022],pace="Fastest"),
        style={'border-width': '0', 'width': '100%', 'height': '400px'}
    )
])

# 4th plot - hospital wait and completed cases
hosp_wait_comp_cases = html.Div([
    html.Iframe(
        id="hosp_wait_comp_plot",
        srcDoc=surgical_plots.wait_complete_plot(
            health_authority="Interior", hospname="100 Mile District General Hospital", year=[2017, 2022]),
        style={'border-width': '0', 'width': '500px',
               'height': '350px', 'display': 'inline-block'}
    )
])



app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

#### Title row ################################
title_row = dbc.Row([
        html.H1('SURGICAL WAIT TIMES - BC', 
        style={'background-color': '#1f77b4', # navy blue -> #000080
                'color': 'white', 
                #'font-weight': 'bolder', 
                #'font-family': 'times new roman',
                'padding-top': '15px',
                'padding-bottom': '15px',
                'bottom-margin': '0'})
    ])


#### health authority buttons and slider ##############
authority_buttons_row = dbc.Row([
        dbc.Col(html.Div(), width = 1),
        dbc.Col(yr_slider, width = 6), 
        dbc.Col(html.Div(), width = 1),
        dbc.Col(ha_buttons, width = 3),
        dbc.Col(html.Div(), width = 1)
        ],
        style={'color':'#1f77b4',  # navy blue
         'background-color': '#D3D3D3',  # light grey -> #D3D3D3
        'font-weight': 'bolder',
        'font-size': '16px',
        'padding-top': '20px',
        'padding-bottom': '20px',
        'top-margin': '0',
        'text-align': "center"}
        )
     
    

##### Cards column ###################
col1 = html.Div(
    [dbc.Col([
        dbc.Row(completed_cases_card),
        html.Br(),
        dbc.Row(wait_cases_card),
        html.Br(),
        dbc.Row(wait_50_card),
        html.Br(),
        dbc.Row(wait_90_card)
    ])],
    style={
        'font-family': 'times new roman',
        'padding-left': 0, 
        "padding-right": 0,
        'text-align': "center"}
    )

############ col2 #######################
###### column 2 needs five rows ########
# row1 elements (titles of top two plots)
row1_col1 = dbc.Row(html.Div("Proportion of completed cases", style = {"font-weight": "bolder", 'text-align': "center"}))
row1_col2 = dbc.Row(html.Div("Health authority", style = {"font-weight": "bolder", 'text-align': "center"}))

row1 = html.Div([dbc.Row(
    [
        dbc.Col(row1_col1, md = 6),
        dbc.Col(html.Div(), md=1),
        dbc.Col(row1_col2, md = 6)
    ]
    )]
)

# row 2 elements (top two plots)
row2_col1 = dbc.Row(proportion_cases)
row2_col2 = dbc.Row(plot_map_object)

row2 = html.Div([dbc.Row(
    [
        dbc.Col(row2_col1, md = 6),
        dbc.Col(row2_col2, md = 6)
    ]
    )], 
    style={"padding-bottom": 0}
)

# row 3 elements (titles of bottom two plots)
row3_col1 = dbc.Row(html.Div("Fastest/Slowest treated procedures", style = {"font-weight": "bolder", 'text-align': "center"}))
row3_col2 = dbc.Row(html.Div("Total completed and waiting cases in Hospital", style = {"font-weight": "bolder", 'text-align': "center"}))

row3 = html.Div([dbc.Row(
    [
        dbc.Col(row3_col1, md = 6),
        dbc.Col(row3_col2, md = 6)
    ]
    )]
)

# row 4 elements (buttons and dropdown of bottom two plots)
row4_col1 = dbc.Row(fast_slow_button)
row4_col2 = dbc.Row([
    dbc.Col(html.Div(), width = 2),
    dbc.Col(hosp_dropdown, width = 8),
    dbc.Col(html.Div(), width=2)])

row4 = html.Div([dbc.Row(
    [
        dbc.Col(row4_col1, md = 6),
        dbc.Col(row4_col2, md = 6)
    ]
    )],
    #style={"padding-bottom": 0, "padding-top": 0}
)

# row 5 elements (bottom two plots)
row5_col1 = dbc.Row(procedure_plot)
row5_col2 = dbc.Row(hosp_wait_comp_cases)

row5 = html.Div([dbc.Row(
    [
        dbc.Col(row5_col1, md = 6),
        dbc.Col(row5_col2, md = 6)
    ]
    )], 
    style={"padding-bottom": 0}
)


col2 = html.Div(
    [
        row1,       # has titles of plots of first row
        row2,      # has top two plots
        row3,
        row4,
        row5
    ],
    style={'padding-left': 0, "padding-right": 0}
    )


########### columns for slider, cards and plots############
main_row = html.Div([
    dbc.Row([
        dbc.Col(col1, md=2),    # Cards column
        dbc.Col(col2, width=9)  # plots column
    ])
],
style={'padding-top': "30px"})


########## layout ################################
app.layout = dbc.Container([
    title_row,
    authority_buttons_row,
    main_row,
    download_button
],
 style={"background-color": "aliceblue"})


############## call backs ######################################################
# 1st plot - callback
@app.callback(
    Output("comp_prop_plot_id", 'srcDoc'),
    [
        Input("year_slider", "value"),
        Input("health_authority_buttons", "value")]
)
def update_comp_prop_plot(year, health_authority):
    if health_authority == "Provincial":
        health_authority = "Provincial Health Services Authority"
    return surgical_plots.comp_prop_plot(year, health_authority)

# 2nd plot - map


@app.callback(
    Output('map', 'srcDoc'),
    Input('health_authority_buttons', 'value'))
def update_map_plot(authority):
    return map_plot(authority)

# chainback dropdown - callback


@app.callback(
    [Output('hospital_dropdown', 'options'),
     Output('hospital_dropdown', 'value')],
    Input('health_authority_buttons', 'value'),
)
def set_hosp_dropdown(health_athority):

    if(health_athority == "Provincial"):
        health_athority = "Provincial Health Services Authority"
    filtered_data = surgical_plots.count[surgical_plots.count.health_authority == health_athority]

    dropdown_options = [{'label': c, 'value': c}
                        for c in sorted(filtered_data.hospital.unique())]
    #values_selected = [dropdown_options[0]]

    return dropdown_options, dropdown_options[0]['label']

# 4th plot - callback


@app.callback(
    Output("hosp_wait_comp_plot", 'srcDoc'),
    [
        Input("health_authority_buttons", "value"),
        Input("year_slider", "value"),
        Input("hospital_dropdown", "value")]
)
def update_wait_complete_plot(health_authority, year, hospname):
    if(health_authority == "Provincial"):
        health_authority = "Provincial Health Services Authority"

    return surgical_plots.wait_complete_plot(health_authority, year, hospname)

# 3rd plot - callback


@app.callback(
    Output("procedure_plot_id", 'srcDoc'),
    [Input("health_authority_buttons", "value"),
     Input("year_slider", "value"),
     Input("fastest_slowest_treatments_buttons", "value")]
)
def update_procedure_plot(health_authority, year, pace):
    return surgical_plots.pace_procedures(health_authority, year,pace)
    

# score cards - callback
@app.callback(
    [
        Output('wait_cases_text', 'children'),
        Output('completed_cases_text', 'children'),
        Output('mean_waiting_time_50%_text', 'children'),
        Output('mean_waiting_time_90%_text', 'children')
    ],
    [
        Input("health_authority_buttons", "value"),
        Input("year_slider", "value")
    ]
)
def update_score_cards(health_authority, year):
    if(health_authority == "Provincial"):
        health_authority = "Provincial Health Services Authority"
    filtered_data = surgical_plots.qdata[
        (surgical_plots.qdata['health_authority'] == health_authority) &
        (surgical_plots.qdata['year'] >= year[0]) &
        (surgical_plots.qdata['year'] <= year[1])
    ]
    total_waiting = filtered_data['waiting'].sum()
    total_completed = filtered_data['completed'].sum()
    mean_wait_time_50 = filtered_data['wait_time_50'].mean()
    mean_wait_time_90 = filtered_data['wait_time_90'].mean()
    return total_waiting, total_completed, round(mean_wait_time_50), round(mean_wait_time_90)

#Download callback
@app.callback(
    Output("download-df-csv", "data"),
    Input("btn-download", "n_clicks"),
    prevent_initial_call=True,
)
def downloading_button(n_clicks):
    return dcc.send_data_frame(surgical_plots.qdata.to_csv, "BC_surgical_wait_times.csv")

if __name__ == '__main__':
    app.run_server(debug=True,host='127.0.0.1')
