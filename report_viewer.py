import pandas as pd
from flask import Flask, render_template, jsonify, request
import os
import argparse

app = Flask(__name__)

# Configuration
parser = argparse.ArgumentParser(description="Music Duplicate Finder Report Viewer")
parser.add_argument("csv_file", nargs='?', help="Path to the CSV report file")
args, _ = parser.parse_known_args()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE_PATH = args.csv_file if args.csv_file else os.path.join(BASE_DIR, 'full_library_new_full.csv')

# Global DataFrame to hold the data, loaded once at startup
df = pd.DataFrame()

def load_data():
    global df
    try:
        df = pd.read_csv(CSV_FILE_PATH)
        # Convert 'Quality (kbps)' to numeric, handling errors
        df['Quality (kbps)'] = pd.to_numeric(df['Quality (kbps)'], errors='coerce')
        df['Quality (kbps)'] = df['Quality (kbps)'].fillna(0).astype(int)

        # Safely convert boolean columns (handles both actual booleans and strings)
        bool_map = {True: True, False: False, 'True': True, 'False': False, 'true': True, 'false': False}
        df['Highest Quality'] = df['Highest Quality'].map(bool_map).fillna(False)
        df['Will Keep'] = df['Will Keep'].map(bool_map).fillna(False)

        # Convert 'Year' to numeric, handling errors and filling NaNs
        df['Year'] = pd.to_numeric(df['Year'], errors='coerce')
        df['Year'] = df['Year'].fillna(0).astype(int) # Fill NaN years with 0 or another placeholder

        print(f"Successfully loaded {len(df)} rows from {CSV_FILE_PATH}")
    except FileNotFoundError:
        print(f"Error: CSV file not found at {CSV_FILE_PATH}")
        df = pd.DataFrame() # Ensure df is empty if file not found
    except Exception as e:
        print(f"Error loading or processing CSV: {e}")
        df = pd.DataFrame()

# Load data when the application starts
with app.app_context():
    load_data()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/summary')
def get_summary():
    if df.empty:
        return jsonify({"error": "Data not loaded or is empty"}), 500

    total_tracks = len(df)
    tracks_to_delete_count = df[(df['Will Keep'] == False) & (df['Highest Quality'] == False)].shape[0]
    tracks_to_keep_count = df['Will Keep'].sum()

    summary_data = {
        "total_duplicate_tracks": int(total_tracks),
        "total_duplicate_groups": int(df['Group ID'].nunique()),
        "unique_artists": int(df['Artist'].nunique()),
        "unique_albums": int(df['Album'].nunique()),
        "tracks_to_delete_count": int(tracks_to_delete_count),
        "will_keep_ratio": {
            "Keep": int(tracks_to_keep_count),
            "Discard": int(total_tracks - tracks_to_keep_count) # Tracks not explicitly marked to keep
        }
    }
    return jsonify(summary_data)

@app.route('/api/duplicates_by_quality')
def get_duplicates_by_quality():
    if df.empty:
        return jsonify({"error": "Data not loaded or is empty"}), 500

    # Filter out 0 kbps if it's a placeholder for unknown quality
    quality_counts = df[df['Quality (kbps)'] > 0]['Quality (kbps)'].value_counts().sort_index().to_dict()
    return jsonify(quality_counts)

@app.route('/api/duplicates_by_format')
def get_duplicates_by_format():
    if df.empty:
        return jsonify({"error": "Data not loaded or is empty"}), 500

    format_counts = df['Format'].value_counts().to_dict()
    return jsonify(format_counts)

@app.route('/api/top_artists_duplicates')
def get_top_artists_duplicates():
    if df.empty:
        return jsonify({"error": "Data not loaded or is empty"}), 500

    top_n = request.args.get('top_n', default=10, type=int)
    artist_counts = df['Artist'].value_counts().head(top_n).to_dict()
    return jsonify(artist_counts)

@app.route('/api/top_albums_duplicates')
def get_top_albums_duplicates():
    if df.empty:
        return jsonify({"error": "Data not loaded or is empty"}), 500

    top_n = request.args.get('top_n', default=10, type=int)
    album_counts = df['Album'].value_counts().head(top_n).to_dict()
    return jsonify(album_counts)

@app.route('/api/duplicates_by_year')
def get_duplicates_by_year():
    if df.empty:
        return jsonify({"error": "Data not loaded or is empty"}), 500

    # Filter out 0 years if they are placeholders for unknown years
    year_counts = df[df['Year'] > 0]['Year'].value_counts().sort_index().to_dict()
    return jsonify(year_counts)

@app.route('/api/duplicate_groups')
def get_duplicate_groups_list():
    if df.empty:
        return jsonify({"error": "Data not loaded or is empty"}), 500

    search_term = request.args.get('search', default='', type=str).lower()
    page = request.args.get('page', default=1, type=int)
    per_page = request.args.get('per_page', default=20, type=int)

    # Aggregate data for the table view
    unique_groups_df = df.groupby('Group ID').agg(
        total_tracks=('Group ID', 'size'),
        highest_quality_count=('Highest Quality', lambda x: x.sum()),
        will_keep_count=('Will Keep', lambda x: x.sum()),
        artists=('Artist', lambda x: ', '.join(x.unique())),
        albums=('Album', lambda x: ', '.join(x.unique()))
    ).reset_index()

    if search_term:
        unique_groups_df = unique_groups_df[
            unique_groups_df['Group ID'].str.lower().str.contains(search_term) |
            unique_groups_df['artists'].str.lower().str.contains(search_term) |
            unique_groups_df['albums'].str.lower().str.contains(search_term)
        ]

    total_filtered_groups = len(unique_groups_df)
    paginated_groups_df = unique_groups_df.iloc[(page - 1) * per_page : page * per_page]

    return jsonify({
        "groups": paginated_groups_df.to_dict(orient='records'),
        "total_groups": total_filtered_groups,
        "page": page,
        "per_page": per_page
    })

@app.route('/api/group_details/<group_id>')
def get_group_details(group_id):
    if df.empty:
        return jsonify({"error": "Data not loaded or is empty"}), 500

    group_data = df[df['Group ID'] == group_id].to_dict(orient='records')
    return jsonify(group_data)

if __name__ == '__main__':
    # Create 'templates' and 'static' directories if they don't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    app.run(host='0.0.0.0', debug=True)
