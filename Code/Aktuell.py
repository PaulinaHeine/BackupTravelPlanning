
import sys
import scipy.stats as stats
import heapq
from collections import defaultdict

from scipy.stats import norm

from Code.import_data import import_data

from datetime import datetime, timedelta


# Hilfsfunktionen (unverändert)

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


'''
#fast and weird
def is_service_available(service_id, date, calendar, calendar_dates):
    date_str = date.strftime("%Y%m%d")
    weekday = get_weekday(date)
    if service_id in calendar_dates:
        exceptions = calendar_dates[service_id]
        for exception in exceptions:
            if exception["date"] == date_str:
                if exception["exception_type"] == 2:
                    return True
                elif exception["exception_type"] == 1:
                    return False
    if service_id in calendar.index:
        service = calendar.loc[service_id]
        if service["start_date"] <= int(date_str) <= service["end_date"]:
            if service[weekday] == 1:
                return True
            elif service[weekday] == 0:
                return False
'''


#correct and slow
def is_service_available(service_id, start_time_obj, calendar, calendar_dates):
    #date_str = date.strftime("%Y%m%d")
    #date = date.date()
    # Convert date to string in YYYYMMDD format
    date_str = start_time_obj.strftime("%Y%m%d")
    weekday = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][start_time_obj.weekday()]

    # Step 1: Check for exceptions in calendar_dates
    if service_id in calendar_dates["service_id"].values:
        exceptions = calendar_dates[calendar_dates["service_id"] == service_id]
        for _, exception in exceptions.iterrows():
            if exception["date"] == int(date_str):
                if exception["exception_type"] == 2:  # Service is added as an exception
                    return True
                elif exception["exception_type"] == 1:  # Service is removed as an exception
                    return False

    # Step 2: Check for regular service in calendar
    if service_id in calendar["service_id"].values:
        service = calendar[calendar["service_id"] == service_id]
        # Check if date is within start_date and end_date
        if int(service["start_date"].iloc[0]) <= int(date_str) <= int(service["end_date"].iloc[0]):
            # Check if the service operates on this weekday
            #is_available = (service[weekday].iloc[0] == 1)
            return True
    return False

def prepare_calendar_dates(calendar_dates):
    grouped = calendar_dates.groupby("service_id")
    calendar_dates_dict = {}
    for service_id, group in grouped:
        exceptions = group.to_dict(orient="records")
        calendar_dates_dict[service_id] = exceptions
    return calendar_dates_dict

######### Graph erstellen
#Fast and weird
'''

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
        if not is_service_available(service_id, date, calendar, calendar_dates):
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
'''
##correct and slow

def create_graph_with_schedule(stop_times, stops, trips, calendar, calendar_dates, date, time, end_time_obj):

    graph = defaultdict(list)
    stop_id_to_name = stops.set_index("stop_id")["stop_name"].to_dict()
    # Filter for active trips today using is_service
    trip_id_to_service = trips.set_index("trip_id")["service_id"].to_dict()
    trip_id_to_route = trips.set_index("trip_id")["route_id"].to_dict()

    calendar_dates_2 = prepare_calendar_dates(calendar_dates)
    stop_times = stop_times.sort_values(by=["trip_id", "stop_sequence"])

    #####
    #Filter
    #####

    stop_times_copy = stop_times.copy()
    # Filter out stops outside the time window
    stop_times_copy["arrival_minutes"] = stop_times_copy["arrival_time"].apply(time_to_minutes)
    stop_times_copy["departure_minutes"] = stop_times_copy["departure_time"].apply(time_to_minutes)

    start_minutes = time_to_minutes(start_time_obj.strftime("%H:%M:%S"))
    end_minutes = time_to_minutes(end_time_obj.strftime("%H:%M:%S"))

    stop_times = stop_times_copy[
        (stop_times_copy["arrival_minutes"] >= start_minutes) &
        (stop_times_copy["departure_minutes"] <= end_minutes)
        ]

    print(f"Rows after time window filter: {len(stop_times)}")


    #trip_id_to_service = trips.set_index("trip_id")["service_id"].to_dict()
    stop_times["service_id"] = stop_times["trip_id"].map(trip_id_to_service)

    grouped = stop_times.groupby("trip_id")
    for trip_id, group in grouped:
        service_id = trip_id_to_service[trip_id]
        if not is_service_available(service_id, start_time_obj, calendar, calendar_dates): # TODO CHECK
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
'''
#new try denis V1
def create_graph_with_schedule(stop_times, stops, trips, calendar, calendar_dates, date, time, end_time_obj):

    graph = defaultdict(list)
    stop_id_to_name = stops.set_index("stop_id")["stop_name"].to_dict()
    # Filter for active trips today using is_service
    trip_id_to_service = trips.set_index("trip_id")["service_id"].to_dict()
    trip_id_to_route = trips.set_index("trip_id")["route_id"].to_dict()

    calendar_dates_2 = prepare_calendar_dates(calendar_dates)
    stop_times = stop_times.sort_values(by=["trip_id", "stop_sequence"])

    #####
    #Filter
    #####

    stop_times_copy = stop_times.copy()
    # Filter out stops outside the time window
    stop_times_copy["arrival_minutes"] = stop_times_copy["arrival_time"].apply(time_to_minutes)
    stop_times_copy["departure_minutes"] = stop_times_copy["departure_time"].apply(time_to_minutes)

    start_minutes = time_to_minutes(start_time_obj.strftime("%H:%M:%S"))
    end_minutes = time_to_minutes(end_time_obj.strftime("%H:%M:%S"))

    stop_times = stop_times_copy[
        (stop_times_copy["arrival_minutes"] >= start_minutes) &
        (stop_times_copy["departure_minutes"] <= end_minutes)
        ]

    print(f"Rows after time window filter: {len(stop_times)}")


    # Precompute service availability
    trip_id_to_service = trips.set_index("trip_id")["service_id"].to_dict()
    # Ensure it's a new DataFrame, not a slice
    #stop_times["service_id"] = stop_times["trip_id"].map(trip_id_to_service)
    stop_times.loc[:, "service_id"] = stop_times["trip_id"].map(trip_id_to_service)

    unique_service_ids = stop_times["service_id"].dropna().unique()
    service_availability = {
        service_id: is_service_available(service_id, date, calendar, calendar_dates)
        for service_id in unique_service_ids
    }

    # Filter using precomputed availability
    # Use .map() with a default value directly to avoid NaN
    # Filter using precomputed availability
    stop_times = stop_times[
    stop_times["service_id"].map(lambda x: service_availability.get(x, False)).astype(bool)
    ]
    # TODO updated version

    # Sortiere stop_times nach Trip und Stop-Sequence
    stop_times = stop_times.sort_values(by=["trip_id", "stop_sequence"])
    grouped = stop_times.groupby("trip_id")


    grouped = stop_times.groupby("trip_id")
    for trip_id, group in grouped:
        service_id = trip_id_to_service[trip_id]
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
'''

'''
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

def compute_transfer_probability_with_departure_delay(transfer_time):
    #transfer_window = departure_time - scheduled_arrival
    #if transfer_window < 0:
    #    return 0.1  # No chance of a successful transfer if arrival is after departure
    return stats.gamma.cdf(transfer_time, a=2, scale=3)



# Dijkstra mit Backup-Routenberechnung
def dijkstra_with_reliability_fixed(graph, start_name, end_name, start_time_minutes, time_budget_minutes,
                                    exclude_routes=set()):
    pq = [(start_time_minutes, start_name, [], 1.0,
           None)]  # (aktuelle Zeit, aktuelle Haltestelle, Pfad, Zuverlässigkeit, letzte Linie)
    visited = set()
    MIN_TRANSFER_TIME = 5  # Mindestumstiegszeit in Minuten

    while pq:
        current_time, current_stop, path, reliability, last_route = heapq.heappop(pq)

        if (current_stop, current_time) in visited:
            continue
        visited.add((current_stop, current_time))

        path = path + [(current_stop, current_time)]

        if current_time - start_time_minutes > time_budget_minutes:
            continue  # Pruning: Abbruch, wenn Zeitbudget überschritten

        for neighbor, departure_time, arrival_time, route_id in graph[current_stop]:
            if departure_time >= current_time and route_id not in exclude_routes:
                # Prüfe, ob es ein Umstieg ist (Linienwechsel)
                is_transfer = last_route is not None and last_route != route_id
                if is_transfer:
                    # Mindestumstiegszeit von 5 Minuten nur bei Umstiegen
                    transfer_time = departure_time - current_time
                    if transfer_time < MIN_TRANSFER_TIME:
                        continue  # Pruning: Zu wenig Zeit für Umstieg

                # Berechne neue Zuverlässigkeit mit Transferwahrscheinlichkeit
                if not is_transfer:  # Keine Zuverlässigkeitsänderung bei gleicher Linie
                    transfer_reliability = 1.0
                else:
                    transfer_reliability = compute_transfer_probability_with_departure_delay(transfer_time)

                new_current_time = arrival_time
                new_reliability = reliability * transfer_reliability

                heapq.heappush(pq, (
                    new_current_time, neighbor, path + [(route_id, departure_time, arrival_time)], new_reliability,
                    route_id))

        if current_stop == end_name:
            return current_time, path, reliability

    return float("inf"), [], 0.0  # Keine Route gefunden


# Backup-Routen finden (Dijkstra an jeder Umstiegshaltestelle, ohne Primärroute)

'''
def find_backup_routes(djikstra_route, graph,)
    identify all the transfer points
    indicate the min reliablitity 
    check transfer time
    
    increase transfer time
    run djiksra with inreased transfer time (do this for every transfer point)
    calcultae backup reliability
    
    
go back to main
    calculate reliability of primary
'''



def find_backup_routes(graph, primary_path, start_time_minutes, time_budget_minutes):
    backup_routes = []
    used_routes = {segment[0] for segment in primary_path if isinstance(segment, tuple) and len(segment) == 3}

    for i in range(1, len(primary_path) - 1, 2):  # Alle Umstiegspunkte durchgehen
        transfer_stop, transfer_time = primary_path[i - 1]

        if transfer_stop in graph:
            backup_time, backup_path, backup_reliability = dijkstra_with_reliability_fixed(
                graph, transfer_stop, primary_path[-1][0], transfer_time, time_budget_minutes, used_routes
            )

            if backup_time < float("inf") and backup_path and backup_path != primary_path:
                alternative_path = []
                alternative_routes = set()

                for j in range(1, len(backup_path) - 1, 2):
                    stop1, time1 = backup_path[j - 1]
                    route, dep, arr = backup_path[j]
                    stop2, _ = backup_path[j + 1]

                    # **Kriterium für alternative Backup-Route:**
                    # - Die Route darf nicht exakt der Primärroute entsprechen.
                    # - Die Haltestellen dürfen wiederverwendet werden, aber nicht in identischen Abschnitten.
                    if route not in used_routes:
                        alternative_path.append((stop1, minutes_to_time(dep), stop2, minutes_to_time(arr), route))
                        alternative_routes.add(route)

                if alternative_path:
                    backup_routes.append((transfer_stop, alternative_path, backup_reliability))
                    used_routes.update(alternative_routes)  # Speichere die genutzten alternativen Linien

    return backup_routes  # Gibt jetzt echte alternative Backup-Routen zurück

# TODO Only exlude route before transfer and one after
# TODO search for mreliable
# TODO Backup rout would start at leats at departure time of missed connection


# Hauptprogramm
if __name__ == "__main__":

    agency, stops, routes, trips, stop_times, calendar, calendar_dates = import_data()

    start_stop_name = "Schattendorf Kirchengasse"
    end_stop_name = "Flughafen Wien Bahnhof"
    start_datetime = "2024-12-20 14:30:00"

    time_budget = "2:10"
    time_budget_hours, time_budget_minutes = map(int, time_budget.split(":"))
    time_budget_minutes = time_budget_hours * 60 + time_budget_minutes / 60

    start_time_obj = datetime.strptime(start_datetime, "%Y-%m-%d %H:%M:%S")
    start_time_minutes = start_time_obj.hour * 60 + start_time_obj.minute

    # In ein reines date-Objekt umwandeln
    start_time_obj = datetime.strptime(start_datetime, "%Y-%m-%d %H:%M:%S")
    end_time_obj = start_time_obj + timedelta(minutes=time_budget_minutes)
    date_obj = start_time_obj.date()

    start_time_minutes = start_time_obj.hour * 60 + start_time_obj.minute

    #fast and weird
    #graph = create_graph_with_schedule(stop_times, stops, trips, calendar, calendar_dates, start_time_obj)

    #slow and correct
    graph = create_graph_with_schedule(stop_times, stops, trips, calendar, calendar_dates, start_time_obj,
                                       start_time_obj, end_time_obj)
    if start_stop_name not in graph or end_stop_name not in graph:
        print("🚨 Ungültige Start- oder Zielhaltestelle!")
        #sys.exit()

    # Haupt-Dijkstra-Lauf
    arrival_time_minutes_fixed, path_fixed, reliability_fixed = dijkstra_with_reliability_fixed(
        graph, start_stop_name, end_stop_name, start_time_minutes, time_budget_minutes
    )

    # Backup-Routen berechnen
    backup_routes = find_backup_routes(graph, path_fixed, start_time_minutes, time_budget_minutes)

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


        print("🔄 Backup-Routen:")
        if backup_routes:
            print("\n🔄 Backup-Routen:")
            for stop, path, reliability in backup_routes:
                print(f"  🔁 Backup von {stop}:")
                last_route = None
                first_segment = True

                for segment in path:
                    start, dep_time, end, arr_time, route = segment

                    if last_route == route:
                        print(f" → {end} (Ankunft: {arr_time})", end="")
                    else:
                        if not first_segment:
                            print()
                        print(f"    🚆 {start} (Abfahrt: {dep_time}) → {end} (Ankunft: {arr_time}) mit Linie {route}",
                              end="")
                        first_segment = False

                    last_route = route

                print(f"\n    🔹 Zuverlässigkeit: {reliability:.2f}\n")
        else:
            print("  ❌ Keine Backup-Routen verfügbar.")

        print()
    else:
        print(f"\n⚠️ Keine zuverlässige Route von {start_stop_name} nach {end_stop_name} gefunden.\n")


# TODO primary