// this declaration exists only for unit tests.
import type { Event, Request } from './types';

function forwardDateHeader(event: Event): Request;

// declaration of the __get__ function injected by babel-plugin-rewire.
export function __get__(name: 'forwardDateHeader'): forwardDateHeader;
