const fs = require('fs');
const https = require('https');

https.get('https://raw.githubusercontent.com/jossy-dude/Trace-Wallet/main/vault_pro/python/parser.py', (res) => {
  let data = '';
  res.on('data', (chunk) => data += chunk);
  res.on('end', () => {
    fs.writeFileSync('parser.py', data);
    console.log('Done parser');
  });
});
