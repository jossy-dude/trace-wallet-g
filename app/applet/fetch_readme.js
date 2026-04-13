const fs = require('fs');
const https = require('https');

https.get('https://raw.githubusercontent.com/jossy-dude/Trace-Wallet/main/README.md', (res) => {
  let data = '';
  res.on('data', (chunk) => data += chunk);
  res.on('end', () => {
    fs.writeFileSync('README.md', data);
    console.log('Done');
  });
});
