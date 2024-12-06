import pandas as pd
import mysql.connector

# Database connection configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Murari@24',  # Replace with your actual MySQL password
    'database': 'cricket_stats'
}

# Connect to MySQL database
conn = mysql.connector.connect(**db_config)
cursor = conn.cursor()

# Drop the BowlingStats table if it exists to avoid conflicts
cursor.execute("DROP TABLE IF EXISTS BowlingStats")

# Step 1: Create the BowlingStats Table with Updated Column Names
cursor.execute('''
CREATE TABLE BowlingStats (
    stat_id INT PRIMARY KEY AUTO_INCREMENT,
    player_id INT,
    format VARCHAR(10),            -- 'ODI', 'T20', 'Test'
    span VARCHAR(20),              -- Career span
    best_bowling_innings VARCHAR(10), -- Allows scores like "7/113"
    best_bowling_match VARCHAR(10),
    balls_bowled INT,
    bowling_average FLOAT,
    bowling_economy FLOAT,
    strike_rate FLOAT,
    conceded INT,
    five_wicket_hauls INT,
    four_wicket_hauls INT,
    innings INT,
    maidens INT,
    matches INT,
    overs FLOAT,
    player_rating FLOAT,
    total_wickets INT,
    FOREIGN KEY (player_id) REFERENCES Players(player_id)
)
''')

# Commit the creation of the table
conn.commit()

# Function to get the correct player_id from the mapping
def get_correct_player_id(player_mapping, csv_id):
    return player_mapping.get(csv_id)

# Load player mappings from `all_players.csv`
player_mapping = {}
players_df = pd.read_csv(r'D:\dbms_project\all_players.csv')  # Adjust path as needed
for _, row in players_df.iterrows():
    csv_id = row['id']
    name = row['name']
    # Get database player_id and update Players table with the correct `id` from CSV
    cursor.execute("SELECT player_id FROM Players WHERE name = %s", (name,))
    result = cursor.fetchone()
    if result:
        player_id = result[0]
        cursor.execute("UPDATE Players SET player_id = %s WHERE player_id = %s", (csv_id, player_id))
        player_mapping[csv_id] = csv_id

# Commit updates to the Players table
conn.commit()

# Step 2: Populate BowlingStats Table
bowling_files = {'ODI': r'D:\dbms_project\ODI_bowling.csv', 'T20': r'D:\dbms_project\t20_bowling.csv', 'Test': r'D:\dbms_project\TEST_bowling.csv'}
for format_type, file_path in bowling_files.items():
    bowling_df = pd.read_csv(file_path)
    for _, row in bowling_df.iterrows():
        # Use the `id` column directly from the CSV for player mapping
        csv_player_id = row['id']
        player_id = get_correct_player_id(player_mapping, csv_player_id)
        if player_id:
            try:
                cursor.execute('''
                    INSERT INTO BowlingStats (
                        player_id, format, span, best_bowling_innings, best_bowling_match, balls_bowled, bowling_average,
                        bowling_economy, strike_rate, conceded, five_wicket_hauls, four_wicket_hauls, innings, maidens,
                        matches, overs, player_rating, total_wickets
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (player_id, format_type, row['sp'], row['bbi'], row['bbm'], row['bl'], row['bwa'], row['bwe'],
                      row['bwsr'], row['cd'], row['fw'], row['fwk'], row['in'], row['md'], row['mt'], row['ov'], 
                      row['pr'], row['wk']))
            except Exception as e:
                print(f"Error inserting into BowlingStats for player ID {csv_player_id}: {e}")
                print("Data causing the error:", row)
        else:
            print(f"Correct Player ID not found for original CSV ID {csv_player_id} in BowlingStats")

# Commit all changes and close the conection
conn.commit()
cursor.close()
conn.close()

print("BowlingStats table created and populated successfully.")
