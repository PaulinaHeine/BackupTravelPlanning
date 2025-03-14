import tkinter as tk
from tkinter import messagebox
import sys
import pandas as pd
import heapq
from collections import defaultdict
from datetime import datetime
from scipy.stats import norm
from Code.import_data import import_data

# Hilfsfunktionen
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
        if is_service_available(service_id, date, calendar, calendar_dates):
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

def compute_transfer_probability_with_departure_delay(scheduled_arrival, scheduled_departure):
    mean_arrival_delay = 3
    std_dev_arrival = 1
    mean_departure_delay = 2
    std_dev_departure = 1
    mu_arrival = scheduled_arrival + mean_arrival_delay
    mu_departure = scheduled_departure + mean_departure_delay
    std_dev_diff = (std_dev_arrival**2 + std_dev_departure**2) ** 0.5
    return norm.cdf(0, loc=mu_departure - mu_arrival, scale=std_dev_diff)

def dijkstra_with_reliability_fixed(graph, start_name, end_name, start_time_minutes):
    pq = [(start_time_minutes, start_name, [], 1.0, None)]
    visited = set()
    while pq:
        current_time, current_stop, path, reliability, last_route = heapq.heappop(pq)
        if (current_stop, current_time) in visited:
            continue
        visited.add((current_stop, current_time))
        path = path + [(current_stop, current_time)]
        for neighbor, departure_time, arrival_time, route_id in graph[current_stop]:
            if departure_time >= current_time:
                transfer_reliability = 1.0 if last_route == route_id else compute_transfer_probability_with_departure_delay(arrival_time, departure_time)
                new_current_time = arrival_time
                new_reliability = reliability * transfer_reliability
                heapq.heappush(pq, (new_current_time, neighbor, path + [(route_id, departure_time, arrival_time)], new_reliability, route_id))
        if current_stop == end_name:
            return current_time, path, reliability
    return float("inf"), [], 0.0


# Funktion zur Berechnung der Route
def calculate_route():
    start_stop_name = start_entry.get()
    end_stop_name = end_entry.get()
    start_datetime = time_entry.get()

    if not start_stop_name or not end_stop_name or not start_datetime:
        messagebox.showerror("Fehler", "Bitte alle Felder ausfüllen!")
        return

    try:
        start_time_obj = datetime.strptime(start_datetime, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        messagebox.showerror("Fehler", "Falsches Datumsformat! Bitte in 'YYYY-MM-DD HH:MM:SS' eingeben.")
        return

    start_time_minutes = start_time_obj.hour * 60 + start_time_obj.minute

    # Daten importieren
    agency, stops, routes, trips, stop_times, calendar, calendar_dates = import_data()
    graph = create_graph_with_schedule(stop_times, stops, trips, calendar, calendar_dates, start_time_obj)

    if start_stop_name not in graph or end_stop_name not in graph:
        messagebox.showerror("Fehler", "Ungültige Start- oder Zielhaltestelle!")
        return

    # Route berechnen
    arrival_time_minutes_fixed, path_fixed, reliability_fixed = dijkstra_with_reliability_fixed(
        graph, start_stop_name, end_stop_name, start_time_minutes
    )

    # Ergebnis anzeigen
    if arrival_time_minutes_fixed < float("inf"):
        arrival_time_fixed = minutes_to_time(arrival_time_minutes_fixed)
        result_text = f"\n📍 Route von {start_stop_name} nach {end_stop_name}:\n"

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
            result_text += f"  🚆 {start} (Abfahrt: {dep_time}) → {stops} mit Linie {route}\n"

        result_text += f"\n🎯 Endstation: {end_stop_name} (Ankunft: {arrival_time_fixed})"
        result_text += f"\n🔹 Gesamt-Zuverlässigkeit: {reliability_fixed:.2f}\n"

        result_label.config(text=result_text)
    else:
        messagebox.showerror("Fehler", "Keine zuverlässige Route gefunden.")

# GUI erstellen
root = tk.Tk()
root.title("Routenfinder")
root.geometry("600x400")

tk.Label(root, text="Startbahnhof:").pack()
start_entry = tk.Entry(root)
start_entry.pack()

tk.Label(root, text="Zielbahnhof:").pack()
end_entry = tk.Entry(root)
end_entry.pack()

tk.Label(root, text="Startzeit (YYYY-MM-DD HH:MM:SS):").pack()
time_entry = tk.Entry(root)
time_entry.pack()

calc_button = tk.Button(root, text="Route berechnen", command=calculate_route)
calc_button.pack()

result_label = tk.Label(root, text="", justify=tk.LEFT, anchor="w")
result_label.pack()

root.mainloop()
