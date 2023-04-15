// thanks to babel-plugin-rewire all *.js modules expose internal functions
// through the __get__ function.
import { __get__ } from '../../cloudfront-fn/forward-host-header.js';
const handlerImpl = __get__('handlerImpl');

describe('forward-host-header', () => {
  describe('handlerImpl', () => {
    it('should copy host to x-host-header', () => {
      const event = {
        request: {
          headers: {
            host: {
              value: 'mumble.codemonger.io',
            },
          },
        },
      };
      expect(handlerImpl(event)).toEqual({
        headers: {
          host: {
            value: 'mumble.codemonger.io',
          },
          'x-host-header': {
            value: 'mumble.codemonger.io',
          },
        },
      });
    });

    it('should not create x-host-header if no host exists', () => {
      const event = {
        request: {
          headers: {
            accept: {
              value: 'application/json',
            },
          },
        },
      };
      expect(handlerImpl(event)).toEqual({
        headers: {
          accept: {
            value: 'application/json',
          },
        },
      });
    });

    it('should overwrite x-host-header', () => {
      const event = {
        request: {
          headers: {
            host: {
              value: 'mumble.codemonger.io',
            },
            'x-host-header': {
              value: 'imposter.social',
            },
          },
        },
      };
      expect(handlerImpl(event)).toEqual({
        headers: {
          host: {
            value: 'mumble.codemonger.io',
          },
          'x-host-header': {
            value: 'mumble.codemonger.io',
          },
        },
      });
    });
  });
});
