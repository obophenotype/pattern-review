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

curators_csv = os.environ['curators_csv']
issues_csv = os.environ['issues_csv']
pattern_dir = os.environ['pattern_dir']
new_ticket_url = os.environ['new_ticket_url']
user = os.environ['gh_user']
pw = os.environ['gh_password']
repo_name = os.environ['repo_name']
pattern_iri_prefix = os.environ['pattern_iri_prefix']

df_curators = pd.read_csv(curators_csv)
df_issues = pd.read_csv(issues_csv)

server = Flask(__name__)
app = dash.Dash(server=server)
app.config.supress_callback_exceptions = True
g = Github(user, pw)

pattern_list = dict()
pattern_curators = dict()
gh_paths = dict()
pattern = None

def overview_page(df_patterns, df_c):
    df_c_counts = df_c['pattern'].value_counts().rename_axis('unique_values').reset_index(name='counts')
    df_p_counts = df_c['value'].value_counts().rename_axis('unique_values').reset_index(name='counts')
    completed = len(df.loc[(df.done == "Yes"),])
    pattern_ct = len(df)
    return html.Div([html.H2("Completed patterns: {}".format(completed)),pattern_table(df_patterns), colour_code_table(),curator_contribution_panel(df_c_counts,df_p_counts,pattern_ct)])

def curator_contribution_panel(df_p,df_c,pattern_ct):
    #print(df_p.head())
    #print(df_c.head())
    df_pc = df_p.loc[(df_p.counts > 0), ['unique_values', 'counts']]
    df_cp = df_c.loc[(df_c.counts > 0), ['unique_values', 'counts']]
    df_pc.columns = ['pattern','value']
    df_cp.columns = ['contributor','value']
    review_ct = df_pc['value'].sum()
    ct_completed = len(df_p.loc[(df_p.counts >=5 ), ['unique_values', 'counts']])
    pc_completed = float(ct_completed)/(pattern_ct)
    pc_completed = round(pc_completed*100,2)
    
    df_pc.sort_values(by=['value'], ascending=True, inplace = True)
    df_cp.sort_values(by=['value'], ascending=True, inplace = True)
    
    return html.Div([
        html.Hr(),
        html.H4("Basic stats:"),
        html.Div("Total number of patterns: {}".format(pattern_ct)),
        html.Div("Reviewed: {} ({} %)".format(ct_completed,pc_completed)),
        html.Div("Total number of reviews: {}".format(review_ct)),
        html.Hr(),
        graph_pattern_contributors(df_pc),
        graph_contributors_patterns(df_cp),
    ], id='graph-div')

def graph_pattern_contributors(df):
    return dcc.Graph(
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
                    l=350
                ),
            )
        }
    )
    
def graph_contributors_patterns(df):
    return dcc.Graph(
        id='contributors-pattern-graph',
        figure={
            'data': [
                go.Bar(
                    y=df['contributor'],
                    x=df['value'],
                    orientation = 'h'
                )
            ],
            'layout': go.Layout(
                barmode='group',
                margin=go.layout.Margin(
                    l=250
                ),
            )
        }
    )

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
                    cell = html.Td(html.A(href=new_ticket_url, children='create', target="_blank"))
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

def colour_code_table():
    rows = []
    rows.append(html.Tr([html.Td(children="Reviewed/threshold",className="tr-done-threshold"),html.Td(children="You reviewed pattern, and 5+ community reviews overall")]))
    rows.append(html.Tr([html.Td(children="Reviewed/not threshold",className="tr-done-notthreshold"),html.Td(children="You reviewed pattern, but there are less than 5 community reviews overall")]))
    rows.append(html.Tr([html.Td(children="Not reviewed/threshold",className="tr-notdone-threshold"),html.Td(children="You have not reviewed pattern, but 5+ community reviews overall")]))
    rows.append(html.Tr([html.Td(children="Not reviewed/not threshold",className="tr-notdone-notthreshold"),html.Td(children="You have not reviewed pattern, and there are less than 5 community reviews overall")]))
    
    return html.Div([
    html.Hr(),
    html.Em("Colour coding: "),
    html.Table(
        rows
    )])

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
    raw_yaml = pattern_dir + pattern_name
    try:
      contents = uopen(raw_yaml).read()
      yaml_content = yaml.round_trip_load(contents,preserve_quotes=True)
    except:
      print(raw_yaml+ " could not be loaded!")
      return {"pattern": pattern_name, "done": "ERROR", "issue": None, "contr": 0}
    
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
    repo = g.get_repo(repo_name)
    contents = repo.get_contents("src/patterns/dosdp-dev")
    for content_file in contents:
        if content_file.name.endswith(".yaml"):
          rows_list.append(create_overview_table_row(content_file))
    contents = repo.get_contents("src/patterns/dosdp-patterns")
    for content_file in contents:
        rows_list.append(create_overview_table_row(content_file))
    df = pd.DataFrame(rows_list)
    df.sort_values(by=['done', 'contr'], inplace=True , ascending=False)
    return df


def sign(approve=True):
    global g, pattern_list, pattern, pattern_curators, user
    yaml_content = pattern_list[pattern]
    contributors = pattern_curators[pattern]
    orcid = get_orcid()
    if approve:
        if orcid in contributors:
            return "Already signed off on this one!"
        contributors.append(orcid)
    else:
        if orcid not in contributors:
            return "You have not signed off on this one!"
        contributors.remove(orcid)
    yaml_content['contributors'] = contributors
    new_yaml = yaml.round_trip_dump(yaml_content,width=1000)
    gh_path = gh_paths[pattern]
    repo = g.get_repo(repo_name)
    file = repo.get_file_contents(gh_path)
    branch = "signed-{}-{}".format(pattern.lower(),user.lower())
    sb = repo.get_branch("master")
    sys.stdout.flush()
    repo.create_git_ref(ref='refs/heads/' + branch, sha=sb.commit.sha)
    repo.update_file(path=gh_path, message="Signed off on {}".format(pattern), content=new_yaml, sha=file.sha, branch=branch)
    repo.create_pull(title="Signed off on {}".format(pattern), body="Signed off on {}".format(pattern), base='master', head=branch, maintainer_can_modify=True)
    pattern_curators[pattern] = contributors
    return "Signed off on {}".format(pattern)


def get_val(dicty,key,ols=False):
    if key in dicty.keys():
        val = dicty[key]
        if isinstance(val,dict):
            out = []
            for key, value in val.items():
                val = str(value)
                if ols:
                    linkout = "https://www.ebi.ac.uk/ols/search?q={}&exact=on".format(val)
                    out.append(html.Div([ html.Em(key + ": "), html.A(href=linkout, children=val, target="_blank")]))
                else:
                    out.append(html.Div([ html.Em(key + ": "), html.Span(val)]))
        elif isinstance(val,list):
            out = []
            for v in val:
                if isinstance(v,dict):
                    outi = []
                    for key, value in v.items():
                        val = str(value)
                        if ols:
                            linkout = "https://www.ebi.ac.uk/ols/search?q={}&exact=on".format(val)
                            outi.append(html.Div([ html.Em(key + ": "), html.A(href=linkout, children=val, target="_blank")]))
                        else:
                            outi.append(html.Div([ html.Em(key + ": "), html.Span(val)]))

                else:
                    out = str(v)
                out.append(html.Div(outi))
        else:
            out = str(val)
        return html.Div(out)
    else:
        return "undefined"

def get_pattern_review():
    global pattern, pattern_list, pattern_iri_prefix, repo_name, gh_paths
    yaml_content = pattern_list[pattern]
    res = ""
    for line in yaml.round_trip_dump(yaml_content, indent=5, block_seq_indent=3).splitlines(True):
        res += line[3:]
    iri = str(yaml_content['pattern_iri'])
    path_gh = "https://github.com/{}/blob/master/{}".format(repo_name,gh_paths[pattern])
    gh_issue = get_issue(pattern)
    return html.Div([
        
        html.H2('Pattern review for {}'.format(pattern)),
        html.Div([html.H4("Name: "), html.Div(str(yaml_content['pattern_name']),id="pname")]),
        html.Div([html.H4("IRI: "), html.Div(html.A(href=path_gh, children=iri, target="_blank"))]),
        html.Div([html.H4("GitHub discussion: "), html.Div(html.A(href=gh_issue, children="{}".format(gh_issue), target="_blank"))]),
        html.Div([html.H4("Description: "),html.Div(get_val(yaml_content,'description'))]),
        html.Div([html.H4("Classes: "),html.Div(get_val(yaml_content,'classes',True))]),
        html.Div([html.H4("Relations: "),html.Div(get_val(yaml_content,'relations',True))]),
        html.Div([html.H4("Annotation Properties: "),html.Span(get_val(yaml_content,'annotationProperties',True))]),
        html.Div([html.H4("Variables: "),html.Div(get_val(yaml_content,'vars'))]),
        html.Div([html.H4("Phenotype name: "),html.Div(get_val(yaml_content,'name'))]),
        html.Div([html.H4("Phenotype annotations: "),html.Div(get_val(yaml_content,'annotations'))]),
        html.Div([html.H4("Phenotype definition: "),html.Div(get_val(yaml_content,'def'))]),
        html.Div([html.H4("EQ: "),html.Div(get_val(yaml_content,'equivalentTo'))]),
        dcc.RadioItems(
            id='radio-sign',
            options = [
                {'label': 'Sign', 'value': 'sign'},
                {'label': 'Unsign', 'value': 'unsign'},
                ],
            value = "",
            labelStyle={'display': 'inline-block'}
            ),
        html.Button('Submit', id='sign-pattern'),
        html.Div("",id='signed'),
        ])

def create_curator_table():
    global pattern_curators
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
    return df_c

# Processing starts
df = get_pattern_table()
df_c = create_curator_table();

#print(str(df_c))
#print(str(df_c.head()))
#print(str(df_c.columns))
#print(str(len(df_c)))
#print()

##########################
## DEFINITION OF LAYOUT ##
##########################

app.layout = html.Div(
    [
        html.H1("Pattern reconciliation monitor"),
        dcc.Location(id='url', refresh=False),
        dcc.Link('Overview table', href='/'),
        html.Div(id='page-content',children=overview_page(df, df_c))
    ],
    className="wrapper",
)

##########################
## CALLBACKS ##
##########################

@app.callback(dash.dependencies.Output('page-content', 'children'),
              [dash.dependencies.Input('url', 'pathname')])
def display_page(pathname):
    global pattern, df, df_c
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
    [dash.dependencies.State('radio-sign', 'value') ])
def update_output(n_clicks, value):    
    if value:
        signthis = None
        if value == "sign":
            signthis = True
        else:
            signthis = False
        msg = sign(signthis)
        return '{}'.format(msg)
    else:
        return 'You must select a sign option!'

#@app.callback(
#    dash.dependencies.Output('url', 'pathname'),
#    [dash.dependencies.Input('hard-reload', 'n_clicks')])
#def hard_reload(n_clicks):
#    global df, df_c    
#    df = get_pattern_table()
#    df_c = create_curator_table();
#    return '/'


if __name__ == '__main__':
    app.run_server(host='0.0.0.0' ,debug=True, port=8050)