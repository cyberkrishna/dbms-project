import pandas as pd
import mysql.connector
from sqlalchemy import create_engine
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.impute import SimpleImputer
import pickle

# Database configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Murari@24',
    'database': 'cricket_stats'
}

def load_data():
    # SQL query to join relevant tables and select key statistics for each player
    query = """
    SELECT p.player_id, p.name, p.role, p.batting_style, p.bowling_style,
           b.matches AS batting_matches, b.innings AS batting_innings, b.runs AS batting_runs, 
           b.average_score AS batting_average, b.strike_rate AS batting_strike_rate, 
           bo.matches AS bowling_matches, bo.innings AS bowling_innings, 
           bo.total_wickets AS bowling_wickets, bo.bowling_average, bo.bowling_economy
    FROM players AS p
    LEFT JOIN battingstats AS b ON p.player_id = b.player_id AND b.format = 'ODI'
    LEFT JOIN bowlingstats AS bo ON p.player_id = bo.player_id AND bo.format = 'ODI'
    """

    # Create a SQLAlchemy engine for compatibility with pandas read_sql
    engine = create_engine('mysql+mysqlconnector://root:Murari%4024@localhost/cricket_stats')
    
    # Load data into a DataFrame
    data = pd.read_sql(query, engine)
    return data

# Load data
data = load_data()

# Select and standardize features for clustering
features = data[['batting_matches', 'batting_innings', 'batting_runs', 'batting_average', 
                 'batting_strike_rate', 'bowling_matches', 'bowling_innings', 
                 'bowling_wickets', 'bowling_average', 'bowling_economy']]

# Check for any NaN values in the initial dataset
print("Initial NaN values in features:")
print(features.isnull().sum())

# Impute NaN values with zero or mean if preferred
imputer = SimpleImputer(strategy='constant', fill_value=0)
features_imputed = imputer.fit_transform(features)

# Confirm that imputation has removed all NaN values
print("NaN values after imputation:")
print(pd.DataFrame(features_imputed).isnull().sum())

# Standardize features
scaler = StandardScaler()
features_scaled = scaler.fit_transform(features_imputed)

# Double-check if any NaN values remain after scaling
print("NaN values after scaling:")
print(pd.DataFrame(features_scaled).isnull().sum())

# Train K-means model with 5 clusters
kmeans = KMeans(n_clusters=5, random_state=42)
data['cluster'] = kmeans.fit_predict(features_scaled)

# Save the model and scaler for use in the Flask application
with open('kmeans_model.pkl', 'wb') as f:
    pickle.dump((kmeans, scaler), f)

print("Data loaded and model trained successfully.")
