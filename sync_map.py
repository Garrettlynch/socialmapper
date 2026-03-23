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
		
		images = []
		if post.embed:
			if hasattr(post.embed, 'images'):
				images = post.embed.images
			elif hasattr(post.embed, 'record') and hasattr(post.embed.record, 'embeds'):
				for e in post.embed.record.embeds:
					if hasattr(e, 'images'):
						images = e.images

		if not images:
			continue
			
		image_url = images[0].fullsize
		
		try:
			img_response = requests.get(image_url)
			content_type = img_response.headers.get('Content-Type', '')
			
			# Map MIME types to extensions
			ext_map = {
				'image/png': '.png',
				'image/webp': '.webp',
				'image/jpeg': '.jpg'
			}
			# Default to .jpg if BlueSky sends something unexpected
			extension = ext_map.get(content_type, '.jpg')
			
			target_dir = os.path.join(BASE_TILE_DIR, z, x)
			os.makedirs(target_dir, exist_ok=True)
			
			target_path = os.path.join(target_dir, f"{y}{extension}")

			if not os.path.exists(target_path):
				print(f"--- ACTION: Downloading {content_type} to {target_path} ---")
				with open(target_path, 'wb') as f:
					f.write(img_response.content)
			else:
				print(f"--- DEBUG: Tile {z}/{x}/{y}{extension} already exists. ---")
		except Exception as e:
			print(f"--- ERROR: Download failed for {z}/{x}/{y}: {e} ---")

if __name__ == "__main__":
	sync_tiles()