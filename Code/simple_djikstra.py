import networkx as nx
import pandas as pd
from Code.import_data import import_data, adjust_time_to_next_day

agency_df, stops_df, routes_df, trips_df, stop_times_df, calendar_df = import_data()

stop_times_df['adjusted_arrival_time'] = stop_times_df['arrival_time'].apply(lambda t: adjust_time_to_next_day(t)[0])
stop_times_df['adjusted_departure_time'] = stop_times_df['departure_time'].apply(lambda t: adjust_time_to_next_day(t)[0])


# Initialisiere den Graphen
G = nx.DiGraph()

# Iteriere über jede Fahrt (trip_id), um die Verbindung zwischen Stopps zu finden
for trip_id in stop_times_df['trip_id'].unique():
    trip_stops = stop_times_df[stop_times_df['trip_id'] == trip_id].sort_values('stop_sequence')

    for i in range(len(trip_stops) - 1):
        start_stop = trip_stops.iloc[i]
        end_stop = trip_stops.iloc[i + 1]

        # Berechne die Fahrzeit zwischen den Stopps
        start_time = pd.to_datetime(start_stop['departure_time'], format='%H:%M:%S')
        end_time = pd.to_datetime(end_stop['arrival_time'], format='%H:%M:%S')
        if start_time < end_time: # start: 10.00 end time: 12.00
            travel_time = (end_time - start_time).seconds
        if end_time < start_time:# end: 1.00 start 23:00
            travel_time = (end_time - start_time).seconds #switch

        # Füge die Kante dem Graphen hinzu
        G.add_edge(start_stop['stop_id'], end_stop['stop_id'], weight=travel_time)
# Funktion zum Finden des kürzesten Pfads zwischen zwei Haltestellen
def find_shortest_path(graph, start_stop_id, end_stop_id):
    try:
        path = nx.dijkstra_path(graph, start_stop_id, end_stop_id, weight='weight')
        path_length = nx.dijkstra_path_length(graph, start_stop_id, end_stop_id, weight='weight')
        return path, path_length
    except nx.NetworkXNoPath:
        return None, float('inf')

# Beispiel: Kürzester Weg zwischen Praterstern (stop_id 2) und Stephansplatz (stop_id 4)
start_stop_id = 2
end_stop_id = 3
shortest_path, total_travel_time = find_shortest_path(G, start_stop_id, end_stop_id)

print("Shortest path:", shortest_path)
print("Total travel time (seconds):", total_travel_time)


# implement start time
