import * as esbuild from 'esbuild';

await esbuild.build({
	logLevel: "info",

  bundle: true,
  splitting: true,
  sourcemap: true,
  target: 'es2016',
  format: 'esm',

	entryPoints: [
		'./web/resources/main.js',
		'./web/resources/js/lazy-load-select.js',
	],
  outdir: 'web/static',
  assetNames: '[name].[hash]',
  chunkNames: 'chunks/[name].[hash]',
  entryNames: '[name].[hash]',

  loader: {
    '.xml': 'copy',
    '.png': 'copy',
    '.ico': 'copy',
    '.svg': 'copy'
  },
})
