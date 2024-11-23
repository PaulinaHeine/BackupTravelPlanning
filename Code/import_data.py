
import pandas as pd

def import_data():
    # @diana and denis, change to your directory
    gtfs_dir = '/Users/paulinaheine/Codes/BackupTravelPlanning/GTFS_OP_2024_obb-2/'

    # load data
    agency_df = pd.read_csv(gtfs_dir + 'agency.txt')
    stops_df = pd.read_csv(gtfs_dir + 'stops.txt')
    routes_df = pd.read_csv(gtfs_dir + 'routes.txt')
    trips_df = pd.read_csv(gtfs_dir + 'trips.txt')
    stop_times_df = pd.read_csv(gtfs_dir + 'stop_times.txt')
    calendar_df = pd.read_csv(gtfs_dir + 'calendar.txt')
    calendar_dates_df = pd.read_csv(gtfs_dir + 'calendar_dates.txt')

    return agency_df, stops_df, routes_df, trips_df, stop_times_df, calendar_df, calendar_dates_df

agency_df, stops_df, routes_df, trips_df, stop_times_df, calendar_df, calendar_dates_df = import_data()


# Funktion zur Anpassung von Zeiten über 24 Stunden
def adjust_time_to_next_day(time_str):
    hours, minutes, seconds = map(int, time_str.split(":"))
    if hours >= 24:
        # Reduziere die Stunden um 24 und markiere als nächster Tag
        hours -= 24
        return f"{hours:02}:{minutes:02}:{seconds:02}", True  # True bedeutet "nächster Tag"
    return time_str, False  # False bedeutet "gleicher Tag"




# Beispielanzeige der Daten
print("Stops Data:")
print(stops_df.head())

print("\nStop Times Data:")
print(stop_times_df.head())


