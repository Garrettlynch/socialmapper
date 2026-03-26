import os
import re
import requests
import json
import base64
from io import BytesIO
from PIL import Image
from flask import Flask, request

app = Flask(__name__)

# Config from Render Environment Variables
HANDLE = os.getenv('BSKY_HANDLE')
PASSWORD = os.getenv('BSKY_PASSWORD')
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_REPO = os.getenv('GITHUB_REPO')

def upload_to_github(path, content, message):
	print(f"DEBUG: Attempting GitHub upload to {path}...")
	url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
	headers = {
		"Authorization": f"token {GITHUB_TOKEN}",
		"Accept": "application/vnd.github.v3+json"
	}
	
	resp = requests.get(url, headers=headers)
	sha = resp.json().get('sha') if resp.status_code == 200 else None

	payload = {
		"message": message,
		"content": base64.b64encode(content).decode('utf-8')
	}
	if sha:
		payload["sha"] = sha

	put_resp = requests.put(url, headers=headers, json=payload)
	if put_resp.status_code in [200, 201]:
		print(f"DEBUG: Successfully uploaded {path}")
		return True
	print(f"DEBUG: GitHub Upload Failed! Status: {put_resp.status_code}, Response: {put_resp.text}")
	return False

@app.route('/sync')
def sync():
	# add the security header check
	secret = os.getenv('RENDER_PASSWORD')
	if request.headers.get('X-Sync-Secret') != secret:
		print("DEBUG: Unauthorized access attempt blocked.")
		return "Unauthorized", 401

	print("DEBUG: --- Sync Started ---")
	print(f"DEBUG: Using Handle: {HANDLE}")
	
	# 1. Login to BlueSky
	login_url = "https://bsky.social/xrpc/com.atproto.server.createSession"
	login_resp = requests.post(login_url, json={"identifier": HANDLE, "password": PASSWORD})
	
	if login_resp.status_code != 200:
		print(f"DEBUG: BlueSky Login Failed! Status: {login_resp.status_code}")
		print(f"DEBUG: BlueSky Error Message: {login_resp.text}")
		return f"BlueSky Login Failed: {login_resp.text}", 500
		
	print("DEBUG: BlueSky Login Successful!")
	session = login_resp.json()
	headers = {"Authorization": f"Bearer {session['accessJwt']}"}

	# 2. Fetch Feed
	print("DEBUG: Fetching BlueSky Feed...")
	feed_url = "https://bsky.social/xrpc/app.bsky.feed.getAuthorFeed"
	feed_resp = requests.get(feed_url, params={"actor": HANDLE, "limit": 5}, headers=headers)
	feed = feed_resp.json().get('feed', [])
	print(f"DEBUG: Found {len(feed)} posts in feed.")

	for item in feed:
		text = item['post']['record'].get('text', '')
		match = re.search(r'map_(\d+)_(\d+)_(\d+)', text)
		
		if match:
			z, x, y = match.groups()
			tile_path = f"tiles/{z}/{x}/{y}.png"
			print(f"DEBUG: Found tile post for {tile_path}")
			
			# Check GitHub
			check_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{tile_path}"
			check_resp = requests.get(check_url, headers={"Authorization": f"token {GITHUB_TOKEN}"})
			
			if check_resp.status_code == 404:
				print(f"DEBUG: Tile {tile_path} is NEW. Processing...")
				images = item['post']['record'].get('embed', {}).get('images', [])
				if not images: 
					print("DEBUG: No images found in post.")
					continue
				
				blob_ref = images[0]['image']['ref']['$link']
				blob_url = "https://bsky.social/xrpc/com.atproto.sync.getBlob"
				img_data = requests.get(blob_url, params={"did": session['did'], "cid": blob_ref}, headers=headers).content
				
				img = Image.open(BytesIO(img_data)).convert('RGB')
				img = img.resize((512, 512), Image.Resampling.LANCZOS)
				
				buffer = BytesIO()
				img.save(buffer, format="PNG")
				upload_to_github(tile_path, buffer.getvalue(), f"New tile: {z}/{x}/{y}")
				return f"Success: {tile_path} synced.", 200
			else:
				print(f"DEBUG: Tile {tile_path} already exists on GitHub. Skipping.")

	print("DEBUG: --- Sync Finished (No new tiles) ---")
	return "No new tiles found.", 200

if __name__ == "__main__":
	app.run(host='0.0.0.0', port=5000)