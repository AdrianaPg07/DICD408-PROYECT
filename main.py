import logging
import pandas as pd
import os
import pyodbc

from spotify import SpotifyAPI
from dotenv import load_dotenv

load_dotenv()

def extract_spotify_data(client_id, client_secret, user_id):
    spotify_api = SpotifyAPI(client_id, client_secret, user_id)

    # Tables list:
    track_data = []
    artist_data = []
    album_data = []
    playlist_data = []

    # Get user data
    user_item = spotify_api.get_user_data()

    # Extract user_name from user_item
    user_name = user_item.get("display_name", "")  # Assuming display_name is available in user_data

    user_dict = {
        "user_name": user_name,
        "user_id": user_id
    }

    user_data = [user_dict]

    # Get playlists 
    playlist_item = spotify_api.get_playlists()

    if playlist_item:
        for item in playlist_item:
            # Playlist information
            playlist_id = item['id']
            playlist_name = item['name']

            playlist_dict = {
                "playlist_id": playlist_id,
                "user_id": user_id,
                "playlist_name": playlist_name
            }
            playlist_data.append(playlist_dict)

            # Get tracks for each playlist
            tracks_item = spotify_api.get_playlist_tracks(playlist_id)

            for i in tracks_item:
                track_id = i['track']['id']
                track_name = i['track']['name']
                artist_id = i["track"]["artists"][0].get("id")
                artist_name = i["track"]["artists"][0].get("name")
                album_id = i["track"]["album"].get("id")
                album_name = i["track"]["album"].get("name")

                track_dict = {
                    "track_id": track_id,
                    "playlist_id": playlist_id,
                    "artist_id": artist_id,
                    "album_id": album_id,
                    "track_name": track_name
                }

                artist_dict = {
                    "artist_id": artist_id,
                    "artist_name": artist_name
                }

                album_dict = {
                    "album_id": album_id,
                    "album_name": album_name
                }

                track_data.append(track_dict)
                artist_data.append(artist_dict)
                album_data.append(album_dict)
                
            # Log the number of tracks found for each playlist
            logging.info(f"Playlist {playlist_id} has {len(tracks_item)} tracks.")
    else:
        logging.info("No playlists found.")

    return user_data, playlist_data, track_data, album_data, artist_data
#TRANSFORM

def transform_data(track_data, artist_data, album_data, playlist_data, user_data):
    track_df = pd.DataFrame(track_data).rename(
        columns={"track_id": "id", "playlist_id": "playlist_id", "artist_id": "artist_id", "album_id": "album_id",
                 "track_name": "name"})
    artist_df = pd.DataFrame(artist_data).rename(columns={"artist_id": "id", "artist_name": "name"})
    album_df = pd.DataFrame(album_data).rename(columns={"album_id": "id", "album_name": "name"})
    playlist_df = pd.DataFrame(playlist_data).rename(
        columns={"playlist_id": "id", "user_id": "user_id", "playlist_name": "name"})
    user_df = pd.DataFrame(user_data).rename(columns={"user_id": "id", "user_name": "name"})
    return user_df, playlist_df, track_df, album_df, artist_df

def check_duplicates_and_missing_values(track_df, artist_df, album_df, playlist_df, user_df):
    for df, name in [(track_df, "track"), (artist_df, "artist"), (album_df, "album"), (playlist_df, "playlist"),
                     (user_df, "user")]:
        duplicate_entries = df[df.duplicated()]
        if not duplicate_entries.empty:
            logging.warning(f"Duplicate {name} found. Duplicates will be removed.")
            df.drop_duplicates(inplace=True)

        if df.isnull().values.any():
            logging.warning(f"Missing values found in {name} data. Please handle missing values appropriately.")
#LOAD
def load_data_to_database(user_df, playlist_df, track_df, album_df, artist_df, db_path):
    try:
        conn = pyodbc.connect(db_path)
        # TRUNCATE TABLES (SOMEE.COM)
        cursor = conn.cursor()
        query = "truncate table [user];truncate table [playlist];truncate table [track];truncate table [album];truncate table [artist]"
        cursor.execute(query)
        cursor.close()

        # TABLE [user] -----------------------------------------------------------------------------
        columns = ', '.join(user_df.columns)
        placeholders = ', '.join(['?'] * len(user_df.columns))

        sql = f"""
        INSERT INTO [user] ({columns})
        VALUES ({placeholders})
        """

        #print(sql)

        cursor = conn.cursor()
        for index, row in user_df.iterrows():
            cursor.execute(sql, tuple(row.tolist()))

        conn.commit()
        # TABLE [playlist] -----------------------------------------------------------------------------
        columns = ', '.join(playlist_df.columns)
        placeholders = ', '.join(['?'] * len(playlist_df.columns))

        sql = f"""
        INSERT INTO [playlist] ({columns})
        VALUES ({placeholders})
        """

        #print(sql)

        cursor = conn.cursor()
        for index, row in playlist_df.iterrows():
            cursor.execute(sql, tuple(row.tolist()))

        conn.commit()
        # TABLE [track] -----------------------------------------------------------------------------
        columns = ', '.join(track_df.columns)
        placeholders = ', '.join(['?'] * len(track_df.columns))

        sql = f"""
        INSERT INTO [track] ({columns})
        VALUES ({placeholders})
        """

        #print(sql)

        cursor = conn.cursor()
        for index, row in track_df.iterrows():
            cursor.execute(sql, tuple(row.tolist()))

        conn.commit()

        # TABLE [album] -----------------------------------------------------------------------------
        columns = ', '.join(album_df.columns)
        placeholders = ', '.join(['?'] * len(album_df.columns))

        sql = f"""
        INSERT INTO [album] ({columns})
        VALUES ({placeholders})
        """

        #print(sql)

        cursor = conn.cursor()
        for index, row in album_df.iterrows():
            cursor.execute(sql, tuple(row.tolist()))

        conn.commit()
        # TABLE [artist] -----------------------------------------------------------------------------
        columns = ', '.join(artist_df.columns)
        placeholders = ', '.join(['?'] * len(artist_df.columns))

        sql = f"""
        INSERT INTO [artist] ({columns})
        VALUES ({placeholders})
        """

        #print(sql)

        cursor = conn.cursor()
        for index, row in artist_df.iterrows():
            cursor.execute(sql, tuple(row.tolist()))

        conn.commit()
        #Close Connection
        conn.close()


        
        #user_df.to_sql('user', conn, if_exists='replace', index=False)
        #playlist_df.to_sql('playlist', conn, if_exists='replace', index=False)
        #track_df.to_sql('track', conn, if_exists='replace', index=False)
        #album_df.to_sql('album', conn, if_exists='replace', index=False)
        #artist_df.to_sql('artist', conn, if_exists='replace', index=False)
    except pyodbc.Error as e:
        logging.error(f"An error occurred during data insertion: {e}", exc_info=True)
    else:
        logging.info("Data loaded to SQLite successfully.")

def etl_pipeline():
    try:
        # Check for required environment variables
        required_env_vars = ['SPOTIFY_CLIENT_ID', 'SPOTIFY_CLIENT_SECRET', 'SPOTIFY_USER_ID', 'server', 'database', 'username', 'password']
        for var in required_env_vars:
            if not os.getenv(var):
                raise EnvironmentError(f"Missing required environment variable: {var}")

        client_id = os.getenv('SPOTIFY_CLIENT_ID')
        client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
        user_id = os.getenv('SPOTIFY_USER_ID')
        db_path = 'DRIVER={ODBC Driver 17 for SQL Server};\
                      SERVER='+os.getenv('server')+';\
                      DATABASE='+os.getenv('database')+';\
                      UID='+os.getenv('username')+';\
                      PWD='+ os.getenv('password')

        # ETL Extract
        user_data, playlist_data, track_data, album_data, artist_data = extract_spotify_data(client_id, client_secret,
                                                                                             user_id)

        # ETL Transform
        user_df, playlist_df, track_df, album_df, artist_df = transform_data(track_data, artist_data, album_data,
                                                                             playlist_data, user_data)

        # Perform data validation checks
        check_duplicates_and_missing_values(track_df, artist_df, album_df, playlist_df, user_df)        

        print(user_df)
        print(playlist_df)
        print(track_df)
        print(album_df)
        print(artist_df)

        user_df.to_csv('user_df.csv', index = False)
        playlist_df.to_csv('playlist_df.csv', index = False)
        track_df.to_csv('track_df.csv', index = False)
        album_df.to_csv('album_df.csv', index = False)
        artist_df.to_csv('artist_df.csv', index = False)
        # ETL Load to SQL
        # Ensure the database is created before loading data (somee.com)
        load_data_to_database(user_df, playlist_df, track_df, album_df, artist_df, db_path)

        logging.info("Data loaded to SQLite successfully.")
    except EnvironmentError as e:
        logging.error(f"Error with environment variables: {e}", exc_info=True)
    except Exception as e:
        logging.error(f"An error occurred during ETL Pipeline: {e}", exc_info=True)


etl_pipeline()