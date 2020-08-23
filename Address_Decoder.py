import googlemaps
import networkx as nx
import pandas as pd
import matplotlib.pyplot as plt
import itertools
import regex as re


def is_coordinate(address):

    return re.search("^[\d., ]+$", address)


def is_hebrew(address):
    return any("\u0590" <= c <= "\u05EA" for c in address)

with open("token.txt") as f:
	    token = f.read().strip()
gmaps = googlemaps.Client(key=token)

# CSV reading and filtering #
print("Reading Address CSV..")
all_cols = ["ID", "Address"]
appendix_a = pd.read_csv('./Addresses.csv', sep=',',
                         index_col=0, encoding="UTF-8")

# Dropping duplicates and saving to a new filtered CSV #
print("Dropping duplicate addresses..")
unique_addresses = appendix_a["Address"].drop_duplicates()
unique_addresses.to_csv("./unique_addresses.csv", sep=',', index_label="ID")
unique = pd.read_csv('./unique_addresses.csv', sep=',', index_col=0)

##########################################################

# Address parsing and processing						 #
addresses = []

#Locate the nearest and furthest waypoints to TLV for optimization #
min_distance_tlv= float("inf")
min_address = ""
max_distance_tlv = float("-inf")
max_address = ""

print("Gathering addresses..")

for index, row in unique.iterrows():
    # Decoding hebrew addresses to avoid messy parsing #
    address = row['Address'].encode('UTF-8').decode('UTF-8')
    if(is_hebrew(address)):
        address = address[::-1]
    # gmaps doesn't handle slashes very well
    address = address.split('/', 1)[0]

    # If address is not a coordinate
    if(not is_coordinate(address)):
        try:
            geocode = gmaps.geocode(address, language="en")[0]
        except:
            print("Invalid address {}. Ignored!".format(address))
            continue
            
        address = geocode["formatted_address"]
        dist_tlv = gmaps.distance_matrix("Tel Aviv", address)
        elements = (dist_tlv.get('rows')[0]).get('elements')[0]
        distance = elements.get('distance').get('value')

        if(distance < min_distance_tlv):
            min_distance_tlv = distance
            min_address = geocode["formatted_address"]

        if(distance > max_distance_tlv):
            max_distance_tlv = distance
            max_address = geocode["formatted_address"]

        res = address

    # If address is a coordinate.
    else:
        # print(address)
        coordinates = address.replace(" ", "").split(",")
        result = gmaps.reverse_geocode(coordinates)

        if(result == []):
            continue

        res = result[0]["formatted_address"]
        dist_tlv = gmaps.distance_matrix("Tel Aviv", res)
        elements = (dist_tlv.get('rows')[0]).get('elements')[0]
        distance = elements.get('distance').get('value')
        if(distance < min_distance_tlv):
            min_distance_tlv = distance
            min_address = res

        if(distance > max_distance_tlv):
            max_distance_tlv = distance
            max_address = res

    addresses.append(res)

# Concatenate all addresses to a list for directions
# Don't include the min and max addreses in waypoints
addresses.remove(max_address)
addresses.remove(min_address)

###########################################################################

# Find the optimized route using google-maps, from the max point to the min point (finish closest to tel aviv)
print("Finding final route..")
optimized_route = gmaps.directions(
    max_address, min_address, waypoints=addresses, optimize_waypoints=True)[0]["waypoint_order"]
final_route = [max_address]
for num in optimized_route:
    final_route.append(addresses[num])
final_route.append(min_address)
formatted_route = []
for route in final_route:
    geocode = gmaps.geocode(route, language="iw")[0]
    formatted_route.append(geocode["formatted_address"])

# Put in dataframe and export to csv for spreadsheets
df = pd.DataFrame(formatted_route, columns=["Address"])
df.index.name = "ID"
print("Exporting to spreadsheet..")
csv_data = df.to_csv("./sorted_route.csv", index=True)

print("Done!")
