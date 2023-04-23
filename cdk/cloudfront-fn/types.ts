// defines common types for CloudFront Function.
// minimum definitions necessary for unit tests are provided.

export type Event = {
  request: Request;
};

export type Request = {
  headers: { [header: string]: HeaderValue };
};

export type HeaderValue = {
  value: string;
};
