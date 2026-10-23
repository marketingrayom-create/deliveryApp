import {test} from 'node:test';
import assert from 'node:assert/strict';
import {extractInvoice} from '../src/services/invoiceService.js';
import {portalKey} from '../src/utils/importIdentity.js';
test('invoice PDF uses authenticated API helper and multipart body',async t=>{
 t.mock.method(globalThis,'fetch',async(url,options)=>{
  assert.equal(url,'/api/invoices/extract');assert.equal(options.method,'POST');assert.equal(options.credentials,'include');
  assert.ok(options.body instanceof FormData);assert.equal(options.body.get('invoice').name,'invoice.pdf');
  assert.equal(options.headers.has('Content-Type'),false);
  return new Response(JSON.stringify({success:true,data:{master:[{'Invoice Number':'TEST001'}],merge:[]}}),{status:200,headers:{'Content-Type':'application/json'}});
 });
 const result=await extractInvoice(new File(['%PDF- test'],'invoice.pdf',{type:'application/pdf'}));
 assert.equal(result.master[0]['Invoice Number'],'TEST001');
});
test('extraction failures do not become successful imports',async t=>{
 t.mock.method(globalThis,'fetch',async()=>new Response(JSON.stringify({message:'Invoice totals do not match'}),{status:422,headers:{'Content-Type':'application/json'}}));
 await assert.rejects(extractInvoice(new File(['test'],'invoice.pdf')),/totals do not match/);
});
test('invoice portal aliases use existing Cocoblu portal',()=>{
 assert.equal(portalKey('B2B_COCOBLU'),portalKey('Cocoblu (CB)'));
 assert.equal(portalKey('COCOBLU RETAIL LIMITED'),portalKey('CB'));
});
