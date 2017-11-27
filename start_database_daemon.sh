# cat > /etc/rsyslog.d/10-custom.conf << EOF1
# if $programname == 'poloniexdb' then {
#   /var/log/poloniexdb.log
#   ~
# }
# EOF1
# 
service rsyslog restart

cat > /lib/systemd/system/poloniexdb.service << EOF2
[Unit]
Description=Poloniex Database Service
After=syslog.target

[Service]
Type=simple
User=joao
Group=latin
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/database.py
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=poloniexdb
Restart=always

[Install]
WantedBy=multi-user.target
EOF2

systemctl daemon-reload
systemctl start poloniexdb
systemctl enable poloniexdb
