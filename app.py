from flask import Flask, render_template, request, jsonify
import sys
import os
from dotenv import load_dotenv

# Add the project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '.'))
sys.path.insert(0, project_root)

from scripts.main_local import RecommendationService, get_db_session, Song, Artist

app = Flask(__name__)
load_dotenv()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/recommend', methods=['POST'])
def recommend():
    try:
        data = request.json
        title = data.get('title', '').strip()
        artist = data.get('artist', '').strip() or None

        if not title:
            return jsonify({'error': 'Please enter a song title.'}), 400

        session = get_db_session()
        service = RecommendationService()
        
        try:
            existing_song = session.query(Song).join(Artist).filter(Song.title == title).first()
            if existing_song:
                song_id = str(existing_song.song_id)
                if service.song_exists_in_chroma(song_id):
                    recommendations = service.get_recommendations_for_song(song_id, title)
                    # Add preview URLs to recommendations
                    for rec in recommendations:
                        rec['preview_url'] = service.get_song_preview_url(rec['title'], rec['artist'])
                    return jsonify({
                        'status': 'success',
                        'message': 'Found existing song',
                        'recommendations': recommendations
                    })
                else:
                    song_id = str(service.get_next_song_id())
            else:
                song_id = str(service.get_next_song_id())
        finally:
            session.close()

        lyrics = service.fetch_lyrics(title, artist)
        if not lyrics:
            return jsonify({'error': 'Could not fetch lyrics for this song. Please try another song.'}), 400

        success = service.add_song_to_chroma(song_id=song_id, title=title, artist=artist or "Unknown Artist", lyrics=lyrics)

        if success:
            recommendations = service.get_recommendations_for_song(song_id, title, lyrics)
            # Add preview URLs to recommendations
            for rec in recommendations:
                rec['preview_url'] = service.get_song_preview_url(rec['title'], rec['artist'])
            return jsonify({
                'status': 'success',
                'message': 'Successfully added song and got recommendations',
                'recommendations': recommendations
            })
        else:
            return jsonify({'error': 'Failed to add song to database'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True) 