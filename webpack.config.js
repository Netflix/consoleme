const webpack = require('webpack');
const path = require('path');
module.exports = {
  mode: "production",
  entry: {
    policyEditor: './consoleme/templates/static/js/policy_editor.jsx'
  },
  output: {
    path: path.resolve(__dirname, "consoleme/templates/static/js/dist"),
    filename: '[name].js',
    publicPath: "/static/js/dist",
    library: '[name]'
  },
  plugins: [
    new webpack.HotModuleReplacementPlugin(),
    new webpack.ProvidePlugin({
      $: "jquery",
      jquery: "jquery",
      "window.jquery": "jquery",
      "window.$": "jquery"
    })
  ],
  devServer: {
    contentBase: './consoleme/templates/static/js/dist',
    hot: true
  },
  resolve: {
    extensions: ['.js', '.jsx', '.css'],
    alias: {
      'jquery-ui': 'jquery-ui-dist/jquery-ui.js'
    }
  },
  module: {
    rules: [
      {
        test: require.resolve('jquery'),
        use: [{
          loader: 'expose-loader',
          options: 'jquery'
        }, {
          loader: 'expose-loader',
          options: '$'
        }]
      },
      {
        test: /\.(js|jsx)$/,
        exclude: /node_modules/,
        use: [
          {
            loader: 'babel-loader',
            options: {
              presets: [
                '@babel/preset-env',
                '@babel/preset-react',
                {
                  'plugins': [
                    '@babel/plugin-proposal-class-properties']
                }],
              plugins: [
                ["@babel/plugin-transform-runtime",
                  {
                    "regenerator": true,
                  }
                ]
              ]
            }
          }
        ]
      }
    ],
  },
  externals: {
    jquery: 'jQuery'
  }
};