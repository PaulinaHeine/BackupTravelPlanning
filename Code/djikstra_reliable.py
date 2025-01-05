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

    # 🔹 1️⃣ Prüfe zuerst `calendar_dates` (Ausnahmen & extra Dienste)
    if service_id in calendar_dates:
        exceptions = calendar_dates[service_id]
        for exception in exceptions:
            if exception["date"] == date_str:
                if exception["exception_type"] == 2:  # 🚀 Linie fährt EXTRA
                    return True
                elif exception["exception_type"] == 1:  # ❌ Linie fällt aus
                    return False

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



# we dont have empirical data about delays from ÖBB, so we use an exponential function to describe it
    # 📌 **Definiere die Arrival Distribution für Ankunftszeiten**
def arrival_distribution(time):
    """
    Beispielhafte Wahrscheinlichkeitsverteilung für Ankunftszeiten.
    Modelliert die Wahrscheinlichkeit, dass ein Transportmittel pünktlich ankommt.
    """
    return max(1 - np.exp(-0.1 * (time - 5)), 0.1)  # Minimum 10% Chance


def compute_reliability(arrival_distribution, departure_time):
    """
    Berechnet die Zuverlässigkeit eines einzelnen Segments gemäß Paper-Formel:

    R_g = P(Y_arr_g ≤ τ_dep_h) * (1 - P(Y_arr_g > τ_dep_h))

    :param arrival_distribution: Funktion für die Ankunftswahrscheinlichkeit
    :param departure_time: Zeitpunkt der geplanten Abfahrt vom Transferpunkt
    :return: Reliability-Wert für dieses Segment
    """


    prob_arrival_on_time = arrival_distribution(departure_time)
    missed_transfer_prob = 1 - prob_arrival_on_time  # P(Y_arr_g > τ_dep_h)

    return prob_arrival_on_time * (1 - missed_transfer_prob)



def calculate_itinerary_reliability(itinerary, arrival_distribution):
    """
    Berechnet die Gesamt-Reliability einer Route gemäß Paper-Formel.

    :param itinerary: Liste von Teilstrecken [(Start, Ziel, Abfahrtszeit, Ankunftszeit)]
    :param arrival_distribution: Funktion für Ankunftswahrscheinlichkeit
    :return: Gesamt-Reliability der Route (zwischen 0 und 1)
    """
    reliability = 1.0  # Starte mit 100%

    for i in range(len(itinerary) - 1):
        _, _, dep_time, _ = itinerary[i]
        segment_reliability = compute_reliability(arrival_distribution, dep_time)
        reliability *= segment_reliability  # Multipliziere für Gesamtzuverlässigkeit

    return reliability



def calculate_missed_transfer_probability(departure_time, arrival_distribution):
    """
    Berechnet die Wahrscheinlichkeit, dass ein Transfer verpasst wird, gemäß Paper-Formel:
    P(Y_arr_g > τ_dep_h) = 1 - P(Y_arr_g ≤ τ_dep_h)

    :param departure_time: Zeitpunkt der geplanten Abfahrt vom Transferpunkt
    :param arrival_distribution: Funktion, die die Ankunftszeit-Wahrscheinlichkeit zurückgibt
    :return: Wahrscheinlichkeit, dass der Transfer verpasst wird
    """
    return 1 - arrival_distribution(departure_time)


def calculate_missed_transfer_probs(graph, arrival_distribution):
    """
    Berechnet die Wahrscheinlichkeit für verpasste Transfers gemäß der Formel:
    P(Y_arr_g > τ_dep_h) = 1 - P(Y_arr_g ≤ τ_dep_h)

    :param graph: Der Graph mit allen Haltestellen und Verbindungen.
    :param arrival_distribution: Funktion, die die Wahrscheinlichkeit einer pünktlichen Ankunft berechnet.
    :return: Dictionary mit { (stop, neighbor): missed_transfer_prob }
    """
    missed_transfer_probs = {}
    for stop in graph:
        for neighbor, departure_time, arrival_time, route_id in graph[stop]:
            missed_transfer_probs[(stop, neighbor)] = 1 - arrival_distribution(departure_time)
    return missed_transfer_probs

def dijkstra_with_reliability(graph, start_name, end_name, start_time_minutes, arrival_distribution):
    """Dijkstra-Algorithmus zur Suche der zuverlässigsten Route basierend auf Zeit."""
    pq = [(start_time_minutes, start_name, [], 1.0)]  # (Abfahrtszeit, aktueller Knoten, Pfad, Reliability)
    visited = set()

    while pq:
        current_time, current_stop, path, reliability = heapq.heappop(pq)

        if (current_stop, current_time) in visited:
            continue
        visited.add((current_stop, current_time))

        path = path + [(current_stop, current_time)]
        for neighbor, departure_time, arrival_time, route_id in graph[current_stop]:
            if departure_time >= current_time:


                rel = compute_reliability(arrival_distribution, departure_time)
                heapq.heappush(pq, (
                arrival_time, neighbor, path + [(route_id, departure_time, arrival_time)], reliability * rel))

        if current_stop == end_name:
            return current_time, path, reliability



    return float("inf"), [], 0.0


def find_best_reliable_itinerary(graph, start_name, end_name, start_time_minutes, arrival_distribution,
                                 missed_transfer_probs):
    """Findet die zuverlässigste Route unter Berücksichtigung der Zeit und Reliability."""
    arrival_time, path, reliability = dijkstra_with_reliability(graph, start_name, end_name, start_time_minutes,
                                                                arrival_distribution, missed_transfer_probs)

    if arrival_time < float("inf"):
        return {
            "route": path,
            "arrival_time": arrival_time,
            "reliability": reliability
        }
    else:
        return None











import sys
import numpy as np

if __name__ == "__main__":
    # 🚆 **Benutzereingabe**
    start_stop_name = "Schattendorf Kirchengasse"
    end_stop_name = "Bad Sauerbrunn Bahnhof"
    start_datetime = "2024-10-16 14:30:00"

    # 🔹 Lade die GTFS-Daten
    agency, stops, routes, trips, stop_times, calendar, calendar_dates = import_data()

    # 🔹 Umwandlung der Startzeit in Minuten
    start_time_obj = datetime.strptime(start_datetime, "%Y-%m-%d %H:%M:%S")
    start_time_minutes = start_time_obj.hour * 60 + start_time_obj.minute

    # 🔹 Erstelle den Graphen für das angegebene Datum
    graph = create_graph_with_schedule(stop_times, stops, trips, calendar, calendar_dates, start_time_obj)

    # 🔹 Überprüfen, ob Haltestellen existieren
    if start_stop_name not in graph or end_stop_name not in graph:
        print("🚨 Ungültige Start- oder Zielhaltestelle!")
        sys.exit()

    # 🔹 **Berechne die Transferwahrscheinlichkeiten mit der neuen Funktion**
    missed_transfer_probs = calculate_missed_transfer_probs(graph, arrival_distribution)

    # 🔹 **Finde den zuverlässigsten Weg mit Reliability-Berechnung**
    arrival_time_minutes, path, reliability = dijkstra_with_reliability(
        graph, start_stop_name, end_stop_name, start_time_minutes, arrival_distribution
    )

    # 📌 **Ergebnis ausgeben**
    if arrival_time_minutes < float("inf"):
        arrival_time = minutes_to_time(arrival_time_minutes)
        print(f"\n📍 Zuverlässigste Route von {start_stop_name} nach {end_stop_name}:")

        for i in range(0, len(path) - 2, 2):
            current_stop, current_time = path[i]
            route_id, departure_time, arrival_time = path[i + 1]
            next_stop, _ = path[i + 2]

            print(f"  🚆 {current_stop} (Abfahrt: {minutes_to_time(departure_time)}) → {next_stop} mit Linie {route_id} (Ankunft: {minutes_to_time(arrival_time)})")

        print(f"\n🎯 Endstation: {end_stop_name} (Ankunft: {minutes_to_time(arrival_time)})")
        print(f"🔹 Gesamt-Zuverlässigkeit der Route: {reliability:.2f}\n")
    else:
        print(f"\n⚠️ Keine zuverlässige Route von {start_stop_name} nach {end_stop_name} gefunden.\n")

