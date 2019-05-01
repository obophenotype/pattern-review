import base64
import os
from urllib.parse import quote as urlquote
from urllib.request import urlopen as uopen
import logging
from flask import Flask, send_from_directory
import dash
from ruamel import yaml
import dash_core_components as dcc
import dash_html_components as html
import dash_table
from dash.dependencies import Input, Output
import pandas as pd
import io
from github import Github
import sys
import pprint
import plotly.graph_objs as go
import math

curators_csv = "http://purl.obolibrary.org/obo/upheno/src/patterns/curators.csv"
issues_csv = "http://purl.obolibrary.org/obo/upheno/src/patterns/pattern_issues.csv"
raw_upheno = "http://purl.obolibrary.org/obo/upheno/src/patterns/"

df_curators = pd.read_csv(curators_csv)
df_issues = pd.read_csv(issues_csv)

server = Flask(__name__)
app = dash.Dash(server=server)
app.config.supress_callback_exceptions = True

user = os.environ['gh_user']
pw = os.environ['gh_password']
g = Github(user, pw)

pattern_list = dict()
pattern_curators = dict()
gh_paths = dict()


def overview_page(df_patterns, df_c):
    value_counts = df_c['pattern'].value_counts()
    df_c_counts = value_counts.rename_axis('unique_values').reset_index(name='counts')
    completed = len(df.loc[(df.done == "Yes"),])
    pattern_ct = len(df)
    return html.Div([html.H2("Completed patterns: {}".format(completed)),pattern_table(df_patterns), curator_contribution_panel(df_c_counts,pattern_ct)])

def curator_contribution_panel(df_p,pattern_ct):
    #print(df.head())
    df = df_p.loc[(df_p.counts > 0), ['unique_values', 'counts']]
    df.columns = ['pattern','value']
    review_ct = df['value'].sum()
    pc_completed = float(len(df_p.loc[(df_p.counts >=5 ), ['unique_values', 'counts']]))/(pattern_ct)
    pc_completed = round(pc_completed*100,2)
    
    df.sort_values(by=['value'], ascending=True, inplace = True)
    return html.Div([
        html.Hr(),
        html.H4("Basic stats:"),
        html.Div("Total number of patterns: {}".format(pattern_ct)),
        html.Div("% reviewed: {} %".format(pc_completed)),
        html.Div("Total number of reviews: {}".format(review_ct)),
        html.Hr(),
        dcc.Graph(
            id='contributors-graph',
            figure={
                'data': [
                    go.Bar(
                        y=df['pattern'],
                        x=df['value'],
                        orientation = 'h'
                    )
                ],
                'layout': go.Layout(
                    barmode='group',
                    margin=go.layout.Margin(
                        l=250,
                        r=10,
                        b=10,
                        t=10,
                        pad=4
                    ),
                )
            }
        )
    ], id='graph-div')

def pattern_table(dataframe):
    rows = []
    for i in range(len(dataframe)):
        row = []
        done = False
        threshold = False
        for col in dataframe.columns:
            value = str(dataframe.iloc[i][col]).strip()
            if col == 'done':
                if value == "Yes":
                    done = True
            if col == 'contr':
                if int(value) >=5:
                    threshold = True
            if col == 'issue':
                if (not value) or (value == "nan"):
                    cell = html.Td(html.A(href='https://github.com/obophenotype/upheno/issues/new', children='create', target="_blank"))
                else:
                    cell = html.Td(html.A(href=value, children='issue', target="_blank"))
            elif col == 'pattern': 
                cell = html.Td(dcc.Link(value, href='/'+value))
            else:
                cell = html.Td(children=value)
            row.append(cell)
        if done and threshold:
            rows.append(html.Tr(row, className="tr-done-threshold"))
        if done and not threshold:
            rows.append(html.Tr(row, className="tr-done-notthreshold"))
        if not done and not threshold:
            rows.append(html.Tr(row, className="tr-notdone-notthreshold"))
        if not done and threshold:
            rows.append(html.Tr(row, className="tr-notdone-threshold"))
    return html.Table(
        # Header
        [html.Tr([html.Th(col) for col in dataframe.columns])] +

        rows
    )
    
def table(dataframe):
    rows = []
    for i in range(len(dataframe)):
        row = []
        for col in dataframe.columns:
            value = str(dataframe.iloc[i][col]).strip()
            cell = html.Td(children=value)
            row.append(cell)
        rows.append(html.Tr(row))
    return html.Table(
        # Header
        [html.Tr([html.Th(col) for col in dataframe.columns])] +

        rows
    )

def get_orcid():
    global df_curators, user 
    rows = df_curators.loc[df_curators['github'] == user]
    return rows['orcid'].iloc[0]
    
def get_pattern_name(path):
    if "/" in path:
        pattern_name = path.rsplit('/', 1)[-1]
    else:
        pattern_name = path
    return pattern_name
    
def get_issue(pattern_name):
    global df_issues 
    pattern_name = get_pattern_name(pattern_name)
    rows = df_issues.loc[df_issues['pattern'] == pattern_name]
    if len(rows)>0:
        return rows['issue'].iloc[0]
    else:
        return None

def create_overview_table_row(content_file): 
    global pattern_list
    pattern_path = str(content_file.path)
    pattern_name = pattern_path.replace("src/patterns/","")
    raw_yaml = raw_upheno + pattern_name
    contents = uopen(raw_yaml).read()
    yaml_content = yaml.round_trip_load(contents,preserve_quotes=True)
    pname = get_pattern_name(pattern_name)
    gh_paths[pname] = pattern_path
    pattern_list[pname] = yaml_content
    if "contributors" in yaml_content.keys(): 
        contributors = yaml_content["contributors"]
    else:
        contributors = []
    pattern_curators[pname] = list(contributors)
    orcid = get_orcid()
    if orcid in contributors:
        processed = "Yes"
    else:
        processed = "No"
    issue = get_issue(pattern_name)
    return {"pattern": pattern_name, "done": processed, "issue": issue, "contr": len(list(contributors))}

def get_pattern_table():
    rows_list = []
    repo = g.get_repo("obophenotype/upheno")
    contents = repo.get_contents("src/patterns/dosdp-dev")
    for content_file in contents:
        rows_list.append(create_overview_table_row(content_file))
    contents = repo.get_contents("src/patterns/dosdp-patterns")
    for content_file in contents:
        rows_list.append(create_overview_table_row(content_file))
    df = pd.DataFrame(rows_list)
    df.sort_values(by=['done', 'contr'], inplace=True , ascending=False)
    return df

pattern = None

def sign():
    global g, pattern_list, pattern, pattern_curators
    yaml_content = pattern_list[pattern]
    contributors = pattern_curators[pattern]
    orcid = get_orcid()
    if orcid in contributors:
        return "Already signed off on this one!"
    contributors.append(orcid)
    yaml_content['contributors'] = contributors
    new_yaml = yaml.round_trip_dump(yaml_content,width=1000)
    gh_path = gh_paths[pattern]
    repo = g.get_repo("obophenotype/upheno")
    file = repo.get_file_contents(gh_path)
    repo.update_file(gh_path, "Signed off on {}".format(pattern), new_yaml, file.sha)
    return "Signed off on {}".format(pattern)


def get_val(dicty,key):
    if key in dicty.keys():
        val = dicty[key]
        if isinstance(val,dict):
            out = []
            for key, value in val.items():
                out.append(html.Div([ html.Em(key + ": "), html.Span(str(value))]))
        elif isinstance(val,list):
            out = []
            for v in val:
                if isinstance(v,dict):
                    outi = []
                    for key, value in v.items():
                        outi.append(html.Div([ html.Em(key + ": "), html.Span(str(value))]))
                else:
                    out = str(v)
                out.append(html.Div(outi))
        else:
            out = str(val)
        return html.Div(out)
    else:
        return "undefined"

def get_pattern_review():
    global pattern, pattern_list
    yaml_content = pattern_list[pattern]
    res = ""
    for line in yaml.round_trip_dump(yaml_content, indent=5, block_seq_indent=3).splitlines(True):
        res += line[3:]
    return html.Div([
        
        html.H2('Pattern review for {}'.format(pattern)),
        html.Div([html.H4("Name: "), html.Div(str(yaml_content['pattern_name']),id="pname")]),
        html.Div([html.H4("IRI: "), html.Div(str(yaml_content['pattern_iri']))]),
        html.Div([html.H4("Description: "),html.Div(get_val(yaml_content,'description'))]),
        html.Div([html.H4("Classes: "),html.Div(get_val(yaml_content,'classes'))]),
        html.Div([html.H4("Relations: "),html.Div(get_val(yaml_content,'relations'))]),
        html.Div([html.H4("Annotation Properties: "),html.Span(get_val(yaml_content,'annotationProperties'))]),
        html.Div([html.H4("Variables: "),html.Div(get_val(yaml_content,'vars'))]),
        html.Div([html.H4("Phenotype name: "),html.Div(get_val(yaml_content,'name'))]),
        html.Div([html.H4("Phenotype annotations: "),html.Div(get_val(yaml_content,'annotations'))]),
        html.Div([html.H4("Phenotype definition: "),html.Div(get_val(yaml_content,'def'))]),
        html.Div([html.H4("EQ: "),html.Div(get_val(yaml_content,'equivalentTo'))]),
        html.Button('Sign', id='sign-pattern'),
        html.Div("",id='signed'),
        ])

df = get_pattern_table()

df_c = pd.DataFrame.from_dict(pattern_curators, orient='index')
df_c['pattern'] = df_c.index
df_c.reset_index()
df_c = pd.melt(df_c, id_vars=['pattern'])
df_c.drop('variable', 1, inplace = True)
df_c = df_c.replace('None', pd.np.nan)
df_c = df_c.loc[df_c['value'] != "None"]
df_c = df_c.loc[df_c['value'] != None]
df_c = df_c.loc[df_c.value.notnull()]

df_c.drop_duplicates(inplace=True)
#print(str(df_c))


#print(str(df_c.head()))
#print(str(df_c.columns))
#print(str(len(df_c)))
#print()
app.logger.info(str(df.head()))

app.layout = html.Div(
    [
        html.H1("Pattern reconciliation monitor"),
        dcc.Location(id='url', refresh=False),
        dcc.Link('Overview table', href='/'),
        html.Div(id='page-content',children=overview_page(df, df_c))
    ],
    className="wrapper",
)

@app.callback(dash.dependencies.Output('page-content', 'children'),
              [dash.dependencies.Input('url', 'pathname')])
def display_page(pathname):
    global pattern
    if pathname:
        if pathname == "/" or pathname == "":
            return overview_page(df, df_c)
        elif pathname.startswith('/dosdp'):
            pattern = get_pattern_name(pathname)
            return get_pattern_review()
        else: 
            return html.Div([
                html.H3('Unknown page: {}'.format(pathname))])
    else:
        return html.Div([
            html.H3('Unknown page')])

@app.callback(
    dash.dependencies.Output('signed', 'children'),
    [dash.dependencies.Input('sign-pattern', 'n_clicks')],
    [dash.dependencies.State('pname', 'value')])
def update_output(n_clicks, value):
    if n_clicks:
        if n_clicks < 1:
            return "<1"
        elif n_clicks == 1:
            msg = sign()
            return '{}'.format(msg)
        else:
            return 'You have already signed, thank you!'
    else: 
        return "None"

if __name__ == '__main__':
    app.run_server(host='0.0.0.0' ,debug=True, port=8050)