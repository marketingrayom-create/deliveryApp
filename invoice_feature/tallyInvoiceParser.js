import {badRequest,validateRecord} from '../utils/shipmentRecords.js';
import {portalName} from '../utils/importIdentity.js';
export function parseTallyInvoice(pages,filename='') {
 const all=pages.flat().sort((a,b)=>a.page-b.page||a.y-b.y||a.x-b.x);
 const find=pattern=>all.find(item=>pattern.test(item.text));
 const money=text=>{
  const raw=String(text).replace(/[₹,\s]/g,'');
  if(!/^-?\d+(?:\.\d+)?$/.test(raw))throw badRequest('Unreadable invoice amount.');
  return Number(raw);
 };
 const below=label=>label?all.find(item=>item.page===label.page&&item.y>label.y+3&&item.y<label.y+23&&Math.abs(item.x-label.x)<6)?.text||'':'';
 const invoiceLabel=find(/^Invoice No\.$/i),invoice=below(invoiceLabel);
 const dated=all.find(item=>item.page===invoiceLabel?.page&&Math.abs(item.y-invoiceLabel.y)<3&&item.text==='Dated');
 const match=below(dated).match(/^(\d{1,2})-([A-Za-z]{3})-(\d{2}|\d{4})$/);
 const months=['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'];
 const month=match?months.indexOf(match[2].toLowerCase())+1:0;
 if(!invoice||!month)throw badRequest('Invoice number/date could not be read in this invoice.');
 const year=match[3].length===2?'20'+match[3]:match[3];
 const invoiceDate=`${year}-${String(month).padStart(2,'0')}-${match[1].padStart(2,'0')}`;
 if(new Date(invoiceDate).toISOString().slice(0,10)!==invoiceDate)throw badRequest('Invalid invoice date.');
 const company=all.find(item=>item.page===1&&item.x<invoiceLabel.x-20&&item.y<invoiceLabel.y+12&&/\b(?:Ltd|Limited)\b/i.test(item.text))?.text;
 const buyer=below(find(/^Buyer \(Bill to\)$/i));
 const consignee=find(/^Consignee \(Ship to\)$/i);
 const address=all.filter(item=>item.page===consignee?.page&&item.x<invoiceLabel.x-10&&item.y>consignee.y&&item.y<consignee.y+90);
 const location=address.find(item=>/\d{6}/.test(item.text)&&/ - /.test(item.text))?.text.replace(/\s*-\s*\d{6}.*$/,'')||'';
 const state=address.find(item=>/^:\s*.*Code\s*:/i.test(item.text))?.text.replace(/^:\s*/,'').replace(/,?\s*Code\s*:.*$/,'')||'';
 if(!company||!buyer)throw badRequest('Seller or buyer could not be read.');
 const common={Company:company,Portal:portalName(buyer),'PO Number':below(find(/^Buyer's Order No\.$/i)),'Invoice Number':invoice,'Invoice Date':invoiceDate,Location:location,'Import Source':'Invoice PDF'};
 const header=find(/^Description of Goods$/i);
 const hsnHeader=all.find(item=>item.page===header?.page&&Math.abs(item.y-header.y)<3&&item.text==='HSN/SAC');
 const qtyHeader=find(/^Quantity$/i),rateHeader=find(/^Rate$/i),amountHeader=find(/^Amount$/i);
 if(!header||!hsnHeader||!qtyHeader||!rateHeader||!amountHeader)throw badRequest('Product table is incomplete.');
 const starts=all.filter(item=>item.x<=50&&/^\d+$/.test(item.text)&&item.y>header.y+15)
  .filter(item=>all.some(other=>other.page===item.page&&Math.abs(other.y-item.y)<4&&/\d[\d,]*\s+PCS$/i.test(other.text)));
 // Continuation pages can restart near the top, after their own repeated table header.
 if(!starts.length)throw badRequest('No readable product lines found.');
 const summaryHeader=all.find(item=>item.text==='HSN/SAC'&&item.y>header.y+100);
 const taxRows=summaryHeader?all.filter(item=>item.page===summaryHeader.page&&item.y>summaryHeader.y+12&&item.y<summaryHeader.y+80&&item.x<summaryHeader.x&&/^\d{4,8}$/.test(item.text)):[];
 const taxByHsn=new Map();
 for(const row of taxRows){
  const cells=all.filter(item=>item.page===row.page&&Math.abs(item.y-row.y)<3);
  const taxable=cells.find(item=>item.x>=qtyHeader.x-20&&item.x<rateHeader.x-10&&/^[\d,.]+$/.test(item.text));
  const rate=cells.find(item=>/%$/.test(item.text));
  const tax=cells.find(item=>item.x>=rateHeader.x+10&&item.x<amountHeader.x-10&&/^[\d,.]+$/.test(item.text));
  if(!taxable||!rate||!tax)throw badRequest('Tax summary could not be read.');
  taxByHsn.set(row.text,{taxable:money(taxable.text),tax:money(tax.text),rate:money(rate.text.replace('%',''))});
 }
 const merge=starts.map((start,index)=>{
  const next=starts[index+1];
  const region=all.filter(item=>item.page>=start.page&&(!next||item.page<=next.page)&&(item.page!==start.page||item.y>=start.y-3)&&(!next||item.page!==next.page||item.y<next.y-3));
  const cells=region.filter(item=>item.page===start.page&&Math.abs(item.y-start.y)<4);
  const hsn=cells.find(item=>item.x>=hsnHeader.x-4&&item.x<qtyHeader.x-10&&/^\d{4,8}$/.test(item.text))?.text||'';
  const qty=cells.find(item=>/\d[\d,]*\s+PCS$/i.test(item.text));
  const rate=cells.find(item=>item.x>=rateHeader.x-7&&item.x<rateHeader.x+25&&/^[\d,.]+$/.test(item.text));
  const amount=cells.find(item=>item.x>=amountHeader.x-10&&/^[\d,.]+$/.test(item.text));
  const meta=region.find(item=>item.x<hsnHeader.x&&/EAN.*ASIN/i.test(item.text));
  const title=region.filter(item=>item.page===start.page&&item.x>50&&item.x<hsnHeader.x-10&&item.y<=(meta?.y??start.y+110)&&!/EAN.*ASIN/i.test(item.text)).map(item=>item.text).join(' ');
  if(!qty||!rate||!amount||!title||!meta)throw badRequest('An invoice product line is incomplete.');
  return validateRecord('merge',{...common,'Product Name':title,ASIN:meta.text.match(/ASIN\s+([A-Z0-9]{10})/i)?.[1]||'',EAN:meta.text.match(/EAN\s+(\d{8,14})/i)?.[1]||'','SKU Code':'','HSN Code':hsn,
   Qty:money(qty.text.replace(/PCS/i,'')),'Unit Cost':money(rate.text),'Total Cost':money(amount.text),IGST:taxByHsn.get(hsn)?.rate??null,CGST:null,SGST:null,'IGST Amount':null,'Total Amount':null});
 });
 const taxable=merge.reduce((sum,row)=>sum+row['Total Cost'],0),qty=merge.reduce((sum,row)=>sum+row.Qty,0);
 const summaryTaxable=[...taxByHsn.values()].reduce((sum,row)=>sum+row.taxable,0),tax=[...taxByHsn.values()].reduce((sum,row)=>sum+row.tax,0);
 if(!taxByHsn.size||Math.abs(taxable-summaryTaxable)>0.02)throw badRequest('Product amounts do not match the tax summary.');
 const totalLabel=all.find(item=>/^Total$/i.test(item.text)&&all.some(other=>other.page===item.page&&Math.abs(other.y-item.y)<5&&/₹/.test(other.text)));
 const totalCells=all.filter(item=>item.page===totalLabel?.page&&Math.abs(item.y-totalLabel.y)<5);
 const totalText=totalCells.find(item=>/₹/.test(item.text))?.text;
 const qtyText=totalCells.find(item=>/PCS$/i.test(item.text))?.text;
 const roundLabel=find(/^Round Off$/i),roundCell=all.find(item=>item.page===roundLabel?.page&&Math.abs(item.y-roundLabel.y)<3&&item.x>amountHeader.x&&/^-?[\d,.]+$/.test(item.text));
 const round=roundCell?money(roundCell.text):0;
 if(!totalText||!qtyText||qty!==money(qtyText.replace(/PCS/i,''))||Math.abs(taxable+tax+round-money(totalText))>0.02)throw badRequest('Invoice totals do not reconcile.');
 const boxes=find(/^Box Count[-:]\s*\d+/i)?.text.match(/\d+/)?.[0];
 return {filename,master:[validateRecord('master',{...common,State:state,Qty:qty,Parcel:boxes?Number(boxes):null,'Without Tax Amount':Number(taxable.toFixed(2)),'Tax Amount':tax,'Invoice Value':money(totalText),'Round Off':round})],merge,
  warnings:['Tax is printed in the invoice summary. Per-product IGST amounts and tax-inclusive totals are not printed, so those fields remain blank. Review before saving.']};
}
