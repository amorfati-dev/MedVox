#!/bin/bash
# Prüft die HTTPS-Kette über die LAN-IP: Zertifikat wird von der Praxis-CA
# (rootCA.pem) beglaubigt, SANs enthalten medvox.local und die LAN-IP, Caddy
# antwortet. Exit 0 = alles in Ordnung.

source "$(dirname "$0")/../common.sh"
CERT="$MEDVOX_TLS/cert.pem"
ROOT="$MEDVOX_TLS/rootCA.pem"
status=0
LAN_IP="${MEDVOX_LAN_IP:-$(lan_ip || true)}"
[[ -n "$LAN_IP" ]] || die "Keine LAN-IP gefunden"
[[ -f "$ROOT" ]] || die "Praxis-CA fehlt ($ROOT) – infra/tls/setup.sh ausführen"

log "launchd: $CADDY_LABEL"
if launchd_running "$CADDY_LABEL"; then ok "läuft"; else warn "nicht aktiv"; status=1; fi

log "Zertifikat-Inhalt ($CERT)"
if [[ -f "$CERT" ]]; then
  sans="$(openssl x509 -in "$CERT" -noout -ext subjectAltName | tail -n +2 | tr -d ' ')"
  echo "   SANs: $sans"
  echo "   gültig bis: $(openssl x509 -in "$CERT" -noout -enddate | cut -d= -f2)"
  [[ "$sans" == *"DNS:medvox.local"* ]] && ok "SAN medvox.local" || { warn "SAN medvox.local fehlt"; status=1; }
  [[ "$sans" == *"IPAddress:$LAN_IP"* ]] && ok "SAN $LAN_IP" || { warn "SAN $LAN_IP fehlt (IP geändert? setup.sh --renew)"; status=1; }
else
  warn "Zertifikat fehlt"; status=1
fi

log "TLS-Handshake mit https://$LAN_IP:$CADDY_HTTPS_PORT gegen rootCA.pem"
out="$(openssl s_client -connect "$LAN_IP:$CADDY_HTTPS_PORT" -servername medvox.local -CAfile "$ROOT" -verify_return_error </dev/null 2>&1 || true)"
if grep -q "Verify return code: 0 (ok)" <<<"$out"; then
  ok "Kette gültig: $(grep -m1 'issuer=' <<<"$out" | sed 's/^ *//')"
else
  warn "Kette ungültig:"; grep -E 'Verify return code|error|verify' <<<"$out" | head -5; status=1
fi

log "HTTP über die Kette (curl --cacert)"
code="$(curl -sS --cacert "$ROOT" --resolve "medvox.local:$CADDY_HTTPS_PORT:$LAN_IP" -o /dev/null -w '%{http_code}' \
  "https://medvox.local:$CADDY_HTTPS_PORT/" 2>&1 || true)"
case "$code" in
  200|404) ok "Caddy antwortet (HTTP $code über medvox.local → $LAN_IP)" ;;
  *) warn "unerwartet: $code"; status=1 ;;
esac
code="$(curl -sS --cacert "$ROOT" -o /dev/null -w '%{http_code}' "https://$LAN_IP:$CADDY_HTTPS_PORT/api/health" 2>&1 || true)"
case "$code" in
  200) ok "/api → Backend erreichbar (HTTP 200)" ;;
  502) ok "/api wird weitergeleitet, Backend auf $API_UPSTREAM läuft noch nicht (HTTP 502 – normal vor WP-2)" ;;
  *) warn "/api: HTTP $code"; status=1 ;;
esac

echo
if (( status == 0 )); then ok "HTTPS im LAN ist in Ordnung"; else warn "HTTPS hat Probleme"; fi
exit $status
