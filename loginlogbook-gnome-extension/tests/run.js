import system from 'system';
import { report, runAll } from './harness.js';
import './metadata.test.js';
import './config.test.js';
import './models.test.js';
import './store.test.js';
await runAll();
system.exit(report());
