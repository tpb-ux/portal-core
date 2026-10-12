"""IndexNow: build grava data/indexnow_pendentes.txt (URLs indexáveis novas/alteradas); `python -m core.indexnow ping` envia e confirma os hashes.
Com noindex global nada é enviado."""
import hashlib, json, re, sys, urllib.request
from pathlib import Path
def _norm(h): return re.sub(r'style\.css\?v=\w+|<script type="application/ld\+json">.*?</script>|© \d{4}', "", h, flags=re.S)
def diff(S):
    hf, pf = S.ROOT / "data/indexnow_hashes.json", S.ROOT / "data/indexnow_pendentes.txt"
    old = json.loads(hf.read_text()) if hf.exists() else {}; new, ch = {}, []
    if not S.NOINDEX:
        for u in S.indexaveis():
            f = S.OUT / u.lstrip("/"); f = f / "index.html" if u.endswith("/") else f
            new[u] = hashlib.sha1(_norm(f.read_text(encoding="utf-8")).encode()).hexdigest()[:16]
            if old.get(u) != new[u]: ch.append(S.BASE + u)
    pf.write_text("\n".join(sorted(ch)), encoding="utf-8"); (S.ROOT / "data/indexnow_hashes.next.json").write_text(json.dumps(new, separators=(",", ":")))
    print(f"IndexNow: {len(ch)} URL(s) novas/alteradas" + (" (desligado: noindex global)" if S.NOINDEX else ""))
def ping(root="."):
    import yaml
    R = Path(root); cfg = yaml.safe_load((R / "config.yaml").read_text()); key = cfg.get("indexnow_key"); base = cfg["base_url"].rstrip("/")
    pf, nxt, hf = R / "data/indexnow_pendentes.txt", R / "data/indexnow_hashes.next.json", R / "data/indexnow_hashes.json"
    urls = [u for u in pf.read_text().split("\n") if u] if pf.exists() else []
    if cfg.get("noindex_global") or not key or not urls: print("IndexNow: nada a enviar"); return
    for i in range(0, len(urls), 10000):
        body = json.dumps({"host": base.split("//")[1], "key": key, "keyLocation": f"{base}/{key}.txt", "urlList": urls[i:i + 10000]}).encode()
        try: r = urllib.request.urlopen(urllib.request.Request("https://api.indexnow.org/indexnow", data=body, headers={"Content-Type": "application/json; charset=utf-8"}), timeout=60); print("IndexNow:", r.status, len(urls[i:i + 10000]))
        except Exception as e: print("IndexNow erro:", e); return
    if nxt.exists(): hf.write_text(nxt.read_text()); nxt.unlink()
if __name__ == "__main__" and sys.argv[1:2] == ["ping"]: ping(sys.argv[2] if len(sys.argv) > 2 else ".")
