import requests
import re
import urllib.parse
import html

def search_ddg(query: str, limit: int = 5) -> list:
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        r = requests.get(url, headers=headers, timeout=8)
        if r.status_code != 200:
            print(f"DDG search returned status {r.status_code}")
            return []
        
        # Match result links
        matches = re.findall(r'class="result__a"\s+href="([^"]+)"[^>]*>(.*?)</a>', r.text, re.DOTALL)
        results = []
        for href, title_html in matches:
            if 'uddg=' in href:
                uddg_match = re.search(r'uddg=([^&]+)', href)
                if uddg_match:
                    raw_url = urllib.parse.unquote(uddg_match.group(1))
                    title = html.unescape(re.sub(r'<[^>]+>', '', title_html)).strip()
                    results.append({"title": title, "url": raw_url})
                    if len(results) >= limit:
                        break
        return results
    except Exception as e:
        print(f"Error searching DDG: {e}")
        return []

if __name__ == "__main__":
    res = search_ddg("python official documentation")
    for r in res:
        print(f"Title: {r['title']}\nURL: {r['url']}\n")
