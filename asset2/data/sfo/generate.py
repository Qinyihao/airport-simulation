#!/usr/bin/env python3
import os, errno
import json
import sys
import logging
from fastkml import kml
from map_adapter import MapAdapter
from IPython.core.debugger import Tracer

OUTPUT_FOLDER = "./build/"

# Setups logger
logger = logging.getLogger(__name__)
logger_handler = logging.StreamHandler(sys.stdout)
logger_handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
logger_handler.setLevel(logging.DEBUG)
logger.addHandler(logger_handler)
logger.setLevel(logging.DEBUG)

def main():

    with open("surface.json") as f:    

        # Creates the output folder
        create_output_folder()

        # Reads data from the input file
        surface_data = json.load(f)
        items = surface_data["features"]

        # Generates airport data
        logger.debug("Generating airport metadata")
        generate_airport_data(items)
        logger.debug("Airport metadata generated")

        # Generates gate data
        logger.debug("Generating gate data")
        generate_gates_data(items)
        logger.debug("Gate data generated")

        # Generates spot position
        logger.debug("Generating spot position data")
        generate_spot_position_data()
        logger.debug("Spot position data generated")

        # Generates runway data
        logger.debug("Genenrating runway data")
        generate_line_data(items, "runway")
        logger.debug("Runway data generated")

        # Generates taxiway data
        logger.debug("Genenrating taxiway data")
        generate_line_data(items, "taxiway")
        logger.debug("Taxiway data generated")

def create_output_folder():
    try:
        os.makedirs(OUTPUT_FOLDER)
    except OSError as e:
        pass

def generate_airport_data(items):

    # Finds out the airport raw data from items
    airport_raw = None
    for item in items:
        if item["properties"]["aeroway"] == "aerodrome":
            airport_raw = item
            break
    if not airport_raw:
        raise Exception("Airport metadata is not found")

    map_adapter = MapAdapter()
    center = get_center(airport_raw["geometry"]["coordinates"][0])
    corners = map_adapter.center2corners(center)
    airport = {
        "name": airport_raw["properties"]["name"],
        "center": center,
        "corners": corners
    }

    # Export data to file
    filename = OUTPUT_FOLDER + "airport-metadata.json"
    export_to_json(filename, airport)

    # Downloads the map
    filename = OUTPUT_FOLDER + "airport.jpg"
    map_adapter.download(filename, center)

def get_center(coordinates):

    # NOTE: this won't work if the area across lat = 0 line

    most_west = coordinates[0][0]
    most_east = coordinates[0][0]
    most_north = coordinates[0][1]
    most_south = coordinates[0][1]

    for c in coordinates:
        most_west = min(most_west, c[0])
        most_east = max(most_east, c[0])
        most_north = max(most_north, c[1])
        most_south = min(most_south, c[1])

    # return {
        # "lat": 37.616324,
        # "lng": -122.385995
    # }
    return {
        "lat": (most_north + most_south) / 2,
        "lng": (most_west + most_east) / 2
    }

def generate_gates_data(items):

    nodes = []

    # Finds gate nodes
    for item in items:
        # Filters out other items
        if item["properties"]["aeroway"] != "gate":
            continue
        index = item["id"].split("/")[1]
        name = item["properties"]["ref"]
        lat = item["geometry"]["coordinates"][1]
        lng = item["geometry"]["coordinates"][0]
        nodes.append({ "index": index, "name": name, "lat": lat, "lng": lng })

    output_filename = OUTPUT_FOLDER + "gates.json"
    export_to_json(output_filename, nodes)

def generate_spot_position_data():

    # Create the KML object to store the parsed result
    k = kml.KML()
    nodes = []

    # Reads spot data from input KML file
    with open("spot.kml", "rb") as f:

        k.from_string(f.read())
        items = list(list(k.features())[0].features())

        for item in items:
            index, name = int(item.name[1:]), item.name
            lat, lng = item.geometry.y, item.geometry.x
            nodes.append({
                "index": index,
                "name": name,
                "lat": lat,
                "lng": lng
            })

    output_filename = OUTPUT_FOLDER + "spots.json"
    export_to_json(output_filename, nodes)

def generate_line_data(items, type_name):

    lines = []

    for item in items:

        # Filters out other items
        if item["properties"]["aeroway"] != type_name:
            continue

        # Retrieves the fields we want
        index = item["id"].split("/")[1]
        name = ""
        if "name" in item["properties"]:
            name = item["properties"]["name"]
        elif "ref" in item["properties"]:
            name = item["properties"]["ref"]
        nodes = item["geometry"]["coordinates"]

        # Puts to the buffer and will export to file later
        lines.append({
            "index": index,
            "name": name,
            "nodes": nodes
        })

    # Add s for plural as the output filename
    output_filename = OUTPUT_FOLDER + type_name + "s.json"
    export_to_json(output_filename, lines)

def export_to_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f)

if __name__ == "__main__":
    main()