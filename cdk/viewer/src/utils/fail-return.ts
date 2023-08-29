import type { FailReturn } from '@builder.io/qwik-city';

/**
 * Returns if a given value represents `FailReturn`.
 *
 * @remarks
 *
 * `FailReturn` wraps a failing result outputted through `RequestEvent.fail`.
 *
 * Narrows `value` to `FailReturn<T>` if this function returns `true`.
 */
export function isFailReturn<T = {}>(value: unknown): value is FailReturn<T> {
  return value != null && (value as FailReturn<T>).failed;
}
