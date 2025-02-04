from flask_cors import CORS
import requests
from real_time_insights import *
from flask import Flask, request, jsonify, send_from_directory, send_file
import uuid
import base64
import json
from historic_insights import *
from baseball_agent_chat import BaseballAnalysisService
from data_processor_vertex_ai import DataProcessor
from video_analyzer import VideoAnalyzer
import os
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)   
CORS(app)
SEGMENT_DIR = os.path.join(os.getcwd(), "segments")
SAVED_SEGMENTS_DIR = os.path.join(os.getcwd(), "saved_segments")
if not os.path.exists(SAVED_SEGMENTS_DIR):
    os.makedirs(SAVED_SEGMENTS_DIR)

DATA_DIRECTORY = "data/event"
GOOGLE_API_KEY = os.environ['GOOGLE_API_KEY']
MODEL_ID = "gemini-2.0-flash-exp"


analysis_service = BaseballAnalysisService()
data_processor = DataProcessor(directory_path=DATA_DIRECTORY)
analyzer = VideoAnalyzer(GOOGLE_API_KEY, MODEL_ID)

url = "https://statsapi.mlb.com/api/v1.1/game/775296/feed/live"
response = requests.get(url)
raw_data = response.json()

gumbo_data = GumboData(**raw_data)
gumbo_utils = GumboUtilities(gumbo_data)
sync_data = {}
with open("sync.json", "r") as f:
    sync_data = json.load(f)
print("Running your server")

@app.route('/team-logo', methods=['POST'])
def get_team_logo():
    try:
        json_data = request.get_json()
        team_id = json_data["team_id"]
        logo_url = f"https://www.mlbstatic.com/team-logos/{team_id}.svg"
        return logo_url
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/list-segments', methods=['GET'])
def list_segments():
    try:
        print("Listing segments")
        segments = os.listdir(SEGMENT_DIR)
        segments = sorted(segments)
        return jsonify({"segments": segments})
    except Exception as e:
        print(f"Error listing segments: {e}")
        return jsonify({"error": "Failed to list segments"}), 500

@app.route('/stream-segment', methods=['GET'])
def stream_segment():
    try:
        segment_name = request.args.get('segmentName')
        if not segment_name:
            return jsonify({"error": "Segment Name is required"}), 400
        segment_path = os.path.join(SEGMENT_DIR, segment_name)
        if not os.path.exists(segment_path):
            return jsonify({"error": f"Segment {segment_name} not found."}), 404
        return send_file(segment_path, mimetype='video/mp4')
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/segment-description', methods=['POST'])
def segment_description():
    try:
        data = request.get_json()
        segment_name = data.get('segmentName')
        if not segment_name:
            return jsonify({"error": "Segment Name is required"}), 400
        segment_path = os.path.join(SEGMENT_DIR, segment_name)
        if not os.path.exists(segment_path):
            return jsonify({"error": f"Segment {segment_name} not found."}), 404
        with open("sync.json", "r") as f:
            data = json.load(f)
        live_data_index = data.get(segment_name)
        if segment_name != "segment_003.mp4":
            live_data_index += 1
        live_data = json.loads(gumbo_utils.get_all_plays()[live_data_index].model_dump_json())
        return live_data
    except Exception as e:
        print(f"Error fetching live data: {e}")
        return jsonify({"error": "Error fetching live data"}), 500

@app.route('/save-segment', methods=['POST'])
def save_segment():
    try:
        data = request.get_json()
        video_data = data.get('videoData')
        if not video_data:
            return jsonify({"error": "Video data is required"}), 400
        if not isinstance(video_data, str) or not video_data.startswith('data:video/mp4;base64,'):
            return jsonify({"error": "Invalid video data format. Expected a base64 string."}), 400
        base64_data = video_data.replace('data:video/mp4;base64,', '')
        video_buffer = base64.b64decode(base64_data)
        segment_name = f"video_segment_{uuid.uuid4()}.mp4"
        file_path = os.path.join(SAVED_SEGMENTS_DIR, segment_name)
        with open(file_path, 'wb') as f:
            f.write(video_buffer)
        return jsonify({"message": f"Segment saved successfully as {segment_name}"}), 200
    except Exception as e:
        print(f"Error saving video segment: {e}")
        return jsonify({"error": "Failed to save segment"}), 500

@app.route('/get-latest-video', methods=['GET'])
async def get_latest_video():
    try:
        video_files = [file for file in os.listdir(SAVED_SEGMENTS_DIR) if file.endswith('.mp4')]
        if not video_files:
            return jsonify({"error": "No video segments found."}), 404
        latest_video_file = max(video_files, key=lambda file: os.path.getmtime(os.path.join(SAVED_SEGMENTS_DIR, file)))
        return jsonify({"latestVideoFile": latest_video_file}), 200
    except Exception as e:
        print(f"Error in get-latest-video: {e}")
        return jsonify({"error": "Internal server error while fetching the latest video."}), 500

@app.route('/saved_segments/<filename>', methods=['GET'])
def serve_saved_segment(filename):
    try:
        file_path = os.path.join(SAVED_SEGMENTS_DIR, filename)
        if not os.path.exists(file_path):
            return jsonify({"error": "File not found"}), 404
        return send_from_directory(SAVED_SEGMENTS_DIR, filename)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def home():
    try:
        return jsonify(message="Welcome to the Flask server!")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/team-details', methods=['POST'])
def get_teams():
    try:
        json_data = request.get_json()
        team_details = gumbo_utils.get_team_details(json_data["team_type"])
        season = json_data["season"]
        players_inside_team = requests.get(f"https://statsapi.mlb.com/api/v1/teams/{team_details.id}/roster?season={season}").json()
        team_info = {
            "team_name": team_details.name,
            "team_id": team_details.id,
            "venue_name": team_details.venue.name,
            "venue_id": team_details.venue.id,
            "players": players_inside_team['roster']
        }
        return team_info
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/player-details', methods=['POST'])
def get_players():
    try:
        json_data = request.get_json()
        player_details = gumbo_utils.get_player_details(json_data["player_id"])
        return player_details.model_dump_json()
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/player-image', methods=['POST'])
def get_player_image():
    try:
        json_data = request.get_json()
        player_id = json_data["player_id"]
        img_url = f"https://securea.mlb.com/mlb/images/players/head_shot/{player_id}.jpg"
        return img_url
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/match-overview', methods=['POST'])
async def match_overview():
    try:
        json_data = request.get_json()
        print(json_data)
        chunk_number = json_data["chunk_number"]
        genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
        client = genai.GenerativeModel('gemini-1.5-flash')
        index_number = sync_data.get(chunk_number)
        app = BaseballInsightApp(gumbo_utils, client, index_number)
        data_processor = BaseballDataProcessor()
        data_processor.load_data('mlb_batters_stats_combined.csv', 'mlb_pitchers_stats_combined.csv')
        historic_insight_analyzer = BaseballStrategyAnalyzer(os.environ["GOOGLE_API_KEY"])
        insights = await app.process_game_update(historic_insight_analyzer, data_processor)
        return insights
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        data = request.get_json()
        print("Getting json data")
        print(data)
        query = data['query']
        video = data['video']
        current_time = data['current_time']
        complete_path_video = os.path.join(SEGMENT_DIR, video)
        result = analysis_service.run(query, complete_path_video, current_time)
        return jsonify({"result": result})
    except Exception as e:
        print(f"Error during processing: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/ingest-data', methods=['POST'])
def ingest_data_endpoint():
    try:
        data_processor.ingest_data()
        return jsonify({"message": "Data ingestion process initiated"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/analyze_rag', methods=['POST'])
def analyze_rag():
    try:
        video_dir = request.form.get('video_dir')
        output_dir = request.form.get('output_dir')
        max_workers = int(request.form.get('max_workers', 4))
        if not video_dir or not output_dir:
            return jsonify({"error": "video_dir and output_dir are required"}), 400
        analyzer.process_segments(video_dir, output_dir, max_workers)
        return jsonify({"message": "Video segments processed successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    url = "https://statsapi.mlb.com/api/v1.1/game/775296/feed/live"
    response = requests.get(url)
    raw_data = response.json()
    gumbo_data = GumboData(**raw_data)
    gumbo_utils = GumboUtilities(gumbo_data)
    sync_data = {}
    with open("sync.json", "r") as f:
        sync_data = json.load(f)
    print("Running your server")
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 7770)))
    print("started")