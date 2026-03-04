# search / fetch
# skills/web.py
import webbrowser

def web_search(query: str) -> str:
    url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    webbrowser.open(url)
    return f"Searching the web for: {query}"
