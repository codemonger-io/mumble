// this declaration exists only for unit tests.

type Event = {
  request: Request;
};

type Request = {
  headers: { [header: string]: HeaderValue };
};

type HeaderValue = {
  value: string;
};

function handlerImpl(event: Event): Request;

// declaration of the __get__ function injected by babel-plugin-rewire.
export function __get__(name: 'handlerImpl'): handlerImpl;
