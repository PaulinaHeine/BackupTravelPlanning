import sys
import pandas as pd
import heapq
from collections import defaultdict
from datetime import datetime
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


# Hilfsfunktion: Wochentag abrufen
def get_weekday(date):
    weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    return weekdays[date.weekday()]


# Prüft, ob ein Service an einem bestimmten Datum verfügbar ist
def is_service_available(service_id, date, calendar, calendar_dates):
    date_str = date.strftime("%Y%m%d")
    weekday = get_weekday(date)

    # Prüfe Ausnahmen in calendar_dates # TODO
    # TODO late evening start

    # Prüfe reguläre Dienste in calendar
    if service_id in calendar.index:
        service = calendar.loc[service_id]
        if service["start_date"] <= int(date_str) <= service["end_date"]:
            if service[weekday] == 1:
                return True  # 1 = Dienst ist an diesem Wochentag aktiv
            elif service[weekday] == 0:
                return False



# Passe die calendar_dates-Daten für Mehrfacheinträge an
def prepare_calendar_dates(calendar_dates):
    grouped = calendar_dates.groupby("service_id")
    calendar_dates_dict = {}

    for service_id, group in grouped:
        exceptions = group.to_dict(orient="records")
        calendar_dates_dict[service_id] = exceptions

    return calendar_dates_dict


# Erstelle einen Graphen basierend auf den GTFS-Daten und Verfügbarkeit
def create_graph_with_schedule(stop_times, stops, trips, calendar, calendar_dates, date):
    # TODO check if arival time < start time + time budget
    graph = defaultdict(list)
    stop_id_to_name = stops.set_index("stop_id")["stop_name"].to_dict()

    trip_id_to_service = trips.set_index("trip_id")["service_id"].to_dict()
    trip_id_to_route = trips.set_index("trip_id")["route_id"].to_dict()

    # Bereite die calendar_dates-Daten vor
    calendar_dates = prepare_calendar_dates(calendar_dates)

    # Sortiere stop_times nach Trip und Stop-Sequence
    stop_times = stop_times.sort_values(by=["trip_id", "stop_sequence"])
    grouped = stop_times.groupby("trip_id")

    for trip_id, group in grouped:
        service_id = trip_id_to_service[trip_id]

        # Prüfe, ob der Service an diesem Datum verfügbar ist
        if is_service_available(service_id, date, calendar, calendar_dates):
            continue

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
                route_id = trip_id_to_route[trip_id]  # Hole die Route/Linie

                graph[start_stop_name].append((end_stop_name, start_departure, end_arrival, route_id))

    return graph


# Dijkstra-Algorithmus für den kürzesten Weg mit Startzeit
def dijkstra_with_time(graph, start_name, end_name, start_time_minutes):
    pq = [(start_time_minutes, start_name, [])]  # (Abfahrtszeit, aktueller Knoten, Pfad)
    visited = set()

    while pq:
        current_time, current_stop, path = heapq.heappop(pq)

        if (current_stop, current_time) in visited:
            continue
        visited.add((current_stop, current_time))

        path = path + [(current_stop, current_time)]

        if current_stop == end_name:
            return current_time, path

        for neighbor, departure_time, arrival_time, route_id in graph[current_stop]:
            # Berücksichtige nur Verbindungen nach der aktuellen Zeit
            if departure_time >= current_time:
                heapq.heappush(pq, (arrival_time, neighbor, path + [(route_id, departure_time, arrival_time)]))

    return float("inf"), []


# Hauptprogramm
if __name__ == "__main__":
    # Benutzereingabe
    start_stop_name = "Schattendorf Kirchengasse"
    end_stop_name = "Bad Sauerbrunn Bahnhof"
    start_datetime = "2024-10-16 14:30:00"

    # Lade die GTFS-Daten
    agency, stops, routes, trips, stop_times, calendar, calendar_dates = import_data()

    # Umwandlung der Startzeit in Minuten
    start_time_obj = datetime.strptime(start_datetime, "%Y-%m-%d %H:%M:%S")
    start_time_minutes = start_time_obj.hour * 60 + start_time_obj.minute

    # Erstelle den Graphen für das angegebene Datum
    graph = create_graph_with_schedule(stop_times, stops, trips, calendar, calendar_dates, start_time_obj)

    # Überprüfen, ob Haltestellen existieren
    if start_stop_name not in graph or end_stop_name not in graph:
        print("Ungültige Start- oder Zielhaltestelle!")
        sys.exit()

    # Finde den kürzesten Weg basierend auf der Startzeit
    arrival_time_minutes, path = dijkstra_with_time(graph, start_stop_name, end_stop_name, start_time_minutes)

    if arrival_time_minutes < float("inf"):
        arrival_time = minutes_to_time(arrival_time_minutes)
        print(f"Shortest path from {start_stop_name} to {end_stop_name}:")

        # Ausgabe des vollständigen Weges mit Linie und Zeiten
        for i in range(0, len(path) - 2, 2):
            current_stop, current_time = path[i]
            route_id, departure_time, arrival_time = path[i + 1]
            next_stop, _ = path[i + 2]
            print(
                f"  • {current_stop} (Departure: {minutes_to_time(departure_time)}) "
                f"--> {next_stop} with line {route_id} (Arrival: {minutes_to_time(arrival_time)})"
            )
        print(f"Endstation: {end_stop_name} (Arrival: {minutes_to_time(arrival_time)} o'clock)")
    else:
        print(f"No way found from {start_stop_name} to {end_stop_name}, sorry.")

