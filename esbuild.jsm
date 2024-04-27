import * as esbuild from 'esbuild';
import fs from 'fs';
import path from 'path';

const src = path.resolve(__dirname, 'web', 'resources');
const dst = path.resolve(__dirname, 'web', 'static');

const entryPoints = [
    ['advanced-search', './js/advanced-search.js'],
    ['balance-chart', './js/balance-chart.js'],
    ['lazy-load-select', './js/lazy-load-select.js'],
    ['mac-address-input', './js/mac-address-input.js'],
    ['confirmable-error', './js/confirmable-error.ts'],
    ['navigation', './js/navigation.js'],
    ['tooltip', './js/tooltip.js'],
    ['table-fixed-header', './js/table-fixed-header.js'],
    ['traffic-graph', './js/traffic-graph.js'],
    ['transaction-chart', './js/transaction-chart.js'],
    ['transaction-form', './js/transaction-form.js'],
    ['unlimited-end-date', './js/unlimited-end-date.js'],
    ['select-multiple-improvement', './js/select-multiple-improvement.js'],
    ['tab-anchor', './js/tab-anchor.ts'],
    ['user-suite', './js/user-suite.ts'],
    ['rooms-table', './js/rooms-table.ts'],
].map((x) => (
  {out: x[0], in: path.join(src, x[1])}
))

let result = await esbuild.build({
  logLevel: "info",

  bundle: true,
  // splitting: true,
  // minify: true,
  sourcemap: true,
  target: 'es2016',
  format: 'esm',
  metafile: true,
  absWorkingDir: src,

  entryPoints: [
    {in: `${src}/main.js`, out: 'main'},
    {in: `${src}/assets.js`, out: 'assets'},
    ...entryPoints,
  ],
  outdir: dst,
  assetNames: '[dir]/[name].[hash]',
  chunkNames: 'chunks/[name].[hash]',
  entryNames: '[name].[hash]',

  loader: {
    '.xml': 'copy',
    '.png': 'copy',
    '.ico': 'copy',
    '.svg': 'copy'
  },

  inject: [path.join(src, "inject-jquery.js")],
  plugins: [{name: "manifest", setup(build){
    build.onEnd(result => generateManifest(result, src, dst))}
  }]
})

// for debug purposes
// fs.writeFileSync(path.join(dst, "meta.json"), JSON.stringify(result.metafile))

// cleanup jobs: turn `result.metafile` into manifest.
function generateManifest(result, src, dst) {
  const outs = result.metafile.outputs

  let entries = {}
  for (const [outname_, outprops] of Object.entries(outs)) {
    const outname = rebase(outname_, src, dst)
    const entry = deriveEntryName(outname, outprops)
    if (entry !== undefined) {
      entries[entry] = outname
    }
  }
  fs.writeFileSync(path.join(dst, "manifest.json"), JSON.stringify(entries))
}

function deriveEntryName(outname, outprops) {
  const {entryPoint, inputs: inputs_} = outprops
  const inputs = inputs_ !== undefined ? Object.keys(inputs_) : undefined
  if (outname.endsWith('.map')) {
    return null
  }
  if (entryPoint !== undefined) {
    return entryPoint.replace(/^js\//, "").replace(/\.ts$/, ".js")
  }
  else if (outname.match(/main\..*\.css/)) {
    return "main.css"
  }
  else if (inputs !== undefined && inputs.length == 1) {
    return inputs[0]
  }
  else {
    throw Error(`output asset ${outname} has no entrypoint and has no unique input (inputs: ${inputs})`)
  }
}

/**
* Given a path relative to `base_old`, derive a presentation relative to `base_new`.
*/
function rebase(p, base_old, base_new) {
  const abs = path.normalize(path.join(base_old, p));
  return path.relative(base_new, abs)
}

