#!/bin/bash
set -euo pipefail
umask 077
apt-get update -qq
export DEBIAN_FRONTEND=noninteractive
apt-get install -y -qq python3 curl ca-certificates >/dev/null
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
printf 'deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian bookworm stable\n' > /etc/apt/sources.list.d/docker.list
apt-get update -qq
apt-get install -y -qq docker-ce docker-ce-cli containerd.io >/dev/null
systemctl enable --now docker
systemctl disable --now exim4 >/dev/null 2>&1 || true
DISK=/dev/disk/by-id/google-mail-data
for n in $(seq 1 30); do [ -b "$DISK" ] && break; sleep 2; done
if ! blkid "$DISK" >/dev/null 2>&1; then mkfs.ext4 -q "$DISK"; fi
mkdir -p /srv/stalwart
mountpoint -q /srv/stalwart || mount -o defaults,nodev,nosuid "$DISK" /srv/stalwart
UUID=$(blkid -s UUID -o value "$DISK")
grep -q "UUID=$UUID " /etc/fstab || echo "UUID=$UUID /srv/stalwart ext4 defaults,nodev,nosuid 0 2" >> /etc/fstab
mkdir -p /srv/stalwart/config /srv/stalwart/data /srv/stalwart/private
chmod 700 /srv/stalwart/private
chown 2000:2000 /srv/stalwart/config /srv/stalwart/data
curl -fsS -H 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/instance/attributes/mail-configure | base64 -d > /usr/local/sbin/progressbar-mail-configure.py
chmod 700 /usr/local/sbin/progressbar-mail-configure.py
cat > /etc/systemd/system/progressbar-mail-configure.service <<'UNIT'
[Unit]
Description=Converge Progress Bar Stalwart mail configuration
After=docker.service network-online.target
Wants=docker.service
RequiresMountsFor=/srv/stalwart
[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /usr/local/sbin/progressbar-mail-configure.py
RemainAfterExit=yes
Restart=on-failure
RestartSec=30
[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable progressbar-mail-configure
systemctl restart progressbar-mail-configure
