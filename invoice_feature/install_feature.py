from pathlib import Path
import shutil

base=Path(r'F:\rajat soni')
backend=base/'Inventory_backend'
frontend=base/'latest_inventory'
source=Path(__file__).parent
for name,target in [('invoiceParser.js',backend/'services'/'invoiceParser.js'),('invoiceRoutes.js',backend/'Routes'/'invoiceRoutes.js'),('invoiceService.js',frontend/'src'/'services'/'invoiceService.js'),('InvoiceUploadModal.jsx',frontend/'src'/'components'/'import'/'InvoiceUploadModal.jsx')]:
 shutil.copyfile(source/name,target)
p=backend/'Server.js';s=p.read_text(encoding='utf-8')
if "import invoiceRoutes from" not in s:s="import invoiceRoutes from './Routes/invoiceRoutes.js';\n"+s
if "app.use('/api/invoices'" not in s:s=s.replace("app.use('/api', inventoryPermissions);","app.use('/api', inventoryPermissions);\napp.use('/api/invoices', invoiceRoutes);")
p.write_text(s,encoding='utf-8')
p=backend/'middleware'/'inventoryPermissions.js';s=p.read_text(encoding='utf-8').replace("'/shipment-records/import', '/shipment-records/import/preview', '/portal/resolve-import'","'/shipment-records/import', '/shipment-records/import/preview', '/portal/resolve-import', '/invoices/extract'");p.write_text(s,encoding='utf-8')
p=frontend/'src'/'App.jsx';s=p.read_text(encoding='utf-8')
if 'import InvoiceUploadModal' not in s:s="import InvoiceUploadModal from './components/import/InvoiceUploadModal.jsx';\n"+s
if 'async function importInvoice(' not in s:
 pos=s.index('  const scopedActive =')
 s=s[:pos]+'''  async function importInvoice(invoice, newOnly = true) {
    if (!recordsReady || recordsLoading || migrating) throw new Error('Wait for database records to load before importing.');
    const preserveExisting = user.role === 'executive' || newOnly;
    let masterResult;
    try {
      masterResult = await importShipmentRecords('master', invoice.master, preserveExisting);
      const mergeResult = await importShipmentRecords('merge', invoice.merge, preserveExisting);
      await inventory.loadCompanies();
      commit({ selectedCompany: invoice.master[0].Company });
      await loadPortals(selectedCompanyId);
      setView('master'); setScreen('shipments'); setPortal('All portals');
      setImportVersion(value => value + 1);
      await loadRecords();
      closeModal();
      setMessage(`Invoice saved. Master: ${masterResult.added} added, ${masterResult.updated} updated. Merge: ${mergeResult.added} added, ${mergeResult.updated} updated. Switch to Merge to see product lines.`);
    } catch (error) {
      if (masterResult) throw new Error(`Master was saved. Merge or refresh failed: ${error.message} Retry this invoice; existing rows will not be duplicated.`);
      throw error;
    }
  }

'''+s[pos:]
if "setModal({ type: 'invoice' })" not in s:s=s.replace('<div className="page-actions">','<div className="page-actions">\n              <button className="button secondary" disabled={!canUpload || !recordsReady || recordsLoading} onClick={() => setModal({ type: \'invoice\' })}>↥ Upload Invoice PDF</button>')
if "modal?.type === 'invoice'" not in s:s=s.replace('{canUpload && modal?.type === "upload" && (', "{canUpload && modal?.type === 'invoice' && <InvoiceUploadModal user={user} onClose={closeModal} onPreview={previewExcelImport} onImport={importInvoice} />}\n\n      {canUpload && modal?.type === \"upload\" && (")
p.write_text(s,encoding='utf-8')
print('Invoice feature installed in both projects')
