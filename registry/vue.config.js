const { defineConfig } = require('@vue/cli-service');
const webpack = require('webpack');

module.exports = defineConfig({
  transpileDependencies: true,
  css: {
    loaderOptions: {
      scss: {
        additionalData: '@import "@/assets/variables.scss";',
      },
    },
  },
  configureWebpack: {
    plugins: [
      new webpack.DefinePlugin({
        __VUE_PROD_HYDRATION_MISMATCH_DETAILS__: 'false',
      }),
    ],
    module: {
      rules: [
        {
          test: /\.ya?ml$/,
          use: 'yaml-loader',
        },
      ],
    },
  },
  devServer: {
    port: 3000,
    proxy: {
      '/api/': {
        target: 'http://localhost:8081/',
        changeOrigin: true,
      },
    },
  },
  outputDir: 'dist/',
});
