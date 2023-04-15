module.exports = api => {
  return {
    presets: [
      [
        '@babel/preset-env',
        {
          targets: {
            node: 'current',
          },
        },
      ],
    ],
    plugins: api.env('test') ? ['rewire'] : [],
  };
};
