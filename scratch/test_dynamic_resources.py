"""
Quick test: verify the new fully-dynamic recommender fetches real URLs
from DuckDuckGo for each missing skill.
"""
import sys
sys.path.insert(0, "Backend")

from models.recomendor import _fetch_all_resources_for_skills, _fetch_videos_parallel

TEST_SKILLS = ["Python", "TensorFlow", "Docker"]

print("=" * 60)
print("Testing LIVE DDG resource fetch for:", TEST_SKILLS)
print("=" * 60)

resources = _fetch_all_resources_for_skills(TEST_SKILLS)

for skill, items in resources.items():
    print(f"\n--- {skill} ---")
    for r in items:
        print(f"  [{r['type'].upper():8}] {r['title']}")
        print(f"           {r['url']}")

print("\n" + "=" * 60)
print("Testing LIVE YouTube video fetch for:", TEST_SKILLS)
print("=" * 60)

videos = _fetch_videos_parallel(TEST_SKILLS, limit=2, timeout_per_skill=8.0)
for skill, vids in videos.items():
    print(f"\n--- {skill} YouTube Videos ---")
    for v in vids:
        print(f"  {v['title'][:70]}")
        print(f"  {v['url']}")
