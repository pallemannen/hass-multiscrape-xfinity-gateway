# hass-multiscrape-xfinity-gateway

Home Assistant Multiscrape example configuration for Xfinity / Comcast Internet Gateway in bridge mode.

You might have to change the IP address. Put xfinity_username and xfinity_password in /config/secrets.yaml and the text below in /config/configuration.yaml

```yaml
multiscrape:
  - name: Xfinity
    resource: "http://10.0.0.1/network_setup.jst"
    scan_interval: 300
    form_submit:
      resource: "http://10.0.0.1/" # login form is served here when unauthenticated
      select: "#pageForm"
      input:
        username: !secret xfinity_username
        password: !secret xfinity_password
      submit_once: true # log in once, reuse the session cookie every scan
      resubmit_on_error: true # auto re-login if the session expires
    sensor:
      - name: "Connection Status"
        unique_id: xfinity_connection_status
        select: ".module.forms .form-row:nth-of-type(1) span.value"
        value_template: "{{ value.strip() }}"
      - name: "Current Time"
        unique_id: xfinity_current_time
        select: ".module.forms .form-row:nth-of-type(2) span.value"
        value_template: "{{ value.strip() }}"
      - name: "System Uptime"
        unique_id: xfinity_time_since_last_reboot
        select: ".module.forms .form-row:nth-of-type(3) span.value"
        value_template: "{{ value.strip() }}"
      - name: "IP Address"
        unique_id: xfinity_external_ip_address
        select: ".module.forms .form-row:nth-of-type(4) span.value"
        value_template: "{{ value.strip() }}"
      - name: "External Default Gateway"
        unique_id: xfinity_external_default_gateway
        select: ".module.forms .form-row:nth-of-type(5) span.value"
        value_template: "{{ value.strip() }}"
      - name: "IPv6 Address"
        unique_id: xfinity_external_ipv6_address
        select: ".module.forms .form-row:nth-of-type(6) span.value"
        value_template: "{{ value.strip() }}"
      - name: "External IPv6 Default Gateway"
        unique_id: xfinity_external_ipv6_default_gateway
        select: ".module.forms .form-row:nth-of-type(7) span.value"
        value_template: "{{ value.strip() }}"
      - name: "Primary DNS"
        unique_id: xfinity_primary_dns
        select: ".module.forms .form-row:nth-of-type(9) span.value"
        value_template: "{{ value.strip() }}"
      - name: "Secondary DNS"
        unique_id: xfinity_secondary_dns
        select: ".module.forms .form-row:nth-of-type(10) span.value"
        value_template: "{{ value.strip() }}"
      - name: "Primary IPv6 DNS"
        unique_id: xfinity_primary_ipv6_dns
        select: ".module.forms .form-row:nth-of-type(11) span.value"
        value_template: "{{ value.strip() }}"
      - name: "Secondary IPv6 DNS"
        unique_id: xfinity_secondary_ipv6_dns
        select: ".module.forms .form-row:nth-of-type(12) span.value"
        value_template: "{{ value.strip() }}"
      - name: "Serial Number"
        unique_id: xfinity_serial_number
        select: ".module.forms.dev_label .form-row:nth-of-type(3) span.value"
        value_template: "{{ value.strip() }}"
```
