/**
 * Async iterator augmented with collection operations.
 *
 * @remarks
 *
 * Deters sequential synchronization (`await`) as much as possible so that
 * I/O operations can be maximally parallelized.
 */
export interface FnAsyncIterator<T> {
  /** Returns the next value. */
  next(): Promise<IteratorResult<T>>;

  /** Halts the async iterator. */
  return(): Promise<IteratorResult<T>>;

  /** Maps values. */
  map<U>(fn: (value: T) => Promise<U>): FnAsyncIterator<U>;

  /**
   * Filters values.
   *
   * @remarks
   *
   * Since a filtered iterator cannot proceed until the next value is resolved,
   * it may result in worse performance.
   * The implementation will mitigate this by looking ahead certain number of
   * items.
   */
  filter(fn: (value: T) => Promise<boolean>): FnAsyncIterator<T>;

  /** Takes up to given number of items. */
  take(count: number): FnAsyncIterator<T>;

  /** Collects all the values as an array. */
  collect(): Promise<T[]>;
}

/** Options for {@link FnAsyncIterator}. */
export interface FnAsyncIteratorOptions {
  /**
   * Number of items to look-ahead for filtering and collecting.
   *
   * @remarks
   *
   * @defaultValue 10
   */
  lookAhead?: number;
}

/** Base abstract implementation of {@link FnAsyncIterator}. */
export abstract class BaseFnAsyncIterator<T> implements FnAsyncIterator<T> {
  protected lookAheadCount: number;

  constructor(readonly options: FnAsyncIteratorOptions) {
    this.lookAheadCount = options.lookAhead ?? 10;
  }

  abstract next(): Promise<IteratorResult<T>>;

  abstract return(): Promise<IteratorResult<T>>;

  map<U>(fn: (value: T) => Promise<U>): FnAsyncIterator<U> {
    return MapFnAsyncIterator.from(this, fn, this.options);
  }

  filter(fn: (value: T) => Promise<boolean>): FnAsyncIterator<T> {
    return FilterFnAsyncIterator.from(this, fn, this.options);
  }

  take(count: number): FnAsyncIterator<T> {
    return TakeFnAsyncIterator.from(this, count, this.options);
  }

  async collect(): Promise<T[]> {
    let results: T[] = [];
    let completed = false;
    do {
      const batch: Promise<IteratorResult<T>>[] = [];
      for (let i = 0; i < this.lookAheadCount; ++i) {
        batch.push(this.next());
      }
      const batchResults = (await Promise.all(batch))
        .filter(({ done }) => !done)
        .map(({ value }) => value);
      if (batchResults.length !== batch.length) {
        completed = true;
      }
      results = results.concat(batchResults);
    } while (!completed);
    return results;
  }
}

/** Wrapper for an existing `AsyncIterator`. */
export class AsyncIteratorWrapper<T> extends BaseFnAsyncIterator<T> {
  /** Wraps a given `AsyncIterator`. */
  static from<T>(
    iterator: AsyncIterator<T>,
    options: FnAsyncIteratorOptions = {},
  ): AsyncIteratorWrapper<T> {
    return new AsyncIteratorWrapper(iterator, options);
  }

  constructor(
    private iterator: AsyncIterator<T>,
    options: FnAsyncIteratorOptions,
  ) {
    super(options);
  }

  next(): Promise<IteratorResult<T>> {
    return this.iterator.next();
  }

  return(): Promise<IteratorResult<T>> {
    return this.iterator.return != null
      ? this.iterator.return()
      : Promise.resolve({ done: true, value: undefined });
  }
}

/** Mapped {@link FnAsyncIterator}. */
class MapFnAsyncIterator<T, U> extends BaseFnAsyncIterator<U> {
  /** Maps another {@link FnAsyncIterator} with a given function. */
  static from<T, U>(
    base: FnAsyncIterator<T>,
    fn: (value: T) => Promise<U>,
    options: FnAsyncIteratorOptions,
  ): MapFnAsyncIterator<T, U> {
    return new MapFnAsyncIterator(base, fn, options);
  }

  constructor(
    private base: FnAsyncIterator<T>,
    private fn: (value: T) => Promise<U>,
    options: FnAsyncIteratorOptions,
  ) {
    super(options);
  }

  next(): Promise<IteratorResult<U>> {
    return this.base.next().then(({ done, value }) => {
      if (done) {
        return Promise.resolve({ done, value });
      }
      return this.fn(value).then(v => Promise.resolve({ done, value: v }));
    });
  }

  return(): Promise<IteratorResult<U>> {
    return this.base.return().then(({ done, value }) => {
      if (done) {
        return { done, value };
      }
      return { done: true, value: undefined };
    })
  }
}

/** Filtered {@link FnAsyncIterator}. */
class FilterFnAsyncIterator<T> extends BaseFnAsyncIterator<T> {
  /** Filters another {@link FnAsyncIterator} with a given function. */
  static from<T>(
    base: FnAsyncIterator<T>,
    fn: (value: T) => Promise<boolean>,
    options: FnAsyncIteratorOptions,
  ): FilterFnAsyncIterator<T> {
    return new FilterFnAsyncIterator(base, fn, options);
  }

  private lookAhead: Promise<FilteredIteratorResult<T>>[];

  constructor(
    private base: FnAsyncIterator<T>,
    private fn: (value: T) => Promise<boolean>,
    options: FnAsyncIteratorOptions,
  ) {
    super(options);
    this.lookAhead = [];
  }

  async next(): Promise<IteratorResult<T>> {
    do {
      if (this.lookAhead.length === 0) {
        this.fillLookAhead();
        if (this.lookAhead.length === 0) {
          return Promise.resolve({ done: true, value: undefined });
        }
      }
      const { done, value, filtered } = await this.lookAhead.shift()!;
      if (done) {
        return Promise.resolve({ done, value });
      }
      this.nextLookAhead();
      if (filtered) {
        return Promise.resolve({ done, value });
      }
    } while (true); // eslint-disable-line no-constant-condition
  }

  fillLookAhead(): void {
    for (let i = 0; i < this.lookAheadCount; ++i) {
      this.nextLookAhead();
    }
  }

  nextLookAhead(): void {
    this.lookAhead.push(this.base.next().then(async ({ done, value }) => {
      if (done) {
        return { done, value, filtered: false };
      }
      const filtered = await this.fn(value);
      return { done, value, filtered };
    }));
  }

  return(): Promise<IteratorResult<T>> {
    return this.base.return();
  }
}

/** Fitered iterator result. */
type FilteredIteratorResult<T> = IteratorResult<T> & {
  /** Whether the filter function has returned for the item. */
  filtered: boolean;
};

/** Taken {@link FnAsyncIterator}. */
class TakeFnAsyncIterator<T> extends BaseFnAsyncIterator<T> {
  /** Takes items from another {@link FnAsyncIterator}. */
  static from<T>(
    base: FnAsyncIterator<T>,
    count: number,
    options: FnAsyncIteratorOptions,
  ): TakeFnAsyncIterator<T> {
    return new TakeFnAsyncIterator(base, count, options);
  }

  // current count.
  private count: number = 0;

  constructor(
    private base: FnAsyncIterator<T>,
    private maxCount: number,
    options: FnAsyncIteratorOptions,
  ) {
    super(options);
  }

  next(): Promise<IteratorResult<T>> {
    if (this.count >= this.maxCount) {
      return Promise.resolve({ done: true, value: undefined });
    }
    this.count++;
    return this.base.next();
  }

  return(): Promise<IteratorResult<T>> {
    return this.base.return();
  }
}
