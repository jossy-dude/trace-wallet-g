async function download() {
  const res = await fetch('https://raw.githubusercontent.com/jossy-dude/Trace-Wallet/main/README.md');
  const text = await res.text();
  require('fs').writeFileSync('README_repo.md', text);
  
  const res2 = await fetch('https://raw.githubusercontent.com/jossy-dude/Trace-Wallet/main/vault_pro/python/parser.py');
  const text2 = await res2.text();
  require('fs').writeFileSync('parser.py', text2);
  
  const res3 = await fetch('https://raw.githubusercontent.com/jossy-dude/Trace-Wallet/main/vault_pro/python/database.py');
  const text3 = await res3.text();
  require('fs').writeFileSync('database.py', text3);
  
  console.log('Downloaded files');
}
download();
