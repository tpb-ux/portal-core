#!/usr/bin/env bash
# Ciclo de um portal na VPS (cron nos minutos 7 e 37). Uso: ops/ciclo.sh /opt/portais/<portal>
# Lê <dir>/portal.env (PORTAL_DIR, PORTAL_WEBROOT, PORTAL_VENV, PORTAL_BRANCH, PORTAL_DATASETS_HORA, PORTAL_NOINDEX)
set -uo pipefail
D="${1:?pasta do portal}"; set -a; source "$D/portal.env"; set +a
cd "$PORTAL_DIR/repo" || exit 1
exec 9>"$D/.lock"; flock -n 9 || { echo "ciclo anterior ainda rodando"; exit 0; }
PY="$PORTAL_VENV/bin/python"; FALHOS=()
log(){ echo "[$(date -u +%FT%TZ)] $*"; }
log "pull"; git fetch -q origin "$PORTAL_BRANCH" && git merge -q -X ours --no-edit "origin/$PORTAL_BRANCH" || { FALHOS+=(pull); git merge --abort 2>/dev/null; }
"$PY" -m pip install -q -r requirements.txt || FALHOS+=(deps)
export PORTAL_EVENTO=cron
if [ "$(date -u +%H)" = "${PORTAL_DATASETS_HORA:-06}" ] && [ "$(date -u +%M)" -lt 30 ]; then
  for t in tools/datasets_*.py; do [ -f "$t" ] && { log "dataset $t"; timeout 3000 "$PY" "$t" || FALHOS+=("$t"); }; done
fi
log "fetch"; timeout 900 "$PY" fetch.py || FALHOS+=(fetch)
log "build"
if timeout 900 "$PY" build.py > "$D/build.log" 2>&1; then
  rsync -a --delete public/ "$PORTAL_WEBROOT/"
  [ "${PORTAL_NOINDEX:-0}" = "1" ] || "$PY" -m core.indexnow ping . || FALHOS+=(indexnow)
else FALHOS+=(build); tail -40 "$D/build.log"; fi
git add -A content static/img data 2>/dev/null; git -c user.name=portal-vps -c user.email=vps@localhost commit -qm "coleta VPS $(date -u +%FT%TZ)" 2>/dev/null || true
"$PY" -m core.alerta . "${FALHOS[@]}"; cp -f ALERTA.txt "$D/ALERTA.txt" 2>/dev/null
log "fim (falhas: ${FALHOS[*]:-nenhuma})"
