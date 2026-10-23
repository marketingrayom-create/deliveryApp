import {test} from 'node:test';
import assert from 'node:assert/strict';
import {parseInvoicePages} from '../services/invoiceParser.js';
import {portalKey,portalName} from '../utils/importIdentity.js';
import {inventoryPermissions} from '../middleware/inventoryPermissions.js';
import {databaseRecord} from '../utils/shipmentRecords.js';

const item=(text,x,y,page=1)=>({text,x,y,page});
function fixture(){
 const pages=[[
  item('Invoice No:',191,218),item('TEST001',191,233),item('Invoice Date',413,218),item('02-Oct-2026',413,233),
  item('EXAMPLE BUSINESS',24,218),item('PRIVATE LIMITED',24,233),item('Company address',24,248),
  item('Order No: PO001',250,278),item('Order Date: 01-Oct-2026',244,293),item('Portal:',413,278),item('B2B_COCOBLU',444,278),
  item('Bill To:',24,358),item('COCOBLU RETAIL LIMITED',24,373),item('Ship To:',191,358),item('COCOBLU RETAIL LIMITED',191,373),
  item('DED5,',191,388),item('GURUGRAM 122103, India',191,433),item('Box Count :',413,463),item('4',472,463),
  item('Channel Product ID',299,519),item('Qty',398,519)
 ],[]];
 const amounts=[['100','984.51','98451.0','17721.18','116172.1','8'],['100','1863.7','186373.','33547.14','219920.1','4']];
 for(let index=0;index<2;index++){
  const page=index+1,y=index?36:563;const values=amounts[index];
  pages[index].push(item(String(index+1),22,y,page),item('Generic product '+index,44,y,page),item('Continued title',44,y+14,page),item('B00000000'+(index+1),307,y,page),
   item('HSN code:',183,y+19,page),item('850760',231,y+19,page),item('Seller Sku Code :',183,y+35,page),item('SKU_'+index,183,y+51,page),item('EAN :',183,y+67,page),item('123456789012'+index,210,y+67,page));
  [395,418,452,491,535].forEach((x,column)=>pages[index].push(item(values[column],x,y,page)));
  pages[index].push(item(index?'3':'',440,y+14,page),item(index?'00':'0',479,y+14,page),item('(18.0) %',495,y+14,page),item(values[5],568,y+14,page));
 }
 pages[1].push(item('Total:',46,200,2),item('200',397,200,2),item('284824.',454,200,2),item('00',476,214,2),item('51268.32',493,200,2),item('336092.3',537,200,2),item('2',570,214,2));
 return pages;
}
test('multi-page invoice reconstructs wrapped money and maps Master plus Merge',()=>{
 const extracted=parseInvoicePages(fixture());
 assert.equal(extracted.master.length,1);assert.equal(extracted.merge.length,2);
 assert.equal(extracted.master[0].Company,'EXAMPLE BUSINESS PRIVATE LIMITED');
 assert.equal(extracted.master[0].Portal,'Cocoblu (CB)');assert.equal(extracted.master[0]['Invoice Date'],'2026-10-02');
 assert.equal(extracted.master[0].Location,'GURUGRAM');assert.equal(extracted.master[0]['Vendor Code/ Shipment Id'],'DED5');
 assert.equal(extracted.master[0].Qty,200);assert.equal(extracted.master[0]['Invoice Value'],336092.32);
 assert.equal(extracted.merge[1]['Unit Cost'],1863.73);assert.equal(extracted.merge[1]['Total Amount'],219920.14);
 assert.equal(extracted.merge[0]['SKU Code'],'SKU_0');assert.equal(extracted.merge[0].IGST,18);
 const mapping={companyId:'company',portalId:'portal'};
 const a=databaseRecord('master',extracted.master[0],mapping);
 const b=databaseRecord('merge',extracted.merge[0],mapping);
 assert.equal(a.shipmentKey,b.shipmentKey);
 assert.equal(b.recordKey,databaseRecord('merge',extracted.merge[0],mapping).recordKey);
});
test('Bill To Cocoblu is a fallback when the portal label is absent',()=>{
 const pages=fixture();pages[0]=pages[0].filter(item=>!['Portal:','B2B_COCOBLU'].includes(item.text));
 assert.equal(parseInvoicePages(pages).master[0].Portal,'Cocoblu (CB)');
});
test('mismatched totals reject the whole invoice before importing',()=>{
 const pages=fixture();pages[1].find(item=>item.text==='51268.32').text='999';
 assert.throws(()=>parseInvoicePages(pages),/printed invoice totals/);
 assert.throws(()=>parseInvoicePages([[]]),/Invoice date/);
});
test('Cocoblu aliases resolve to one portal identity',()=>{
 for(const alias of ['B2B_COCOBLU','Cocoblu','COCOBLU RETAIL LIMITED','cocoblu (cb)','CB']){
  assert.equal(portalName(alias),'Cocoblu (CB)');assert.equal(portalKey(alias),portalKey('Cocoblu (CB)'));
 }
});
test('invoice extraction preserves existing user permissions',()=>{
 for(const role of ['visitor','executive','admin','super_admin']){
  const res={status(code){this.code=code;return this;},json(body){this.body=body;}};let allowed=false;
  inventoryPermissions({user:{role},method:'POST',path:'/invoices/extract'},res,()=>{allowed=true;});
  assert.equal(allowed,role!=='visitor');if(role==='visitor')assert.equal(res.code,403);
 }
});
