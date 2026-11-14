'use strict';
// Preserve the old JSON CLI while retaining the three separate legacy-context observations.
try {
  const runner=require('../suite-runner.cjs');
  const options=runner.parseArgs(process.argv.slice(2),{group:'snake-regression/run.js'});
  if(options===undefined)process.exit(0);
  const out=runner.run(options);
  console.log(JSON.stringify(out.value.results.map(r=>({file:r.id.split('@')[0].split('/').pop(),passed:r.passed,exit:r.exit,detail:r.action,receipt:r.receipt_path})),null,2));
  console.error('SUITE_LEDGER '+out.report+' '+out.sha256);
  process.exitCode=out.value.passed?0:1;
} catch(error) { console.error(error.stack);process.exitCode=2; }
