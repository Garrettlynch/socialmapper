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
		client.login(HANDLE, PASSWORD)
		print(f"--- DEBUG: Logged in as {HANDLE} ---")
		# We need this token to verify our 'Blob' request
		session_token = client.get_session_token()
	except Exception as e:
		print(f"--- ERROR: Login failed: {e} ---")
		return

	print(f"--- DEBUG: Fetching author feed for {HANDLE} ---")
	try:
		response = client.get_author_feed(actor=HANDLE, limit=30)
		feed = response.feed
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
		
		# Navigate the data structure to find the 'Blob' reference
		if not (post.record.embed and hasattr(post.record.embed, 'images')):
			continue
			
		# Get the first image blob
		blob_ref = post.record.embed.images[0].image.ref
		author_did = post.author.did
		
		# Construct the direct 'getBlob' URL
		blob_url = f"https://bsky.social/xrpc/com.atproto.sync.getBlob?did={author_did}&cid={blob_ref}"
		
		try:
			# We MUST include the Authorization header to get the original file
			img_response = requests.get(blob_url, headers={'Authorization': f'Bearer {session_token}'})
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

			if not os.path.exists(target_path):
				print(f"--- ACTION: Downloading Blob ({content_type}) to {target_path} ---")
				with open(target_path, 'wb') as f:
					f.write(img_response.content)
			else:
				print(f"--- DEBUG: Tile {z}/{x}/{y}{extension} already exists. ---")
		except Exception as e:
			print(f"--- ERROR: Blob download failed for {z}/{x}/{y}: {e} ---")

if __name__ == "__main__":
	sync_tiles()