"""Check public ChefTap endpoints without sending account credentials."""
import urllib.error
import urllib.request
from bs4 import BeautifulSoup

for url in (
    "https://cheftap.com/",
    "https://cheftap.com/xmlrpc.php",
    "https://media.cheftap.com/",
):
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        response = urllib.request.urlopen(request, timeout=15)
    except urllib.error.HTTPError as error:
        response = error
    except Exception as error:
        print(url, type(error).__name__, str(error)[:120])
        continue
    with response:
        print(url, response.status, response.headers.get("Server"), response.headers.get("Retry-After"))
        body = response.read(10000).decode("utf-8", errors="replace")
        print(" ".join(BeautifulSoup(body, "html.parser").stripped_strings)[:500])
