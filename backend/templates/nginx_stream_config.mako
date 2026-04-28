server {
  listen ${listen_port}${' udp' if stream_protocol == 'udp' else ''};
  proxy_pass ${upstream_host}:${upstream_port};
  proxy_connect_timeout ${proxy_connect_timeout};
  proxy_timeout ${proxy_timeout};
% if stream_protocol == 'udp':
  proxy_responses 1;
% endif
}
