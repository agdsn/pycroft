import path from 'path';
import process from 'process';
import webpack from "webpack";
import ManifestPlugin from "webpack-manifest-plugin";
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
        'advanced-search': './js/advanced-search.js',
        'balance-chart': './js/balance-chart.js',
        'lazy-load-select': './js/lazy-load-select.js',
        'mac-address-input': './js/mac-address-input.js',
        'confirmable-error': './js/confirmable-error.ts',
        'main': './main.js',
        'navigation': './js/navigation.js',
        'tooltip': './js/tooltip.js',
        'table-fixed-header': './js/table-fixed-header.js',
        'traffic-graph': './js/traffic-graph.js',
        'transaction-chart': './js/transaction-chart.js',
        'transaction-form': './js/transaction-form.js',
        'unlimited-end-date': './js/unlimited-end-date.js',
        'select-multiple-improvement': './js/select-multiple-improvement.js',
        'tab-anchor': './js/tab-anchor.ts',
        'rooms-table': './js/rooms-table.ts',
    },
    output: {
        path: dst,
        filename: `[name].[chunkhash].${PROD ? 'min.js' : 'js'}`,
        hashFunction: 'md5',
        hashDigest: 'hex',
        hashDigestLength: 32,
        pathinfo: !PROD,
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
        minimizer: [
            // Compress JavaScript
            new TerserPlugin({
                cache: true,
                parallel: true,
                sourceMap: true,
            }),
        ],
        runtimeChunk: {
            name: "main",
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
    },
    plugins: [
        // Clean the destination
        new CleanWebpackPlugin(),
        // Create stable module IDs
        new webpack.HashedModuleIdsPlugin({
            hashFunction: 'md5',
            hashDigest: 'hex',
            hashDigestLength: 32,
        }),
        // Put CSS into a separate file
        new MiniCssExtractPlugin({
            filename: '[name].[hash].css',
            chunkFilename: '[id].[hash].css',
            allChunks: true,
        }),
        // Generate a manifest file, that maps entries and assets to their
        // output file.
        new ManifestPlugin(),
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
            // Inject 'bootstrap' symbol into bootstrap-table`
            // This is required because the BS5 version detection requires that:
            // `constants/index.js` probes `bootstrap.Tooltip.VERSION`
            // and assumes BS4 if that does not work for whatever reason.
            {
                test: /\.js$/,
                use: {
                    loader: "imports-loader",
                    options: {
                        // generates `const bootstrap = require('bootstrap')`
                        type: 'commonjs',
                        imports: {
                            'syntax': 'single',
                            'moduleName': 'bootstrap',
                            'name': 'bootstrap',
                        },
                    },
                },
                include: path.join(dep, "bootstrap-table")
            },
            // Inject jQuery import into bootstrap-datepicker locales
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
                include: path.join(dep, "bootstrap-datepicker", "dist", "locales"),
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
                    {
                        loader: "style-loader",
                    },
                    {
                        loader: MiniCssExtractPlugin.loader,
                    },
                    {
                        loader: "css-loader",
                    },
                ],
            },
            // Handle other assets
            {
                test: [
                    /\.(?:gif|ico|jpg|png|svg)$/, // Images
                    /\.(?:eot|otf|ttf|woff|woff2)$/, // Fonts
                    /\.(?:xml)$/, // static XML initial for openSearch
                ],
                use: {
                    loader: 'file-loader',
                    options: {
                        name: "[path][name].[hash].[ext]",
                        publicPath: './',
                        esModule: false,
                    },
                },
            },
        ],
    },
};
