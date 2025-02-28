from datetime import datetime, timedelta
import pandas as pd

# Function to import GTFS data
def import_data():
    # Directory where GTFS data files are stored
    gtfs_dir = 'C:/Users/Diana Lutska/DAPP/GTFS_OP_2024_obb/'

    # Load each of the necessary GTFS files into pandas DataFrames
    agency_df = pd.read_csv(gtfs_dir + 'agency.txt')  
    stops_df = pd.read_csv(gtfs_dir + 'stops.txt')    
    routes_df = pd.read_csv(gtfs_dir + 'routes.txt')  
    trips_df = pd.read_csv(gtfs_dir + 'trips.txt')   
    stop_times_df = pd.read_csv(gtfs_dir + 'stop_times.txt') 
    calendar_df = pd.read_csv(gtfs_dir + 'calendar.txt') 
    calendar_dates_df = pd.read_csv(gtfs_dir + 'calendar_dates.txt')  
    shapes_df = pd.read_csv(gtfs_dir + 'shapes.txt')  

    return agency_df, stops_df, routes_df, trips_df, stop_times_df, calendar_df, calendar_dates_df


# Function to adjust time if needed (if hours are greater than or equal to 24)
def adjust_time_if_needed(time_str):
    hours, minutes, seconds = map(int, time_str.split(":"))
    # If hours are 24 or more, subtract 24 hours to adjust the time
    if hours >= 24:
        adjusted_hours = hours - 24  # Reduce hours by 24
        return f"{adjusted_hours:02}:{minutes:02}:{seconds:02}"  
    return time_str  


# Function to prepare the data for further processing (creating 'legs' for each trip)
def prepare_data(stops_df, trips_df, stop_times_df):
    # Sort the stop_times_df by trip_id and stop_sequence to order the stops in the correct sequence
    legcreation_df = stop_times_df.sort_values(['trip_id', 'stop_sequence']).reset_index(drop=True)
    
    # Drop unnecessary columns from the stop_times_df that are not needed for the legs
    legcreation_df = legcreation_df.drop(columns=['stop_headsign', 'pickup_type', 'drop_off_type', 'shape_dist_traveled'])
    
    # Merge with the stops_df to get the stop names (based on the stop_id)
    legcreation_df = legcreation_df.merge(stops_df[['stop_id', 'stop_name']], on='stop_id', how='left')
    legcreation_df = legcreation_df.drop(columns=['stop_id']) 

    # Shift the 'stop_name' and 'arrival_time' columns to create departure and arrival stop and time for each leg
    legcreation_df['arrival_stop_name'] = legcreation_df['stop_name'].shift(-1)
    legcreation_df['arrival_time'] = legcreation_df['arrival_time'].shift(-1)

    # Filter out the last stop of each trip (it doesn't have a next stop)
    legs_df = legcreation_df[legcreation_df['trip_id'] == legcreation_df['trip_id'].shift(-1)].copy()

    # Drop unnecessary columns from trips_df 
    trips_df = trips_df.drop(columns=['shape_id', 'trip_headsign', 'trip_short_name', 'direction_id', 'block_id'])

   # Apply the time adjustment function to the 'arrival_time' and 'departure_time' columns
    legs_df['arrival_time'] = legs_df['arrival_time'].apply(adjust_time_if_needed)
    legs_df['departure_time'] = legs_df['departure_time'].apply(adjust_time_if_needed)

    # Merge the legs_df with trips_df to include  route_id and service_id, etc.
    legs_df = legs_df.merge(trips_df, on='trip_id', how='left')

    # Create a 'leg' by combining necessary information
    legs_df['leg'] = list(zip(
        legs_df['trip_id'],
        legs_df['stop_name'], 
        legs_df['departure_time'], 
        legs_df['arrival_stop_name'], 
        legs_df['arrival_time'], 
        legs_df['route_id'],
        legs_df['service_id']
    ))

    # Select only the 'leg' column to return as the final output
    processed_legs_df = legs_df['leg']

    return processed_legs_df  # Return the processed list of legs

