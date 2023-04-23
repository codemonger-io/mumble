function forwardDateHeader(event) {
  var request = event.request;
  var headers = request.headers;
  // copies Date header to X-Signature-Date if Signature header is present
  // TODO: how about to apply this only to restricted requests?
  var date = headers['date'];
  var signature = headers['signature'];
  if (date != null && signature != null) {
    headers['x-signature-date'] = date;
  }
  return request;
}

// prevents `babel-plugin-rewire` from removing `forwardDateHeader`
function callForwardDateHeader(event) {
  return forwardDateHeader(event);
}
