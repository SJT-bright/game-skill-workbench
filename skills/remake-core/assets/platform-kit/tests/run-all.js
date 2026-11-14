'use strict';
// Maintenance guide: ../../../references/platform-suite-records.md
// One aggregate entry; child observations are produced once and consumed by input identity.
try { require('./suite-runner.cjs').main(); }
catch (error) { console.error(error.stack); process.exitCode = 2; }
