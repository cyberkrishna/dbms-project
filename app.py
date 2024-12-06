from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import numpy as np
import mysql.connector
from sklearn.cluster import KMeans as kmeans
from sklearn.preprocessing import StandardScaler as scaler
import bcrypt
import pickle
import matplotlib.pyplot as plt
import io
import base64

app = Flask(__name__)
app.secret_key = "your_secret_key"

# Database connection configuration
DB_HOST = 'localhost'
DB_USER = 'root'
DB_PASSWORD = 'Murari@24'
DB_NAME = 'cricket_stats'

# Database connection helper function
def query_db(query, args=(), one=False):
    conn = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    cur = conn.cursor(dictionary=True)
    cur.execute(query, args)
    rv = cur.fetchall()
    conn.close()
    return (rv[0] if rv else None) if one else rv

# Home route
@app.route('/')
def home():
    if 'username' in session:
        return render_template('home.html', username=session['username'])
    return redirect(url_for('login'))

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Query the database for the user
        user = query_db("SELECT * FROM Users WHERE username = %s", (username,), one=True)

        if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            session['username'] = user['username']

            # Check if the user is admin
            if username.lower() == "admin":
                session['is_admin'] = True
                return redirect(url_for('admin_page'))
            else:
                session['is_admin'] = False
                return redirect(url_for('home'))
        else:
            # Pass error message to the template
            return render_template('login.html', message="Invalid Username or Password", is_error=True)

    # Render the login page without a message
    return render_template('login.html', message=None, is_error=False)



# Signup route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip()
        password = request.form['password']

        # Validate inputs
        if len(password) < 8:
            return render_template('signup.html', message="Password must be at least 8 characters long.", is_error=True)

        try:
            # Hash password
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

            # Database connection
            conn = mysql.connector.connect(
                host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME
            )
            cursor = conn.cursor(dictionary=True)

            # Check for duplicate username
            cursor.execute("SELECT * FROM Users WHERE username = %s", (username,))
            if cursor.fetchone():
                
                return render_template(
                    'signup.html',
                    message="Username already exists. Please choose a different one.",
                    is_error=True
                )

            # Check for duplicate email
            cursor.execute("SELECT * FROM Users WHERE email = %s", (email,))
            if cursor.fetchone():
                return render_template(
                    'signup.html',
                    message="Email is already registered. Please use a different email.",
                    is_error=True
                )

            # Insert user into database
            cursor.execute(
                "INSERT INTO Users (username, email, password_hash) VALUES (%s, %s, %s)",
                (username, email, password_hash.decode('utf-8')),
            )
            conn.commit()
            return redirect(url_for('login'))

        except mysql.connector.Error as err:
            return render_template(
                'signup.html',
                message=f"Database Error: {err}",
                is_error=True
            )
        except Exception as e:
            return render_template(
                'signup.html',
                message=f"Unexpected Error: {e}",
                is_error=True
            )
        finally:
            if conn.is_connected():
                conn.close()

    return render_template('signup.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin_page():
    if 'username' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))  # Redirect to login if not an admin

    if request.method == 'POST':
        username = request.form.get('username')  # Use the username as a unique identifier
        try:
            conn = mysql.connector.connect(
                host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME
            )
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Users WHERE username = %s", (username,))
            conn.commit()
            conn.close()
            message = f"User {username} has been deleted successfully."
        except mysql.connector.Error as err:
            message = f"Error: {err}"
        return redirect(url_for('admin_page', message=message))

    # Fetch all users except the admin
    conn = mysql.connector.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME
    )
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT username, email FROM Users WHERE username != 'admin'")
    users = cursor.fetchall()
    conn.close()

    return render_template('admin.html', users=users)

# Logout route
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))
# Route to display profile page
@app.route('/profile', methods=['GET'])
def profile():
    # Check if the user is logged in
    if 'username' not in session:
        return redirect(url_for('login'))

    # Fetch user details from the database
    username = session['username']
    user_details = query_db("SELECT * FROM Users WHERE username = %s", (username,), one=True)

    if user_details:
        return render_template('profile.html', user_details=user_details)
    else:
        return "User details not found.", 404

# Route to handle editing preferences
@app.route('/edit_preferences', methods=['GET', 'POST'])
def edit_preferences():
    # Check if the user is logged in
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        favorite_players = request.form.get('favorite_players')
        favorite_team = request.form.get('favorite_team')
        dream_team = request.form.get('dream_team')

        # Update user preferences in the database
        username = session['username']
        conn = mysql.connector.connect(
            host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME
        )
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE Users 
            SET favorite_players = %s, favorite_team = %s, dream_team = %s 
            WHERE username = %s
        """, (favorite_players, favorite_team, dream_team, username))
        conn.commit()
        conn.close()

        return redirect(url_for('profile'))

    # Fetch current user preferences for pre-filling the form
    username = session['username']
    user_details = query_db("SELECT * FROM Users WHERE username = %s", (username,), one=True)

    return render_template('profile.html', user_details=user_details)
# Search Player route
@app.route('/search_player')
def search_player():
    if 'username' in session:
        return render_template('search_player.html', username=session['username'])
    return redirect(url_for('login'))

# Autocomplete route for player name suggestions in search
@app.route('/autocomplete')
def autocomplete():
    search_query = request.args.get('q', '')
    if not search_query:
        return jsonify([])

    players = query_db("SELECT name FROM Players WHERE name LIKE %s", (f"%{search_query}%",))
    suggestions = [player['name'] for player in players]
    return jsonify(suggestions)
@app.route('/autocomplete_players', methods=['GET'])
def autocomplete_players():
    search_query = request.args.get('q', '')
    players = query_db("SELECT DISTINCT name FROM Players WHERE name LIKE %s", (f"%{search_query}%",))
    return jsonify([player['name'] for player in players])

@app.route('/autocomplete_teams', methods=['GET'])
def autocomplete_teams():
    search_query = request.args.get('q', '')
    teams = query_db("SELECT DISTINCT country FROM Players WHERE country LIKE %s", (f"%{search_query}%",))
    return jsonify([team['country'] for team in teams])

# Search route to process player search query
@app.route('/search', methods=['GET'])
def search():
    player_name = request.args.get('query')
    player = query_db("SELECT player_id FROM Players WHERE name LIKE %s", (f"%{player_name}%",), one=True)
    
    if player:
        return redirect(url_for('player_details', player_id=player['player_id']))
    else:
        return render_template('search_player.html', message="Player not found", is_error=True)

# Helper function to fetch detailed player statistics by player_id
def get_player_stats(player_id):
    return query_db("""
        SELECT 
            Players.name AS player_name,
            Players.country AS country,
            Players.role AS role,
            Players.batting_style AS batting_style,
            Players.bowling_style AS bowling_style,

            -- ODI Stats
            BattingODI.matches AS odi_batting_matches,
            BattingODI.innings AS odi_batting_innings,
            BattingODI.runs AS odi_batting_runs,
            BattingODI.high_score AS odi_batting_high_score,
            BattingODI.average_score AS odi_batting_average,
            BattingODI.strike_rate AS odi_batting_strike_rate,
            BattingODI.hundreds AS odi_batting_hundreds,
            BattingODI.fifties AS odi_batting_fifties,

            BowlingODI.matches AS odi_bowling_matches,
            BowlingODI.innings AS odi_bowling_innings,
            BowlingODI.total_wickets AS odi_bowling_total_wickets,
            BowlingODI.best_bowling_innings AS odi_bowling_best_innings,
            BowlingODI.bowling_average AS odi_bowling_average,
            BowlingODI.bowling_economy AS odi_bowling_economy,
            BowlingODI.strike_rate AS odi_bowling_strike_rate,
            BowlingODI.maidens AS odi_bowling_maidens,
            BowlingODI.four_wicket_hauls AS odi_bowling_four_wicket_hauls,
            BowlingODI.five_wicket_hauls AS odi_bowling_five_wicket_hauls,

            -- T20 Stats
            BattingT20.matches AS t20_batting_matches,
            BattingT20.innings AS t20_batting_innings,
            BattingT20.runs AS t20_batting_runs,
            BattingT20.high_score AS t20_batting_high_score,
            BattingT20.average_score AS t20_batting_average,
            BattingT20.strike_rate AS t20_batting_strike_rate,
            BattingT20.hundreds AS t20_batting_hundreds,
            BattingT20.fifties AS t20_batting_fifties,

            BowlingT20.matches AS t20_bowling_matches,
            BowlingT20.innings AS t20_bowling_innings,
            BowlingT20.total_wickets AS t20_bowling_total_wickets,
            BowlingT20.best_bowling_innings AS t20_bowling_best_innings,
            BowlingT20.bowling_average AS t20_bowling_average,
            BowlingT20.bowling_economy AS t20_bowling_economy,
            BowlingT20.strike_rate AS t20_bowling_strike_rate,
            BowlingT20.maidens AS t20_bowling_maidens,
            BowlingT20.four_wicket_hauls AS t20_bowling_four_wicket_hauls,
            BowlingT20.five_wicket_hauls AS t20_bowling_five_wicket_hauls,

            -- Test Stats
            BattingTest.matches AS test_batting_matches,
            BattingTest.innings AS test_batting_innings,
            BattingTest.runs AS test_batting_runs,
            BattingTest.high_score AS test_batting_high_score,
            BattingTest.average_score AS test_batting_average,
            BattingTest.strike_rate AS test_batting_strike_rate,
            BattingTest.hundreds AS test_batting_hundreds,
            BattingTest.fifties AS test_batting_fifties,

            BowlingTest.matches AS test_bowling_matches,
            BowlingTest.innings AS test_bowling_innings,
            BowlingTest.total_wickets AS test_bowling_total_wickets,
            BowlingTest.best_bowling_innings AS test_bowling_best_innings,
            BowlingTest.bowling_average AS test_bowling_average,
            BowlingTest.bowling_economy AS test_bowling_economy,
            BowlingTest.strike_rate AS test_bowling_strike_rate,
            BowlingTest.maidens AS test_bowling_maidens,
            BowlingTest.four_wicket_hauls AS test_bowling_four_wicket_hauls,
            BowlingTest.five_wicket_hauls AS test_bowling_five_wicket_hauls

        FROM Players
        LEFT JOIN (SELECT * FROM BattingStats WHERE format = 'ODI') AS BattingODI ON Players.player_id = BattingODI.player_id
        LEFT JOIN (SELECT * FROM BattingStats WHERE format = 'T20') AS BattingT20 ON Players.player_id = BattingT20.player_id
        LEFT JOIN (SELECT * FROM BattingStats WHERE format = 'Test') AS BattingTest ON Players.player_id = BattingTest.player_id
        LEFT JOIN (SELECT * FROM BowlingStats WHERE format = 'ODI') AS BowlingODI ON Players.player_id = BowlingODI.player_id
        LEFT JOIN (SELECT * FROM BowlingStats WHERE format = 'T20') AS BowlingT20 ON Players.player_id = BowlingT20.player_id
        LEFT JOIN (SELECT * FROM BowlingStats WHERE format = 'Test') AS BowlingTest ON Players.player_id = BowlingTest.player_id
        WHERE Players.player_id = %s
    """, (player_id,), one=True)

# Add your existing comparison and similar players logic here...




@app.route('/compare_players', methods=['GET', 'POST'])
def compare_players():
    if request.method == 'POST':
        player1_name = request.form.get('player1_name')
        player2_name = request.form.get('player2_name')

        # Fetch player IDs based on names
        player1 = query_db("SELECT player_id FROM Players WHERE name = %s", (player1_name,), one=True)
        player2 = query_db("SELECT player_id FROM Players WHERE name = %s", (player2_name,), one=True)

        if player1 and player2:
            player1_data = get_player_stats(player1['player_id'])
            player2_data = get_player_stats(player2['player_id'])

            # Data for Bar Charts
            runs_data = {
                'labels': ['ODI', 'T20', 'Test'],
                'player1': [player1_data['odi_batting_runs'], player1_data['t20_batting_runs'], player1_data['test_batting_runs']],
                'player2': [player2_data['odi_batting_runs'], player2_data['t20_batting_runs'], player2_data['test_batting_runs']]
            }

            matches_innings_highscore_data = {
                'labels': ['ODI', 'T20', 'Test'],
                'matches': {
                    'player1': [player1_data['odi_batting_matches'], player1_data['t20_batting_matches'], player1_data['test_batting_matches']],
                    'player2': [player2_data['odi_batting_matches'], player2_data['t20_batting_matches'], player2_data['test_batting_matches']]
                },
                'innings': {
                    'player1': [player1_data['odi_batting_innings'], player1_data['t20_batting_innings'], player1_data['test_batting_innings']],
                    'player2': [player2_data['odi_batting_innings'], player2_data['t20_batting_innings'], player2_data['test_batting_innings']]
                },
                'high_score': {
                    'player1': [player1_data['odi_batting_high_score'], player1_data['t20_batting_high_score'], player1_data['test_batting_high_score']],
                    'player2': [player2_data['odi_batting_high_score'], player2_data['t20_batting_high_score'], player2_data['test_batting_high_score']]
                }
            }

            hundreds_fifties_data = {
                'labels': ['ODI', 'T20', 'Test'],
                'hundreds': {
                    'player1': [player1_data['odi_batting_hundreds'], player1_data['t20_batting_hundreds'], player1_data['test_batting_hundreds']],
                    'player2': [player2_data['odi_batting_hundreds'], player2_data['t20_batting_hundreds'], player2_data['test_batting_hundreds']]
                },
                'fifties': {
                    'player1': [player1_data['odi_batting_fifties'], player1_data['t20_batting_fifties'], player1_data['test_batting_fifties']],
                    'player2': [player2_data['odi_batting_fifties'], player2_data['t20_batting_fifties'], player2_data['test_batting_fifties']]
                }
            }

            # Pass data to template
            return render_template(
                'player_comparison.html',
                player1_data=player1_data,
                player2_data=player2_data,
                runs_data=runs_data,
                matches_innings_highscore_data=matches_innings_highscore_data,
                hundreds_fifties_data=hundreds_fifties_data
            )
        else:
            return render_template('compare_players.html', message="Player not found", is_error=True)
                
            
    return render_template('compare_players.html')



@app.route('/autocomplete_player', methods=['GET'])
def autocomplete_player():
    search_query = request.args.get('q', '')
    if not search_query:
        return jsonify([])

    # Fetch player names matching the search query
    players = query_db("SELECT name FROM Players WHERE name LIKE %s", (f"%{search_query}%",))
    suggestions = [player['name'] for player in players]
    return jsonify(suggestions)
from scipy.spatial.distance import euclidean

@app.route('/search_similar_players', methods=['GET', 'POST'])
def search_similar_players():
    if request.method == 'POST':
        player_name = request.form.get('player_name')
        role = request.form.get('role')
        batting_style = request.form.get('batting_style')
        bowling_style = request.form.get('bowling_style')

        # Fetch the selected player's data
        player_data = query_db("""
            SELECT * FROM players AS p
            LEFT JOIN battingstats AS b ON p.player_id = b.player_id AND b.format = 'ODI'
            LEFT JOIN bowlingstats AS bo ON p.player_id = bo.player_id AND bo.format = 'ODI'
            WHERE p.name = %s
        """, (player_name,), one=True)

        if not player_data:
            return render_template('search_similar_player.html', message="Player not found", is_error=True)

        # Load the pre-trained model and scaler
        with open('kmeans_model.pkl', 'rb') as f:
            kmeans, scaler = pickle.load(f)

        # Prepare player data for clustering, handling NaN values
        player_features = np.array([[ 
            player_data.get('matches', 0) or 0, player_data.get('innings', 0) or 0,
            player_data.get('runs', 0) or 0, player_data.get('average_score', 0) or 0,
            player_data.get('strike_rate', 0) or 0, player_data.get('matches', 0) or 0,
            player_data.get('innings', 0) or 0, player_data.get('total_wickets', 0) or 0,
            player_data.get('bowling_average', 0) or 0, player_data.get('bowling_economy', 0) or 0
        ]])

        # Scale and predict the cluster for the selected player
        player_features_scaled = scaler.transform(player_features)
        player_cluster = kmeans.predict(player_features_scaled)[0]

        # Fetch all players and filter by cluster in Python
        all_players = query_db("""
            SELECT p.name, p.role, p.country, p.batting_style, p.bowling_style, 
                   b.matches AS batting_matches, b.runs AS batting_runs, b.average_score AS batting_average, 
                   b.strike_rate AS batting_strike_rate, bo.matches AS bowling_matches, 
                   bo.innings AS bowling_innings, bo.total_wickets AS bowling_wickets, 
                   bo.bowling_average, bo.bowling_economy
            FROM players AS p
            LEFT JOIN battingstats AS b ON p.player_id = b.player_id AND b.format = 'ODI'
            LEFT JOIN bowlingstats AS bo ON p.player_id = bo.player_id AND bo.format = 'ODI'
        """)

        # Prepare a list to hold similar players with distance
        similar_players_with_distance = []
        for player in all_players:
            # Handle NaN values in each player's data before prediction
            player_features = np.array([[ 
                player.get('batting_matches', 0) or 0, player.get('batting_innings', 0) or 0, 
                player.get('batting_runs', 0) or 0, player.get('batting_average', 0) or 0, 
                player.get('batting_strike_rate', 0) or 0, player.get('bowling_matches', 0) or 0, 
                player.get('bowling_innings', 0) or 0, player.get('bowling_wickets', 0) or 0, 
                player.get('bowling_average', 0) or 0, player.get('bowling_economy', 0) or 0 
            ]])
            player_features_scaled = scaler.transform(player_features)
            player_cluster_pred = kmeans.predict(player_features_scaled)[0]

            # Only add players in the same cluster but exclude the searched player
            if player_cluster_pred == player_cluster and player['name'] != player_data['name']:
                distance = euclidean(player_features_scaled[0], player_features_scaled.flatten())

                similar_players_with_distance.append((player, distance))

        # Sort players by distance and select the top 3
        similar_players_with_distance.sort(key=lambda x: x[1])
        top_similar_players = [player for player, _ in similar_players_with_distance[:3]]

        return render_template('similar_player.html', 
                               player_data=player_data, 
                               similar_players=top_similar_players, 
                               selected_player_name=player_name)

    # GET request: Show form to input player name and filters
    return render_template('search_similar_player.html')

@app.route('/player/<int:player_id>')
def player_details(player_id):
    player_data = get_player_stats(player_id)
    if player_data:
        
        return render_template('player_details.html', player_data=player_data)
    else:
        return "Player not found", 404


# Run the app
if __name__ == '__main__':
    app.run(debug=True)
