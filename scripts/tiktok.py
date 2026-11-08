"""Helper per il collegamento a TikTok: scambio codice OAuth, refresh e upload in bozza."""
import os, sys, json, math, requests

API = "https://open.tiktokapis.com"
REDIRECT = "https://csaldano08-ai.github.io/tecno-timmy-legal/"


def token_call(data):
    data = dict(data, client_key=os.environ["TT_CLIENT_KEY"], client_secret=os.environ["TT_CLIENT_SECRET"])
    r = requests.post(API + "/v2/oauth/token/", data=data, timeout=60)
    j = r.json()
    if "access_token" not in j:
        sys.exit("Errore TikTok: %s - %s" % (j.get("error"), j.get("error_description")))
    return j


def save_refresh(j):
    with open("/tmp/refresh_token", "w") as f:
        f.write(j["refresh_token"])


def auth(code):
    j = token_call({"grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT})
    save_refresh(j)
    print("Collegamento riuscito. Scope:", j.get("scope"))


def upload(path):
    j = token_call({"grant_type": "refresh_token", "refresh_token": os.environ["TT_REFRESH_TOKEN"]})
    save_refresh(j)
    h = {"Authorization": "Bearer " + j["access_token"], "Content-Type": "application/json; charset=UTF-8"}
    size = os.path.getsize(path)
    chunk = size if size <= 64 * 1024 * 1024 else 10 * 1024 * 1024
    total = max(1, size // chunk)
    body = {"source_info": {"source": "FILE_UPLOAD", "video_size": size, "chunk_size": chunk, "total_chunk_count": total}}
    r = requests.post(API + "/v2/post/publish/inbox/video/init/", headers=h, json=body, timeout=60).json()
    if r.get("error", {}).get("code") != "ok":
        sys.exit("Init fallito: %s" % r.get("error"))
    url = r["data"]["upload_url"]
    with open(path, "rb") as f:
        for i in range(total):
            start = i * chunk
            data = f.read(chunk if i < total - 1 else size - start)
            end = start + len(data) - 1
            hh = {"Content-Type": "video/mp4", "Content-Length": str(len(data)),
                  "Content-Range": "bytes %d-%d/%d" % (start, end, size)}
            pr = requests.put(url, headers=hh, data=data, timeout=600)
            if pr.status_code not in (200, 201, 206):
                sys.exit("Upload fallito al blocco %d: HTTP %d" % (i + 1, pr.status_code))
    print("Video caricato nella casella di posta TikTok come bozza. publish_id:", r["data"]["publish_id"])


if __name__ == "__main__":
    {"auth": auth, "upload": upload}[sys.argv[1]](sys.argv[2])
