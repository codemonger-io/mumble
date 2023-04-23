// thanks to babel-plugin-rewire all *.js modules expose internal functions
// through the __get__ function.
import { __get__ } from '../../cloudfront-fn/forward-date-header.js';
const forwardDateHeader = __get__('forwardDateHeader');

describe('forward-date-header', () => {
  describe('forwardDateHeader', () => {
    it('should copy date to x-signature-date', () => {
      const event = {
        request: {
          headers: {
            date: {
              value: '19 Apr 2023 10:22:46 GMT',
            },
            signature: {
              value: 'value does not matter to tests',
            },
          },
        },
      };
      expect(forwardDateHeader(event)).toEqual({
        headers: {
          date: {
            value: '19 Apr 2023 10:22:46 GMT',
          },
          signature: {
            value: 'value does not matter to tests',
          },
          'x-signature-date': {
            value: '19 Apr 2023 10:22:46 GMT',
          },
        },
      });
    });

    it('should not create x-signature-date if no date exists', () => {
      const event = {
        request: {
          headers: {
            signature: {
              value: 'value does not matter to tests',
            },
          },
        },
      };
      expect(forwardDateHeader(event)).toEqual({
        headers: {
          signature: {
            value: 'value does not matter to tests',
          },
        },
      });
    });

    it('should not create x-signature-date if no signature exists', () => {
      const event = {
        request: {
          headers: {
            date: {
              value: '19 Apr 2023 10:22:46 GMT',
            },
          },
        },
      };
      expect(forwardDateHeader(event)).toEqual({
        headers: {
          date: {
            value: '19 Apr 2023 10:22:46 GMT',
          },
        },
      });
    });

    it('should overwrite x-signature-date', () => {
      const event = {
        request: {
          headers: {
            date: {
              value: '19 Apr 2023 10:22:46 GMT',
            },
            signature: {
              value: 'value does not matter to tests',
            },
            'x-signature-date': {
              value: '18 Dec 2019 10:08:46 GMT',
            },
          },
        },
      };
      expect(forwardDateHeader(event)).toEqual({
        headers: {
          date: {
            value: '19 Apr 2023 10:22:46 GMT',
          },
          signature: {
            value: 'value does not matter to tests',
          },
          'x-signature-date': {
            value: '19 Apr 2023 10:22:46 GMT',
          },
        },
      });
    });
  });
});
