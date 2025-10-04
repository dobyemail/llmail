
# ============================================
# dovecot/Dockerfile - Dockerfile dla serwera IMAP
# ============================================
FROM dovecot/dovecot:latest

# Kopiuj konfigurację
COPY dovecot.conf /etc/dovecot/dovecot.conf
COPY users /etc/dovecot/users

# Ustaw uprawnienia
RUN chmod 600 /etc/dovecot/users

# Utwórz strukturę folderów
RUN mkdir -p /var/mail/test@localhost/Maildir && \
    chown -R 1000:1000 /var/mail

EXPOSE 143 993

CMD ["dovecot", "-F"]
