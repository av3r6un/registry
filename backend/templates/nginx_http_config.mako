<%!
  def names(value):
    if isinstance(value, str):
      return value
    return ' '.join(value)
%>
% if ssl_enabled:
server {
  listen 80;
  server_name ${names(server_names)};

  location /.well-known/acme-challenge/ {
    root ${certbot_webroot};
  }

  return 301 https://$host$request_uri;
}

server {
  listen 443 ssl;
  server_name ${names(server_names)};

  client_max_body_size ${client_max_body_size};

  ssl_certificate ${letsencrypt_dir}/live/${cert_name}/fullchain.pem;
  ssl_certificate_key ${letsencrypt_dir}/live/${cert_name}/privkey.pem;
  ssl_protocols TLSv1.2 TLSv1.3;
  ssl_prefer_server_ciphers off;

  location / {
    proxy_pass ${upstream_scheme}://${upstream_host}:${upstream_port};
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }
}
% else:
server {
  listen 80;
  server_name ${names(server_names)};

  client_max_body_size ${client_max_body_size};

  location /.well-known/acme-challenge/ {
    root ${certbot_webroot};
  }

  location / {
    proxy_pass ${upstream_scheme}://${upstream_host}:${upstream_port};
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }
}
% endif
