import urllib.request, urllib.parse

prompt = "a cute blue cartoon cat sitting on a cloud"
encoded = urllib.parse.quote(prompt)
url = f"https://image.pollinations.ai/prompt/{encoded}?width=512&height=512&nologo=true"
print("Downloading from:", url)
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
response = urllib.request.urlopen(req, timeout=60)
data = response.read()
ct = response.headers.get("Content-Type")
print(f"SUCCESS! Got {len(data)} bytes, content-type: {ct}")
with open("test_pollinations.png", "wb") as f:
    f.write(data)
print("Saved to test_pollinations.png")
