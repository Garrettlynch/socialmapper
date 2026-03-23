import os
import re
import requests
from io import BytesIO
from PIL import Image

HANDLE = os.getenv('BSKY_HANDLE')
PASSWORD = os.getenv('BSKY_PASSWORD')
BASE_TILE_DIR = "tiles"
TARGET_SIZE = (512, 512)

def process_image(content, extension):
	"""Checks image size and resizes to 512x512 if necessary."""
	img = Image.open(BytesIO(content))
	
	# Preserve transparency for formats that support it
	if extension in ['.png', '.webp']:
		img = img.convert("RGBA")
	else:
		img = img.convert("RGB")
	
	if img.size != TARGET_SIZE:
		print(f"--- ACTION: Resizing from {img.size} to {TARGET_SIZE} ---")
		img = img.resize(TARGET_SIZE, Image.Resampling.LANCZOS)
	
	output = BytesIO()
	# Map extension back to Pillow's save format
	save_formats = {'.png': 'PNG', '.webp': 'WEBP', '.jpg': 'JPEG'}
	fmt = save_formats.get(extension, 'JPEG')
	
	# WebP and JPEG use 'quality', PNG is lossless by default
	if fmt == 'WEBP':
		img.save(output, format=fmt, lossless=True) # Change to quality=90 if you want smaller files
	elif fmt == 'JPEG':
		img.save(output, format=fmt, quality=95)
	else:
		img.save(output, format=fmt)
		
	return output.getvalue()

def sync_tiles():
	print(f"--- DEBUG: Starting sync for {HANDLE} ---")
	
	# 1. Login
	login_url = "https://bsky.social/xrpc/com.atproto.server.createSession"
	try:
		login_resp = requests.post(login_url, json={"identifier": HANDLE, "password": PASSWORD})
		login_resp.raise_for_status()
		session_data = login_resp.json()
		access_jwt = session_data['accessJwt']
		user_did = session_data['did']
	except Exception as e:
		print(f"--- ERROR: Login failed: {e} ---")
		return

	# 2. Fetch Feed
	feed_url = "https://bsky.social/xrpc/app.bsky.feed.getAuthorFeed"
	headers = {"Authorization": f"Bearer {access_jwt}"}
	try:
		feed_resp = requests.get(feed_url, params={"actor": HANDLE, "limit": 30}, headers=headers)
		feed_resp.raise_for_status()
		feed = feed_resp.json().get('feed', [])
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
		embed = record.get('embed', {})
		images = embed.get('images', [])
		if not images:
			continue
			
		blob_ref = images[0].get('image', {}).get('ref', {}).get('$link')
		
		# 3. Download and Process
		blob_url = "https://bsky.social/xrpc/com.atproto.sync.getBlob"
		try:
			img_resp = requests.get(blob_url, params={"did": user_did, "cid": blob_ref}, headers=headers)
			if img_resp.status_code != 200:
				continue

			# Improved Detection (Magic Numbers)
			file_content = img_resp.content
			header = file_content[:12]
			
			if header.startswith(b'\x89PNG\r\n\x1a\n'):
				extension = '.png'
			elif header.startswith(b'RIFF') and header[8:12] == b'WEBP':
				extension = '.webp'
			else:
				extension = '.jpg'
			
			final_content = process_image(file_content, extension)
			
			target_dir = os.path.join(BASE_TILE_DIR, z, x)
			os.makedirs(target_dir, exist_ok=True)
			
			# Cleanup logic (removes any existing file with a different extension)
			for ext in ['.png', '.webp', '.jpg', '.jpeg']:
				old_path = os.path.join(target_dir, f"{y}{ext}")
				if os.path.exists(old_path) and ext != extension:
					os.remove(old_path)

			target_path = os.path.join(target_dir, f"{y}{extension}")
			with open(target_path, 'wb') as f:
				f.write(final_content)
			print(f"--- SUCCESS: Processed {z}/{x}/{y} as {extension} ---")
				
		except Exception as e:
			print(f"--- ERROR: Processing failed for {z}/{x}/{y}: {e} ---")

if __name__ == "__main__":
	sync_tiles()