
import os
from flask import (Flask, render_template, request,
                   send_from_directory, jsonify)
import pandas as pd
import RPA


app = Flask(__name__)

def dataframe(table):
    tup = tuple(table.itertuples(index=False, name=None))
    return tup

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/resources/<path:path>')
def send_resources(path):
    return send_from_directory('resources', path)

@app.route('/FormPage')
def uploadResumePage():
    return render_template('Form.html')

@app.route('/InfoPage')
def classifierPage():
    return render_template('InfoPage.html')

##########Temporary route before fitting GA####################
########## No Longer Active ####################
@app.route('/TempAction', methods=['POST'])
def TempAction():
    budget = request.form['name']
    property_type = request.form['Property_Type']
    traveltime = int(request.form['traveltime'])
    # WorkLoc1 = request.form['WorkLoc1']
    # WorkLoc2 = request.form['WorkLoc2']
    CoA = [int(x) for x in (request.form['WorkLoc1'], request.form['WorkLoc2']) if x != '']
    # CoA = [int(x) for x in (WorkLoc1, WorkLoc2) if x != '']
    finlist = pd.read_csv('./DB/scrapped_listings.csv', index_col=0)
    finlist = finlist.sample(frac=1).drop(columns= ['Location']).head(10)
    finlist["AvgTravelTime"] = finlist["AvgTravelTime"].apply(int)
    print(budget)
    print(CoA)
    print(property_type)
    print(traveltime)

    if budget:
        result = dataframe(finlist)
        #result = table.to_html()
        #result = result.to_html(classes='table table-stripped')
        
    else:
        result = "Please enter keyword for a quick profile match"

    return render_template('ListingsOutput.html', results = result)
##########Temporary route before fitting GA####################


########## Form To RPA Route #################
@app.route('/GAAction', methods=['POST'])
def GetProperty():
    budget = int(request.form['name'])
    property_type = request.form['Property_Type']
    comfortable_travel_time = int(request.form['traveltime'])
    
    # CoA = [int(x) for x in (request.form['WorkLoc1'], request.form['WorkLoc2']) if x != '']
    CoA = [x for x in (request.form['WorkLoc1'], request.form['WorkLoc2']) if x != '']
    
    # print(type(budget))
    # print(CoA)
    # print(type(property_type))
    # print(type(comfortable_travel_time))

    result = RPA.start_house_search(CoA, budget, property_type, comfortable_travel_time)
    result = result.drop(columns= ['Property'])
    result["Travel Time (mins)"] = result["Travel Time (mins)"].apply(int)

    # print(result)

    if isinstance(result, pd.DataFrame):
        result = dataframe(result)
        return render_template('ListingsOutput.html', results = result)
        
    else:
        return render_template('ErrorPage.html')

    









if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080, debug=True)