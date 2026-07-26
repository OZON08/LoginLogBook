import system from 'system';
import { report } from './harness.js';
import './metadata.test.js';
import './config.test.js';
import './models.test.js';
system.exit(report());
