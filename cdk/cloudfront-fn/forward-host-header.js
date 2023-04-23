function forwardHostHeader(event) {
  var request = event.request;
  var headers = request.headers;
  // copies the Host header to X-Host-Header
  var host = headers['host'];
  if (host != null) {
    headers['x-host-header'] = host;
  }
  return request;
}

// prevents `babel-plugin-rewire` from removing `forwardHostHeader`
function callForwardHostHeader(event) {
  return forwardHostHeader(event);
}
