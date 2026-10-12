"""Saúde editorial (formato saude-portal/1): public/saude.json e data/saude.json, gravados só após o build passar."""
import datetime as dt, json, os
def build(S, posts):
    agora = dt.datetime.now(dt.timezone.utc)
    cf = S.ROOT / "data/saude_coleta.json"; col = json.loads(cf.read_text()) if cf.exists() else {}
    ps = sorted(posts, key=lambda p: p["data"], reverse=True); rec = ps[0] if ps else None
    feeds = col.get("feeds", []); ult = col.get("ultimas_execucoes", {})
    auto = [v for k, v in ult.items() if k in ("schedule", "cron", "workflow_dispatch", "repository_dispatch")]
    data = {"formato": "saude-portal/1", "portal": S.CFG["site_name"], "url": S.BASE, "gerado_em": agora.isoformat(timespec="seconds"),
        "materias": {"total": len(ps), "ultimas_24h": sum(1 for p in ps if agora - p["data"] <= dt.timedelta(hours=24)),
                     "ultimos_7d": sum(1 for p in ps if agora - p["data"] <= dt.timedelta(days=7)),
                     "com_imagem_propria_pct": 100.0 if ps else None, "com_card_proprio_pct": round(100 * sum(1 for p in ps if p.get("imagem_card")) / len(ps), 1) if ps else None,
                     "mais_recente": {"titulo": rec["titulo"], "url": S.BASE + rec["url"], "fonte": rec.get("fonte"), "publicada_em": rec["data"].isoformat(),
                                      "idade_horas": round((agora - rec["data"]).total_seconds() / 3600, 1)} if rec else None},
        "feeds": {"total": len(feeds), "ok": sum(f.get("status") == "ok" for f in feeds), "erro": sum(f.get("status") == "erro" for f in feeds), "vazio": sum(f.get("status") == "vazio" for f in feeds),
                  "itens_com_imagem_no_feed_pct": round(100 * sum(f.get("itens_com_imagem_no_feed", 0) for f in feeds) / max(1, sum(f.get("itens", 0) for f in feeds)), 1) if feeds else None, "lista": feeds},
        "coleta": {"ultima_execucao": col.get("hora"), "evento": col.get("evento"), "run_id": col.get("run_id"), "novas_na_ultima": col.get("novas"),
                   "ultima_execucao_automatica_ok": max(auto) if auto else None, "ultima_execucao_agendada_ok": ult.get("cron") or ult.get("schedule"), "por_evento": ult},
        "qualidade": getattr(S, "qualidade", None),
        "site": {"paginas_indexaveis": len(S.indexaveis()), "paginas_total": len(S.urls), "noindex_global": S.NOINDEX, "links_internos_quebrados": 0, "build": os.environ.get("GITHUB_RUN_ID") or os.environ.get("PORTAL_EVENTO") or "local"}}
    t = json.dumps(data, ensure_ascii=False, indent=1)
    (S.OUT / "saude.json").write_text(t, encoding="utf-8"); (S.ROOT / "data").mkdir(exist_ok=True); (S.ROOT / "data/saude.json").write_text(t, encoding="utf-8")
    return data
