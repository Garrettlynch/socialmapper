import os
import re
import requests
from atproto import Client

# 1. Pull credentials from GitHub Secrets
HANDLE = os.getenv('BSKY_HANDLE')
PASSWORD = os.getenv('BSKY_PASSWORD')
BASE_TILE_DIR = "tiles"

def sync_tiles():
	client = Client()
	try:
		# Log in to BlueSky
		client.login(HANDLE, PASSWORD)
		print(f"--- DEBUG: Logged in as {HANDLE} ---")
	except Exception as e:
		print(f"--- ERROR: Login failed: {e} ---")
		return

	# 2. Fetch your personal feed (Author Feed)
	# This is much faster and more reliable than the global search
	print(f"--- DEBUG: Fetching author feed for {HANDLE} ---")
	
	try:
		# We check the last 30 posts on your timeline
		response = client.get_author_feed(actor=HANDLE, limit=30)
		feed = response.feed
		print(f"--- DEBUG: Found {len(feed)} total posts in your recent feed ---")
	except Exception as e:
		print(f"--- ERROR: Failed to fetch feed: {e} ---")
		return

	for item in feed:
		post = item.post
		# Some items in the feed might be reposts; we only want your original posts
		if not hasattr(post.record, 'text'):
			continue
			
		post_text = post.record.text
		
		# 3. Use Regex to find the pattern map_Z_X_Y
		match = re.search(r'map_(\d+)_(\d+)_(\d+)', post_text)
		
		if not match:
			continue

		z, x, y = match.groups()
		print(f"--- DEBUG: Found potential tile: map_{z}_{x}_{y} ---")

		# 4. Check for attached images
		# We check both standard embeds and nested embeds (like in quoted posts)
		images = []
		if post.embed:
			if hasattr(post.embed, 'images'):
				images = post.embed.images
			elif hasattr(post.embed, 'record') and hasattr(post.embed.record, 'embeds'):
				for e in post.embed.record.embeds:
					if hasattr(e, 'images'):
						images = e.images

		if not images:
			print(f"--- DEBUG: Pattern found in '{post_text[:20]}...' but no image attached. ---")
			continue
			
		image_url = images[0].fullsize
		
		# 5. Create folder structure: tiles/z/x/
		target_dir = os.path.join(BASE_TILE_DIR, z, x)
		os.makedirs(target_dir, exist_ok=True)
		
		# Save as y.jpg
		target_path = os.path.join(target_dir, f"{y}.jpg")

		# 6. Download if the file is new
		if not os.path.exists(target_path):
			print(f"--- ACTION: Downloading new tile to {target_path} ---")
			try:
				img_data = requests.get(image_url).content
				with open(target_path, 'wb') as f:
					f.write(img_data)
				print("--- DEBUG: Save successful. ---")
			except Exception as e:
				print(f"--- ERROR: Download failed: {e} ---")
		else:
			print(f"--- DEBUG: Tile {z}/{x}/{y} already exists. Skipping. ---")

if __name__ == "__main__":
	sync_tiles()
	print("--- DEBUG: Sync process finished. ---")