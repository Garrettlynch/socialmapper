import os
import requests
from atproto import Client

# 1. Pull credentials from GitHub Secrets
HANDLE = os.getenv('BSKY_HANDLE')
PASSWORD = os.getenv('BSKY_PASSWORD')
BASE_TILE_DIR = "tiles"

def sync_tiles():
	client = Client()
	try:
		client.login(HANDLE, PASSWORD)
		print(f"Logged in as {HANDLE}")
	except Exception as e:
		print(f"Login failed: {e}")
		return

	# 2. Search for posts from YOU with the hashtag prefix
	# We search specifically for your posts to avoid strangers' images
	search_query = f"from:{HANDLE} #map_"
	print(f"Searching for: {search_query}")
	
	try:
		results = client.app.bsky.feed.search_posts(params={'q': search_query})
	except Exception as e:
		print(f"Search failed: {e}")
		return

	for post in results.posts:
		# Extract the tag (e.g., map_0_1_1)
		map_tag = next((t['tag'] for t in post.record.tags if t['tag'].startswith('map_')), None)
		
		if not map_tag:
			continue

		# Parse coordinates
		try:
			parts = map_tag.split('_')
			z, x, y = parts[1], parts[2], parts[3]
		except (IndexError, ValueError):
			print(f"Skipping invalid tag: {map_tag}")
			continue

		# Get the first image in the post
		if not post.embed or not hasattr(post.embed, 'images') or not post.embed.images:
			continue
			
		image_url = post.embed.images[0].fullsize
		
		# 3. Create folder structure: tiles/z/x/
		target_dir = os.path.join(BASE_TILE_DIR, z, x)
		os.makedirs(target_dir, exist_ok=True)
		
		# Save as y.jpg (matching your JS logic)
		target_path = os.path.join(target_dir, f"{y}.jpg")

		# 4. Download if the file is new
		if not os.path.exists(target_path):
			print(f"Found new tile! Downloading {z}/{x}/{y}...")
			img_data = requests.get(image_url).content
			with open(target_path, 'wb') as f:
				f.write(img_data)
		else:
			print(f"Tile {z}/{x}/{y} already exists. Skipping.")

if __name__ == "__main__":
	sync_tiles()