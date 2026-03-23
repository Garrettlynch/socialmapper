import os
import re
import requests

HANDLE = os.getenv('BSKY_HANDLE')
PASSWORD = os.getenv('BSKY_PASSWORD')
BASE_TILE_DIR = "tiles"

def sync_tiles():
	print(f"--- DEBUG: Starting sync for {HANDLE} ---")
	
	# 1. Direct Login via XRPC to get a JWT
	login_url = "https://bsky.social/xrpc/com.atproto.server.createSession"
	try:
		login_resp = requests.post(login_url, json={"identifier": HANDLE, "password": PASSWORD})
		login_resp.raise_for_status()
		session_data = login_resp.json()
		access_jwt = session_data['accessJwt']
		user_did = session_data['did']
		print("--- DEBUG: Login successful, JWT retrieved ---")
	except Exception as e:
		print(f"--- ERROR: Direct Login failed: {e} ---")
		return

	# 2. Fetch Feed via XRPC
	feed_url = "https://bsky.social/xrpc/app.bsky.feed.getAuthorFeed"
	headers = {"Authorization": f"Bearer {access_jwt}"}
	try:
		feed_resp = requests.get(feed_url, params={"actor": HANDLE, "limit": 30}, headers=headers)
		feed_resp.raise_for_status()
		feed = feed_resp.json().get('feed', [])
		print(f"--- DEBUG: Found {len(feed)} items in feed ---")
	except Exception as e:
		print(f"--- ERROR: Feed fetch failed: {e} ---")
		return

	for item in feed:
		post = item.get('post', {})
		record = post.get('record', {})
		post_text = record.get('text', '')
		
		match = re.search(r'map_(\d+)_(\d+)_(\d+)', post_text)
		if not match:
			continue

		z, x, y = match.groups()
		
		# Navigate the JSON structure for images
		embed = record.get('embed', {})
		images = embed.get('images', [])
		
		if not images:
			continue
			
		# Get the CID (Content ID) of the blob
		blob_ref = images[0].get('image', {}).get('ref', {}).get('$link')
		if not blob_ref:
			continue
		
		# 3. Download the Raw Blob
		blob_url = "https://bsky.social/xrpc/com.atproto.sync.getBlob"
		try:
			blob_params = {"did": user_did, "cid": blob_ref}
			img_resp = requests.get(blob_url, params=blob_params, headers=headers)
			
			if img_resp.status_code != 200:
				print(f"--- ERROR: Blob {z}/{x}/{y} failed with status {img_resp.status_code} ---")
				continue

			# --- NEW DETECTION LOGIC START ---
			# Peek at the first few bytes (the "Magic Number") to identify the real file type
			file_content = img_resp.content
			header = file_content[:8]
			
			if header.startswith(b'\x89PNG\r\n\x1a\n'):
				extension = '.png'
				detected_type = 'image/png'
			elif header.startswith(b'RIFF') and header[8:12] == b'WEBP':
				extension = '.webp'
				detected_type = 'image/webp'
			else:
				extension = '.jpg'
				detected_type = 'image/jpeg'
			# --- NEW DETECTION LOGIC END ---
			
			target_dir = os.path.join(BASE_TILE_DIR, z, x)
			os.makedirs(target_dir, exist_ok=True)
			
			# Clean up old formats to avoid cluttering the repo
			for old_ext in ['.png', '.webp', '.jpg', '.jpeg']:
				old_path = os.path.join(target_dir, f"{y}{old_ext}")
				if os.path.exists(old_path) and old_ext != extension:
					os.remove(old_path)

			target_path = os.path.join(target_dir, f"{y}{extension}")
			
			with open(target_path, 'wb') as f:
				f.write(file_content)
			print(f"--- ACTION: Saved {target_path} (Detected: {detected_type}) ---")
				
		except Exception as e:
			print(f"--- ERROR: Download failed for {z}/{x}/{y}: {e} ---")

if __name__ == "__main__":
	sync_tiles()