#!/usr/bin/env node
import React from 'react';
import { render } from 'ink';
import { App } from './components/App.js';

// Welcome message
console.clear();
console.log('\x1b[34m');
console.log('╔═══════════════════════════════════════════════════════════╗');
console.log('║                                                           ║');
console.log('║     ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗              ║');
console.log('║     ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝              ║');
console.log('║     ██║███████║██████╔╝██║   ██║██║███████╗              ║');
console.log('║██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║              ║');
console.log('║╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║              ║');
console.log('║ ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝              ║');
console.log('║                                                           ║');
console.log('║     Just A Rather Very Intelligent System                 ║');
console.log('║     Powered by Claude Code                                ║');
console.log('║                                                           ║');
console.log('╚═══════════════════════════════════════════════════════════╝');
console.log('\x1b[0m');

render(<App />);
