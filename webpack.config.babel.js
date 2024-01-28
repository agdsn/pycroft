import path from 'path';
import process from 'process';
import webpack from "webpack";
import { WebpackManifestPlugin } from "webpack-manifest-plugin";
import MiniCssExtractPlugin from "mini-css-extract-plugin";
const { CleanWebpackPlugin } = require('clean-webpack-plugin');
import TerserPlugin from "terser-webpack-plugin";

// Check for production mode
const PROD = process.env.NODE_ENV === "production";

const src = path.resolve(__dirname, 'web', 'resources');
const dep = path.join(src, 'node_modules');
const dst = path.resolve(__dirname, 'web', 'static');

export default {
    mode: PROD ? "production" : "development",
    // We're creating a web application
    target: 'web',
    context: src,
    entry: {
        'main': './main.js',
        'advanced-search': {
            import: './js/advanced-search.js',
            dependOn: 'main',
        },
        'balance-chart': {
            import: './js/balance-chart.js',
            dependOn: 'main',
        },
        'lazy-load-select': {
            import: './js/lazy-load-select.js',
            dependOn: 'main',
        },
        'mac-address-input': {
            import: './js/mac-address-input.js',
            dependOn: 'main',
        },
        'confirmable-error': {
            import: './js/confirmable-error.ts',
            dependOn: 'main',
        },
        'navigation': {
            import: './js/navigation.js',
            dependOn: 'main',
        },
        'tooltip': {
            import: './js/tooltip.js',
            dependOn: 'main',
        },
        'table-fixed-header': {
            import: './js/table-fixed-header.js',
            dependOn: 'main',
        },
        'traffic-graph': {
            import: './js/traffic-graph.js',
            dependOn: 'main',
        },
        'transaction-chart': {
            import: './js/transaction-chart.js',
            dependOn: 'main',
        },
        'transaction-form': {
            import: './js/transaction-form.js',
            dependOn: 'main',
        },
        'unlimited-end-date': {
            import: './js/unlimited-end-date.js',
            dependOn: 'main',
        },
        'select-multiple-improvement': {
            import: './js/select-multiple-improvement.js',
            dependOn: 'main',
        },
        'tab-anchor': {
            import: './js/tab-anchor.ts',
            dependOn: 'main',
        },
        'user-suite': {
            import: './js/user-suite.ts',
            dependOn: 'main',
        },
        'rooms-table': {
            import: './js/rooms-table.ts',
            dependOn: 'main',
        },
    },
    output: {
        path: dst,
        publicPath: '',
        filename: `[name].[chunkhash].${PROD ? 'min.js' : 'js'}`,
        assetModuleFilename: "[path][name].[hash][ext]",
        hashFunction: 'md5',
        hashDigest: 'hex',
        hashDigestLength: 32,
        pathinfo: !PROD,
    },
    cache: {
        type: 'filesystem',
        buildDependencies: {
          config: [__filename],
          // If you have other things the build depends on you can add them here
          // Note that webpack, loaders and all modules referenced from your config are automatically added
        },
    },
    watchOptions: {
        aggregateTimeout: 1000,
        ignored: [
            dep,
        ],
    },
    devtool: PROD ? "source-map" : "eval-source-map",
    resolve: {
        symlinks: false,
        extensions: ['.js', '.ts'],
    },
    optimization: {
        minimizer: PROD ? [
            // Compress JavaScript
            new TerserPlugin({
                parallel: true,
            }),
        ] : [],
        runtimeChunk: {
            name: "runtime",
        },
        splitChunks: {
            cacheGroups: {
                vendor: {
                    name: "vendor",
                    chunks: "all",
                    enforce: true,
                    test: dep,
                },
            },
        },
        moduleIds: 'deterministic',
    },
    plugins: [
        // Clean the destination
        new CleanWebpackPlugin(),
        // Put CSS into a separate file
        new MiniCssExtractPlugin({
            filename: '[name].[contenthash].css',
            chunkFilename: '[id].[contenthash].css',
        }),
        // Generate a manifest file, that maps entries and assets to their
        // output file.
        new WebpackManifestPlugin({}),
    ].concat(PROD ? [
        // PROD plugins
    ] : [
        // !PROD plugins
    ]),
    module: {
        rules: [
            // Use the source-map-loader to reuse existing source maps, that
            // are provided by dependencies
            {
                test: /\.[j]sx?$/,  // TODO look at how we can deal with this and typescript
                use: ["source-map-loader"],
                enforce: "pre",
                include: dep,
            },
            {
                test: /\.tsx?$/,
                use: 'ts-loader',
                exclude: dep,
            },
            // Expose our table module as a global variable.
            // Functions from this module are referenced through
            // data-*-attributes for use by bootstrap-table.
            // This is necessary because `bootstrap-table` requires
            // the referenced function to be globally accessible, like
            // `window.fooFormatter`, and does not import it from somewhere.
            {
                test: path.join(src, 'js', 'table.js'),
                use: {
                    loader: "expose-loader",
                    options: {
                        exposes: "table",
                    },
                },
            },
            // Inject jQuery import into bootstrap-table
            // and bootstrap-datepicker/locales
            {
                test: /\.js$/,
                use: {
                    loader: "imports-loader",
                    options: {
                        type: 'commonjs',
                        imports: {
                            'moduleName': 'jquery',
                            'name': 'jQuery',
                        }
                    },
                },
                include: [
                    path.join(dep, "bootstrap-table", "dist"),
                    path.join(dep, "bootstrap-datepicker", "dist", "locales"),
                ],
            },
            // Transpile modern JavaScript for older browsers.
            {
                test: /\.jsx?$/,
                exclude: dep,
                use: {
                    loader: 'babel-loader',
                    options: {
                        cacheDirectory: true,
                        // Use the recommended preset-env
                        presets: [
                            ['@babel/preset-env', {
                                targets: {
                                    browsers: [
                                        'IE 11',
                                        'FF 52',
                                        'Chrome 49',
                                    ],
                                },
                                // Let webpack handle modules
                                modules: false,
                                forceAllTransforms: PROD,
                            }],
                        ],
                        // Import the babel runtime instead of inlining it in
                        // every file.
                        plugins: [
                            ['@babel/plugin-transform-runtime', {
                                helpers: false,
                                regenerator: true,
                                useESModules: true,
                            }],
                        ],
                    },
                },
            },
            // Handle CSS
            {
                test: /\.css$/,
                use: [
                    MiniCssExtractPlugin.loader,
                    "css-loader",
                ],
            },
            // Handle other assets
            {
                test: [
                    /\.(?:gif|ico|jpg|png|svg)$/, // Images
                    /\.(?:eot|otf|ttf|woff|woff2)$/, // Fonts
                    /\.(?:xml)$/, // static XML initial for openSearch
                ],
                exclude: dep,
                type: "asset/resource",
            },
        ],
    },
};
