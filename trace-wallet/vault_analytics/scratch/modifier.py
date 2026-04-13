import re

with open('index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Update boot() to include welcome logic
text = text.replace('function boot() { syncData(); loadSettings(); navigate(\'command\'); startSessionTimer(); }', 
    '''function boot() { 
    syncData(); 
    loadSettings(); 
    navigate('command'); 
    startSessionTimer(); 
    setTimeout(() => {
        if (!VS.settings.has_shown_welcome) showWelcomeModal();
    }, 1000);
}''')

# 2. Update renderLedgerList to include the detail drawer
ledger_func_start = text.find('function renderLedgerList')
if ledger_func_start != -1:
    end_of_func = text.find('}', text.find('document.getElementById(\\'ledger-list\\').innerHTML = html;', ledger_func_start)) + 1
    new_ledger = '''function renderLedgerList(txs) {
    const list = document.getElementById('ledger-list');
    if (txs.length === 0) { list.innerHTML = '<div class=\"text-center py-10 text-on-surface-variant font-bold\">No transactions found.</div>'; return; }
    
    let html = '';
    txs.forEach(tx => {
        const cColor = tx.type === 'Income' ? 'bg-on-tertiary-container/20 text-on-tertiary-container' : 'bg-primary/10 text-primary dark:text-blue-300';
        const sign = tx.type === 'Income' ? '+' : '-';
        const amtColor = tx.type === 'Income' ? 'text-on-tertiary-container' : 'text-on-surface dark:text-slate-100';
        
        const dt = new Date(tx.date);
        const tf = dt.toLocaleTimeString('en-US',{hour:'numeric',minute:'2-digit'});
        
        let badges = '';
        if(tx.ghost_fee) badges += '<span class=\"bg-violet-500 text-white text-[8px] font-bold px-1.5 py-0.5 rounded uppercase ml-2\">Ghost Fee</span>';
        if(tx.is_anomaly) badges += '<span class=\"bg-error text-white text-[8px] font-bold px-1.5 py-0.5 rounded uppercase ml-2 shadow-[0_0_10px_rgba(255,0,0,0.5)]\">Anomaly</span>';
        
        const icon = (VS.settings.category_icons && VS.settings.category_icons[tx.category]) ? VS.settings.category_icons[tx.category] : 'receipt_long';
        
        html += `
        <div class=\"border-b border-outline-variant/10 dark:border-slate-800 last:border-0 hover:bg-surface-container/50 dark:hover:bg-slate-800/50 transition-colors cursor-pointer group rounded-xl p-1\" onclick=\"renderLedgerDetail(${tx.id})\">
            <div class=\"flex items-center justify-between p-4\">
                <div class=\"flex items-center gap-4\">
                    <div class=\"w-10 h-10 rounded-full flex items-center justify-center font-bold relative overflow-hidden ${cColor}\">
                        <div class=\"absolute inset-0 opacity-20 bg-current\"></div>
                        <span class=\"material-symbols-outlined text-[18px] relative z-10\">${icon}</span>
                    </div>
                    <div>
                        <p class=\"font-bold font-headline text-sm tracking-tight\">${tx.description||tx.merchant||'Unknown'}${badges}</p>
                        <p class=\"text-[10px] uppercase font-bold text-on-surface-variant mt-0.5\">${tx.category} • ${tf}</p>
                    </div>
                </div>
                <div class=\"text-right\">
                    <p class=\"font-headline font-extrabold text-lg ${amtColor}\">${sign}$${parseFloat(tx.amount).toLocaleString('en-US',{minimumFractionDigits:2})}</p>
                </div>
            </div>
            
            <!-- EXPANABLE DETAIL DRAWER -->
            <div id=\"tx-detail-${tx.id}\" class=\"tx-detail-drawer hidden overflow-hidden px-4 pb-4 animate-in slide-in-from-top-2 fade-in duration-300\">
                <div class=\"p-6 rounded-2xl bg-surface-container dark:bg-slate-900 border border-outline-variant/20 dark:border-slate-700 shadow-inner grid grid-cols-2 md:grid-cols-4 gap-6\">
                    <div>
                        <p class=\"text-[9px] uppercase tracking-widest font-bold text-on-surface-variant mb-1\">AI Confidence</p>
                        <div class=\"flex items-center gap-2\">
                            <div class=\"w-2 h-2 rounded-full ${tx.is_anomaly ? 'bg-error' : 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.5)]'}\"></div>
                            <span class=\"text-xs font-bold\">${tx.is_anomaly ? 'LOW (Needs Review)' : 'HIGH'}</span>
                        </div>
                    </div>
                    <div>
                        <p class=\"text-[9px] uppercase tracking-widest font-bold text-on-surface-variant mb-1\">Source Bank</p>
                        <p class=\"text-xs font-bold\">${tx.bank || 'Manual Entry'}</p>
                    </div>
                    <div>
                        <p class=\"text-[9px] uppercase tracking-widest font-bold text-on-surface-variant mb-1\">Extracted Fees / VAT</p>
                        <p class=\"text-xs font-bold text-error\">$${(parseFloat(tx.fee||0) + parseFloat(tx.vat||0)).toFixed(2)}</p>
                    </div>
                    <div class=\"flex items-center justify-end gap-2\">
                        <button onclick=\"event.stopPropagation(); openEntryModal(${tx.id})\" class=\"bg-primary text-white px-4 py-2 rounded-xl text-xs font-bold inline-flex items-center gap-1 hover:brightness-110 press-effect\"><span class=\"material-symbols-outlined text-[16px]\">edit</span> Deep Edit</button>
                    </div>
                    <div class=\"col-span-2 md:col-span-4 mt-2 pt-4 border-t border-outline-variant/10 dark:border-slate-700\">
                        <p class=\"text-[9px] uppercase tracking-widest font-bold text-on-surface-variant mb-2\">Raw Payload Data</p>
                        <p class=\"font-mono text-[10px] text-slate-500 overflow-x-auto break-all\">${JSON.stringify({id:tx.id, src:tx.source, acc:tx.account, merchant:tx.merchant})}</p>
                    </div>
                </div>
            </div>
        </div>`;
    });
    list.innerHTML = html;
}'''
    text = text[:ledger_func_start] + new_ledger + text[end_of_func:]

# 3. Add Category Building UI in Settings
cat_html = '''
            <!-- Custom Categories -->
            <section class="bg-surface-container-lowest dark:bg-slate-900 border border-outline-variant/10 dark:border-slate-800 rounded-3xl p-8 shadow-sm">
                <div class="flex items-center justify-between mb-6 border-b border-slate-100 dark:border-slate-800 pb-4">
                    <div class="flex items-center gap-3"><span class="material-symbols-outlined text-primary dark:text-blue-300">category</span><h3 class="font-headline font-bold text-lg">Custom Categories</h3></div>
                    <button onclick="promptCustomCategory()" class="text-xs font-bold bg-primary/10 text-primary px-3 py-1.5 rounded-full flex items-center gap-1 press-effect"><span class="material-symbols-outlined text-sm">add</span> Add Category</button>
                </div>
                <div id="category-settings-list" class="flex flex-wrap gap-3">
                    <p class="text-sm text-on-surface-variant text-center py-4 w-full">No custom categories yet. Start building your own tags.</p>
                </div>
            </section>
'''
text = text.replace('<!-- Parser Studio -->', cat_html + '\n            <!-- Parser Studio -->')

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(text)

print("HTML modifications applied.")
