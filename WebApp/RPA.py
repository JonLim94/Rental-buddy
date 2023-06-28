import pandas as pd
import tagui as t
import time

# Defining knowledge bases
KB = 'DB/Knowledge Base_Complete.xlsx'
df_time = pd.read_excel(KB,"Travel Time",index_col = 0)
df_ave_rent = pd.read_excel(KB,"Ave Rental",index_col = 0)
df_ave_rent = df_ave_rent.drop('MRT Code',axis=1)
df_ave_rent_minmax = df_ave_rent.drop('MRT Unique',axis=1)
df_ave_rent_ori_processed = df_ave_rent_minmax[df_ave_rent_minmax['Average Room Rental Prices (S$)'] != "No data"]
df_ave_rent_minmax = df_ave_rent_minmax[df_ave_rent_minmax['Average Room Rental Prices (S$)'] != "No data"]
df_index = df_ave_rent.drop(["MRT Unique",
                             "Average Room Rental Prices (S$)",
                             "Average 3-Room House Rental Prices (S$)",
                             "Average 4-Room House Rental Prices (S$)",
                             "Average 5-Room House Rental Prices (S$)",
                            "Average Overall Whole-house Rental"],axis=1)

df_MRT_code = pd.read_excel('DB/Knowledge Base_Complete.xlsx',"Ave Rental",index_col = 0)
df_MRT_code = df_MRT_code.drop(['MRT Unique',
                                "Average Room Rental Prices (S$)",
                             "Average 3-Room House Rental Prices (S$)",
                             "Average 4-Room House Rental Prices (S$)",
                             "Average 5-Room House Rental Prices (S$)",
                            "Average Overall Whole-house Rental"],axis=1)

df_MRT_code = df_MRT_code.rename(columns={'MRT Code':'MRT ID'})
df_MRT_code = df_MRT_code.set_index('Station Name')

# MRT Index by index (e.g. 1: Admiralty, 2: Aljunied,  etc)
MRT_index_name = df_index.to_dict()

# MRT index by name (e.g. Admiralty: 1, Aljunied: 2, etc)
MRT_name_index = {value: key for key, value in MRT_index_name['Station Name'].items()}

MRT_codes = df_MRT_code.to_dict()

for column in df_ave_rent_minmax.columns:
    if column == "Station Name":
        continue

    else:
        df_ave_rent_minmax[column] = (df_ave_rent_minmax[column] - df_ave_rent_minmax[column].min())/ (df_ave_rent_minmax[column].max() - df_ave_rent_minmax[column].min())


# Max and Mins for normalization purposes
time_min = 0
time_max = 97

room_rent_min = df_ave_rent_ori_processed['Average Room Rental Prices (S$)'].min()
room_rent_max = df_ave_rent_ori_processed['Average Room Rental Prices (S$)'].max()
house_rent_min = df_ave_rent_ori_processed['Average Overall Whole-house Rental'].min()
house_rent_max = df_ave_rent_ori_processed['Average Overall Whole-house Rental'].max()


# # Functions start here

def find_nearest_station(CoA_postcodes):
    '''for CoA, just input a list of 6-digit postcode'''
    closest_stations = []
    t.init()
    attempts = 0
    
    for i in range(len(CoA_postcodes)):  
        while attempts < 4: 
            try:            
                t.url("https://www.onemap.gov.sg/main/v2/")
                t.wait(2)
                t.type('//input[@id="search-text"]',f"[clear]{CoA_postcodes[i]}[enter]")
                t.click('//div[@id="map"]')
                cs = t.read('//div[@id="mrt_0"]')
                cs = cs[:cs.find("MRT")-1].lower()
                closest_stations.append(cs)
                t.wait(1)
                break
        
            except:
                attempts += 1
                continue

    t.close()

    return closest_stations


def ave_rental_calculate(house_type,index):
    if df_ave_rent["Average Room Rental Prices (S$)"][index] == "No data":
        return "No data"
    else:
        if house_type.lower() == "room":
            ave_rental = float(df_ave_rent_minmax["Average Room Rental Prices (S$)"][index])
        elif house_type.lower() == "entire house":
            ave_rental = float(df_ave_rent_minmax["Average Overall Whole-house Rental"][index])
        else:
            ave_rental = "Invalid housetype"

        return ave_rental



def normalize_all(house_type,budget,comfortable_travel_time):
    if house_type.lower() == "room":
        budget = (budget - room_rent_min) / (room_rent_max - room_rent_min)
    else:
        budget = (budget - house_rent_min) / (house_rent_max - house_rent_min)
    
    comfortable_travel_time = comfortable_travel_time / time_max
    
    return budget, comfortable_travel_time



def shortlist_stations(closest_station,budget,house_type,comfortable_travel_time, budget_weight = 0.2, time_weight = 0.65, shortlist_num = 2):
    scores, stations_and_time, time_ave = [],[],[]

    for i in range(1,172):
        average_rental = df_ave_rent["Average Room Rental Prices (S$)"][i]
        average_rental_norm = ave_rental_calculate(house_type,i)

        if average_rental_norm == "No data":
            continue

        else:
            time_total = 0
            for station in closest_station:
                CoA_time = float(df_time[i][MRT_name_index[station]])/time_max
                time_total += CoA_time
                
            time_average = time_total/len(closest_station)    
            
            # Budget bonus rules
            if average_rental>0.7*budget and average_rental < 1.1*budget:
                budget_bonus = 1.5
            elif average_rental>0.5*budget and average_rental<0.7*budget:
                budget_bonus = 1
            elif average_rental>1.5*budget and average_rental<2.0*budget:
                budget_bonus = -1
            elif average_rental>2.0*budget and average_rental<2.5*budget:
                budget_bonus = -2.1
            elif average_rental>2.5*budget:
                budget_bonus = -5
            else:
                budget_bonus = 0

            # Time penalty rules:
            if time_average > comfortable_travel_time:
                time_penalty = 0.5*float(time_average*time_max - comfortable_travel_time)
            else:
                time_penalty = 0

            # total score above would result in "the smaller the better". Score is inversed to generate a "bigger score better" setting
            total_score = (1/(0.2*average_rental_norm+0.65*time_average+1))*10 + budget_bonus - time_penalty
            scores.append(round(total_score,4))
            stations_and_time.append([MRT_index_name['Station Name'][i],time_average*time_max])

    scores, stations_and_time = zip(*sorted(zip(scores, stations_and_time),reverse = True))
    
    stations = []
    ave_travel_time = []
    for item in stations_and_time:
        stations.append(item[0])
        ave_travel_time.append(item[1])
    
    stations = tuple(stations)
    ave_travel_time = tuple(ave_travel_time)
    
    return stations[:shortlist_num], ave_travel_time[:shortlist_num]
    


def scoring(price,
            travel_time,
            budget,
            house_type,
            comfortable_travel_time):
    
    housing_dict = {'room':{'min':917,
                           'max':3200},             
            'entire house':{'min':2317,
                            'max':3800}}
    
    hd = housing_dict[house_type.lower()]
    norm_price = (price - hd['min']/(hd['max']-hd['min']))
    norm_travel_time = travel_time/97 # time_max = 97, time_min = 0
    
    # Budget Bonus scoring to boost properties around the budget set.
    # Prevents the situation where lowest price is always favoured regardless of budget.
    if price>0.7*budget and price< 1.1*budget:
        budget_bonus = 1.5
    elif price>0.5*budget and price<0.7*budget:
        budget_bonus = 1
    elif price>1.5*budget and price<2.0*budget:
        budget_bonus = -1
    elif price>2.0*budget:
        budget_bonus = -2.1
    elif price>2.5*budget:
        budget_bonus = -5
    else:
        budget_bonus = 0
    
    # Travel Time Penalty if exceed the 
    if float(travel_time)>comfortable_travel_time:
        time_penalty = 0.5*float(travel_time-comfortable_travel_time)
    else:
        time_penalty = 0
    
    # in the nearest MRT formula, the bigger weight is on travel time as the price reflects an average
    
    score = (1/(0.65*norm_price+0.2*norm_travel_time+1))*10 + budget_bonus - time_penalty
    
    return score



def lets_wait(target_element):
    start_time = time.time()
    time_lapsed = 0
    while not t.present(target_element) and time_lapsed < 8:
        t.wait(1)
        end_time = time.time()
        time_lapsed = end_time - start_time
    return target_element



def time_converter(input_data):
    input_time = [time for time in input_data.split() if time.isnumeric()]
    input_unit = input_data.split()
    if len(input_time) == 2:
        hour_to_min = int(input_time[0]) * 60
        total_time = hour_to_min + int(input_time[1])
    
    elif len(input_time) == 1 and ("hr" not in input_unit or 'h' not in input_unit):
        total_time = (input_time[0])
    
    elif len(input_time) == 1:
        total_time = int(input_time[0]) * 60
    
    else:
        total_time = 0
    
    return total_time


def shortlist_generation(prop_titles,prop_addresses,prop_prices,travel_times,links,scores):
    if (len(prop_titles)+len(prop_addresses)+len(prop_prices)+len(travel_times)+len(links))/5 != len(scores):
        return "Scrape does not tally"

    else:
        shortlist = pd.DataFrame({'Property' : prop_titles,
                                          'Address' : prop_addresses,
                                          'Price (S$/mo)' : prop_prices,
                                          'Travel Time (mins)': travel_times,
                                         'Property Score': scores,
                                         'Links' : links})

        shortlist = shortlist.sort_values(by=['Property Score'],ascending=False)

        return shortlist



def ave_time_generation(address,CoA):
    tt_total = 0.0
    for i in range(len(list(CoA))):
        tt = time_check(address,f"Singapore {CoA[i]}")
        tt_total += float(tt)
    ave_time = float(tt_total) / len(CoA)
    return ave_time



def URL_generator(max_price, house_type, mrt_name):
    
    global df_MRT_code
    url_adapted = mrt_name.replace(" ","+")
    MRT_code = df_MRT_code['MRT ID'][mrt_name]
    split_code = MRT_code.split()

    url_mrt = ""
    concat_code = ""
    for code in split_code:
        url_mrt += f"&MRT_STATIONS[]={code}"
        concat_code += f"/{code}"
    concat_code = concat_code[1:]
    url_mrt = url_mrt[1:]
    
    ud = {'url':'https://www.propertyguru.com.sg/',
        'rental housing':'property-for-rent?market=residential&listing_type=rent&',
       'max price':f'maxprice={str(max_price)}&',
           'room':'beds[]=-1&',
           'entire house':'beds[]=0&beds[]=1&beds[]=2&beds[]=3&beds[]=4&beds[]=5&',
           'search true':'search=true',
           'MRT search method':f"freetext={url_adapted}&",
           'sort method':'&sort=price&order=asc'}
    
    base = ud['url']
    rental_housing = ud['rental housing'] 
    max_price = ud['max price']
    house_type = ud[house_type.lower()]
    mrt_search = ud['MRT search method']
    ending = ud['search true']
    sort_method = ud['sort method']
    
    full_url = "".join([base,rental_housing,max_price,house_type,mrt_search,ending,sort_method])
    return full_url




def time_check(start_point, end_point):
    
    gothere_startpoint = start_point.replace(" ","%20")
    gothere_endpoint = end_point.replace(" ","%20")
    
    tc = {"url":f'https://gothere.sg/maps#q:from%20{gothere_startpoint}%20to%20{gothere_endpoint}%20at%2012%3A30pm',
                        "search box":'//input[@id="q"]',
                         "search button": '//input[@id="ss"]'}
    
    min_time = 1000
    # method begins here:
    t.url(tc['url'])
    
    t.click(tc['search button'])

    for mode in ["train","bus"]:
        t.click(f'//li[@id="{mode}"]')

        for i in range(1,t.count(f'//div[@mode="{mode}"]/p[@class="n1"]')+1):
            travel_time = time_converter(t.read(f'(//div[@mode="{mode}"]/p[@class="n1"])[{i}]'))
            if int(travel_time) < int(min_time):
                min_time = travel_time

    return min_time
    



def shortlist_properties(url, CoA, budget, house_type, comfortable_travel_time, time_average, 
                         shortlist_num = 5, no_change_max = 7):
    '''Function to scrape website and shortlist properties based on travel time and price. 
    CoA and CoA_name here should be in a list format'''
    
    wd = {'no results':'''//h3[text()="Sorry, we couldn't find any results for:"])''',
        'search box':'//input[@placeholder="Search Location"]',
        'prop title':'//div[@class="gallery-container"]/a/@title',
       'prop address':'//span[@itemprop="streetAddress"]',
        'prop price':'//li[@class="list-price pull-left"]/span[@class="price"]',
        'prop link':'(//div[@class="gallery-container"]/a/@href)',
        'next page':'//li[@class="pagination-next"]/a',
       'stop code': '//span[@data-dobid="hdw"]'}

    count = 1
    t.init()
    t.url(url)
    
    # this loop is to prevent captcha from stopping the process. User needs to click the verify in order to proceed.
    while not t.present(wd['search box']):
        t.wait(1)
    
    
    next_page = True
    t.wait(4)
    if t.present(wd['no results']):
        return "Sorry, we couldn't find any results. Please update your search criteria"
    
        
    else:
        # Initialisation
        scores = []
        scores = scores + [-1000]*(shortlist_num - len(scores))
        prop_titles, prop_addresses, prop_prices, links, travel_times = [scores.copy() for _ in range(5)]
        temp_address_memory, temp_time_memory = [],[]
        no_change_count = 0

        while next_page:
            lets_wait(wd['prop address'])
            prop_no = t.count(wd['prop address'])

            for i in range(1, prop_no + 1):
                skip_timecheck = False
                prop_address = t.read(f"({wd['prop address']})[{i}]")
                price = t.read(f"({wd['prop price']})[{i}]")
                price = int(price.replace(',',''))
                prop_score = scoring(price,time_average,budget,house_type,comfortable_travel_time) #ave_travel_time here is station[1] in nearest station


                for j in range(len(scores)):
                    if prop_score > scores[j]:
                        link = t.read(f"{wd['prop link']}[{i}]")
                        prop_title = t.read(f"({wd['prop title']})[{i}]")
                        # print(prop_title)

                        # Removing initialized 0s
                        scores.remove(scores[j])
                        prop_titles.remove(prop_titles[j])
                        prop_addresses.remove(prop_addresses[j])
                        prop_prices.remove(prop_prices[j])
                        links.remove(links[j])
                        travel_times.remove(travel_times[j])

                        # Appending new information
                        prop_titles.append(prop_title)
                        prop_addresses.append(prop_address) 
                        prop_prices.append(price)
                        links.append(link)
                        skip_timecheck = False
                        break
                        
                    else:
                        skip_timecheck = True


                if skip_timecheck:
                    no_change_count += 1
                    if no_change_count > no_change_max:
                        break
                    else:
                        continue

                else: 
                    no_change_count = 0
                    # print(no_change_count)
                    if prop_address not in temp_address_memory:
                        current_url = t.url()
                        ave_time = ave_time_generation(prop_address, CoA)
                        travel_times.append(ave_time)
                        temp_address_memory.append(prop_address) # Memory component to save redundant searches
                        temp_time_memory.append(ave_time) # Memory to recall the saved address
                        t.url(current_url)
                    else:
                        travel_times.append(temp_time_memory[temp_address_memory.index(prop_address)])

                    prop_score = scoring(price,ave_time,budget,house_type,comfortable_travel_time)
                    scores.append(prop_score)


            if no_change_count > no_change_max:
                shortlist = shortlist_generation(prop_titles,prop_addresses,prop_prices,travel_times,links,scores)
                break

            elif t.present(wd['next page']):
                count += 1
                t.url(f"{url[:49]}/{count}{url[49:]}")
                t.wait(3)
            else:
                shortlist = shortlist_generation(prop_titles,prop_addresses,prop_prices,travel_times,links,scores)
                next_page = False
  
    t.close()

    return shortlist



# CoA = ["138567","298137"]
# budget = 1500
# house_type = "Room"
# comfortable_travel_time = 46




def start_house_search(CoA, budget, house_type, comfortable_travel_time, mrt_shortlist=1,prop_shortlist=10, no_change_max=7):
    # house_type = house_type
    to_be_concatenated = []
    
    closest_stations = find_nearest_station(CoA)
    stations, ave_travel_time = shortlist_stations(closest_stations, 
                                                   budget, 
                                                   house_type,
                                                   comfortable_travel_time, 
                                                   shortlist_num = mrt_shortlist)

    for i in range(len(stations)):
        URL = URL_generator(budget, house_type, stations[i])
        shortlist = shortlist_properties(URL, 
                                         CoA,
                                         budget, 
                                         house_type, 
                                         comfortable_travel_time, 
                                         ave_travel_time[i],
                                        shortlist_num = prop_shortlist,
                                        no_change_max = no_change_max)
        to_be_concatenated.append(shortlist)


    shortlisted_properties = pd.concat(to_be_concatenated)
    
    t.close()

    return shortlisted_properties




# shortlist = start_house_search(CoA, budget, house_type, comfortable_travel_time,prop_shortlist=5,no_change_max=2)
# print(shortlist)

if __name__ == "main":
	print("shortlist")




