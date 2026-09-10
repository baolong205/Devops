const fs = require('node:fs');
const path = require('node:path');

const source = path.join(__dirname, '..', 'index.html');
const targetDirectory = path.join(__dirname, '..', 'public');
const target = path.join(targetDirectory, 'index.html');

fs.mkdirSync(targetDirectory, { recursive: true });
fs.copyFileSync(source, target);
console.log(`Copied ${source} to ${target}`);