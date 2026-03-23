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
		client.login(HANDLE, PASSWORD)
		print(f"Successfully logged in as {HANDLE}")
	except Exception as e:
		print(f"Login failed: {e}")
		return

	# 2. Search for the text "map_" in your posts. 
	# This is more reliable than strict hashtag filtering.
	search_query = f"from:{HANDLE} map_"
	print(f"Searching BlueSky for: {search_query}")
	
	try:
		# We fetch the latest posts containing your search string
		results = client.app.bsky.feed.search_posts(params={'q': search_query, 'sort': 'latest'})
	except Exception as e:
		print(f"Search failed: {e}")
		return

	if not results.posts:
		print("No posts found matching the criteria.")
		return

	for post in results.posts:
		post_text = post.record.text
		print(f"Processing post: '{post_text[:50]}...'")

		# 3. Use Regex to find the pattern map_Z_X_Y
		# This matches map_ followed by three groups of numbers
		match = re.search(r'map_(\d+)_(\d+)_(\d+)', post_text)
		
		if not match:
			print("No coordinate pattern found in this post text. Skipping.")
			continue

		# Extract coordinates from the regex match groups
		z, x, y = match.groups()
		print(f"Found tile coordinates: Z={z}, X={x}, Y={y}")

		# 4. Check for attached images
		if not post.embed or not hasattr(post.embed, 'images') or not post.embed.images:
			print("Post found but no image is attached. Skipping.")
			continue
			
		image_url = post.embed.images[0].fullsize
		
		# 5. Create folder structure: tiles/z/x/
		target_dir = os.path.join(BASE_TILE_DIR, z, x)
		os.makedirs(target_dir, exist_ok=True)
		
		# Save as y.jpg (matching your Leaflet JS logic)
		target_path = os.path.join(target_dir, f"{y}.jpg")

		# 6. Download if the file is new
		if not os.path.exists(target_path):
			print(f"Downloading new tile to: {target_path}")
			try:
				img_data = requests.get(image_url).content
				with open(target_path, 'wb') as f:
					f.write(img_data)
				print("Download complete.")
			except Exception as e:
				print(f"Failed to download image: {e}")
		else:
			print(f"Tile {z}/{x}/{y} already exists in repository. Skipping.")

if __name__ == "__main__":
	sync_tiles()
	print("Sync process finished.")