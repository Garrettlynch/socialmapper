import os
import re
import requests
from atproto import Client

HANDLE = os.getenv('BSKY_HANDLE')
PASSWORD = os.getenv('BSKY_PASSWORD')
BASE_TILE_DIR = "tiles"

def sync_tiles():
	client = Client()
	try:
		# 1. Login to establish the session
		client.login(HANDLE, PASSWORD)
		print(f"--- DEBUG: Logged in as {HANDLE} ---")
		
		# 2. Use export_session() to get the JWT reliably
		session = client.export_session()
		session_token = session.access_jwt
		print("--- DEBUG: Session token successfully retrieved ---")
		
	except Exception as e:
		print(f"--- ERROR: Login/Session failed: {e} ---")
		return

	print(f"--- DEBUG: Fetching author feed for {HANDLE} ---")
	try:
		response = client.get_author_feed(actor=HANDLE, limit=30)
		feed = response.feed
		print(f"--- DEBUG: Found {len(feed)} items in feed ---")
	except Exception as e:
		print(f"--- ERROR: Failed to fetch feed: {e} ---")
		return

	for item in feed:
		post = item.post
		if not hasattr(post.record, 'text'):
			continue
			
		post_text = post.record.text
		match = re.search(r'map_(\d+)_(\d+)_(\d+)', post_text)
		
		if not match:
			continue

		z, x, y = match.groups()
		
		# Navigate the record to find images
		if not (hasattr(post.record, 'embed') and hasattr(post.record.embed, 'images')):
			continue
			
		blob_ref = post.record.embed.images[0].image.ref
		author_did = post.author.did
		
		blob_url = f"https://bsky.social/xrpc/com.atproto.sync.getBlob?did={author_did}&cid={blob_ref}"
		
		try:
			# Request the RAW file using the session token
			img_response = requests.get(blob_url, headers={'Authorization': f'Bearer {session_token}'})
			
			if img_response.status_code != 200:
				print(f"--- ERROR: Failed to download blob {z}/{x}/{y}. Status: {img_response.status_code} ---")
				continue

			content_type = img_response.headers.get('Content-Type', '')
			
			ext_map = {
				'image/png': '.png',
				'image/webp': '.webp',
				'image/jpeg': '.jpg'
			}
			extension = ext_map.get(content_type, '.jpg')
			
			target_dir = os.path.join(BASE_TILE_DIR, z, x)
			os.makedirs(target_dir, exist_ok=True)
			
			target_path = os.path.join(target_dir, f"{y}{extension}")

			# Remove old formats if they exist to prevent duplicates (e.g. remove .webp if we have .png)
			for old_ext in ['.png', '.webp', '.jpg', '.jpeg']:
				old_path = os.path.join(target_dir, f"{y}{old_ext}")
				if old_ext != extension and os.path.exists(old_path):
					os.remove(old_path)
					print(f"--- DEBUG: Removed old format: {old_path} ---")

			if not os.path.exists(target_path):
				print(f"--- ACTION: Downloading raw blob ({content_type}) to {target_path} ---")
				with open(target_path, 'wb') as f:
					f.write(img_response.content)
			else:
				print(f"--- DEBUG: Tile {z}/{x}/{y}{extension} already exists. ---")
		except Exception as e:
			print(f"--- ERROR: Blob download failed for {z}/{x}/{y}: {e} ---")

if __name__ == "__main__":
	sync_tiles()