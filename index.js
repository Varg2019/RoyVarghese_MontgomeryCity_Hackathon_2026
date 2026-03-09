const fs = require('fs');

const raw = fs.readFileSync('data.json', 'utf8');
const data = JSON.parse(raw);

console.log(data);