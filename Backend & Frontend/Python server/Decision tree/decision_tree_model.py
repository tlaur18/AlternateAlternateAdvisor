import sqlite3
import pandas as pd
import joblib
import sys
import os
import hashlib
import json
from math import sin, cos, sqrt, atan2, radians, isnan, floor

db_path = 'data\\PE2014A\\PE2014A.sqlite'

def create_connection(db_file):
    conn = None
    try:
        conn = sqlite3.connect(db_file)
    except sqlite3.Error as e:
        print(e)

    return conn


def get_airport_coords(conn):
    query = "SELECT ICAO, Latitude as latitude, Longitude AS longitude, LongestRunway AS longest_runway, HasILSApproach AS has_ils, HasRNAVApproach AS has_rnav, HasLocalizerApproach AS has_loc FROM (SELECT * FROM Airport INNER JOIN Point P on Airport.Point = P.Id) WHERE ICAO != ''"

    cur = conn.cursor()
    cur.execute(query)
    
    columns_names = list(map(lambda x: x[0], cur.description))
    rows = cur.fetchall()
    
    return rows, columns_names

def get_more_airport_data(conn):
    query = "SELECT alternates_airports_displayed_to_user as alternates, alternates_airport_is_towered_displayed_to_user AS has_tower, alternates_airport_approaches_displayed_to_user AS approaches FROM '1_mio_alternate_data'"

    cur = conn.cursor()
    cur.execute(query)
    
    columns_names = list(map(lambda x: x[0], cur.description))
    rows = cur.fetchall()
    
    return rows, columns_names

def get_aircraft_data(conn):
#     query = "SELECT * FROM 'airplane_data (corrected with missing aircrafts) (from CSV)'"
    query = "SELECT aircraft_type_icao, MAX(aircraft_max_landing_weight) AS aircraft_max_landing_weight, MIN(aircraft_min_runway_length) AS aircraft_min_runway_length FROM 'airplane_data (corrected with missing aircrafts) (from CSV)' GROUP BY (aircraft_type_icao)"

    cur = conn.cursor()
    cur.execute(query)
    
    columns_names = list(map(lambda x: x[0], cur.description))
    rows = cur.fetchall()
    
    return rows, columns_names


def calc_coord_distance(lat1, lon1, lat2, lon2):
    # Calculates distance between two points in km
    
    R = 6373.0    # Approximate radius of earth in km

    lat1 = radians(lat1)
    lon1 = radians(lon1)
    lat2 = radians(lat2)
    lon2 = radians(lon2)

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = R * c
    
    return distance


def get_grid_square(lat, lon):
    lat += 90
    lon += 180
    
    lat_rounded = floor(lat)
    lon_rounded = floor(lon)
    
    # square_id = 360 * lat_rounded + lon_rounded
    square_id = 180 * lon_rounded + lat_rounded
    return square_id


class Airport:
    def __init__(self, icao):
        self.icao = icao
        # self.lat = df_airport_data.loc[icao]["latitude"] if (icao in df_airport_coords.index) else None
        # self.lon = df_airport_data.loc[icao]["longitude"] if (icao in df_airport_coords.index) else None
        self.lat = df_airport_data.loc[icao]["latitude"]
        # self.lat = str(self.lat) if isnan(self.lat) else self.lat
        self.lon = df_airport_data.loc[icao]["longitude"]
        # self.lon = str(self.lon) if isnan(self.lon) else self.lon
        self.has_tower = df_airport_data.loc[icao]["has_tower"]
        # self.has_tower = str(self.has_tower) if isnan(self.has_tower) else self.has_tower
        self.approaches = df_airport_data.loc[icao]["approaches"]
        # self.approaches = str(self.approaches) if isnan(self.approaches) else self.approaches
        self.has_ils = isinstance(self.approaches, str) and "ILS" in self.approaches
        self.longest_runway = df_airport_data.loc[icao]["longest_runway"]

    def __str__(self):
        return "  - " + str(self.icao) + "{:10.3f}".format(self.lat) + "{:10.3f}".format(self.lon) + "\tTower:" + str(self.has_tower) + "   Approaches:" + str(self.approaches)
    
    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)


class Alternate(Airport):
    def __init__(self, icao, dest_airport):
        super().__init__(icao)
        self.distance = round(calc_coord_distance(dest_airport.lat, dest_airport.lon, self.lat, self.lon), 3)
    
    def __str__(self):
        return "  - " + str(self.icao) + "{:10.3f}".format(self.distance) + "km" + "\tTower:" + str(self.has_tower) + "   Approaches:" + str(self.approaches)

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)

def my_hash(string):
    return int(str(int(hashlib.sha256(string.encode('utf-8')).hexdigest(), base=16))[:10])


def init_airport_data():
    # Fetching airport coordinates
    dirname = os.path.dirname(__file__)
    conn = create_connection(os.path.join(dirname, db_path))
    rows, column_names = get_airport_coords(conn)
    df_airport_coords = pd.DataFrame(rows, columns=column_names)
    df_airport_coords = df_airport_coords.set_index("ICAO")
    
    # Fethcing more airport features (tower, approaches) 
    rows, column_names = get_more_airport_data(conn)
    df_airport_data = pd.DataFrame(rows, columns=column_names)
    
    for column in df_airport_data.columns:
        df_airport_data[column] = df_airport_data[column].astype(str)

    airport_dict = {}

    for i, row in df_airport_data.iterrows():
        if i % 10000 == 0:
            progress = round(i / len(df_airport_data.index) * 100, 2)
            print(str(progress) + "%  ", end="\r")



        alternates = row["alternates"].split(",")
        towers = row["has_tower"].split(",")
        approaches = row["approaches"].replace(", ", ";").split(",")

        for i in range(len(alternates)):
            if alternates[i] not in airport_dict.keys():
                value = []
                value.append(1 if towers[i] == "Towered" else 0)
                value.append(approaches[i])

                airport_dict[alternates[i]] = value

    print("100%  ", end="\r")
    df_airport_data = pd.DataFrame.from_dict(airport_dict, orient='index', columns=["has_tower", "approaches"])
    
    # Combining dataframes to make the one and only airport_data
    df_airport_data = pd.concat([df_airport_coords, df_airport_data], axis=1).sort_index()
    
    return df_airport_data



def init_aircraft_data():
    dirname = os.path.dirname(__file__)
    conn = create_connection(os.path.join(dirname, db_path))
    rows, column_names = get_aircraft_data(conn)
    df_aircraft_data = pd.DataFrame(rows, columns=column_names)
    df_aircraft_data = df_aircraft_data.set_index("aircraft_type_icao")

    return df_aircraft_data


def get_airport_data(icao):
    return df_airport_data.to_dict(orient="index")[icao]


def init_machine_learning_model():
    # Importing decision tree model
    dirname = os.path.dirname(__file__)
    dt = joblib.load(os.path.join(dirname, "./models/pure.joblib"))
    
    return dt


def convert_to_alternate_objects(dest, alternates):
    converted_alternates = []
    for alternate_icao in alternates:
        if alternate_icao == dest.icao:
            continue
        if alternate_icao not in df_airport_data.index:
            continue
        converted_alternates.append(Alternate(alternate_icao, dest))
    
    return converted_alternates


def get_aircraft_weight_class(weight):
    if weight < 15500:
        return 0
    elif weight < 300000:
        return 1
    elif weight < 1234000:
        return 2
    else:
        return 3


def make_prediction(dest_icao, aircraft_icao):
    dest_icao = dest_icao.upper()
    aircraft_icao = aircraft_icao.upper()

    dest = Airport(dest_icao)

    aircraft_weight_class = get_aircraft_weight_class(df_aircraft_data["aircraft_max_landing_weight"][aircraft_icao])

    attributes = [dest.lat, dest.lon, aircraft_weight_class]

    number_of_non_zero_probs = sum(i > 0 for i in dt.predict_proba([attributes])[0])
    predicted_alternates = dt.classes_[dt.predict_proba([attributes])[0].argsort()[-number_of_non_zero_probs:][::-1]]
    predicted_alternates = convert_to_alternate_objects(dest, predicted_alternates)

    # # Pipeline sorting
    # predicted_alternates = sorted(predicted_alternates, key=lambda x: x.distance)
    # predicted_alternates = sorted(predicted_alternates, key=lambda x: x.has_tower, reverse=True)

    return dest, predicted_alternates


df_airport_data = init_airport_data()
df_aircraft_data = init_aircraft_data()
dt = init_machine_learning_model()

