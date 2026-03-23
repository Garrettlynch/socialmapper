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

	# Search for the string "map_" from your handle
	search_query = f"from:{HANDLE} map_"
	print(f"--- DEBUG: Searching for '{search_query}' ---")
	
	try:
		results = client.app.bsky.feed.search_posts(params={'q': search_query, 'sort': 'latest'})
		print(f"--- DEBUG: Found {len(results.posts)} total posts matching 'map_' ---")
	except Exception as e:
		print(f"--- ERROR: Search failed: {e} ---")
		return

	for post in results.posts:
		post_text = post.record.text
		print(f"--- DEBUG: Checking post text: '{post_text}' ---")

		match = re.search(r'map_(\d+)_(\d+)_(\d+)', post_text)
		if not match:
			print("--- DEBUG: No map_Z_X_Y pattern found in this text. ---")
			continue

		z, x, y = match.groups()
		print(f"--- DEBUG: Pattern Match Found! Z={z}, X={x}, Y={y} ---")

		# Check for images
		if not post.embed:
			print("--- DEBUG: Post has no embed data. ---")
			continue
		
		# BlueSky sometimes nests images differently. Let's check both possibilities.
		images = []
		if hasattr(post.embed, 'images'):
			images = post.embed.images
		elif hasattr(post.embed, 'record') and hasattr(post.embed.record, 'embeds'):
			# This handles quoted posts or specialized embeds
			for e in post.embed.record.embeds:
				if hasattr(e, 'images'):
					images = e.images

		if not images:
			print("--- DEBUG: No images found in embed. ---")
			continue
			
		image_url = images[0].fullsize
		print(f"--- DEBUG: Image URL located: {image_url[:50]}... ---")
		
		target_dir = os.path.join(BASE_TILE_DIR, z, x)
		os.makedirs(target_dir, exist_ok=True)
		target_path = os.path.join(target_dir, f"{y}.jpg")

		if not os.path.exists(target_path):
			print(f"--- ACTION: Downloading to {target_path} ---")
			img_data = requests.get(image_url).content
			with open(target_path, 'wb') as f:
				f.write(img_data)
		else:
			print(f"--- DEBUG: {target_path} already exists. Skipping. ---")

if __name__ == "__main__":
	sync_tiles()