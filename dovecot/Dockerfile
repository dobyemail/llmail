
# ============================================
# dovecot/Dockerfile - Dockerfile dla serwera IMAP
# ============================================
FROM dovecot/dovecot:latest

# Kopiuj konfigurację
COPY dovecot.conf /etc/dovecot/dovecot.conf
COPY users /etc/dovecot/users

# Ustaw uprawnienia
## chmod niedostępny w bazowym obrazie – pomijamy na etapie build

## Tworzenie struktury katalogów i własności pozostawiamy runtime (start Dovecota)

EXPOSE 143 993

CMD ["dovecot", "-F"]
