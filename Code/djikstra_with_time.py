import pandas as pd
import heapq
from collections import defaultdict
from datetime import datetime, timedelta
from Code.import_data import import_data


# Hilfsfunktion: Zeit in Minuten umwandeln
def time_to_minutes(time_str):
    hours, minutes, seconds = map(int, time_str.split(":"))
    return hours * 60 + minutes + seconds / 60


# Hilfsfunktion: Minuten in Zeit umwandeln
def minutes_to_time(minutes):
    hours = int(minutes // 60)
    minutes = int(minutes % 60)
    return f"{hours:02d}:{minutes:02d}"


# Lade die GTFS-Daten
def load_gtfs_data(stops_file, stop_times_file, trips_file):
    stops = pd.read_csv(stops_file)
    stop_times = pd.read_csv(stop_times_file)
    trips = pd.read_csv(trips_file)
    return stops, stop_times, trips


# Erstelle einen Graphen basierend auf den GTFS-Daten und Abfahrtszeiten
def create_graph_with_schedule(stop_times, stops):
    graph = defaultdict(list)
    stop_id_to_name = stops.set_index("stop_id")["stop_name"].to_dict()
    stop_name_to_id = {v: k for k, v in stop_id_to_name.items()}

    # Sortiere stop_times nach Trip und Stop-Sequence
    stop_times = stop_times.sort_values(by=["trip_id", "stop_sequence"])
    grouped = stop_times.groupby("trip_id")

    for _, group in grouped:
        stops_in_trip = group["stop_id"].tolist()
        arrival_times = group["arrival_time"].tolist()
        departure_times = group["departure_time"].tolist()

        # Füge Verbindungen zwischen aufeinanderfolgenden Haltestellen hinzu
        for i in range(len(stops_in_trip) - 1):
            start_stop_id = stops_in_trip[i]
            end_stop_id = stops_in_trip[i + 1]

            start_departure = time_to_minutes(departure_times[i])
            end_arrival = time_to_minutes(arrival_times[i + 1])

            travel_time = end_arrival - start_departure  # Dauer in Minuten

            if travel_time > 0:  # Vermeide ungültige Zeiten
                start_stop_name = stop_id_to_name[start_stop_id]
                end_stop_name = stop_id_to_name[end_stop_id]
                graph[start_stop_name].append((end_stop_name, start_departure, end_arrival))

    return graph, stop_name_to_id, stop_id_to_name


# Dijkstra-Algorithmus für den kürzesten Weg mit Startzeit
def dijkstra_with_time(graph, start_name, end_name, start_time_minutes):
    pq = [(start_time_minutes, start_name, [])]  # (Abfahrtszeit, aktueller Knoten, Pfad)
    visited = set()

    while pq:
        current_time, current_stop, path = heapq.heappop(pq)

        if (current_stop, current_time) in visited:
            continue
        visited.add((current_stop, current_time))

        path = path + [current_stop]

        if current_stop == end_name:
            return current_time, path

        for neighbor, departure_time, arrival_time in graph[current_stop]:
            # Berücksichtige nur Verbindungen nach der aktuellen Zeit
            if departure_time >= current_time:
                heapq.heappush(pq, (arrival_time, neighbor, path))

    return float("inf"), []


# Hauptprogramm
if __name__ == "__main__":
    # Benutzereingabe
    start_stop_name = "Schattendorf Kirchengasse"  #input("Geben Sie den Namen der Start-Haltestelle ein: ")
    end_stop_name =  "Baumgarten im Bgld Florianiplatz" #input("Geben Sie den Namen der Ziel-Haltestelle ein: ")
    start_datetime =  "2024-10-20 14:30:00" #input("Geben Sie die Startzeit ein (Format: YYYY-MM-DD HH:MM:SS): ")

    # Lade die GTFS-Daten
    agency, stops, routes, trips, stop_times, calendar, calendar_dates = import_data()
    graph, stop_name_to_id, stop_id_to_name = create_graph_with_schedule(stop_times, stops)

    # Überprüfen, ob Haltestellen existieren
    if start_stop_name not in graph or end_stop_name not in graph:
        print("Ungültige Start- oder Zielhaltestelle!")
        exit()

    # Umwandlung der Startzeit in Minuten
    start_time_obj = datetime.strptime(start_datetime, "%Y-%m-%d %H:%M:%S")
    start_time_minutes = start_time_obj.hour * 60 + start_time_obj.minute

    # Finde den kürzesten Weg basierend auf der Startzeit
    arrival_time_minutes, path = dijkstra_with_time(graph, start_stop_name, end_stop_name, start_time_minutes)

    if arrival_time_minutes < float("inf"):
        arrival_time = minutes_to_time(arrival_time_minutes)
        print(f"Kürzester Weg von {start_stop_name} nach {end_stop_name}: {path}")
        print(f"Ankunftszeit: {arrival_time} Uhr")
    else:
        print(f"Kein Weg von {start_stop_name} nach {end_stop_name} gefunden.")

