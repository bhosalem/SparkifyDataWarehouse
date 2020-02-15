import os
import glob
import psycopg2
import pandas as pd
from sql_queries import *


def process_song_file(cur, filepath):
    """Load Data into the song and artist table
       For each of the file identifed in the process data table,reads 
       the json file into pandas dataframe extract the required data 
       columns from the file and insert into the song and artist tables.
       
       Parameters:
       cur object : cursor object defined for sparkify connection in main()
       filepath (string): Path to the song/log data files
       
       Returns : none
    """
    # open song file
    df = pd.read_json(filepath,lines=True)

    # insert song record
    song_data = df.loc[:,['song_id','title','artist_id','year','duration']].values.tolist()
    for row in song_data:
        cur.execute(song_table_insert, row)
    
    # insert artist record
    artist_data =df.loc[:,['artist_id','artist_name','artist_location','artist_latitude','artist_longitude']].values.tolist()
    for row in artist_data:
        cur.execute(artist_table_insert, row)


def process_log_file(cur, filepath):
    """Load data into the users and time and sonplay fact table
    
       For each of the file identifed in the process data table,
       reads thee json file into pandas dataframe,extract the 
       required data columns from the file and insert into the 
       users and time tables.
       
       Function also derives the artist_id and song_id keys for 
       inserts into fact table songplays
       
       Parameters:
       cur object : cursor object defined for sparkify connection in main()
       filepath (string): Path to the song/log data files
       
       Returns : none
    """
    # open log file
    df = pd.read_json(filepath,lines=True)

    # filter by NextSong action
    df = df[df['page'] =='NextSong']

    # convert timestamp column to datetime
    t = pd.to_datetime(df['ts'],unit='ms')
    
    # insert time data records
    time_data = (t.dt.time,t.dt.hour,t.dt.day,t.dt.week,t.dt.month,t.dt.year,t.dt.weekday)
    column_labels = ('start_time','hour','day','week','month','year','weekday')
    time_df = pd.DataFrame.from_dict(dict(zip(column_labels,time_data)))

    for i, row in time_df.iterrows():
        cur.execute(time_table_insert, list(row))

    # load user table
    user_df = df.loc[:,['userId','firstName','lastName','gender','level']]

    # insert user records
    for i, row in user_df.iterrows():
        cur.execute(user_table_insert, row)

    # insert songplay records
    for index, row in df.iterrows():
        
        # get songid and artistid from song and artist tables
        cur.execute(song_select, (row.song, row.artist, row.length))
        results = cur.fetchone()
        
        if results:
            songid, artistid = results
        else:
            songid, artistid = None, None

        # insert songplay record
        songplay_data = (pd.to_datetime(row.ts,unit ='ms'),row.userId,row.level,songid,artistid,row.sessionId,row.location,row.userAgent)
        cur.execute(songplay_table_insert, songplay_data)


def process_data(cur, conn, filepath, func):
    """Derives files present in the filepath, displays the total
       number of files fount in the supplied filepath, invokes
       function defined by func parameter
       
       Parameters:
       cur object : cursor object defined for sparkify connection in main()
       conn object : connection object defined to connect to sparkify DB in main()
       filepath (string): Path to the song/log data files
       func (string): Name of the function to call based on data file
       
       Returns : none
    """
    # get all files matching extension from directory
    all_files = []
    for root, dirs, files in os.walk(filepath):
        files = glob.glob(os.path.join(root,'*.json'))
        for f in files :
            all_files.append(os.path.abspath(f))

    # get total number of files found
    num_files = len(all_files)
    print('{} files found in {}'.format(num_files, filepath))

    # iterate over files and process
    for i, datafile in enumerate(all_files, 1):
        func(cur, datafile)
        conn.commit()
        print('{}/{} files processed.'.format(i, num_files))


def main():
    """This is main function which connects to sparkify database and 
       then calls process data for song data and log data separately
       to load all tables and at the end close the connection.
    """
    conn = psycopg2.connect("host=127.0.0.1 dbname=sparkifydb user=student password=student")
    cur = conn.cursor()
    cur.execute(create_songplay_seq)
    cur.execute(create_time_seq)
    process_data(cur, conn, filepath='data/song_data', func=process_song_file)
    process_data(cur, conn, filepath='data/log_data', func=process_log_file)
    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
