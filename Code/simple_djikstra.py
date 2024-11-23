
from Code.import_data import import_data
import heapq
from collections import defaultdict




# Hilfsfunktion: Zeit in Minuten umwandeln
def time_to_minutes(time_str):
    hours, minutes, seconds = map(int, time_str.split(":"))
    return hours * 60 + minutes + seconds / 60


# Lade die GTFS-Daten
agency, stops, routes, trips, stop_times, calendar = import_data()


# Erstelle einen Graphen basierend auf Fahrzeiten
def create_graph_with_travel_time(stop_times):
    graph = defaultdict(list)

    # Sortiere stop_times nach Trip und Stop-Sequence
    stop_times = stop_times.sort_values(by=["trip_id", "stop_sequence"])
    grouped = stop_times.groupby("trip_id")

    for _, group in grouped:
        stops = group["stop_id"].tolist()
        arrival_times = group["arrival_time"].tolist()
        departure_times = group["departure_time"].tolist()

        # Füge Verbindungen zwischen aufeinanderfolgenden Haltestellen hinzu
        for i in range(len(stops) - 1):
            start_stop = stops[i]
            end_stop = stops[i + 1]

            start_time = time_to_minutes(departure_times[i])
            end_time = time_to_minutes(arrival_times[i + 1])

            travel_time = end_time - start_time  # Dauer in Minuten

            if travel_time > 0:  # Vermeide negative oder ungültige Zeiten
                graph[start_stop].append((end_stop, travel_time))

    return graph


# Dijkstra-Algorithmus für den kürzesten Weg
def dijkstra(graph, start, end):
    pq = [(0, start, [])]  # (Gesamtzeit, aktueller Knoten, Pfad)
    visited = set()

    while pq:
        total_time, current_stop, path = heapq.heappop(pq)

        if current_stop in visited:
            continue
        visited.add(current_stop)

        path = path + [current_stop]

        if current_stop == end:
            return total_time, path

        for neighbor, travel_time in graph[current_stop]:
            if neighbor not in visited:
                heapq.heappush(pq, (total_time + travel_time, neighbor, path))

    return float("inf"), []


# Hauptprogramm
if __name__ == "__main__":
    start_stop = "at:47:1172:0:1"  # "at:46:2065"  # Beispiel-Start-Haltestelle
    end_stop = "at:46:7423"  # Beispiel-Ziel-Haltestelle

    # Lade die GTFS-Daten
    agency, stops, routes, trips, stop_times, calendar = import_data()
    graph = create_graph_with_travel_time(stop_times)

    total_time, path = dijkstra(graph, start_stop, end_stop)
    if total_time < float("inf"):
        print(f"Kürzester Weg von {start_stop} nach {end_stop}: {path}")
        print(f"Gesamtfahrzeit: {total_time} Minuten")
    else:
        print(f"Kein Weg von {start_stop} nach {end_stop} gefunden.")
