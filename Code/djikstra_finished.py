import sys
import pandas as pd
import heapq
from collections import defaultdict
from datetime import datetime
from scipy.stats import norm
from Code.import_data import import_data
from scipy.stats import gamma
import numpy as np

# Hilfsfunktion: Zeit in Minuten umwandeln
def time_to_minutes(time_str):
    hours, minutes, seconds = map(int, time_str.split(":"))
    return hours * 60 + minutes + seconds / 60

def minutes_to_time(minutes):
    hours = int(minutes // 60)
    minutes = int(minutes % 60)
    return f"{hours:02d}:{minutes:02d}"

def get_weekday(date):
    weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    return weekdays[date.weekday()]

def is_service_available(service_id, date, calendar, calendar_dates):
    date_str = date.strftime("%Y%m%d")
    weekday = get_weekday(date)
    if service_id in calendar_dates:
        exceptions = calendar_dates[service_id]
        for exception in exceptions:
            if exception["date"] == date_str:
                if exception["exception_type"] == 2: #added
                    return True
                elif exception["exception_type"] == 1: #reduced
                    return False
    if service_id in calendar.index:
        service = calendar.loc[service_id]
        if service["start_date"] <= int(date_str) <= service["end_date"]:
            if service[weekday] == 1: # workiung
                return True
            elif service[weekday] == 0: #not working
                return False

def prepare_calendar_dates(calendar_dates):
    grouped = calendar_dates.groupby("service_id")
    calendar_dates_dict = {}
    for service_id, group in grouped:
        exceptions = group.to_dict(orient="records")
        calendar_dates_dict[service_id] = exceptions
    return calendar_dates_dict

def create_graph_with_schedule(stop_times, stops, trips, calendar, calendar_dates, date):
    graph = defaultdict(list)
    stop_id_to_name = stops.set_index("stop_id")["stop_name"].to_dict()
    trip_id_to_service = trips.set_index("trip_id")["service_id"].to_dict()
    trip_id_to_route = trips.set_index("trip_id")["route_id"].to_dict()
    calendar_dates = prepare_calendar_dates(calendar_dates)
    stop_times = stop_times.sort_values(by=["trip_id", "stop_sequence"])
    grouped = stop_times.groupby("trip_id")
    for trip_id, group in grouped:
        service_id = trip_id_to_service[trip_id]
        if is_service_available(service_id, date, calendar, calendar_dates): # TODO CHECK
            continue
        stops_in_trip = group["stop_id"].tolist()
        arrival_times = group["arrival_time"].tolist()
        departure_times = group["departure_time"].tolist()
        for i in range(len(stops_in_trip) - 1):
            start_stop_id = stops_in_trip[i]
            end_stop_id = stops_in_trip[i + 1]
            start_departure = time_to_minutes(departure_times[i])
            end_arrival = time_to_minutes(arrival_times[i + 1])
            travel_time = end_arrival - start_departure
            if travel_time > 0:
                start_stop_name = stop_id_to_name[start_stop_id]
                end_stop_name = stop_id_to_name[end_stop_id]
                route_id = trip_id_to_route[trip_id]
                graph[start_stop_name].append((end_stop_name, start_departure, end_arrival, route_id))
    return graph


######



def convert_itinerary_for_transfer(itinerary):
    """
    Konvertiert ein Dijkstra-Itinerary in ein passendes Format für Transferberechnungen.

    Parameters:
        itinerary (list of tuples): Pfad mit Haltestellen, Zeiten und Routen.

    Returns:
        list of tuples: Konvertiertes Itinerary mit Start/Ende, Zeiten und Routen-IDs.
    """
    converted = []
    for i in range(len(itinerary)):
        if i % 2 == 0:  # Haltestelle
            stop_name = itinerary[i][0]
            #current_time = itinerary[i][1]
        if i % 2 != 0:
            route_id = itinerary[i][0]
            dep_time = itinerary[i][1]
            arr_time = itinerary[i][2]


            converted.append([stop_name, route_id, dep_time, arr_time])

    return converted


def is_transfer(i, itinerary):
    """
    Berechnet die Transferwahrscheinlichkeit für ein Itinerary, falls ein Transfer stattfindet.

    Parameters:
        itinerary (list of tuples): Liste der Reiseabschnitte (Legs) mit Ankunfts- und Abfahrtszeiten.

    Returns:
        float: Wahrscheinlichkeit des Transfers.
    """
    if len(itinerary) < 2:
        return 1.0  # Kein Transfer notwendig bei einem einzelnen Leg

    prev_leg = itinerary[i][1]
    next_leg = itinerary[i+1][1]
    if prev_leg != next_leg:
        return True  # transfer


# (1) und (2)
def transfer_probability_with_delays(itinerary, arrival_time, departure_time, delay_distribution = gamma(a=2, scale=1.5, random_seed = 42)):
    """
    Berechnet die Transferwahrscheinlichkeit unter Berücksichtigung von Verzögerungen
    sowohl bei Ankunft als auch bei Abfahrt.

    Parameters:
        arrival_time (float): Planmäßige Ankunftszeit des vorherigen Beins.
        departure_time (float): Planmäßige Abfahrtszeit des nächsten Beins.
        delay_distribution (scipy.stats distribution): Verteilung der Verzögerungen.

    Returns:
        float: Wahrscheinlichkeit für einen erfolgreichen Transfer.
    """

    # Simuliere Verzögerungen für Ankunft und Abfahrt
    arrival_delay = round(delay_distribution.rvs(random_state = 20))
    departure_delay = round(delay_distribution.rvs(random_state = 3))

    # Berechne effektive Ankunfts- und Abfahrtszeiten
    effective_arrival_time = arrival_time + arrival_delay
    effective_departure_time = departure_time + departure_delay

    # Berechne den Zeitabstand
    time_difference = effective_departure_time - effective_arrival_time

    # Berechne die Wahrscheinlichkeit basierend auf dem Zeitabstand
    # Maximalwert auf 1 beschränken, Minimalwert bei 0
    if time_difference > 0:
        #return min(1.0, time_difference / 10)  # Skalierung: Dividiert durch 10 (anpassbar)
        probability = norm.cdf(time_difference, loc=1, scale=2)
        return min(1.0, probability)  # Maximalwert auf 1 beschränken

    else:
        return 0.0  # Transfer nicht möglich

# TODO speak to denis, random seed route id



def transfer_probability(itinerary):
    #itinerary = convert_itinerary_for_transfer(itinerary)
    prob = 1
    for i in range(len(itinerary)-1):
        p = is_transfer(i, itinerary)
        if p == False:
            prob *= 1
        elif p == True:
            arrival_time = itinerary[i][3]
            departure_time = itinerary[i+1][2]
            prob *= transfer_probability_with_delays(arrival_time, departure_time, delay_distribution = gamma(a=2, scale=1.5))
        return prob



'''
# Beispiel
if __name__ == "__main__":
    # Gamma-Verteilung für Verzögerungen
    delay_distribution = gamma(a=2, scale=1.5)  # Formparameter = 2, Skalenparameter = 1.5

    # Planmäßige Zeiten
    arrival_time = 12  # Planmäßige Ankunftszeit
    departure_time = 14  # Planmäßige Abfahrtszeit

    # Berechne Transferwahrscheinlichkeit
    transfer_prob = transfer_probability_with_delays(arrival_time, departure_time, delay_distribution)
    print(f"Transfer Probability with Delays: {transfer_prob}")









def compute_transfer_probability_with_departure_delay(scheduled_arrival, scheduled_departure):
    mean_arrival_delay = 3
    std_dev_arrival = 1
    mean_departure_delay = 2
    std_dev_departure = 1
    mu_arrival = scheduled_arrival + mean_arrival_delay
    mu_departure = scheduled_departure + mean_departure_delay
    std_dev_diff = (std_dev_arrival**2 + std_dev_departure**2) ** 0.5
    return norm.cdf(0, loc=mu_departure - mu_arrival, scale=std_dev_diff)
'''


def dijkstra_with_reliability_fixed(graph, start_name, end_name, start_time_minutes, time_budget_minutes):
    pq = [(start_time_minutes, start_name, [], 1.0, None)]
    visited = set()
    while pq:
        current_time, current_stop, path, reliability, last_route = heapq.heappop(pq)
        if (current_stop, current_time) in visited:
            continue
        visited.add((current_stop, current_time))
        path = path + [(current_stop, current_time)]
        if current_time - start_time_minutes > time_budget_minutes:
            continue  # Prune Lösungen, die über dem Zeitbudget liegen
        for neighbor, departure_time, arrival_time, route_id in graph[current_stop]:
            if departure_time >= current_time:
                transfer_reliability = 1.0 if last_route == route_id else compute_transfer_probability_with_departure_delay(arrival_time, departure_time)
                new_current_time = arrival_time
                new_reliability = reliability * transfer_reliability
                heapq.heappush(pq, (new_current_time, neighbor, path + [(route_id, departure_time, arrival_time)], new_reliability, route_id))
        if current_stop == end_name:
            return current_time, path, reliability
    return float("inf"), [], 0.0

if __name__ == "__main__":
    start_stop_name = "Schattendorf Kirchengasse"
    #start_stop_name ="Klagenfurt Hauptbahnhof"
    end_stop_name = "Flughafen Wien Bahnhof"
    #end_stop_name = "Villach Hauptbahnhof"
    start_datetime = "2024-10-16 14:30:00"

    time_budget = "6:30"
    time_budget_hours, time_budget_minutes = map(int, time_budget.split(":"))
    time_budget_minutes = time_budget_hours * 60 + time_budget_minutes / 60

    agency, stops, routes, trips, stop_times, calendar, calendar_dates = import_data()
    start_time_obj = datetime.strptime(start_datetime, "%Y-%m-%d %H:%M:%S")
    start_time_minutes = start_time_obj.hour * 60 + start_time_obj.minute
    graph = create_graph_with_schedule(stop_times, stops, trips, calendar, calendar_dates, start_time_obj)
    if start_stop_name not in graph or end_stop_name not in graph:
        print("🚨 Ungültige Start- oder Zielhaltestelle!")
        sys.exit()
    arrival_time_minutes_fixed, path_fixed, reliability_fixed = dijkstra_with_reliability_fixed(
        graph, start_stop_name, end_stop_name, start_time_minutes, time_budget_minutes
    )
    # Ergebnis anzeigen
    if arrival_time_minutes_fixed < float("inf"):
        arrival_time_fixed = minutes_to_time(arrival_time_minutes_fixed)
        print(f"\n📍 Optimierte zuverlässigste Route von {start_stop_name} nach {end_stop_name}:")

        last_route = None
        grouped_routes = []

        for i in range(1, len(path_fixed) - 1, 2):
            current_stop, current_time = path_fixed[i - 1]
            route_id, departure_time, arrival_time = path_fixed[i]
            next_stop, _ = path_fixed[i + 1]

            if route_id == last_route:
                grouped_routes[-1]["stops"].append((next_stop, arrival_time))
            else:
                grouped_routes.append({
                    "route_id": route_id,
                    "start_stop": current_stop,
                    "departure_time": departure_time,
                    "stops": [(next_stop, arrival_time)]
                })
            last_route = route_id

        for segment in grouped_routes:
            start = segment["start_stop"]
            dep_time = minutes_to_time(segment["departure_time"])
            route = segment["route_id"]
            stops = " → ".join([f"{stop} (Ankunft: {minutes_to_time(arr)})" for stop, arr in segment["stops"]])
            print(f"  🚆 {start} (Abfahrt: {dep_time}) → {stops} mit Linie {route}")

        print(f"\n🎯 Endstation: {end_stop_name} (Ankunft: {arrival_time_fixed})")
        print(f"🔹 Gesamt-Zuverlässigkeit der Route: {reliability_fixed:.2f}\n")
    else:
        print(f"\n⚠️ Keine zuverlässige Route von {start_stop_name} nach {end_stop_name} gefunden.\n")


