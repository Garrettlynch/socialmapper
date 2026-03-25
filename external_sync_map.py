import os
import re
import requests
import json
import base64
from io import BytesIO
from PIL import Image
from flask import Flask

app = Flask(__name__)

# Config from Render Environment Variables
HANDLE = os.getenv('BSKY_HANDLE')
PASSWORD = os.getenv('BSKY_PASSWORD')
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_REPO = os.getenv('GITHUB_REPO')

def upload_to_github(path, content, message):
	"""Uploads file content directly to GitHub via API."""
	url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
	headers = {
		"Authorization": f"token {GITHUB_TOKEN}",
		"Accept": "application/vnd.github.v3+json"
	}
	
	# Check if file exists to get the SHA (required for updating files)
	resp = requests.get(url, headers=headers)
	sha = resp.json().get('sha') if resp.status_code == 200 else None

	payload = {
		"message": message,
		"content": base64.b64encode(content).decode('utf-8')
	}
	if sha:
		payload["sha"] = sha

	put_resp = requests.put(url, headers=headers, json=payload)
	return put_resp.status_code in [200, 201]

def get_current_latest():
	"""Fetches the existing latest.json from GitHub."""
	url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/latest.json"
	headers = {"Authorization": f"token {GITHUB_TOKEN}"}
	resp = requests.get(url, headers=headers)
	if resp.status_code == 200:
		content = base64.b64decode(resp.json()['content'])
		return json.loads(content)
	return None

@app.route('/sync')
def sync():
	# 1. Login to BlueSky
	login_url = "https://bsky.social/xrpc/com.atproto.server.createSession"
	login_resp = requests.post(login_url, json={"identifier": HANDLE, "password": PASSWORD})
	if login_resp.status_code != 200:
		return "BlueSky Login Failed", 500
		
	session = login_resp.json()
	headers = {"Authorization": f"Bearer {session['accessJwt']}"}

	# 2. Fetch Feed
	feed_url = "https://bsky.social/xrpc/app.bsky.feed.getAuthorFeed"
	feed_resp = requests.get(feed_url, params={"actor": HANDLE, "limit": 5}, headers=headers)
	feed = feed_resp.json().get('feed', [])

	for item in feed:
		text = item['post']['record'].get('text', '')
		match = re.search(r'map_(\d+)_(\d+)_(\d+)', text)
		
		if match:
			z, x, y = match.groups()
			tile_path = f"tiles/{z}/{x}/{y}.png"
			
			# Check if tile already exists on GitHub
			check_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{tile_path}"
			check_resp = requests.get(check_url, headers={"Authorization": f"token {GITHUB_TOKEN}"})
			
			if check_resp.status_code == 404:
				# TILE IS NEW: Process and Upload
				images = item['post']['record'].get('embed', {}).get('images', [])
				if not images: continue
				
				blob_ref = images[0]['image']['ref']['$link']
				blob_url = "https://bsky.social/xrpc/com.atproto.sync.getBlob"
				img_data = requests.get(blob_url, params={"did": session['did'], "cid": blob_ref}, headers=headers).content
				
				# Resize using Pillow
				img = Image.open(BytesIO(img_data)).convert('RGB')
				img = img.resize((512, 512), Image.Resampling.LANCZOS)
				
				buffer = BytesIO()
				img.save(buffer, format="PNG")
				final_content = buffer.getvalue()
				
				# Upload Tile
				upload_to_github(tile_path, final_content, f"New tile: {z}/{x}/{y}")
				
				# Update latest.json
				old_latest = get_current_latest()
				new_json = {
					"newest": {"z": int(z), "x": int(x), "y": int(y)},
					"previous": old_latest.get('newest') if old_latest else None
				}
				upload_to_github("latest.json", json.dumps(new_json, indent=4).encode(), "Update latest.json")
				
				return f"Success: Tile {z}/{x}/{y} uploaded.", 200

	return "No new tiles found.", 200

if __name__ == "__main__":
	# For local testing only
	app.run(host='0.0.0.0', port=5000)