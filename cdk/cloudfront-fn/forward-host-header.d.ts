// this declaration exists only for unit tests.
import type { Event, Request } from './types';

type ForwardHostHeader = (event: Event) => Request;

// declaration of the __get__ function injected by babel-plugin-rewire.
export function __get__(name: 'forwardHostHeader'): ForwardHostHeader;
