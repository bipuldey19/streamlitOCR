import streamlit as st
import requests
import json
import re
import os
import time
import moviepy.editor as mp
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import tempfile

st.set_page_config(page_title="Spotify Lyrics GIF Video Creator", layout="wide")

# Custom CSS
st.markdown("""
<style>
.main {
    background-color: #191414;
    color: #1DB954;
}
.stButton button {
    background-color: #1DB954;
    color: white;
}
.stTextInput > div > div > input {
    background-color: #333;
    color: white;
}
</style>
""", unsafe_allow_html=True)

st.title("Spotify Lyrics GIF Video Creator")
st.markdown("Enter a Spotify track URL to create a lyrics video with GIFs")

# Function to extract Spotify track ID from URL
def extract_track_id(url):
    match = re.search(r'track/([a-zA-Z0-9]+)', url)
    if match:
        return match.group(1)
    return None

# Function to get song info from Spotify
def get_song_info(track_url):
    try:
        # Use the provided API to get song information
        api_url = f"https://spotisongdownloader.to/api/composer/spotify/xsingle_track.php?url={track_url}"
        response = requests.get(api_url)
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error fetching song info: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None

# Function to get lyrics from LrcLib
def get_lyrics(artist, track_name, album_name=None, duration=None):
    try:
        # Prepare the API URL with proper encoding
        api_url = "https://lrclib.net/api/get"
        params = {
            "artist_name": artist,
            "track_name": track_name
        }
        
        # Add optional parameters if available
        if album_name:
            params["album_name"] = album_name
        if duration:
            # Convert duration string to seconds
            if isinstance(duration, str) and 'm' in duration and 's' in duration:
                minutes, seconds = duration.split('m')
                seconds = seconds.replace('s', '').strip()
                duration_seconds = int(minutes) * 60 + int(seconds)
                params["duration"] = duration_seconds
        
        response = requests.get(api_url, params=params)
        
        if response.status_code == 200 and response.content:
            return response.json()
        else:
            st.warning(f"Lyrics not found or API error: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error fetching lyrics: {str(e)}")
        return None

# Function to search for GIFs on GIPHY
def search_gif(query, api_key):
    try:
        api_url = "https://api.giphy.com/v1/gifs/search"
        params = {
            "api_key": api_key,
            "q": query,
            "limit": 1,
            "rating": "g"
        }
        
        response = requests.get(api_url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            if data["data"]:
                return data["data"][0]["images"]["original"]["url"]
            else:
                return None
        else:
            st.warning(f"GIPHY API error: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error searching for GIF: {str(e)}")
        return None

# Function to create a text image with lyrics
def create_text_image(line, width=640, height=480, background_color=(0, 0, 0, 180)):
    # Create a transparent background
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Create semi-transparent background for text
    draw.rectangle([(0, height//2 - 50), (width, height//2 + 50)], fill=background_color)
    
    # Choose a font
    try:
        font = ImageFont.truetype("arial.ttf", 36)
    except IOError:
        font = ImageFont.load_default()
    
    # Calculate text position to center it
    text_width, text_height = draw.textsize(line, font=font)
    position = ((width - text_width) // 2, (height - text_height) // 2)
    
    # Draw the text
    draw.text(position, line, font=font, fill=(255, 255, 255, 255))
    
    return img

# Function to download a GIF and convert to frames
def download_gif_frames(gif_url, target_size=(640, 480)):
    try:
        response = requests.get(gif_url)
        if response.status_code == 200:
            # Save GIF to a temporary file
            with tempfile.NamedTemporaryFile(suffix='.gif', delete=False) as temp_file:
                temp_file.write(response.content)
                temp_file_path = temp_file.name
            
            # Load the GIF with moviepy
            clip = mp.VideoFileClip(temp_file_path)
            
            # Delete the temporary file
            os.unlink(temp_file_path)
            
            # Resize the clip to the target size
            clip = clip.resize(target_size)
            
            return clip
        else:
            st.warning(f"Failed to download GIF: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error processing GIF: {str(e)}")
        return None

# Function to create a video with lyrics and GIFs
def create_lyrics_video(lyrics, song_info, giphy_api_key):
    try:
        if not lyrics or "syncedLyrics" not in lyrics or not lyrics["syncedLyrics"]:
            st.error("No synced lyrics available for this song.")
            return None
        
        # Parse the synced lyrics
        synced_lines = []
        for line in lyrics["syncedLyrics"].split("\n"):
            if line.strip():
                time_match = re.match(r'\[(\d{2}):(\d{2})\.(\d{2})\](.*)', line)
                if time_match:
                    minutes, seconds, milliseconds, text = time_match.groups()
                    timestamp = int(minutes) * 60 + int(seconds) + int(milliseconds) / 100
                    synced_lines.append((timestamp, text.strip()))
        
        if not synced_lines:
            st.error("Failed to parse synced lyrics.")
            return None
        
        # Add an end timestamp
        duration_str = song_info.get("duration", "0m 0s")
        if 'm' in duration_str and 's' in duration_str:
            minutes, seconds = duration_str.split('m')
            seconds = seconds.replace('s', '').strip()
            total_duration = int(minutes) * 60 + int(seconds)
        else:
            # Use the last timestamp + 5 seconds as fallback
            total_duration = synced_lines[-1][0] + 5
        
        synced_lines.append((total_duration, ""))
        
        # Create clips for each line
        clips = []
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i in range(len(synced_lines) - 1):
            current_time, current_line = synced_lines[i]
            next_time = synced_lines[i+1][0]
            duration = next_time - current_time
            
            if current_line:
                search_terms = current_line.split()
                # Use the first few words as the search term for better results
                search_term = " ".join(search_terms[:min(3, len(search_terms))])
                
                status_text.text(f"Processing line {i+1}/{len(synced_lines)-1}: {current_line}")
                
                # Search for a GIF
                gif_url = search_gif(search_term, giphy_api_key)
                
                if gif_url:
                    # Download and process the GIF
                    gif_clip = download_gif_frames(gif_url)
                    
                    if gif_clip:
                        # Create text clip
                        text_clip = mp.TextClip(current_line, fontsize=30, color='white', bg_color='black',
                                              font='Arial-Bold', size=gif_clip.size, method='caption')
                        text_clip = text_clip.set_position(('center', 'bottom')).set_duration(duration)
                        
                        # Combine GIF and text
                        gif_clip = gif_clip.set_duration(duration)
                        composite = mp.CompositeVideoClip([gif_clip, text_clip])
                        clips.append(composite)
                    else:
                        # Fallback to a simple text clip
                        text_clip = mp.TextClip(current_line, fontsize=30, color='white', bg_color='black',
                                              font='Arial-Bold', size=(640, 480), method='caption')
                        text_clip = text_clip.set_duration(duration)
                        clips.append(text_clip)
                else:
                    # Fallback to a simple text clip
                    text_clip = mp.TextClip(current_line, fontsize=30, color='white', bg_color='black',
                                          font='Arial-Bold', size=(640, 480), method='caption')
                    text_clip = text_clip.set_duration(duration)
                    clips.append(text_clip)
            
            progress_bar.progress((i + 1) / (len(synced_lines) - 1))
        
        # Concatenate all clips
        status_text.text("Combining all clips...")
        final_clip = mp.concatenate_videoclips(clips)
        
        # Add song info at the beginning
        song_info_text = f"{song_info['song_name']}\nby {song_info['artist']}"
        intro_clip = mp.TextClip(song_info_text, fontsize=30, color='white', bg_color='black',
                               font='Arial-Bold', size=(640, 480), method='caption')
        intro_clip = intro_clip.set_duration(3)
        
        # Combine intro and lyrics video
        final_clip = mp.concatenate_videoclips([intro_clip, final_clip])
        
        # Create a temporary file for the output
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
            output_path = temp_file.name
        
        # Write the final video file
        status_text.text("Writing video file...")
        final_clip.write_videofile(output_path, codec='libx264', fps=24)
        
        status_text.text("Video creation complete!")
        progress_bar.progress(1.0)
        
        return output_path
    except Exception as e:
        st.error(f"Error creating video: {str(e)}")
        return None

# Main app functionality
spotify_url = st.text_input("Enter Spotify Track URL", "https://open.spotify.com/track/7CyPwkp0oE8Ro9Dd5CUDjW")
giphy_api_key = st.text_input("Enter your GIPHY API Key (Get one at https://developers.giphy.com/)", type="password")

if st.button("Generate Lyrics Video"):
    if not spotify_url:
        st.error("Please enter a Spotify track URL")
    elif not giphy_api_key:
        st.error("Please enter your GIPHY API key")
    else:
        with st.spinner("Fetching song information..."):
            song_info = get_song_info(spotify_url)
            
            if song_info:
                st.subheader("Song Information")
                col1, col2 = st.columns([1, 3])
                
                with col1:
                    st.image(song_info["img"], width=200)
                
                with col2:
                    st.write(f"**Song:** {song_info['song_name']}")
                    st.write(f"**Artist:** {song_info['artist']}")
                    st.write(f"**Album:** {song_info['album_name']}")
                    st.write(f"**Released:** {song_info['released']}")
                    st.write(f"**Duration:** {song_info['duration']}")
                
                with st.spinner("Fetching lyrics..."):
                    # Split artists if there are multiple
                    artists = song_info["artist"].split("&")[0].strip()
                    
                    lyrics = get_lyrics(
                        artist=artists,
                        track_name=song_info["song_name"].split("(")[0].strip(),
                        album_name=song_info.get("album_name", ""),
                        duration=song_info.get("duration", "")
                    )
                    
                    if lyrics:
                        st.subheader("Lyrics")
                        st.write(lyrics["plainLyrics"])
                        
                        with st.spinner("Creating lyrics video with GIFs..."):
                            video_path = create_lyrics_video(lyrics, song_info, giphy_api_key)
                            
                            if video_path:
                                st.subheader("Lyrics Video")
                                st.video(video_path)
                                
                                # Provide download link
                                with open(video_path, "rb") as file:
                                    btn = st.download_button(
                                        label="Download Video",
                                        data=file,
                                        file_name=f"{song_info['song_name'].replace(' ', '_')}_lyrics.mp4",
                                        mime="video/mp4"
                                    )
                    else:
                        st.error("Lyrics not found for this song.")
            else:
                st.error("Failed to fetch song information.")

st.markdown("---")
st.markdown("### How It Works")
st.markdown("""
1. Enter a Spotify track URL
2. The app fetches song information using the Spotify API
3. Then it gets the lyrics from LrcLib API
4. For each line of lyrics, it searches for a relevant GIF on GIPHY
5. Finally, it combines all the GIFs with the lyrics text to create a video
""")

st.markdown("### Requirements")
st.markdown("""
- GIPHY API key (get one for free at [https://developers.giphy.com/](https://developers.giphy.com/))
- Python packages: streamlit, requests, moviepy, Pillow
""")

st.markdown("### Install Dependencies")
st.code("""
pip install streamlit requests moviepy Pillow
""")

st.markdown("### Run the App")
st.code("""
streamlit run app.py
""")
