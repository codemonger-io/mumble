export default {
  development: {
    // you have to specify at least one URL.
    callbackUrls: [
      'http://localhost:5173/',
    ],
    // you can omit or leave the following empty.
    logoutUrls: [
      'http://localhost:5173/',
    ],
  },
  production: {
    // you have to specify at least one URL.
    callbackUrls: [
      'https://example.com/',
    ],
    // you can omit or leave the following empty.
    logoutUrls: [
      'https://example.com/',
    ],
  },
}
