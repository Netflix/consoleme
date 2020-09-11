module.exports = function (api) {
  api.cache(true);

  const presets = ["@babel/preset-env", "@babel/preset-react"];
  const plugins = [
    "@babel/plugin-proposal-class-properties",
    { loose: true },
    "@babel/plugin-transform-runtime",
  ];

  return {
    presets,
    plugins,
  };
};
