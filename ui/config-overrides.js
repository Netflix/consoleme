const MonacoWebpackPlugin = require("monaco-editor-webpack-plugin");
const webpack = require("webpack");

module.exports = function override(config, env) {
  const appTarget = process.env.APP_TARGET || "default";
  config.plugins = [
    ...config.plugins,
    new webpack.NormalModuleReplacementPlugin(
      /(.*)Default(\.*)/,
      function (resource) {
        resource.request =
          appTarget === "default" ? resource.request : appTarget;
      }
    ),
    new MonacoWebpackPlugin({
      languages: ["yaml", "json"],
    }),
  ];
  return config;
};
