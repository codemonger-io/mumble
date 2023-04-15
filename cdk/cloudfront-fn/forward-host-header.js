function handlerImpl(event) {
  var request = event.request;
  var headers = request.headers;
  // copies the Host header to X-Host-Header
  var host = headers['host'];
  if (host != null) {
    headers['x-host-header'] = host;
  }
  return request;
}

function handler(event) {
  return handlerImpl(event);
}
