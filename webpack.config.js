const webpack = require("webpack");
const path = require("path");

const MonacoWebpackPlugin = require("monaco-editor-webpack-plugin");

module.exports = {
  mode: "production",
  entry: {
    policyEditor: "./consoleme/templates/static/js/policy_editor.jsx",
    selfService: "./consoleme/templates/static/js/components/SelfService.js",
    createCloneFeature:
      "./consoleme/templates/static/js/components/CreateCloneFeature.js",
    consoleMeDataTable:
      "./consoleme/templates/static/js/components/ConsoleMeDataTable.js",
    dynamicConfig:
      "./consoleme/templates/static/js/components/DynamicConfig.js",
    policyRequestsReview:
      "./consoleme/templates/static/js/components/PolicyRequestsReview.js",
  },
  output: {
    path: path.resolve(__dirname, "consoleme/templates/static/js/dist/"),
    filename: "[name].js",
    chunkFilename: "[name].bundle.js",
    publicPath: "/static/js/dist/",
    library: "[name]",
  },
  plugins: [
    // Useful for Development:
    // new webpack.DefinePlugin({
    //   "process.env.NODE_ENV": JSON.stringify("development"),
    // }),
    new webpack.HotModuleReplacementPlugin(),
    new webpack.ProvidePlugin({
      $: "jquery",
      jquery: "jquery",
      "window.jquery": "jquery",
      "window.$": "jquery",
    }),
    new MonacoWebpackPlugin({
      // available options are documented at https://github.com/Microsoft/monaco-editor-webpack-plugin#options
      languages: ["json", "yaml"],
      publicPath: "/static/js/dist/",
    }),
  ],
  devServer: {
    contentBase: "./consoleme/templates/static/js/dist/",
    hot: true,
  },
  resolve: {
    extensions: [".js", ".jsx", ".css", ".ttf"],
    alias: {
      "jquery-ui": "jquery-ui-dist/jquery-ui.js",
    },
    symlinks: false,
    cacheWithContext: false,
  },
  module: {
    rules: [
      {
        test: /\.css$/i,
        use: ["style-loader", "css-loader"],
      },
      {
        test: /\.ttf$/,
        use: ["file-loader"],
      },
      {
        test: require.resolve("jquery"),
        use: [
          {
            loader: "expose-loader",
            options: "jquery",
          },
          {
            loader: "expose-loader",
            options: "$",
          },
        ],
      },
      {
        test: /\.(js|jsx)$/,
        exclude: /node_modules/,
        use: [
          {
            loader: "babel-loader",
            options: {
              presets: [
                "@babel/preset-env",
                "@babel/preset-react",
                {
                  plugins: ["@babel/plugin-proposal-class-properties"],
                },
              ],
              plugins: [
                [
                  "@babel/plugin-transform-runtime",
                  {
                    regenerator: true,
                  },
                ],
              ],
            },
          },
        ],
      },
    ],
  },
  externals: {
    jquery: "jQuery",
  },
  // Enable these for easier development when running locally
  // devtool: "source-map",
  // optimization: {
  //   minimize: false,
  //   splitChunks: {
  //     chunks: "async",
  //   },
  // },
};
